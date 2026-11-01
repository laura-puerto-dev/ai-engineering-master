"""Tests for document extraction and ingestion."""

from datetime import date
from pathlib import Path

import pytest

from policy_consultant.ingestion import extract_text, ingest_documents
from policy_consultant.models import PolicyDocument


@pytest.fixture
def sample_document() -> PolicyDocument:
    return PolicyDocument(
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


def test_extracts_markdown_content(tmp_path: Path) -> None:
    path = tmp_path / "policy.md"
    content = "# Vacaciones\n\nLos empleados tienen derecho a vacaciones."
    path.write_text(content, encoding="utf-8")

    assert extract_text(path) == content


def test_rejects_unsupported_format(tmp_path: Path) -> None:
    path = tmp_path / "policy.pdf"

    with pytest.raises(ValueError, match="Unsupported document format"):
        extract_text(path)


def test_ingests_only_current_documents(
    sample_document: PolicyDocument,
    tmp_path: Path,
) -> None:
    current = sample_document.copy()
    superseded = sample_document.copy()
    superseded["status"] = "superseded"
    superseded["version"] = "0.9"
    superseded["effective_to"] = date(2026, 1, 1)

    path = tmp_path / current["path"]
    path.parent.mkdir(parents=True)
    path.write_text("# Current policy", encoding="utf-8")

    ingested = list(ingest_documents([current, superseded], tmp_path))

    assert len(ingested) == 1
    assert ingested[0]["content"] == "# Current policy"
    assert ingested[0]["metadata"]["version"] == "1.0"


def test_preserves_document_metadata(
    sample_document: PolicyDocument,
    tmp_path: Path,
) -> None:
    path = tmp_path / sample_document["path"]
    path.parent.mkdir(parents=True)
    path.write_text("# Policy", encoding="utf-8")

    ingested = list(ingest_documents([sample_document], tmp_path))

    assert ingested[0]["metadata"] == sample_document
    assert ingested[0]["metadata"] is not sample_document
    assert ingested[0]["metadata"]["allowed_roles"] == [
        "employee",
        "manager",
        "hr",
    ]


def test_ingestion_is_lazy(
    sample_document: PolicyDocument,
    tmp_path: Path,
) -> None:
    """A later document's file is never touched until it is actually pulled
    from the generator, proving content is read one at a time rather than
    all at once up front.
    """
    path = tmp_path / sample_document["path"]
    path.parent.mkdir(parents=True)
    path.write_text("# Policy", encoding="utf-8")

    missing = sample_document.copy()
    missing["document_id"] = "ES-002"
    missing["path"] = "data/corpus/spain/ES-002.md"

    generator = ingest_documents([sample_document, missing], tmp_path)

    first = next(generator)
    assert first["content"] == "# Policy"

    with pytest.raises(FileNotFoundError):
        next(generator)
