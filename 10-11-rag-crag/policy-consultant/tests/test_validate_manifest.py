from datetime import date
from pathlib import Path

import pytest
import yaml

from policy_consultant.corpus_manifest import (
    load_access_model,
    validate_fields,
    validate_lifecycle_dates,
    validate_no_duplicate_versions,
    validate_version_history,
)
from policy_consultant.models import AccessModel, PolicyDocument


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


@pytest.fixture
def access_model() -> AccessModel:
    return AccessModel(
        countries={"spain", "mexico", "england", "global"},
        languages={"es", "en"},
        roles={"employee", "manager", "hr"},
    )


def test_rejects_duplicate_document_versions(
    sample_document: PolicyDocument,
) -> None:
    duplicate = sample_document.copy()

    with pytest.raises(ValueError, match="Duplicate document version"):
        validate_no_duplicate_versions([sample_document, duplicate])


def test_rejects_invalid_roles(
    sample_document: PolicyDocument,
    access_model: AccessModel,
    tmp_path: Path,
) -> None:
    document = sample_document.copy()
    document["allowed_roles"] = ["admin"]

    document_path = tmp_path / document["path"]
    document_path.parent.mkdir(parents=True)
    document_path.touch()

    with pytest.raises(ValueError, match="Invalid allowed_roles"):
        validate_fields(document, tmp_path, access_model)


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
    access_model: AccessModel,
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
        validate_fields(document, tmp_path, access_model)


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


def test_new_country_language_and_role_validate_via_config_alone(
    sample_document: PolicyDocument,
    tmp_path: Path,
) -> None:
    """A deployment can extend its access model with a country, language,
    and role this codebase has never seen, purely through AccessModel data
    — no change to corpus_manifest.py is needed.
    """
    document = sample_document.copy()
    document["country"] = "germany"
    document["language"] = "de"
    document["allowed_roles"] = ["finance_admin"]
    document["status"] = "current"
    document["effective_to"] = None

    document_path = tmp_path / document["path"]
    document_path.parent.mkdir(parents=True)
    document_path.touch()

    extended_access_model = AccessModel(
        countries={"germany"},
        languages={"de"},
        roles={"finance_admin"},
    )

    validate_fields(document, tmp_path, extended_access_model)


def test_load_access_model_reads_yaml(tmp_path: Path) -> None:
    path = tmp_path / "access-model.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "countries": ["spain", "germany"],
                "languages": ["es", "de"],
                "roles": ["employee", "finance_admin"],
            }
        ),
        encoding="utf-8",
    )

    access_model = load_access_model(path)

    assert access_model["countries"] == {"spain", "germany"}
    assert access_model["languages"] == {"es", "de"}
    assert access_model["roles"] == {"employee", "finance_admin"}


def test_load_access_model_rejects_non_mapping(tmp_path: Path) -> None:
    path = tmp_path / "access-model.yaml"
    path.write_text(yaml.safe_dump(["just", "a", "list"]), encoding="utf-8")

    with pytest.raises(TypeError, match="Access model must be a mapping"):
        load_access_model(path)


@pytest.mark.parametrize("key", ["countries", "languages", "roles"])
def test_load_access_model_rejects_empty_dimension(tmp_path: Path, key: str) -> None:
    content = {
        "countries": ["spain"],
        "languages": ["es"],
        "roles": ["employee"],
    }
    content[key] = []

    path = tmp_path / "access-model.yaml"
    path.write_text(yaml.safe_dump(content), encoding="utf-8")

    with pytest.raises(TypeError, match=f"Access model '{key}'"):
        load_access_model(path)


@pytest.mark.parametrize("key", ["countries", "languages", "roles"])
def test_load_access_model_rejects_blank_value(tmp_path: Path, key: str) -> None:
    content = {
        "countries": ["spain"],
        "languages": ["es"],
        "roles": ["employee"],
    }
    content[key] = [*content[key], "   "]

    path = tmp_path / "access-model.yaml"
    path.write_text(yaml.safe_dump(content), encoding="utf-8")

    with pytest.raises(ValueError, match=f"Access model '{key}' must not contain"):
        load_access_model(path)


@pytest.mark.parametrize("key", ["countries", "languages", "roles"])
def test_load_access_model_rejects_duplicate_value(tmp_path: Path, key: str) -> None:
    content = {
        "countries": ["spain"],
        "languages": ["es"],
        "roles": ["employee"],
    }
    content[key] = [*content[key], content[key][0]]

    path = tmp_path / "access-model.yaml"
    path.write_text(yaml.safe_dump(content), encoding="utf-8")

    with pytest.raises(ValueError, match=f"Access model '{key}' contains duplicate"):
        load_access_model(path)
