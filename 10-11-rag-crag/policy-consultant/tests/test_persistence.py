"""Integration tests for persistence.py (src/policy_consultant/persistence.py).

Every embedding here is synthetic (plain Python float lists built by
_make_chunks below) — persist_document never calls an EmbeddingModel, so
these tests never load sentence-transformers/torch. policy_app_ready
already gives an autocommit admin connection to the migrated test
database (see conftest.py), which is exactly the connection shape
persist_document requires.
"""

from __future__ import annotations

from datetime import date

import psycopg
import pytest

from policy_consultant.models import DocumentChunk, EmbeddedChunk, PolicyDocument
from policy_consultant.persistence import persist_document

pytestmark = pytest.mark.integration

REAL_DIMENSIONS = 1024


def _make_document(
    *,
    document_id: str = "ES-001",
    version: str = "1.0",
    country: str = "spain",
    allowed_roles: list[str] | None = None,
) -> PolicyDocument:
    return PolicyDocument(
        document_id=document_id,
        path=f"data/corpus/{document_id}.md",
        country=country,
        language="es",
        allowed_roles=(
            allowed_roles if allowed_roles is not None else ["employee", "manager", "hr"]
        ),
        version=version,
        effective_from=date(2026, 1, 1),
        effective_to=None,
        status="current",
    )


def _make_chunks(
    document: PolicyDocument,
    count: int,
    *,
    model_id: str = "fake-model",
    dimensions: int = REAL_DIMENSIONS,
    text_prefix: str = "Text",
) -> list[EmbeddedChunk]:
    document_id = document["document_id"]
    version = document["version"]
    return [
        EmbeddedChunk(
            document=document,
            chunk=DocumentChunk(
                chunk_id=f"{document_id}:{version}:{ordinal}",
                document_id=document_id,
                ordinal=ordinal,
                section_path=[f"{ordinal + 1}. Section"],
                text=f"{text_prefix} {ordinal}",
            ),
            embedding=[float(ordinal + 1)] * dimensions,
            model_id=model_id,
        )
        for ordinal in range(count)
    ]


def _read_documents(conn: psycopg.Connection) -> list[tuple[object, ...]]:
    rows = conn.execute(
        "SELECT document_id, version FROM documents ORDER BY document_id"
    ).fetchall()
    return [tuple(row) for row in rows]


def _read_chunks(conn: psycopg.Connection, document_id: str) -> list[tuple[object, ...]]:
    rows = conn.execute(
        """
        SELECT chunk_id, ordinal, text, section_path
        FROM chunks WHERE document_id = %s ORDER BY ordinal
        """,
        (document_id,),
    ).fetchall()
    return [tuple(row) for row in rows]


def _read_index_metadata(conn: psycopg.Connection) -> tuple[object, ...] | None:
    row = conn.execute(
        """
        SELECT embedding_model_id, embedding_model_revision, embedding_dimensions,
               embeddings_normalized
        FROM index_metadata
        """
    ).fetchone()
    return tuple(row) if row is not None else None


# --- initial insert / update / idempotency ------------------------------


def test_persist_document_inserts_document_and_chunks(
    policy_app_ready: psycopg.Connection,
) -> None:
    document = _make_document()
    chunks = _make_chunks(document, 3)

    persist_document(
        policy_app_ready,
        document,
        chunks,
        embedding_model_revision="rev-1",
        embeddings_normalized=True,
    )

    assert _read_documents(policy_app_ready) == [("ES-001", "1.0")]
    rows = _read_chunks(policy_app_ready, "ES-001")
    assert [row[0] for row in rows] == [f"ES-001:1.0:{i}" for i in range(3)]
    assert [row[1] for row in rows] == [0, 1, 2]
    assert [row[2] for row in rows] == ["Text 0", "Text 1", "Text 2"]


def test_persist_document_updates_metadata_and_replaces_all_chunks(
    policy_app_ready: psycopg.Connection,
) -> None:
    document_v1 = _make_document(version="1.0")
    persist_document(
        policy_app_ready,
        document_v1,
        _make_chunks(document_v1, 2),
        embedding_model_revision="rev-1",
        embeddings_normalized=True,
    )

    document_v2 = _make_document(version="1.1")
    chunks_v2 = _make_chunks(document_v2, 4, text_prefix="New text")
    persist_document(
        policy_app_ready,
        document_v2,
        chunks_v2,
        embedding_model_revision="rev-1",
        embeddings_normalized=True,
    )

    assert _read_documents(policy_app_ready) == [("ES-001", "1.1")]
    rows = _read_chunks(policy_app_ready, "ES-001")
    assert [row[0] for row in rows] == [f"ES-001:1.1:{i}" for i in range(4)]
    assert [row[2] for row in rows] == [f"New text {i}" for i in range(4)]


def test_persist_document_is_idempotent(policy_app_ready: psycopg.Connection) -> None:
    document = _make_document()
    chunks = _make_chunks(document, 2)

    for _ in range(2):
        persist_document(
            policy_app_ready,
            document,
            chunks,
            embedding_model_revision="rev-1",
            embeddings_normalized=True,
        )

    assert _read_documents(policy_app_ready) == [("ES-001", "1.0")]
    assert _read_chunks(policy_app_ready, "ES-001") == [
        ("ES-001:1.0:0", 0, "Text 0", ["1. Section"]),
        ("ES-001:1.0:1", 1, "Text 1", ["2. Section"]),
    ]


def test_persist_document_preserves_chunk_order_and_relationships(
    policy_app_ready: psycopg.Connection,
) -> None:
    document = _make_document()
    chunks = _make_chunks(document, 3)
    # Delivered out of order on purpose: persistence must not depend on
    # insertion order, only on the ordinal column and ORDER BY at read time.
    shuffled_chunks = [chunks[2], chunks[0], chunks[1]]

    persist_document(
        policy_app_ready,
        document,
        shuffled_chunks,
        embedding_model_revision="rev-1",
        embeddings_normalized=True,
    )

    rows = _read_chunks(policy_app_ready, "ES-001")
    assert rows == [
        ("ES-001:1.0:0", 0, "Text 0", ["1. Section"]),
        ("ES-001:1.0:1", 1, "Text 1", ["2. Section"]),
        ("ES-001:1.0:2", 2, "Text 2", ["3. Section"]),
    ]


def test_persist_document_does_not_affect_other_documents(
    policy_app_ready: psycopg.Connection,
) -> None:
    document_a = _make_document(document_id="ES-001")
    document_b = _make_document(document_id="MX-001", country="mexico")

    persist_document(
        policy_app_ready,
        document_a,
        _make_chunks(document_a, 2),
        embedding_model_revision="rev-1",
        embeddings_normalized=True,
    )
    persist_document(
        policy_app_ready,
        document_b,
        _make_chunks(document_b, 2),
        embedding_model_revision="rev-1",
        embeddings_normalized=True,
    )

    # Update A again.
    document_a_v2 = _make_document(document_id="ES-001", version="1.1")
    persist_document(
        policy_app_ready,
        document_a_v2,
        _make_chunks(document_a_v2, 3, text_prefix="Updated"),
        embedding_model_revision="rev-1",
        embeddings_normalized=True,
    )

    assert _read_documents(policy_app_ready) == [("ES-001", "1.1"), ("MX-001", "1.0")]
    assert _read_chunks(policy_app_ready, "MX-001") == [
        ("MX-001:1.0:0", 0, "Text 0", ["1. Section"]),
        ("MX-001:1.0:1", 1, "Text 1", ["2. Section"]),
    ]


# --- rollback and model-consistency guards ------------------------------


def test_persist_document_rolls_back_index_metadata_when_first_ever_persistence_fails(
    policy_app_ready: psycopg.Connection,
) -> None:
    """A chunk whose embedding doesn't fit the real VECTOR(1024) column
    fails only at the PostgreSQL INSERT, not at Python validation (which
    only checks the chunks agree with each other, not against the fixed
    column width). On a fresh database this is also the first-ever
    persistence attempt, so index_metadata's bootstrap INSERT has already
    run earlier in the same transaction — proving that it, too, rolls
    back along with documents and chunks.
    """
    document = _make_document()
    bad_chunks = _make_chunks(document, 2, dimensions=4)

    with pytest.raises(psycopg.Error):
        persist_document(
            policy_app_ready,
            document,
            bad_chunks,
            embedding_model_revision="rev-1",
            embeddings_normalized=True,
        )

    assert _read_documents(policy_app_ready) == []
    assert _read_chunks(policy_app_ready, "ES-001") == []
    assert _read_index_metadata(policy_app_ready) is None


def test_persist_document_rolls_back_a_partially_executed_update(
    policy_app_ready: psycopg.Connection,
) -> None:
    """A NaN embedding component — still 1024 dimensions, same model_id/
    revision/dimensions/normalized as the already-registered
    index_metadata — is the only deterministic way to fail *after* the
    documents UPSERT, the chunks DELETE, and the first new chunk INSERT
    have already run in this transaction, without violating Python-level
    validation (which checks shape/consistency, never numeric content —
    see _validate_document_and_chunks's docstring) or the index_metadata
    compatibility guard (nothing here is incompatible with it). pgvector
    itself rejects NaN at INSERT time (verified directly against the
    running database: psycopg.errors.DataException, "NaN not allowed in
    vector"), so this proves the whole transaction — not just the failed
    chunk — rolls back, leaving the original version 1.0 untouched.
    """
    document_v1 = _make_document(version="1.0")
    persist_document(
        policy_app_ready,
        document_v1,
        _make_chunks(document_v1, 2),
        embedding_model_revision="rev-1",
        embeddings_normalized=True,
    )

    document_v2 = _make_document(version="1.1")
    chunks_v2 = _make_chunks(document_v2, 2, text_prefix="New")
    chunks_v2[1]["embedding"][0] = float("nan")  # still 1024 dimensions

    with pytest.raises(psycopg.errors.DataException, match="NaN"):
        persist_document(
            policy_app_ready,
            document_v2,
            chunks_v2,
            embedding_model_revision="rev-1",
            embeddings_normalized=True,
        )

    assert _read_documents(policy_app_ready) == [("ES-001", "1.0")]
    assert _read_chunks(policy_app_ready, "ES-001") == [
        ("ES-001:1.0:0", 0, "Text 0", ["1. Section"]),
        ("ES-001:1.0:1", 1, "Text 1", ["2. Section"]),
    ]
    assert _read_index_metadata(policy_app_ready) == ("fake-model", "rev-1", 1024, True)


@pytest.mark.parametrize(
    ("model_id", "revision"),
    [
        ("fake-model", "rev-2"),  # same model_id, different revision
        ("other-model", "rev-1"),  # different model_id
    ],
)
def test_persist_document_rejects_incompatible_embedding_model(
    policy_app_ready: psycopg.Connection,
    model_id: str,
    revision: str,
) -> None:
    document_a = _make_document(document_id="ES-001")
    persist_document(
        policy_app_ready,
        document_a,
        _make_chunks(document_a, 2, model_id="fake-model"),
        embedding_model_revision="rev-1",
        embeddings_normalized=True,
    )

    document_b = _make_document(document_id="MX-001", country="mexico")
    with pytest.raises(ValueError, match="Embedding model mismatch"):
        persist_document(
            policy_app_ready,
            document_b,
            _make_chunks(document_b, 2, model_id=model_id),
            embedding_model_revision=revision,
            embeddings_normalized=True,
        )

    assert _read_index_metadata(policy_app_ready) == ("fake-model", "rev-1", 1024, True)
    assert _read_documents(policy_app_ready) == [("ES-001", "1.0")]


def test_persist_document_preserves_previous_version_when_update_is_rejected(
    policy_app_ready: psycopg.Connection,
) -> None:
    document_v1 = _make_document(version="1.0")
    persist_document(
        policy_app_ready,
        document_v1,
        _make_chunks(document_v1, 2, model_id="fake-model"),
        embedding_model_revision="rev-1",
        embeddings_normalized=True,
    )

    document_v2 = _make_document(version="1.1")
    with pytest.raises(ValueError, match="Embedding model mismatch"):
        persist_document(
            policy_app_ready,
            document_v2,
            _make_chunks(document_v2, 3, model_id="fake-model", text_prefix="New"),
            embedding_model_revision="rev-2",
            embeddings_normalized=True,
        )

    assert _read_documents(policy_app_ready) == [("ES-001", "1.0")]
    assert _read_chunks(policy_app_ready, "ES-001") == [
        ("ES-001:1.0:0", 0, "Text 0", ["1. Section"]),
        ("ES-001:1.0:1", 1, "Text 1", ["2. Section"]),
    ]
