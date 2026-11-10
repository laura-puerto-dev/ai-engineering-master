"""Integration tests for retrieval.py (src/policy_consultant/retrieval.py).

Embeddings are synthetic, deterministic "unit vectors" (one component set
to 1.0, the rest 0.0) seeded directly as admin — never BGE-M3. This lets
each test construct a query embedding that is the exact closest match to
a specific, known chunk, so that country/role isolation can be proven
even when the unauthorized chunk is mathematically the best match: if it
never comes back despite being closest, the exclusion can only be RLS,
not distance ranking.

Documents/roles reuse the same four-document scenario as
test_security.py (ES-001 spain all-roles, ES-006 spain manager/hr-only,
MX-001 mexico all-roles, GLB-001 global all-roles) — deliberately no
england document, so a country with zero authorized documents is
available for the "no results" case without inventing anything exotic.
"""

from __future__ import annotations

from pathlib import Path

import psycopg
import pytest

from policy_consultant.corpus_manifest import load_access_model
from policy_consultant.db import app_connection
from policy_consultant.models import AccessModel
from policy_consultant.retrieval import retrieve_relevant_chunks

pytestmark = pytest.mark.integration

TEST_DATABASE_NAME = "policy_consultant_test"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ACCESS_MODEL_PATH = PROJECT_ROOT / "config" / "access-model.yaml"
DIMENSIONS = 1024

_DOCUMENTS = [
    # (document_id, country, allowed_roles, unit_vector_index)
    ("ES-001", "spain", ["employee", "manager", "hr"], 0),
    ("ES-006", "spain", ["manager", "hr"], 1),
    ("MX-001", "mexico", ["employee", "manager", "hr"], 2),
    ("GLB-001", "global", ["employee", "manager", "hr"], 3),
]


def _unit_vector(index: int) -> list[float]:
    vector = [0.0] * DIMENSIONS
    vector[index] = 1.0
    return vector


@pytest.fixture
def access_model() -> AccessModel:
    return load_access_model(ACCESS_MODEL_PATH)


@pytest.fixture
def seeded_chunks(policy_app_ready: psycopg.Connection) -> psycopg.Connection:
    admin = policy_app_ready
    for document_id, country, allowed_roles, vector_index in _DOCUMENTS:
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
            VALUES (%s, %s, 0, ARRAY['1. Section'], %s, %s, 'fake-model')
            """,
            (
                f"{document_id}:1.0:0",
                document_id,
                f"Text of {document_id}",
                _unit_vector(vector_index),
            ),
        )
    return admin


def test_retrieves_an_authorized_chunk_with_the_closest_match_first(
    seeded_chunks: psycopg.Connection, access_model: AccessModel
) -> None:
    with app_connection(
        country="spain", role="employee", access_model=access_model, dbname=TEST_DATABASE_NAME
    ) as conn:
        results = retrieve_relevant_chunks(conn, _unit_vector(0), top_k=10)

    assert results[0]["chunk_id"] == "ES-001:1.0:0"
    assert results[0]["document_id"] == "ES-001"
    assert results[0]["version"] == "1.0"
    assert results[0]["section_path"] == ["1. Section"]
    assert results[0]["text"] == "Text of ES-001"
    assert results[0]["distance"] == pytest.approx(0.0, abs=1e-9)


def test_never_returns_a_chunk_from_an_unauthorized_country_even_as_the_closest_match(
    seeded_chunks: psycopg.Connection, access_model: AccessModel
) -> None:
    with app_connection(
        country="spain", role="employee", access_model=access_model, dbname=TEST_DATABASE_NAME
    ) as conn:
        # Query is the exact vector of MX-001's chunk (mexico, unauthorized
        # for a spain user) — the best possible mathematical match.
        results = retrieve_relevant_chunks(conn, _unit_vector(2), top_k=10)

    document_ids = {r["document_id"] for r in results}
    assert "MX-001" not in document_ids
    assert document_ids <= {"ES-001", "GLB-001"}


def test_never_returns_a_role_restricted_chunk_even_as_the_closest_match(
    seeded_chunks: psycopg.Connection, access_model: AccessModel
) -> None:
    with app_connection(
        country="spain", role="employee", access_model=access_model, dbname=TEST_DATABASE_NAME
    ) as conn:
        # Query is the exact vector of ES-006's chunk (spain, but
        # manager/hr-only — unauthorized for an employee).
        results = retrieve_relevant_chunks(conn, _unit_vector(1), top_k=10)

    document_ids = {r["document_id"] for r in results}
    assert "ES-006" not in document_ids


def test_a_global_document_is_visible_from_any_authorized_country(
    seeded_chunks: psycopg.Connection, access_model: AccessModel
) -> None:
    with app_connection(
        country="mexico", role="employee", access_model=access_model, dbname=TEST_DATABASE_NAME
    ) as conn:
        results = retrieve_relevant_chunks(conn, _unit_vector(3), top_k=10)

    assert results[0]["document_id"] == "GLB-001"


def test_top_k_limits_the_number_of_rows_returned(
    seeded_chunks: psycopg.Connection, access_model: AccessModel
) -> None:
    with app_connection(
        country="spain", role="employee", access_model=access_model, dbname=TEST_DATABASE_NAME
    ) as conn:
        # spain/employee is authorized for ES-001 and GLB-001 — 2 possible
        # rows — but only 1 is requested.
        results = retrieve_relevant_chunks(conn, _unit_vector(0), top_k=1)

    assert len(results) == 1
    assert results[0]["document_id"] == "ES-001"


def test_returns_an_empty_list_when_nothing_is_indexed_yet(
    policy_app_ready: psycopg.Connection, access_model: AccessModel
) -> None:
    # policy_app_ready is migrated but deliberately not seeded: there is
    # no row to find, not even a global one (unlike seeded_chunks, where
    # GLB-001 is visible to every valid country/role and so could never
    # produce a genuinely empty result).
    with app_connection(
        country="england", role="employee", access_model=access_model, dbname=TEST_DATABASE_NAME
    ) as conn:
        results = retrieve_relevant_chunks(conn, _unit_vector(0), top_k=10)

    assert results == []


def test_version_reflects_the_documents_current_row_not_a_stale_value(
    seeded_chunks: psycopg.Connection, access_model: AccessModel
) -> None:
    seeded_chunks.execute("UPDATE documents SET version = '2.0' WHERE document_id = 'ES-001'")

    with app_connection(
        country="spain", role="employee", access_model=access_model, dbname=TEST_DATABASE_NAME
    ) as conn:
        results = retrieve_relevant_chunks(conn, _unit_vector(0), top_k=1)

    assert results[0]["version"] == "2.0"


def test_rejects_non_positive_top_k(
    seeded_chunks: psycopg.Connection, access_model: AccessModel
) -> None:
    with (
        app_connection(
            country="spain", role="employee", access_model=access_model, dbname=TEST_DATABASE_NAME
        ) as conn,
        pytest.raises(ValueError, match="top_k must be greater than 0"),
    ):
        retrieve_relevant_chunks(conn, _unit_vector(0), top_k=0)
