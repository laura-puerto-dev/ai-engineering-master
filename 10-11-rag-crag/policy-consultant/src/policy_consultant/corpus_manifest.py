"""Validation rules for config/corpus-manifest.yaml, derived from the
versioning and access-control model in docs/corpus-inventory.md: every
document must resolve to a real file, declare a valid country/role scope,
and carry an effective_from/effective_to/status combination consistent
with the corpus's versioning rules (a current document has no end date,
a superseded one must have one, and every policy has exactly one current
version).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import cast

import yaml

from policy_consultant.models import PolicyDocument

VALID_COUNTRIES = {"spain", "mexico", "england", "global"}
VALID_LANGUAGES = {"es", "en"}
VALID_ROLES = {"employee", "manager", "hr"}
VALID_STATUSES = {"current", "superseded"}


def load_documents(manifest_path: Path) -> list[PolicyDocument]:
    with manifest_path.open(encoding="utf-8") as file:
        data: object = yaml.safe_load(file)

    if not isinstance(data, dict):
        raise TypeError("Manifest must be a mapping")

    documents = data.get("documents")

    if not isinstance(documents, list):
        raise TypeError("Manifest 'documents' must be a list")

    if not all(isinstance(document, dict) for document in documents):
        raise TypeError("Each document must be a mapping")

    return cast("list[PolicyDocument]", documents)


def validate_fields(document: PolicyDocument, project_root: Path) -> None:
    document_id = document["document_id"]

    if not (project_root / document["path"]).is_file():
        raise FileNotFoundError(f"Document not found: {document['path']}")

    if document["country"] not in VALID_COUNTRIES:
        raise ValueError(f"Invalid country in {document_id}")

    if document["language"] not in VALID_LANGUAGES:
        raise ValueError(f"Invalid language in {document_id}")

    roles = document["allowed_roles"]
    if not isinstance(roles, list) or not roles or not set(roles) <= VALID_ROLES:
        raise ValueError(f"Invalid allowed_roles in {document_id}")

    if document["status"] not in VALID_STATUSES:
        raise ValueError(f"Invalid status in {document_id}")


def validate_lifecycle_dates(document: PolicyDocument) -> None:
    document_id = document["document_id"]
    effective_from = document["effective_from"]
    effective_to = document["effective_to"]
    status = document["status"]

    if not isinstance(effective_from, date):
        raise TypeError(f"Invalid effective_from in {document_id}")

    if effective_to is not None and (
        not isinstance(effective_to, date) or effective_to <= effective_from
    ):
        raise ValueError(f"Invalid effective_to in {document_id}")

    if status == "current" and effective_to is not None:
        raise ValueError(f"Current document has an end date: {document_id}")

    if status == "superseded" and effective_to is None:
        raise ValueError(f"Superseded document has no end date: {document_id}")


def validate_no_duplicate_versions(documents: list[PolicyDocument]) -> None:
    seen = set()
    for document in documents:
        key = (document["document_id"], document["version"])
        if key in seen:
            raise ValueError(f"Duplicate document version: {key}")
        seen.add(key)


def validate_version_history(documents: list[PolicyDocument]) -> None:
    """Every document_id must resolve to exactly one current version, and any
    superseded version must end on or before that current version begins.
    This holds regardless of how many documents or historical versions the
    corpus grows to, unlike a fixed document count.
    """
    by_document_id: dict[str, list[PolicyDocument]] = {}
    for document in documents:
        by_document_id.setdefault(document["document_id"], []).append(document)

    for document_id, versions in by_document_id.items():
        current_versions = [v for v in versions if v["status"] == "current"]

        if len(current_versions) != 1:
            raise ValueError(
                f"{document_id} must have exactly one current version, "
                f"found {len(current_versions)}"
            )

        current_start = current_versions[0]["effective_from"]

        for version in versions:
            effective_to = version["effective_to"]
            if (
                version["status"] == "superseded"
                and effective_to is not None
                and effective_to > current_start
            ):
                raise ValueError(
                    f"Superseded version of {document_id} ends after its current version begins"
                )


def validate_manifest(documents: list[PolicyDocument], project_root: Path) -> str:
    """Run every check against the loaded documents and return a human-readable
    summary. Raises on the first violation found.
    """
    for document in documents:
        validate_fields(document, project_root)
        validate_lifecycle_dates(document)

    validate_no_duplicate_versions(documents)
    validate_version_history(documents)

    current_count = sum(doc["status"] == "current" for doc in documents)
    superseded_count = sum(doc["status"] == "superseded" for doc in documents)
    policy_count = len({doc["document_id"] for doc in documents})

    return (
        f"Manifest validated successfully: {policy_count} policies "
        f"({current_count} current document(s), {superseded_count} superseded document(s))."
    )
