"""Tests for the pure parts of scripts/evaluation/calibrate_threshold.py:
evidence matching and loading the real calibration question file. Real
BGE-M3 retrieval and PostgreSQL access (main(), _run_calibration) are
exercised manually when the script is actually run — the same category
as scripts/smoke_test_rag.py — and are not covered here.

scripts/ is deliberately not an importable package (see
test_sync_corpus_script.py's own docstring) — the module is loaded
straight from its file path instead of adding scripts/ to sys.path or
giving it an __init__.py.
"""

from __future__ import annotations

import importlib.util
import types
from pathlib import Path

import pytest

from policy_consultant.models import RetrievedChunk

SCRIPT_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "scripts"
    / "evaluation"
    / "calibrate_threshold.py"
)


def _load_script() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("calibrate_threshold_script", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def script() -> types.ModuleType:
    return _load_script()


def _chunk(chunk_id: str, document_id: str, distance: float) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        document_id=document_id,
        version="1.0",
        section_path=["1. Section"],
        text="text",
        distance=distance,
    )


# --- _find_expected_evidence --------------------------------------------


def test_finds_evidence_at_rank_zero(script: types.ModuleType) -> None:
    retrieved = [_chunk("A:1.0:0", "A", 0.1), _chunk("B:1.0:0", "B", 0.5)]
    expected = [{"chunk_id": "A:1.0:0", "document_id": "A"}]

    matches = script._find_expected_evidence(retrieved, expected)

    assert matches == [
        {"chunk_id": "A:1.0:0", "document_id": "A", "found": True, "rank": 0, "distance": 0.1}
    ]


def test_finds_evidence_at_a_later_rank(script: types.ModuleType) -> None:
    retrieved = [_chunk("A:1.0:0", "A", 0.1), _chunk("B:1.0:0", "B", 0.5)]
    expected = [{"chunk_id": "B:1.0:0", "document_id": "B"}]

    matches = script._find_expected_evidence(retrieved, expected)

    assert matches[0]["found"] is True
    assert matches[0]["rank"] == 1
    assert matches[0]["distance"] == 0.5


def test_reports_not_found_when_chunk_is_absent_from_retrieved(script: types.ModuleType) -> None:
    retrieved = [_chunk("A:1.0:0", "A", 0.1)]
    expected = [{"chunk_id": "C:1.0:0", "document_id": "C"}]

    matches = script._find_expected_evidence(retrieved, expected)

    assert matches == [
        {"chunk_id": "C:1.0:0", "document_id": "C", "found": False, "rank": None, "distance": None}
    ]


def test_reports_not_found_when_nothing_was_retrieved_at_all(script: types.ModuleType) -> None:
    expected = [{"chunk_id": "A:1.0:0", "document_id": "A"}]

    matches = script._find_expected_evidence([], expected)

    assert matches[0]["found"] is False
    assert matches[0]["rank"] is None


def test_handles_multiple_expected_evidence_entries_independently(script: types.ModuleType) -> None:
    retrieved = [_chunk("A:1.0:0", "A", 0.1)]
    expected = [
        {"chunk_id": "A:1.0:0", "document_id": "A"},
        {"chunk_id": "Z:1.0:0", "document_id": "Z"},
    ]

    matches = script._find_expected_evidence(retrieved, expected)

    assert matches[0]["found"] is True
    assert matches[1]["found"] is False


def test_matches_only_the_exact_chunk_not_merely_the_same_document(
    script: types.ModuleType,
) -> None:
    """A different chunk from the right document must not count as a
    match — only the specific fragment that contains the fact does.
    """
    retrieved = [_chunk("A:1.0:7", "A", 0.2)]
    expected = [{"chunk_id": "A:1.0:3", "document_id": "A"}]

    matches = script._find_expected_evidence(retrieved, expected)

    assert matches[0]["found"] is False


def test_returns_empty_list_for_an_abstain_question_with_no_expected_evidence(
    script: types.ModuleType,
) -> None:
    retrieved = [_chunk("A:1.0:0", "A", 0.1)]

    assert script._find_expected_evidence(retrieved, []) == []


# --- _load_calibration_questions ----------------------------------------


def test_loads_the_real_calibration_file(script: types.ModuleType) -> None:
    questions = script._load_calibration_questions(script.CALIBRATION_QUESTIONS_PATH)

    assert len(questions) == 8
    assert {q["expected_outcome"] for q in questions} == {"answerable", "abstain"}
    assert sum(q["expected_outcome"] == "answerable" for q in questions) == 4
    assert sum(q["expected_outcome"] == "abstain" for q in questions) == 4
