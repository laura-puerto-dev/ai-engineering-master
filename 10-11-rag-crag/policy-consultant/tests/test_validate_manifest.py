from datetime import date
from pathlib import Path

import pytest

from policy_consultant.corpus_manifest import (
    validate_fields,
    validate_lifecycle_dates,
    validate_no_duplicate_versions,
    validate_version_history,
)
from policy_consultant.models import PolicyDocument


@pytest.fixture
def sample_document() -> PolicyDocument:
    return PolicyDocument(
        document_id="MX-001",
        path="data/corpus/mexico/MX-001-vacaciones-y-permisos.md",
        country="mexico",
        language="es",
        allowed_roles=["employee", "manager", "hr"],
        version="1.0",
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 10, 31),
        status="superseded",
    )


def test_rejects_duplicate_document_versions(
    sample_document: PolicyDocument,
) -> None:
    duplicate = sample_document.copy()

    with pytest.raises(ValueError, match="Duplicate document version"):
        validate_no_duplicate_versions([sample_document, duplicate])


def test_rejects_invalid_roles(
    sample_document: PolicyDocument,
    tmp_path: Path,
) -> None:
    document = sample_document.copy()
    document["allowed_roles"] = ["admin"]

    document_path = tmp_path / document["path"]
    document_path.parent.mkdir(parents=True)
    document_path.touch()

    with pytest.raises(ValueError, match="Invalid allowed_roles"):
        validate_fields(document, tmp_path)


def test_rejects_current_document_with_end_date(
    sample_document: PolicyDocument,
) -> None:
    document = sample_document.copy()
    document["status"] = "current"

    with pytest.raises(ValueError, match="Current document has an end date"):
        validate_lifecycle_dates(document)


def test_rejects_overlapping_policy_versions(
    sample_document: PolicyDocument,
) -> None:
    superseded = sample_document.copy()
    superseded["effective_to"] = date(2026, 11, 15)

    current = sample_document.copy()
    current["version"] = "1.1"
    current["status"] = "current"
    current["effective_from"] = date(2026, 10, 31)
    current["effective_to"] = None

    with pytest.raises(ValueError, match="ends after its current version begins"):
        validate_version_history([superseded, current])


@pytest.mark.parametrize(
    ("field", "invalid_value", "expected_error"),
    [
        ("country", "france", "Invalid country"),
        ("language", "fr", "Invalid language"),
        ("status", "draft", "Invalid status"),
    ],
)
def test_rejects_invalid_metadata(
    sample_document: PolicyDocument,
    tmp_path: Path,
    field: str,
    invalid_value: str,
    expected_error: str,
) -> None:
    document = sample_document.copy()

    if field == "country":
        document["country"] = invalid_value
    elif field == "language":
        document["language"] = invalid_value
    elif field == "status":
        document["status"] = invalid_value

    document_path = tmp_path / document["path"]
    document_path.parent.mkdir(parents=True)
    document_path.touch()

    with pytest.raises(ValueError, match=expected_error):
        validate_fields(document, tmp_path)


@pytest.mark.parametrize("current_count", [0, 2])
def test_requires_exactly_one_current_version(
    sample_document: PolicyDocument,
    current_count: int,
) -> None:
    documents = []

    for index in range(current_count):
        document = sample_document.copy()
        document["version"] = f"1.{index + 1}"
        document["status"] = "current"
        document["effective_to"] = None
        documents.append(document)

    if current_count == 0:
        documents.append(sample_document.copy())

    with pytest.raises(
        ValueError,
        match="must have exactly one current version",
    ):
        validate_version_history(documents)
