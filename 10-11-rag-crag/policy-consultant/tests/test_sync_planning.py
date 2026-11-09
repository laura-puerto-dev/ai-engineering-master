"""Tests for sync._plan_sync — pure, no PostgreSQL. sync_corpus's
DB-touching orchestration is covered by tests/test_sync.py instead.
"""

from __future__ import annotations

from datetime import date

import pytest

from policy_consultant.models import PolicyDocument
from policy_consultant.sync import _plan_sync, _StoredDocument


def _make_document(
    *,
    document_id: str = "ES-001",
    version: str = "1.0",
    country: str = "spain",
    language: str = "es",
    allowed_roles: list[str] | None = None,
    effective_from: date = date(2026, 1, 1),
    path: str = "data/corpus/spain/ES-001.md",
    status: str = "current",
) -> PolicyDocument:
    return PolicyDocument(
        document_id=document_id,
        path=path,
        country=country,
        language=language,
        allowed_roles=allowed_roles if allowed_roles is not None else ["employee", "manager"],
        version=version,
        effective_from=effective_from,
        effective_to=None,
        status=status,
    )


def _make_stored(
    *,
    version: str = "1.0",
    country: str = "spain",
    language: str = "es",
    allowed_roles: list[str] | None = None,
    effective_from: date = date(2026, 1, 1),
    path: str = "data/corpus/spain/ES-001.md",
) -> _StoredDocument:
    return _StoredDocument(
        version=version,
        country=country,
        language=language,
        allowed_roles=allowed_roles if allowed_roles is not None else ["employee", "manager"],
        effective_from=effective_from,
        path=path,
    )


def test_plans_a_new_document_not_yet_in_postgres() -> None:
    document = _make_document(document_id="ES-001")

    plan = _plan_sync([document], {})

    assert plan["to_insert"] == [document]
    assert plan["to_update"] == []
    assert plan["unchanged"] == []


def test_plans_a_version_update_when_effective_from_advances() -> None:
    document = _make_document(version="1.1", effective_from=date(2026, 6, 1))
    stored = {"ES-001": _make_stored(version="1.0", effective_from=date(2026, 1, 1))}

    plan = _plan_sync([document], stored)

    assert plan["to_update"] == [document]
    assert plan["rejected_stale"] == []


@pytest.mark.parametrize("stale_effective_from", [date(2026, 1, 1), date(2025, 12, 1)])
def test_rejects_a_version_change_whose_effective_from_does_not_advance(
    stale_effective_from: date,
) -> None:
    document = _make_document(version="1.1", effective_from=stale_effective_from)
    stored = {"ES-001": _make_stored(version="1.0", effective_from=date(2026, 1, 1))}

    plan = _plan_sync([document], stored)

    assert plan["rejected_stale"] == ["ES-001"]
    assert plan["to_update"] == []


def test_unchanged_when_same_version_and_nothing_else_differs() -> None:
    document = _make_document()
    stored = {"ES-001": _make_stored()}

    plan = _plan_sync([document], stored)

    assert plan["unchanged"] == ["ES-001"]
    assert plan["to_update_metadata"] == []
    assert plan["metadata_conflict"] == []


def test_unchanged_when_allowed_roles_differ_only_in_order() -> None:
    document = _make_document(allowed_roles=["manager", "employee"])
    stored = {"ES-001": _make_stored(allowed_roles=["employee", "manager"])}

    plan = _plan_sync([document], stored)

    assert plan["unchanged"] == ["ES-001"]


def test_plans_metadata_update_when_allowed_roles_actually_differ() -> None:
    document = _make_document(allowed_roles=["employee", "manager", "hr"])
    stored = {"ES-001": _make_stored(allowed_roles=["employee", "manager"])}

    plan = _plan_sync([document], stored)

    assert plan["to_update_metadata"] == [document]
    assert plan["unchanged"] == []


def test_plans_metadata_update_when_path_differs() -> None:
    document = _make_document(path="data/corpus/spain/renamed.md")
    stored = {"ES-001": _make_stored(path="data/corpus/spain/ES-001.md")}

    plan = _plan_sync([document], stored)

    assert plan["to_update_metadata"] == [document]


@pytest.mark.parametrize(
    "overrides",
    [
        {"country": "mexico"},
        {"language": "en"},
        {"effective_from": date(2026, 2, 1)},
    ],
)
def test_flags_metadata_conflict_when_country_language_or_effective_from_differ(
    overrides: dict[str, object],
) -> None:
    document = _make_document(**overrides)  # type: ignore[arg-type]
    stored = {"ES-001": _make_stored()}

    plan = _plan_sync([document], stored)

    assert plan["metadata_conflict"] == ["ES-001"]
    assert plan["to_update_metadata"] == []
    assert plan["unchanged"] == []


def test_metadata_conflict_takes_priority_over_a_concurrent_safe_change() -> None:
    document = _make_document(country="mexico", allowed_roles=["employee", "manager", "hr"])
    stored = {"ES-001": _make_stored(allowed_roles=["employee", "manager"])}

    plan = _plan_sync([document], stored)

    assert plan["metadata_conflict"] == ["ES-001"]
    assert plan["to_update_metadata"] == []


def test_flags_a_stored_document_missing_from_the_current_manifest() -> None:
    plan = _plan_sync([], {"ES-999": _make_stored()})

    assert plan["missing_from_manifest"] == ["ES-999"]


def test_superseded_manifest_entries_do_not_prevent_a_missing_flag() -> None:
    superseded = _make_document(document_id="ES-999", status="superseded")
    plan = _plan_sync([superseded], {"ES-999": _make_stored()})

    # ES-999 has no *current* manifest entry, so it is still reported as
    # missing — a superseded-only record does not count as "still present".
    assert plan["missing_from_manifest"] == ["ES-999"]


def test_plans_a_mixed_batch_correctly() -> None:
    new_doc = _make_document(document_id="ES-001")
    updated_doc = _make_document(
        document_id="ES-002", version="1.1", effective_from=date(2026, 6, 1)
    )
    stale_doc = _make_document(document_id="ES-003", version="1.1", effective_from=date(2025, 1, 1))
    unchanged_doc = _make_document(document_id="ES-004")
    metadata_doc = _make_document(document_id="ES-005", allowed_roles=["hr"])
    conflict_doc = _make_document(document_id="ES-006", country="mexico")

    stored = {
        "ES-002": _make_stored(version="1.0", effective_from=date(2026, 1, 1)),
        "ES-003": _make_stored(version="1.0", effective_from=date(2026, 1, 1)),
        "ES-004": _make_stored(),
        "ES-005": _make_stored(allowed_roles=["employee", "manager"]),
        "ES-006": _make_stored(),
        "ES-999": _make_stored(),
    }

    plan = _plan_sync(
        [new_doc, updated_doc, stale_doc, unchanged_doc, metadata_doc, conflict_doc],
        stored,
    )

    assert [doc["document_id"] for doc in plan["to_insert"]] == ["ES-001"]
    assert [doc["document_id"] for doc in plan["to_update"]] == ["ES-002"]
    assert plan["rejected_stale"] == ["ES-003"]
    assert plan["unchanged"] == ["ES-004"]
    assert [doc["document_id"] for doc in plan["to_update_metadata"]] == ["ES-005"]
    assert plan["metadata_conflict"] == ["ES-006"]
    assert plan["missing_from_manifest"] == ["ES-999"]
