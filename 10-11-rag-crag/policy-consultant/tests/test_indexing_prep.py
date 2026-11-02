"""Tests for prepare_indexable_chunks and its renumbering helper."""

from collections.abc import Callable, Iterator
from datetime import date
from pathlib import Path

import pytest

from policy_consultant import indexing_prep
from policy_consultant.chunking import chunk_document
from policy_consultant.indexing_prep import _renumber_chunks, prepare_indexable_chunks
from policy_consultant.models import DocumentChunk, IngestedDocument, PolicyDocument


@pytest.fixture
def make_policy_document(tmp_path: Path) -> Callable[..., PolicyDocument]:
    """Write a markdown file under tmp_path and return the PolicyDocument
    pointing at it, so ingest_documents can read it directly."""

    def _make(
        document_id: str,
        content: str,
        *,
        version: str = "1.0",
    ) -> PolicyDocument:
        relative_path = f"data/corpus/{document_id}.md"
        file_path = tmp_path / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

        return PolicyDocument(
            document_id=document_id,
            path=relative_path,
            country="spain",
            language="es",
            allowed_roles=["employee", "manager", "hr"],
            version=version,
            effective_from=date(2026, 1, 1),
            effective_to=None,
            status="current",
        )

    return _make


@pytest.fixture
def make_document_chunk() -> Callable[..., DocumentChunk]:
    def _make(*, ordinal: int, text: str) -> DocumentChunk:
        return DocumentChunk(
            chunk_id=f"ES-001:1.0:{ordinal}",
            document_id="ES-001",
            ordinal=ordinal,
            section_path=["1. Section"],
            text=text,
        )

    return _make


def test_full_pipeline_from_documents_to_indexable_chunks(
    tmp_path: Path,
    make_policy_document: Callable[..., PolicyDocument],
) -> None:
    document = make_policy_document(
        "ES-001",
        "## 1. First\n\nFirst section text.\n\n## 2. Second\n\nSecond section text.\n",
    )

    items = list(
        prepare_indexable_chunks(
            [document], tmp_path, strategy="structured_recursive", max_chars=1000
        )
    )

    assert [item["chunk"]["text"] for item in items] == [
        "First section text.",
        "Second section text.",
    ]
    assert [item["chunk"]["section_path"] for item in items] == [["1. First"], ["2. Second"]]


def test_chunks_share_the_same_document_reference(
    tmp_path: Path,
    make_policy_document: Callable[..., PolicyDocument],
) -> None:
    document = make_policy_document(
        "ES-001",
        "## 1. First\n\nText one.\n\n## 2. Second\n\nText two.\n",
    )

    items = list(
        prepare_indexable_chunks(
            [document], tmp_path, strategy="structured_recursive", max_chars=1000
        )
    )

    assert len(items) == 2
    assert items[0]["document"] is items[1]["document"]
    assert items[0]["document"] == document


def test_ordinals_and_chunk_ids_follow_the_existing_format(
    tmp_path: Path,
    make_policy_document: Callable[..., PolicyDocument],
) -> None:
    document = make_policy_document(
        "ES-001",
        "## 1. First\n\nText one.\n\n## 2. Second\n\nText two.\n",
        version="1.3",
    )

    items = list(
        prepare_indexable_chunks(
            [document], tmp_path, strategy="structured_recursive", max_chars=1000
        )
    )

    assert [item["chunk"]["ordinal"] for item in items] == [0, 1]
    assert [item["chunk"]["chunk_id"] for item in items] == ["ES-001:1.3:0", "ES-001:1.3:1"]


def test_preserves_chunks_with_empty_section_path_when_they_have_content(
    tmp_path: Path,
    make_policy_document: Callable[..., PolicyDocument],
) -> None:
    document = make_policy_document("ES-001", "Just plain text with no headings at all.")

    items = list(
        prepare_indexable_chunks(
            [document], tmp_path, strategy="structured_recursive", max_chars=1000
        )
    )

    assert len(items) == 1
    assert items[0]["chunk"]["section_path"] == []
    assert items[0]["chunk"]["text"] == "Just plain text with no headings at all."


def test_renumber_chunks_drops_blank_text_and_renumbers(
    make_document_chunk: Callable[..., DocumentChunk],
) -> None:
    chunks = [
        make_document_chunk(ordinal=0, text="Real text."),
        make_document_chunk(ordinal=1, text="   "),
        make_document_chunk(ordinal=2, text="More real text."),
    ]

    renumbered = list(_renumber_chunks(iter(chunks), "ES-001", "1.0"))

    assert [chunk["text"] for chunk in renumbered] == ["Real text.", "More real text."]
    assert [chunk["ordinal"] for chunk in renumbered] == [0, 1]
    assert [chunk["chunk_id"] for chunk in renumbered] == ["ES-001:1.0:0", "ES-001:1.0:1"]


def test_lazy_across_documents(
    tmp_path: Path,
    make_policy_document: Callable[..., PolicyDocument],
) -> None:
    first = make_policy_document("ES-001", "## 1. First\n\nText.\n")
    missing = make_policy_document("ES-002", "## 1. First\n\nText.\n")
    (tmp_path / missing["path"]).unlink()

    stream = prepare_indexable_chunks(
        [first, missing], tmp_path, strategy="structured_recursive", max_chars=1000
    )

    first_item = next(stream)
    assert first_item["chunk"]["text"] == "Text."

    with pytest.raises(FileNotFoundError):
        next(stream)


def test_lazy_within_a_document(
    tmp_path: Path,
    make_policy_document: Callable[..., PolicyDocument],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document = make_policy_document(
        "ES-001",
        "## 1. First\n\nFirst.\n\n## 2. Second\n\nSecond.\n\n## 3. Third\n\nThird.\n",
    )

    pulled: list[DocumentChunk] = []

    def counting_chunk_document(
        document: IngestedDocument,
        strategy: str,
        max_chars: int,
    ) -> Iterator[DocumentChunk]:
        for chunk in chunk_document(document, strategy, max_chars):
            pulled.append(chunk)
            yield chunk

    monkeypatch.setattr(indexing_prep, "chunk_document", counting_chunk_document)

    stream = prepare_indexable_chunks(
        [document], tmp_path, strategy="structured_recursive", max_chars=1000
    )
    next(stream)

    assert len(pulled) == 1
