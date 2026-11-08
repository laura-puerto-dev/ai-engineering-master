"""Tests for persistence._validate_document_and_chunks — pure, no
PostgreSQL. persist_document's DB-touching behavior is covered by
tests/test_persistence.py instead.
"""

from __future__ import annotations

from datetime import date

import pytest

from policy_consultant.models import DocumentChunk, EmbeddedChunk, PolicyDocument
from policy_consultant.persistence import _validate_document_and_chunks


def _make_document(
    *,
    document_id: str = "ES-001",
    version: str = "1.0",
    status: str = "current",
) -> PolicyDocument:
    return PolicyDocument(
        document_id=document_id,
        path=f"data/corpus/{document_id}.md",
        country="spain",
        language="es",
        allowed_roles=["employee", "manager", "hr"],
        version=version,
        effective_from=date(2026, 1, 1),
        effective_to=None,
        status=status,
    )


def _make_chunk(
    document: PolicyDocument,
    *,
    ordinal: int,
    chunk_id: str | None = None,
    document_id: str | None = None,
    model_id: str = "fake-model",
    embedding: list[float] | None = None,
) -> EmbeddedChunk:
    owning_document_id = document_id if document_id is not None else document["document_id"]
    version = document["version"]
    return EmbeddedChunk(
        document=document,
        chunk=DocumentChunk(
            chunk_id=(
                chunk_id
                if chunk_id is not None
                else f"{owning_document_id}:{version}:{ordinal}"
            ),
            document_id=owning_document_id,
            ordinal=ordinal,
            section_path=["1. Section"],
            text=f"Text {ordinal}",
        ),
        embedding=embedding if embedding is not None else [0.1, 0.2, 0.3, 0.4],
        model_id=model_id,
    )


def test_accepts_well_formed_document_and_chunks() -> None:
    document = _make_document()
    chunks = [_make_chunk(document, ordinal=0), _make_chunk(document, ordinal=1)]

    _validate_document_and_chunks(document, chunks, "rev-1")  # must not raise


def test_accepts_chunks_submitted_out_of_order() -> None:
    document = _make_document()
    # Ordinals are still 0-based and consecutive as a set, just not
    # delivered in ordinal order — validation only checks the set, not
    # the input order (persistence relies on SQL ORDER BY for retrieval,
    # not on insertion order).
    chunks = [
        _make_chunk(document, ordinal=2),
        _make_chunk(document, ordinal=0),
        _make_chunk(document, ordinal=1),
    ]

    _validate_document_and_chunks(document, chunks, "rev-1")  # must not raise


def test_rejects_empty_revision() -> None:
    document = _make_document()
    chunks = [_make_chunk(document, ordinal=0)]

    with pytest.raises(ValueError, match="embedding_model_revision"):
        _validate_document_and_chunks(document, chunks, "")


def test_rejects_empty_chunks() -> None:
    document = _make_document()

    with pytest.raises(ValueError, match="must not be empty"):
        _validate_document_and_chunks(document, [], "rev-1")


def test_rejects_non_current_status() -> None:
    document = _make_document(status="superseded")
    chunks = [_make_chunk(document, ordinal=0)]

    with pytest.raises(ValueError, match="not 'current'"):
        _validate_document_and_chunks(document, chunks, "rev-1")


def test_rejects_chunk_whose_document_metadata_is_for_another_document() -> None:
    document = _make_document(document_id="ES-001")
    other_document = _make_document(document_id="ES-002")
    chunk = _make_chunk(other_document, ordinal=0)

    with pytest.raises(ValueError, match="ES-002"):
        _validate_document_and_chunks(document, [chunk], "rev-1")


def test_rejects_chunk_whose_document_metadata_has_a_different_version() -> None:
    document = _make_document(version="1.1")
    stale_document = _make_document(version="1.0")
    # Same document_id, but the chunk's embedded document metadata is stale.
    chunk = _make_chunk(stale_document, ordinal=0, chunk_id="ES-001:1.1:0")

    with pytest.raises(ValueError, match="version"):
        _validate_document_and_chunks(document, [chunk], "rev-1")


def test_rejects_chunk_whose_own_document_id_field_disagrees() -> None:
    document = _make_document(document_id="ES-001")
    chunk = _make_chunk(document, ordinal=0, document_id="ES-999", chunk_id="ES-001:1.0:0")

    with pytest.raises(ValueError, match="ES-999"):
        _validate_document_and_chunks(document, [chunk], "rev-1")


def test_rejects_gap_in_ordinals() -> None:
    document = _make_document()
    chunks = [_make_chunk(document, ordinal=0), _make_chunk(document, ordinal=2)]

    with pytest.raises(ValueError, match="0-based and consecutive"):
        _validate_document_and_chunks(document, chunks, "rev-1")


def test_rejects_duplicate_ordinals() -> None:
    document = _make_document()
    chunks = [
        _make_chunk(document, ordinal=0),
        _make_chunk(document, ordinal=0, chunk_id="ES-001:1.0:0"),
    ]

    with pytest.raises(ValueError, match="0-based and consecutive"):
        _validate_document_and_chunks(document, chunks, "rev-1")


def test_rejects_chunk_id_with_a_stale_version() -> None:
    document = _make_document(version="1.1")
    chunk = _make_chunk(document, ordinal=0, chunk_id="ES-001:1.0:0")

    with pytest.raises(ValueError, match="does not match expected"):
        _validate_document_and_chunks(document, [chunk], "rev-1")


def test_rejects_mixed_model_ids() -> None:
    document = _make_document()
    chunks = [
        _make_chunk(document, ordinal=0, model_id="model-a"),
        _make_chunk(document, ordinal=1, model_id="model-b"),
    ]

    with pytest.raises(ValueError, match="model_id"):
        _validate_document_and_chunks(document, chunks, "rev-1")


def test_rejects_inconsistent_embedding_dimensions() -> None:
    document = _make_document()
    chunks = [
        _make_chunk(document, ordinal=0, embedding=[0.1, 0.2]),
        _make_chunk(document, ordinal=1, embedding=[0.1, 0.2, 0.3]),
    ]

    with pytest.raises(ValueError, match="dimensions"):
        _validate_document_and_chunks(document, chunks, "rev-1")
