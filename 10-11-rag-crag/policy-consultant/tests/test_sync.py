"""Integration tests for sync.py (src/policy_consultant/sync.py).

Embeddings are synthetic (FakeEmbeddingModel, 1024 dimensions to satisfy
the real VECTOR(1024) column — never sentence-transformers/torch).
Document content lives under tmp_path, following the same convention as
tests/test_ingestion.py, so these tests never depend on the real corpus
under data/corpus/.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import cast

import psycopg
import pytest

from policy_consultant.corpus_manifest import load_access_model
from policy_consultant.models import AccessModel, PolicyDocument, SyncReport
from policy_consultant.sync import _update_document_metadata, sync_corpus

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ACCESS_MODEL_PATH = PROJECT_ROOT / "config" / "access-model.yaml"


class FakeEmbeddingModel:
    """Deterministic, 1024-dimensional (matches the real chunks.embedding
    column) stand-in for EmbeddingModel. Records every text it was asked
    to embed, so tests can assert a document's content was never
    re-embedded.
    """

    def __init__(self, *, model_id: str = "fake-model", dimensions: int = 1024) -> None:
        self._model_id = model_id
        self._dimensions = dimensions
        self.calls: list[str] = []

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        self.calls.extend(texts)
        return [[0.1] * self._dimensions for _ in texts]


class SelectivelyFailingEmbeddingModel(FakeEmbeddingModel):
    """Like FakeEmbeddingModel, but raises for any batch containing a
    marker substring — used to fail exactly one document's embedding
    step while letting every other document in the same sync run
    succeed normally.
    """

    def __init__(
        self,
        *,
        fail_when_text_contains: str,
        model_id: str = "fake-model",
        dimensions: int = 1024,
    ) -> None:
        super().__init__(model_id=model_id, dimensions=dimensions)
        self._fail_when_text_contains = fail_when_text_contains

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if any(self._fail_when_text_contains in text for text in texts):
            raise RuntimeError("deliberate embedding failure")
        return super().embed_batch(texts)


@pytest.fixture
def access_model() -> AccessModel:
    return load_access_model(ACCESS_MODEL_PATH)


def _write_document(
    tmp_path: Path,
    *,
    document_id: str = "ES-001",
    relative_path: str = "spain/ES-001.md",
    content: str = "# Policy\n\nSome content.",
    country: str = "spain",
    language: str = "es",
    allowed_roles: list[str] | None = None,
    version: str = "1.0",
    effective_from: date = date(2026, 1, 1),
) -> PolicyDocument:
    path = tmp_path / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

    return PolicyDocument(
        document_id=document_id,
        path=relative_path,
        country=country,
        language=language,
        allowed_roles=allowed_roles if allowed_roles is not None else ["employee", "manager"],
        version=version,
        effective_from=effective_from,
        effective_to=None,
        status="current",
    )


def _read_document_row(
    conn: psycopg.Connection, document_id: str
) -> tuple[object, ...] | None:
    row = conn.execute(
        "SELECT version, country, allowed_roles, path FROM documents WHERE document_id = %s",
        (document_id,),
    ).fetchone()
    return tuple(row) if row is not None else None


def _read_chunk_ids(conn: psycopg.Connection, document_id: str) -> list[str]:
    rows = conn.execute(
        "SELECT chunk_id FROM chunks WHERE document_id = %s ORDER BY ordinal", (document_id,)
    ).fetchall()
    return [row[0] for row in rows]


def _sync(
    conn: psycopg.Connection,
    documents: list[PolicyDocument],
    tmp_path: Path,
    access_model: AccessModel,
    model: FakeEmbeddingModel,
    *,
    model_revision: str = "rev-1",
) -> SyncReport:
    return sync_corpus(
        conn,
        documents,
        tmp_path,
        access_model,
        model,
        chunking_strategy="structured_recursive",
        max_chars=500,
        embedding_batch_size=10,
        embedding_model_revision=model_revision,
        embeddings_normalized=True,
    )


# --- insert / update / unchanged ----------------------------------------


def test_syncs_a_new_document(
    policy_app_ready: psycopg.Connection, tmp_path: Path, access_model: AccessModel
) -> None:
    document = _write_document(tmp_path)
    model = FakeEmbeddingModel()

    report = _sync(policy_app_ready, [document], tmp_path, access_model, model)

    assert report["inserted"] == ["ES-001"]
    assert _read_document_row(policy_app_ready, "ES-001") is not None
    assert len(model.calls) > 0


def test_does_not_regenerate_embeddings_for_an_unchanged_document(
    policy_app_ready: psycopg.Connection, tmp_path: Path, access_model: AccessModel
) -> None:
    document = _write_document(tmp_path)
    model = FakeEmbeddingModel()

    first_report = _sync(policy_app_ready, [document], tmp_path, access_model, model)
    assert first_report["inserted"] == ["ES-001"]
    calls_after_first_sync = len(model.calls)

    second_report = _sync(policy_app_ready, [document], tmp_path, access_model, model)

    assert second_report["unchanged"] == ["ES-001"]
    assert second_report["inserted"] == []
    assert len(model.calls) == calls_after_first_sync  # no new embedding calls


def test_updates_version_and_replaces_chunks_when_effective_from_advances(
    policy_app_ready: psycopg.Connection, tmp_path: Path, access_model: AccessModel
) -> None:
    model = FakeEmbeddingModel()
    v1 = _write_document(tmp_path, content="# Policy\n\nOriginal content.")
    _sync(policy_app_ready, [v1], tmp_path, access_model, model)
    original_chunk_ids = _read_chunk_ids(policy_app_ready, "ES-001")

    v2 = _write_document(
        tmp_path,
        content="# Policy\n\nUpdated content, quite different and longer than before.",
        version="1.1",
        effective_from=date(2026, 6, 1),
    )
    report = _sync(policy_app_ready, [v2], tmp_path, access_model, model)

    assert report["updated"] == ["ES-001"]
    row = _read_document_row(policy_app_ready, "ES-001")
    assert row is not None
    assert row[0] == "1.1"
    assert _read_chunk_ids(policy_app_ready, "ES-001") != original_chunk_ids


def test_rejects_a_stale_version_whose_effective_from_does_not_advance(
    policy_app_ready: psycopg.Connection, tmp_path: Path, access_model: AccessModel
) -> None:
    model = FakeEmbeddingModel()
    v1 = _write_document(tmp_path, effective_from=date(2026, 6, 1))
    _sync(policy_app_ready, [v1], tmp_path, access_model, model)
    original_row = _read_document_row(policy_app_ready, "ES-001")

    stale = _write_document(tmp_path, version="1.1", effective_from=date(2026, 1, 1))
    report = _sync(policy_app_ready, [stale], tmp_path, access_model, model)

    assert report["rejected_stale"] == ["ES-001"]
    assert _read_document_row(policy_app_ready, "ES-001") == original_row


# --- metadata-only update and conflicts ---------------------------------


def test_updates_allowed_roles_without_touching_chunks_or_embeddings(
    policy_app_ready: psycopg.Connection, tmp_path: Path, access_model: AccessModel
) -> None:
    model = FakeEmbeddingModel()
    original = _write_document(tmp_path, allowed_roles=["employee", "manager"])
    _sync(policy_app_ready, [original], tmp_path, access_model, model)
    original_chunk_ids = _read_chunk_ids(policy_app_ready, "ES-001")
    calls_after_first_sync = len(model.calls)

    widened = _write_document(tmp_path, allowed_roles=["employee", "manager", "hr"])
    report = _sync(policy_app_ready, [widened], tmp_path, access_model, model)

    assert report["updated_metadata"] == ["ES-001"]
    row = _read_document_row(policy_app_ready, "ES-001")
    assert row is not None
    stored_roles = cast("list[str]", row[2])
    assert set(stored_roles) == {"employee", "manager", "hr"}
    assert _read_chunk_ids(policy_app_ready, "ES-001") == original_chunk_ids
    assert len(model.calls) == calls_after_first_sync  # no new embedding calls


def test_flags_metadata_conflict_when_country_changes_without_a_version_bump(
    policy_app_ready: psycopg.Connection, tmp_path: Path, access_model: AccessModel
) -> None:
    model = FakeEmbeddingModel()
    original = _write_document(tmp_path, country="spain")
    _sync(policy_app_ready, [original], tmp_path, access_model, model)
    original_row = _read_document_row(policy_app_ready, "ES-001")

    recountried = _write_document(tmp_path, country="mexico")
    report = _sync(policy_app_ready, [recountried], tmp_path, access_model, model)

    assert report["metadata_conflict"] == ["ES-001"]
    assert _read_document_row(policy_app_ready, "ES-001") == original_row


# --- missing from manifest, per-document failure isolation -------------


def test_leaves_a_document_missing_from_the_manifest_untouched(
    policy_app_ready: psycopg.Connection, tmp_path: Path, access_model: AccessModel
) -> None:
    model = FakeEmbeddingModel()
    document = _write_document(tmp_path)
    _sync(policy_app_ready, [document], tmp_path, access_model, model)

    report = _sync(policy_app_ready, [], tmp_path, access_model, model)

    assert report["missing_from_manifest"] == ["ES-001"]
    assert _read_document_row(policy_app_ready, "ES-001") is not None


def test_one_documents_failure_does_not_block_the_rest_of_the_sync(
    policy_app_ready: psycopg.Connection, tmp_path: Path, access_model: AccessModel
) -> None:
    model = FakeEmbeddingModel()
    good = _write_document(tmp_path, document_id="ES-001", relative_path="spain/ES-001.md")
    # Exists on disk (passes validate_manifest's is_file() check) but has
    # an unsupported extension, so extraction fails only once processing
    # actually reaches it — a per-document failure, not a global one.
    bad_path = tmp_path / "spain" / "ES-002.pdf"
    bad_path.parent.mkdir(parents=True, exist_ok=True)
    bad_path.write_text("not markdown", encoding="utf-8")
    bad = PolicyDocument(
        document_id="ES-002",
        path="spain/ES-002.pdf",
        country="spain",
        language="es",
        allowed_roles=["employee"],
        version="1.0",
        effective_from=date(2026, 1, 1),
        effective_to=None,
        status="current",
    )

    report = _sync(policy_app_ready, [good, bad], tmp_path, access_model, model)

    assert report["inserted"] == ["ES-001"]
    assert len(report["failed"]) == 1
    assert report["failed"][0][0] == "ES-002"
    assert "Unsupported document format" in report["failed"][0][1]
    assert _read_document_row(policy_app_ready, "ES-001") is not None


# --- global aborts -------------------------------------------------------


def test_aborts_before_processing_anything_when_the_manifest_is_invalid(
    policy_app_ready: psycopg.Connection, tmp_path: Path, access_model: AccessModel
) -> None:
    model = FakeEmbeddingModel()
    invalid = _write_document(tmp_path, country="atlantis")

    with pytest.raises(ValueError, match="Invalid country"):
        _sync(policy_app_ready, [invalid], tmp_path, access_model, model)

    assert model.calls == []
    assert _read_document_row(policy_app_ready, "ES-001") is None


def test_aborts_before_processing_anything_on_a_global_embedding_model_mismatch(
    policy_app_ready: psycopg.Connection, tmp_path: Path, access_model: AccessModel
) -> None:
    first_model = FakeEmbeddingModel(model_id="model-a")
    seed = _write_document(tmp_path, document_id="ES-900", relative_path="spain/ES-900.md")
    _sync(policy_app_ready, [seed], tmp_path, access_model, first_model)

    second_model = FakeEmbeddingModel(model_id="model-b")
    document = _write_document(tmp_path)

    with pytest.raises(ValueError, match="Embedding model mismatch"):
        _sync(policy_app_ready, [document], tmp_path, access_model, second_model)

    assert second_model.calls == []
    assert _read_document_row(policy_app_ready, "ES-001") is None


# --- sync-level failure isolation and metadata-path edge cases ---------


def test_embedding_failure_during_update_preserves_previous_version_and_does_not_block_others(
    policy_app_ready: psycopg.Connection, tmp_path: Path, access_model: AccessModel
) -> None:
    """Covers the synchronizer's own error isolation — not a repeat of
    Etapa 4's SQL-level rollback test. The failure here happens entirely
    inside the embedding step, before persist_document is ever called for
    ES-001's new version, so there is nothing for PostgreSQL to roll
    back: the point is that sync_corpus never attempts the write at all,
    and that ES-002 (unrelated, in the same run) is unaffected.
    """
    good_model = FakeEmbeddingModel()
    v1 = _write_document(
        tmp_path,
        document_id="ES-001",
        relative_path="spain/ES-001.md",
        content="# Policy\n\nOriginal content.",
    )
    _sync(policy_app_ready, [v1], tmp_path, access_model, good_model)
    original_row = _read_document_row(policy_app_ready, "ES-001")
    original_chunk_ids = _read_chunk_ids(policy_app_ready, "ES-001")

    failing_model = SelectivelyFailingEmbeddingModel(fail_when_text_contains="BOOM")
    v1_1 = _write_document(
        tmp_path,
        document_id="ES-001",
        relative_path="spain/ES-001.md",
        content="# Policy\n\nBOOM, this content fails to embed.",
        version="1.1",
        effective_from=date(2026, 6, 1),
    )
    other = _write_document(
        tmp_path,
        document_id="ES-002",
        relative_path="spain/ES-002.md",
        content="# Other policy\n\nFine content.",
    )

    report = _sync(policy_app_ready, [v1_1, other], tmp_path, access_model, failing_model)

    assert len(report["failed"]) == 1
    assert report["failed"][0][0] == "ES-001"
    assert "deliberate embedding failure" in report["failed"][0][1]
    assert report["inserted"] == ["ES-002"]

    assert _read_document_row(policy_app_ready, "ES-001") == original_row
    assert _read_chunk_ids(policy_app_ready, "ES-001") == original_chunk_ids


def test_update_document_metadata_returns_false_when_the_stored_version_no_longer_matches(
    policy_app_ready: psycopg.Connection, tmp_path: Path, access_model: AccessModel
) -> None:
    model = FakeEmbeddingModel()
    document = _write_document(tmp_path, allowed_roles=["employee", "manager"])
    _sync(policy_app_ready, [document], tmp_path, access_model, model)
    original_row = _read_document_row(policy_app_ready, "ES-001")

    updated = _update_document_metadata(
        policy_app_ready,
        "ES-001",
        "0.9",  # the planner's stale, no-longer-matching view of the version
        ["employee", "manager", "hr"],
        "spain/renamed.md",
    )

    assert updated is False
    assert _read_document_row(policy_app_ready, "ES-001") == original_row


def test_updates_path_without_touching_chunks_or_embeddings(
    policy_app_ready: psycopg.Connection, tmp_path: Path, access_model: AccessModel
) -> None:
    model = FakeEmbeddingModel()
    original = _write_document(tmp_path, relative_path="spain/ES-001.md")
    _sync(policy_app_ready, [original], tmp_path, access_model, model)
    original_chunk_ids = _read_chunk_ids(policy_app_ready, "ES-001")
    calls_after_first_sync = len(model.calls)

    renamed = _write_document(tmp_path, relative_path="spain/ES-001-renamed.md")
    report = _sync(policy_app_ready, [renamed], tmp_path, access_model, model)

    assert report["updated_metadata"] == ["ES-001"]
    row = _read_document_row(policy_app_ready, "ES-001")
    assert row is not None
    assert row[3] == "spain/ES-001-renamed.md"
    assert _read_chunk_ids(policy_app_ready, "ES-001") == original_chunk_ids
    assert len(model.calls) == calls_after_first_sync
