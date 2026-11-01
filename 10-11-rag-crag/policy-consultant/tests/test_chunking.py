"""Tests for the structured_recursive chunking strategy."""

from collections.abc import Callable
from datetime import date

import pytest

from policy_consultant.chunking import chunk_document, structured_recursive
from policy_consultant.models import IngestedDocument, PolicyDocument


@pytest.fixture
def make_document() -> Callable[[str], IngestedDocument]:
    metadata = PolicyDocument(
        document_id="ES-001",
        path="data/corpus/spain/ES-001.md",
        country="spain",
        language="es",
        allowed_roles=["employee", "manager", "hr"],
        version="1.0",
        effective_from=date(2026, 1, 1),
        effective_to=None,
        status="current",
    )

    def _make(content: str) -> IngestedDocument:
        return IngestedDocument(metadata=metadata, content=content)

    return _make


def test_splits_by_h2_sections(make_document: Callable[[str], IngestedDocument]) -> None:
    content = "## 1. First\n\nFirst section text.\n\n## 2. Second\n\nSecond section text.\n"
    document = make_document(content)

    chunks = list(structured_recursive(document, max_chars=1000))

    assert [chunk["section_path"] for chunk in chunks] == [["1. First"], ["2. Second"]]
    assert [chunk["text"] for chunk in chunks] == ["First section text.", "Second section text."]
    assert [chunk["ordinal"] for chunk in chunks] == [0, 1]
    assert [chunk["chunk_id"] for chunk in chunks] == ["ES-001:1.0:0", "ES-001:1.0:1"]


def test_nested_heading_with_empty_parent(
    make_document: Callable[[str], IngestedDocument],
) -> None:
    content = (
        "## 5. Location\n\n"
        "### 5.1 Within country\n\nText A.\n\n"
        "### 5.2 Abroad\n\nText B.\n"
    )
    document = make_document(content)

    chunks = list(structured_recursive(document, max_chars=1000))

    assert len(chunks) == 2
    assert chunks[0]["section_path"] == ["5. Location", "5.1 Within country"]
    assert chunks[1]["section_path"] == ["5. Location", "5.2 Abroad"]
    assert [chunk["text"] for chunk in chunks] == ["Text A.", "Text B."]


def test_leading_content_before_first_section(
    make_document: Callable[[str], IngestedDocument],
) -> None:
    content = "# Title\n\nSome preamble metadata.\n\n## 1. First\n\nSection text.\n"
    document = make_document(content)

    chunks = list(structured_recursive(document, max_chars=1000))

    assert chunks[0]["section_path"] == []
    assert "Title" in chunks[0]["text"]
    assert "Some preamble metadata." in chunks[0]["text"]
    assert chunks[1]["section_path"] == ["1. First"]
    assert chunks[1]["text"] == "Section text."


def test_section_under_max_chars_stays_whole(
    make_document: Callable[[str], IngestedDocument],
) -> None:
    content = "## 1. Short\n\nShort text here.\n"
    document = make_document(content)

    chunks = list(structured_recursive(document, max_chars=1000))

    assert len(chunks) == 1
    assert chunks[0]["text"] == "Short text here."


def test_long_section_splits_by_paragraph(
    make_document: Callable[[str], IngestedDocument],
) -> None:
    paragraph_a = "A" * 40
    paragraph_b = "B" * 40
    paragraph_c = "C" * 40
    content = f"## 1. Long\n\n{paragraph_a}\n\n{paragraph_b}\n\n{paragraph_c}\n"
    document = make_document(content)

    chunks = list(structured_recursive(document, max_chars=50))

    assert [chunk["text"] for chunk in chunks] == [paragraph_a, paragraph_b, paragraph_c]
    assert all(chunk["section_path"] == ["1. Long"] for chunk in chunks)


def test_consecutive_paragraphs_merge_up_to_max_chars(
    make_document: Callable[[str], IngestedDocument],
) -> None:
    paragraphs = ["A" * 100, "B" * 100, "C" * 100, "D" * 100]
    content = "## 1. Section\n\n" + "\n\n".join(paragraphs) + "\n"
    document = make_document(content)

    # Combined body is 406 chars (> 250), so it must split; two paragraphs
    # (202 chars) fit within 250, three (304 chars) don't.
    chunks = list(structured_recursive(document, max_chars=250))

    assert [chunk["text"] for chunk in chunks] == [
        f"{paragraphs[0]}\n\n{paragraphs[1]}",
        f"{paragraphs[2]}\n\n{paragraphs[3]}",
    ]
    assert all(len(chunk["text"]) <= 250 for chunk in chunks)


def test_table_breaks_paragraph_grouping(
    make_document: Callable[[str], IngestedDocument],
) -> None:
    intro = "Intro paragraph."
    table = "| A | B |\n| --- | --- |\n| 1 | 2 |"
    outro = "Outro paragraph."
    content = f"## 1. Section\n\n{intro}\n\n{table}\n\n{outro}\n"
    document = make_document(content)

    # max_chars is small enough to force splitting even though intro and
    # outro would otherwise be short enough to merge with a neighbor.
    chunks = list(structured_recursive(document, max_chars=60))

    assert [chunk["text"] for chunk in chunks] == [intro, table, outro]


def test_table_block_never_split(make_document: Callable[[str], IngestedDocument]) -> None:
    table = "\n".join(
        ["| A | B |", "| --- | --- |"] + [f"| row{i} | value{i} |" for i in range(20)]
    )
    content = f"## 1. Table\n\n{table}\n"
    document = make_document(content)

    chunks = list(structured_recursive(document, max_chars=50))

    assert len(chunks) == 1
    assert chunks[0]["text"] == table


def test_list_splits_between_items_not_within(
    make_document: Callable[[str], IngestedDocument],
) -> None:
    items = [f"- Item number {i} with some extra padding text." for i in range(10)]
    list_block = "\n".join(items)
    content = f"## 1. List\n\n{list_block}\n"
    document = make_document(content)

    chunks = list(structured_recursive(document, max_chars=120))

    assert len(chunks) > 1
    assert "\n".join(chunk["text"] for chunk in chunks) == list_block
    for item in items:
        assert sum(item in chunk["text"] for chunk in chunks) == 1


def test_long_prose_paragraph_splits_at_word_boundaries(
    make_document: Callable[[str], IngestedDocument],
) -> None:
    words = [f"word{i}" for i in range(30)]
    paragraph = " ".join(words)
    content = f"## 1. Long\n\n{paragraph}\n"
    document = make_document(content)

    chunks = list(structured_recursive(document, max_chars=40))

    assert len(chunks) > 1
    assert " ".join(chunk["text"] for chunk in chunks) == paragraph
    for chunk in chunks:
        assert len(chunk["text"]) <= 40
        assert all(word in words for word in chunk["text"].split())


def test_single_word_longer_than_max_chars_is_hard_cut(
    make_document: Callable[[str], IngestedDocument],
) -> None:
    long_word = "x" * 100
    content = f"## 1. Long\n\n{long_word}\n"
    document = make_document(content)

    chunks = list(structured_recursive(document, max_chars=30))

    assert len(chunks) == 4
    assert "".join(chunk["text"] for chunk in chunks) == long_word
    assert all(len(chunk["text"]) <= 30 for chunk in chunks)


def test_chunk_ids_unique_and_ordinals_increase(
    make_document: Callable[[str], IngestedDocument],
) -> None:
    content = (
        "## 1. First\n\nText one.\n\n## 2. Second\n\nText two.\n\n## 3. Third\n\nText three.\n"
    )
    document = make_document(content)

    chunks = list(structured_recursive(document, max_chars=1000))

    ordinals = [chunk["ordinal"] for chunk in chunks]
    assert ordinals == sorted(ordinals)
    assert len(set(ordinals)) == len(ordinals)
    ids = [chunk["chunk_id"] for chunk in chunks]
    assert len(set(ids)) == len(ids)
    assert ids == [f"ES-001:1.0:{ordinal}" for ordinal in ordinals]


def test_chunk_document_rejects_unknown_strategy(
    make_document: Callable[[str], IngestedDocument],
) -> None:
    document = make_document("## 1. X\n\nY.\n")

    with pytest.raises(ValueError, match="Unsupported chunking strategy"):
        chunk_document(document, "nonexistent", max_chars=1000)


def test_document_without_headings_falls_back_to_single_section(
    make_document: Callable[[str], IngestedDocument],
) -> None:
    content = "Just plain text with no headings at all."
    document = make_document(content)

    chunks = list(structured_recursive(document, max_chars=1000))

    assert len(chunks) == 1
    assert chunks[0]["section_path"] == []
    assert chunks[0]["text"] == content


@pytest.mark.parametrize("max_chars", [0, -5])
def test_rejects_non_positive_max_chars(
    make_document: Callable[[str], IngestedDocument],
    max_chars: int,
) -> None:
    document = make_document("## 1. X\n\nY.\n")

    with pytest.raises(ValueError, match="max_chars must be greater than 0"):
        structured_recursive(document, max_chars)
