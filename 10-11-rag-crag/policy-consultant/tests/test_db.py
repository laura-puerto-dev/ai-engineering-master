"""Integration tests for the connection layer (src/policy_consultant/db.py).

Every operation runs against the dedicated test database (TEST_DATABASE_NAME
from tests/conftest.py), passed explicitly to admin_connection()/
app_connection() — never the default .env target, which would be the
development database.
"""

from __future__ import annotations

from pathlib import Path

import psycopg
import pytest
from psycopg.pq import TransactionStatus

from policy_consultant.corpus_manifest import load_access_model
from policy_consultant.db import admin_connection, app_connection
from policy_consultant.models import AccessModel

pytestmark = pytest.mark.integration

TEST_DATABASE_NAME = "policy_consultant_test"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ACCESS_MODEL_PATH = PROJECT_ROOT / "config" / "access-model.yaml"

_DOCUMENTS = [
    # (document_id, country, allowed_roles)
    ("ES-001", "spain", ["employee", "manager", "hr"]),
    ("ES-006", "spain", ["manager", "hr"]),
    ("MX-001", "mexico", ["employee", "manager", "hr"]),
    ("GLB-001", "global", ["employee", "manager", "hr"]),
]


@pytest.fixture
def access_model() -> AccessModel:
    return load_access_model(ACCESS_MODEL_PATH)


@pytest.fixture
def seeded_documents(policy_app_ready: psycopg.Connection) -> None:
    """Seeds the real four-document scenario through admin_connection
    itself — exercising the module under test, not conftest's lower-
    level pg_connection directly — against the already-migrated test
    database (policy_app_ready only ensures that precondition).
    """
    with admin_connection(dbname=TEST_DATABASE_NAME) as conn:
        for document_id, country, allowed_roles in _DOCUMENTS:
            conn.execute(
                """
                INSERT INTO documents
                    (document_id, version, country, language, allowed_roles,
                     effective_from, path)
                VALUES (%s, '1.0', %s, 'es', %s, '2026-01-01', %s)
                """,
                (document_id, country, allowed_roles, f"data/corpus/{document_id}.md"),
            )
            conn.execute(
                """
                INSERT INTO chunks
                    (chunk_id, document_id, ordinal, section_path, text, embedding, model_id)
                VALUES (%s, %s, 0, ARRAY[]::text[], 'text', %s, 'fake-model')
                """,
                (f"{document_id}:1.0:0", document_id, [0.0] * 1024),
            )


# --- admin_connection --------------------------------------------------


def test_admin_connection_connects_as_the_admin_role(_test_database_ready: None) -> None:
    with admin_connection(dbname=TEST_DATABASE_NAME) as conn:
        row = conn.execute("SELECT current_user").fetchone()
        assert row is not None
        assert row[0] == "policy_consultant_admin"


def test_admin_connection_can_write_and_bypasses_rls(seeded_documents: None) -> None:
    with admin_connection(dbname=TEST_DATABASE_NAME) as conn:
        rows = conn.execute("SELECT document_id FROM documents ORDER BY document_id").fetchall()
    assert [row[0] for row in rows] == ["ES-001", "ES-006", "GLB-001", "MX-001"]


def test_admin_connection_closes_on_exit(_test_database_ready: None) -> None:
    with admin_connection(dbname=TEST_DATABASE_NAME) as conn:
        pass
    assert conn.closed


# --- app_connection: identity and RLS-scoped reads ----------------------


def test_app_connection_connects_as_policy_app(
    seeded_documents: None, access_model: AccessModel
) -> None:
    with app_connection(
        country="spain", role="employee", access_model=access_model, dbname=TEST_DATABASE_NAME
    ) as conn:
        row = conn.execute("SELECT current_user").fetchone()
        assert row is not None
        assert row[0] == "policy_app"


def test_app_connection_reads_only_authorized_rows(
    seeded_documents: None, access_model: AccessModel
) -> None:
    with app_connection(
        country="mexico", role="employee", access_model=access_model, dbname=TEST_DATABASE_NAME
    ) as conn:
        rows = conn.execute("SELECT document_id FROM documents ORDER BY document_id").fetchall()
    assert [row[0] for row in rows] == ["GLB-001", "MX-001"]


def test_app_connection_denies_unauthorized_country(
    seeded_documents: None, access_model: AccessModel
) -> None:
    with app_connection(
        country="mexico", role="employee", access_model=access_model, dbname=TEST_DATABASE_NAME
    ) as conn:
        visible = [row[0] for row in conn.execute("SELECT document_id FROM documents").fetchall()]
    assert "ES-001" not in visible
    assert "ES-006" not in visible


def test_app_connection_denies_unauthorized_role(
    seeded_documents: None, access_model: AccessModel
) -> None:
    with app_connection(
        country="spain", role="employee", access_model=access_model, dbname=TEST_DATABASE_NAME
    ) as conn:
        visible = [row[0] for row in conn.execute("SELECT document_id FROM documents").fetchall()]
    assert "ES-006" not in visible  # requires manager or hr


# --- app_connection: context validated before connecting ----------------


@pytest.mark.parametrize(
    ("country", "role", "match"),
    [
        ("", "employee", "country"),
        ("spain", "", "role"),
        ("atlantis", "employee", "Unrecognized country"),
        ("spain", "intern", "Unrecognized role"),
        ("global", "employee", "document scope"),
    ],
)
def test_app_connection_rejects_invalid_context_before_connecting(
    access_model: AccessModel, country: str, role: str, match: str
) -> None:
    with (
        pytest.raises(ValueError, match=match),
        app_connection(
            country=country, role=role, access_model=access_model, dbname=TEST_DATABASE_NAME
        ),
    ):
        pass


# --- app_connection: transaction lifetime, rollback, and no leakage ------


def test_app_connection_propagates_exceptions_from_within_an_open_transaction(
    seeded_documents: None, access_model: AccessModel
) -> None:
    """Confirms the caller's exception (a) occurs while a genuine,
    explicit transaction is open — TransactionStatus.INTRANS, not
    autocommit-per-statement — (b) propagates out of app_connection
    unchanged, and (c) leaves the connection closed, with a later,
    independent call unaffected.

    This does not, and with a strictly read-only role cannot, directly
    observe a ROLLBACK being issued as distinct from the connection
    simply closing with nothing committed: PostgreSQL discards
    uncommitted work identically either way, and policy_app never
    writes anything that could reveal a difference between the two.
    Rolling back on exception is psycopg3's own conn.transaction()
    guarantee, already well-tested library behavior — what this test
    verifies is that app_connection doesn't interfere with it.
    """

    class _Boom(Exception):
        pass

    held_conn: psycopg.Connection | None = None
    held_status: TransactionStatus | None = None
    with (
        pytest.raises(_Boom),
        app_connection(
            country="spain", role="employee", access_model=access_model, dbname=TEST_DATABASE_NAME
        ) as conn,
    ):
        held_conn = conn
        conn.execute("SELECT document_id FROM documents")
        held_status = conn.info.transaction_status
        raise _Boom("deliberate failure inside the block")

    assert held_status == TransactionStatus.INTRANS
    assert held_conn is not None
    assert held_conn.closed

    # A fresh, independent call afterward must work normally.
    with app_connection(
        country="spain", role="employee", access_model=access_model, dbname=TEST_DATABASE_NAME
    ) as conn:
        rows = conn.execute("SELECT document_id FROM documents ORDER BY document_id").fetchall()
    assert [row[0] for row in rows] == ["ES-001", "GLB-001"]


def test_successive_app_connections_do_not_leak_context(
    seeded_documents: None, access_model: AccessModel
) -> None:
    with app_connection(
        country="spain", role="employee", access_model=access_model, dbname=TEST_DATABASE_NAME
    ) as conn:
        rows = conn.execute("SELECT document_id FROM documents ORDER BY document_id").fetchall()
        spain_view = [row[0] for row in rows]

    with app_connection(
        country="mexico", role="employee", access_model=access_model, dbname=TEST_DATABASE_NAME
    ) as conn:
        rows = conn.execute("SELECT document_id FROM documents ORDER BY document_id").fetchall()
        mexico_view = [row[0] for row in rows]

    assert spain_view == ["ES-001", "GLB-001"]
    assert mexico_view == ["GLB-001", "MX-001"]


def test_app_connection_closes_on_exit(seeded_documents: None, access_model: AccessModel) -> None:
    with app_connection(
        country="spain", role="employee", access_model=access_model, dbname=TEST_DATABASE_NAME
    ) as conn:
        pass
    assert conn.closed
