"""Tests for the pure parts of scripts/sync_corpus.py — report formatting
and exit-code selection. Both take only a SyncReport (plain data) and
return text/an int, so they're tested without Postgres, without the real
embedding model, and without running main() itself.

scripts/ is deliberately not an importable package (see pyproject.toml:
only src/policy_consultant is built as a wheel package) — scripts are
meant to be run directly with `uv run python scripts/...py`, not
imported. The module is loaded here straight from its file path instead
of adding scripts/ to sys.path or giving it an __init__.py.
"""

from __future__ import annotations

import importlib.util
import types
from pathlib import Path

import pytest

from policy_consultant.models import SyncReport

SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "sync_corpus.py"


def _load_script() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("sync_corpus_script", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def script() -> types.ModuleType:
    return _load_script()


def _make_report(**overrides: object) -> SyncReport:
    report = SyncReport(
        inserted=[],
        updated=[],
        updated_metadata=[],
        unchanged=[],
        rejected_stale=[],
        metadata_conflict=[],
        missing_from_manifest=[],
        failed=[],
    )
    report.update(overrides)  # type: ignore[typeddict-item]
    return report


# --- constants --------------------------------------------------------


def test_default_parameters_match_what_was_agreed(script: types.ModuleType) -> None:
    assert script.CHUNKING_STRATEGY == "structured_recursive"
    assert script.MAX_CHARS == 1000
    assert script.EMBEDDING_BATCH_SIZE == 32


# --- _format_report -----------------------------------------------------


def test_format_report_lists_document_ids_for_each_non_empty_category(
    script: types.ModuleType,
) -> None:
    report = _make_report(inserted=["ES-001", "GLB-002"], unchanged=["MX-001"])

    text = script._format_report(report)

    assert "Inserted (2): ES-001, GLB-002" in text
    assert "Unchanged (1): MX-001" in text
    assert "Updated (0): -" in text


def test_format_report_includes_failed_document_ids_and_messages(
    script: types.ModuleType,
) -> None:
    report = _make_report(failed=[("ES-007", "Unsupported document format: .pdf")])

    text = script._format_report(report)

    assert "Failed (1): ES-007: Unsupported document format: .pdf" in text


def test_format_report_on_an_entirely_empty_report(script: types.ModuleType) -> None:
    report = _make_report()

    text = script._format_report(report)

    assert text.count("(0): -") == 8  # 7 categories + failed


# --- _exit_code_for ------------------------------------------------------


def test_exit_code_is_zero_for_a_clean_report(script: types.ModuleType) -> None:
    report = _make_report(inserted=["ES-001"], unchanged=["MX-001"])

    assert script._exit_code_for(report) == 0


def test_exit_code_is_one_when_something_failed(script: types.ModuleType) -> None:
    report = _make_report(failed=[("ES-007", "boom")])

    assert script._exit_code_for(report) == 1


def test_exit_code_is_one_when_a_version_was_rejected_as_stale(
    script: types.ModuleType,
) -> None:
    report = _make_report(rejected_stale=["ES-003"])

    assert script._exit_code_for(report) == 1


def test_exit_code_is_one_on_a_metadata_conflict(script: types.ModuleType) -> None:
    report = _make_report(metadata_conflict=["ES-006"])

    assert script._exit_code_for(report) == 1


def test_exit_code_is_one_when_a_document_is_missing_from_the_manifest(
    script: types.ModuleType,
) -> None:
    report = _make_report(missing_from_manifest=["ES-999"])

    assert script._exit_code_for(report) == 1
