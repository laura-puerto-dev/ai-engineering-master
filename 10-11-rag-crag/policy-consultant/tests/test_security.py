"""Integration tests for Row-Level Security (migrations/002_security.sql).

Every test authenticates as policy_app itself — never the superuser admin
connection — because policy_consultant_admin always bypasses RLS and
would prove nothing about the policies under test.

app.country and app.role are authorization context, not authentication:
these tests set them directly to simulate what a trusted backend would
do after authenticating a real identity. They say nothing about, and do
not substitute for, that authentication step.
"""

from __future__ import annotations

from pathlib import Path

import psycopg
import pytest

pytestmark = pytest.mark.integration

REAL_MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"

_DOCUMENTS = [
    # (document_id, country, allowed_roles)
    ("ES-001", "spain", ["employee", "manager", "hr"]),
    ("ES-006", "spain", ["manager", "hr"]),
    ("MX-001", "mexico", ["employee", "manager", "hr"]),
    ("GLB-001", "global", ["employee", "manager", "hr"]),
]


@pytest.fixture
def seeded_documents(policy_app_ready: psycopg.Connection) -> psycopg.Connection:
    """Seeds the real four-document scenario (one chunk each) as admin,
    using the actual country/role vocabulary from config/access-model.yaml
    rather than invented values. Returns the admin connection.
    """
    admin = policy_app_ready
    for document_id, country, allowed_roles in _DOCUMENTS:
        admin.execute(
            """
            INSERT INTO documents
                (document_id, version, country, language, allowed_roles, effective_from, path)
            VALUES (%s, '1.0', %s, 'es', %s, '2026-01-01', %s)
            """,
            (document_id, country, allowed_roles, f"data/corpus/{document_id}.md"),
        )
        admin.execute(
            """
            INSERT INTO chunks
                (chunk_id, document_id, ordinal, section_path, text, embedding, model_id)
            VALUES (%s, %s, 0, ARRAY[]::text[], 'text', %s, 'fake-model')
            """,
            (f"{document_id}:1.0:0", document_id, [0.0] * 1024),
        )
    return admin


def _visible_document_ids(
    conn: psycopg.Connection, *, country: str | None, role: str | None
) -> list[str]:
    with conn.transaction():
        if country is not None:
            conn.execute("SELECT set_config('app.country', %s, true)", (country,))
        if role is not None:
            conn.execute("SELECT set_config('app.role', %s, true)", (role,))
        rows = conn.execute("SELECT document_id FROM documents ORDER BY document_id").fetchall()
    return [row[0] for row in rows]


def _visible_chunk_ids(
    conn: psycopg.Connection, *, country: str | None, role: str | None
) -> list[str]:
    with conn.transaction():
        if country is not None:
            conn.execute("SELECT set_config('app.country', %s, true)", (country,))
        if role is not None:
            conn.execute("SELECT set_config('app.role', %s, true)", (role,))
        rows = conn.execute("SELECT chunk_id FROM chunks ORDER BY chunk_id").fetchall()
    return [row[0] for row in rows]


# --- Documents: country and role scoping ---------------------------------


def test_allows_access_to_documents_of_the_users_own_country(
    seeded_documents: psycopg.Connection, policy_app_connection: psycopg.Connection
) -> None:
    visible = _visible_document_ids(policy_app_connection, country="spain", role="employee")
    assert visible == ["ES-001", "GLB-001"]


def test_allows_access_to_global_documents_regardless_of_country(
    seeded_documents: psycopg.Connection, policy_app_connection: psycopg.Connection
) -> None:
    visible = _visible_document_ids(policy_app_connection, country="england", role="employee")
    assert visible == ["GLB-001"]


def test_denies_access_to_documents_of_other_countries(
    seeded_documents: psycopg.Connection, policy_app_connection: psycopg.Connection
) -> None:
    visible = _visible_document_ids(policy_app_connection, country="mexico", role="employee")
    assert visible == ["GLB-001", "MX-001"]
    assert "ES-001" not in visible
    assert "ES-006" not in visible


def test_denies_access_when_role_is_not_authorized(
    seeded_documents: psycopg.Connection, policy_app_connection: psycopg.Connection
) -> None:
    visible = _visible_document_ids(policy_app_connection, country="spain", role="employee")
    assert "ES-006" not in visible  # ES-006 requires manager or hr


# --- Fail-closed: missing, empty, or unknown context ----------------------


@pytest.mark.parametrize(
    ("country", "role"),
    [
        ("spain", None),
        (None, "employee"),
        (None, None),
    ],
)
def test_denies_all_access_when_country_or_role_is_missing(
    seeded_documents: psycopg.Connection,
    policy_app_connection: psycopg.Connection,
    country: str | None,
    role: str | None,
) -> None:
    assert _visible_document_ids(policy_app_connection, country=country, role=role) == []


@pytest.mark.parametrize(
    ("country", "role"),
    [
        ("", "employee"),
        ("spain", ""),
        ("", ""),
    ],
)
def test_denies_all_access_when_context_values_are_empty_strings(
    seeded_documents: psycopg.Connection,
    policy_app_connection: psycopg.Connection,
    country: str,
    role: str,
) -> None:
    assert _visible_document_ids(policy_app_connection, country=country, role=role) == []


def test_denies_access_with_unknown_country(
    seeded_documents: psycopg.Connection, policy_app_connection: psycopg.Connection
) -> None:
    # access_context_is_set() validates app.country against the real
    # *user*-country vocabulary (spain, mexico, england) — an
    # unrecognized value denies everything, including global documents.
    visible = _visible_document_ids(policy_app_connection, country="france", role="employee")
    assert visible == []


def test_denies_access_when_country_is_the_global_sentinel_itself(
    seeded_documents: psycopg.Connection, policy_app_connection: psycopg.Connection
) -> None:
    # 'global' is a document scope, not a valid user country — a context
    # that claims it must be denied like any other unrecognized value,
    # not accidentally accepted because it happens to equal the sentinel.
    visible = _visible_document_ids(policy_app_connection, country="global", role="employee")
    assert visible == []


def test_denies_access_with_unknown_role(
    seeded_documents: psycopg.Connection, policy_app_connection: psycopg.Connection
) -> None:
    # An unrecognized role matches no document's allowed_roles — not even
    # a global one, since role authorization never has a wildcard.
    visible = _visible_document_ids(policy_app_connection, country="spain", role="intern")
    assert visible == []


# --- Chunks follow their document's visibility -----------------------------


def test_chunks_are_protected_the_same_way_as_their_document(
    seeded_documents: psycopg.Connection, policy_app_connection: psycopg.Connection
) -> None:
    visible = _visible_chunk_ids(policy_app_connection, country="mexico", role="employee")
    assert visible == ["GLB-001:1.0:0", "MX-001:1.0:0"]


def test_chunks_of_an_unauthorized_document_remain_hidden(
    seeded_documents: psycopg.Connection, policy_app_connection: psycopg.Connection
) -> None:
    visible = _visible_chunk_ids(policy_app_connection, country="spain", role="employee")
    assert "ES-006:1.0:0" not in visible  # ES-006 requires manager or hr
    assert "MX-001:1.0:0" not in visible  # a different country


# --- policy_app cannot write, bypass RLS, or alter security -----------------


def test_policy_app_cannot_write_documents_or_chunks(
    seeded_documents: psycopg.Connection, policy_app_connection: psycopg.Connection
) -> None:
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        policy_app_connection.execute(
            "INSERT INTO documents "
            "(document_id, version, country, language, allowed_roles, effective_from, path) "
            "VALUES ('X-1', '1.0', 'spain', 'es', ARRAY['employee'], '2026-01-01', 'x.md')"
        )
    policy_app_connection.rollback()

    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        policy_app_connection.execute(
            "UPDATE documents SET version = '2.0' WHERE document_id = 'ES-001'"
        )
    policy_app_connection.rollback()

    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        policy_app_connection.execute("DELETE FROM chunks WHERE chunk_id = 'ES-001:1.0:0'")
    policy_app_connection.rollback()


def test_policy_app_can_read_but_not_modify_index_metadata(
    seeded_documents: psycopg.Connection, policy_app_connection: psycopg.Connection
) -> None:
    """migrations/003_policy_app_index_metadata_read.sql grants SELECT
    only: policy_app can check embedding-model compatibility (see
    persistence.verify_embedding_model_compatibility) but still can't
    write index_metadata — that stays exclusive to the admin connection.
    """
    rows = policy_app_connection.execute("SELECT * FROM index_metadata").fetchall()
    assert rows == []  # no document has been persisted on this connection's path
    policy_app_connection.rollback()

    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        policy_app_connection.execute(
            "INSERT INTO index_metadata "
            "(embedding_model_id, embedding_model_revision, "
            "embedding_dimensions, embeddings_normalized) "
            "VALUES ('m', 'r', 1024, true)"
        )
    policy_app_connection.rollback()


def test_policy_app_cannot_access_schema_migrations(
    seeded_documents: psycopg.Connection, policy_app_connection: psycopg.Connection
) -> None:
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        policy_app_connection.execute("SELECT * FROM schema_migrations")
    policy_app_connection.rollback()


def test_policy_app_is_not_superuser_and_cannot_bypass_rls(
    seeded_documents: psycopg.Connection, policy_app_connection: psycopg.Connection
) -> None:
    row = policy_app_connection.execute(
        "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = 'policy_app'"
    ).fetchone()
    assert row == (False, False)
    policy_app_connection.rollback()


def test_policy_app_cannot_modify_security_policies(
    seeded_documents: psycopg.Connection, policy_app_connection: psycopg.Connection
) -> None:
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        policy_app_connection.execute("ALTER TABLE documents DISABLE ROW LEVEL SECURITY")
    policy_app_connection.rollback()

    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        policy_app_connection.execute("DROP POLICY documents_select ON documents")
    policy_app_connection.rollback()


# --- Context is transaction-local, not session-wide -------------------------


def test_context_set_with_set_local_does_not_persist_after_the_transaction(
    seeded_documents: psycopg.Connection, policy_app_connection: psycopg.Connection
) -> None:
    with policy_app_connection.transaction():
        policy_app_connection.execute("SET LOCAL app.country = 'spain'")
        policy_app_connection.execute("SET LOCAL app.role = 'employee'")
        during = policy_app_connection.execute(
            "SELECT document_id FROM documents ORDER BY document_id"
        ).fetchall()

    # New, separate implicit transaction: nothing re-establishes the context.
    after = policy_app_connection.execute(
        "SELECT document_id FROM documents ORDER BY document_id"
    ).fetchall()
    policy_app_connection.rollback()

    assert [row[0] for row in during] == ["ES-001", "GLB-001"]
    assert after == []


# --- A pre-existing policy_app role is never trusted silently --------------
#
# Both tests start from policy_app_ready (role already exists, safely,
# with migrations fully applied), then tamper with it directly and
# re-execute 002_security.sql's raw text — not apply_migrations, whose
# ledger would just skip a migration already marked applied and never
# re-run the check at all. Neither test drops/recreates the role itself:
# DROP ROLE is cluster-wide and fails once policy_app has any dependent
# object in *any* database in this cluster (e.g. the dev database, from
# a previous manual run) — ALTER avoids that entirely.
#
# The tampering statement and the re-run both happen inside one explicit
# transaction that is rolled back, not undone by a compensating ALTER in
# a finally block: policy_app's attributes are cluster-wide, so a finally
# that never runs (process killed mid-test, for example) would otherwise
# risk leaving SUPERUSER permanently on a real role. A rollback is a
# property PostgreSQL itself guarantees for any uncommitted transaction
# once the connection goes away, regardless of whether Python cleanup
# code ever gets to run.


def test_refuses_a_preexisting_policy_app_role_with_dangerous_attributes(
    policy_app_ready: psycopg.Connection,
) -> None:
    security_sql = (REAL_MIGRATIONS_DIR / "002_security.sql").read_text(encoding="utf-8")

    with (
        pytest.raises(psycopg.errors.RaiseException, match="SUPERUSER"),
        policy_app_ready.transaction(),
    ):
        policy_app_ready.execute("ALTER ROLE policy_app SUPERUSER")
        policy_app_ready.execute(security_sql)  # pyright: ignore[reportCallIssue, reportArgumentType]

    row = policy_app_ready.execute(
        "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = 'policy_app'"
    ).fetchone()
    assert row == (False, False)


def test_refuses_when_policy_app_already_owns_a_protected_table(
    policy_app_ready: psycopg.Connection,
) -> None:
    security_sql = (REAL_MIGRATIONS_DIR / "002_security.sql").read_text(encoding="utf-8")

    with (
        pytest.raises(psycopg.errors.RaiseException, match="owns documents or chunks"),
        policy_app_ready.transaction(),
    ):
        policy_app_ready.execute("ALTER TABLE documents OWNER TO policy_app")
        policy_app_ready.execute(security_sql)  # pyright: ignore[reportCallIssue, reportArgumentType]

    row = policy_app_ready.execute(
        "SELECT tableowner FROM pg_tables WHERE schemaname = 'public' AND tablename = 'documents'"
    ).fetchone()
    assert row is not None
    assert row[0] == "policy_consultant_admin"
