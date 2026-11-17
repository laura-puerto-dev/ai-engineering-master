"""Tests for the pure parts of scripts/run_evaluation.py: evidence
matching/recall, abstention-outcome metrics, citation structural
validation, dataset loading, and the --run safety guard.

Real embeddings, PostgreSQL retrieval, and Claude generation
(_run_question, main() called with --run) are exercised manually when
the script is actually run — the same category as
scripts/smoke_test_rag.py — and are not covered here.

scripts/ is deliberately not an importable package (see
test_sync_corpus_script.py's own docstring) — the module is loaded
straight from its file path instead of adding scripts/ to sys.path or
giving it an __init__.py.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import types
from pathlib import Path
from typing import Any

import pytest

from policy_consultant.models import Citation, RetrievedChunk

SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "run_evaluation.py"


def _load_script() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("run_evaluation_script", SCRIPT_PATH)
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


def _citation(chunk_id: str, document_id: str = "A") -> Citation:
    return Citation(
        document_id=document_id, version="1.0", section_path=["1. Section"], chunk_id=chunk_id
    )


# --- _find_expected_evidence ------------------------------------------------


def test_finds_evidence_at_rank_zero(script: types.ModuleType) -> None:
    retrieved = [_chunk("A:1.0:0", "A", 0.1)]
    expected = [{"chunk_id": "A:1.0:0", "document_id": "A"}]

    matches = script._find_expected_evidence(retrieved, expected)

    assert matches[0]["found"] is True
    assert matches[0]["rank"] == 0


def test_reports_not_found_when_absent_from_retrieved(script: types.ModuleType) -> None:
    retrieved = [_chunk("A:1.0:0", "A", 0.1)]
    expected = [{"chunk_id": "Z:1.0:0", "document_id": "Z"}]

    matches = script._find_expected_evidence(retrieved, expected)

    assert matches[0]["found"] is False
    assert matches[0]["rank"] is None


def test_matches_only_the_exact_chunk_not_merely_the_same_document(
    script: types.ModuleType,
) -> None:
    retrieved = [_chunk("A:1.0:7", "A", 0.2)]
    expected = [{"chunk_id": "A:1.0:3", "document_id": "A"}]

    matches = script._find_expected_evidence(retrieved, expected)

    assert matches[0]["found"] is False


# --- _evidence_recall_summary -----------------------------------------------


def test_recall_summary_for_a_single_found_evidence(script: types.ModuleType) -> None:
    matches = [{"chunk_id": "A", "document_id": "A", "found": True, "rank": 0, "distance": 0.1}]

    summary = script._evidence_recall_summary(matches)

    assert summary == {"expected_count": 1, "found_count": 1, "all_found": True, "any_found": True}


def test_recall_summary_for_multiple_evidence_all_found(script: types.ModuleType) -> None:
    matches = [
        {"chunk_id": "A", "document_id": "A", "found": True, "rank": 0, "distance": 0.1},
        {"chunk_id": "B", "document_id": "B", "found": True, "rank": 1, "distance": 0.2},
    ]

    summary = script._evidence_recall_summary(matches)

    assert summary == {"expected_count": 2, "found_count": 2, "all_found": True, "any_found": True}


def test_recall_summary_for_partially_recovered_evidence(script: types.ModuleType) -> None:
    """A question with two expected chunks where only one was retrieved
    must not be reported as "all evidence found" just because something
    relevant came back.
    """
    matches = [
        {"chunk_id": "A", "document_id": "A", "found": True, "rank": 0, "distance": 0.1},
        {"chunk_id": "B", "document_id": "B", "found": False, "rank": None, "distance": None},
    ]

    summary = script._evidence_recall_summary(matches)

    assert summary == {"expected_count": 2, "found_count": 1, "all_found": False, "any_found": True}


def test_recall_summary_is_none_for_an_abstain_question(script: types.ModuleType) -> None:
    assert script._evidence_recall_summary([]) is None


# --- _aggregate_retrieval_metrics -------------------------------------------


def test_aggregate_retrieval_metrics_skips_abstain_questions(script: types.ModuleType) -> None:
    summaries = [
        {"expected_count": 1, "found_count": 1, "all_found": True, "any_found": True},
        {"expected_count": 2, "found_count": 1, "all_found": False, "any_found": True},
        None,  # abstain question: must not be counted as 0/0 success or failure
    ]

    metrics = script._aggregate_retrieval_metrics(summaries)

    assert metrics["answerable_with_evidence"] == 2
    assert metrics["evidence_recall_at_k"] == pytest.approx(2 / 3)
    assert metrics["pct_all_evidence_found"] == pytest.approx(0.5)
    assert metrics["pct_any_evidence_found"] == pytest.approx(1.0)


def test_aggregate_retrieval_metrics_with_no_applicable_questions(
    script: types.ModuleType,
) -> None:
    metrics = script._aggregate_retrieval_metrics([None, None])

    assert metrics["answerable_with_evidence"] == 0
    assert metrics["evidence_recall_at_k"] is None


# --- _aggregate_abstention_metrics ------------------------------------------


def test_aggregate_abstention_metrics_reports_both_classes_separately(
    script: types.ModuleType,
) -> None:
    records = [
        ("answerable", False),  # answered correctly
        ("answerable", True),  # incorrectly abstained
        ("abstain", True),  # correctly abstained
        ("abstain", False),  # incorrectly answered
    ]

    metrics = script._aggregate_abstention_metrics(records)

    assert metrics["answerable_questions"] == 2
    assert metrics["answerable_answered_rate"] == pytest.approx(0.5)
    assert metrics["abstain_questions"] == 2
    assert metrics["abstain_correct_rate"] == pytest.approx(0.5)


# --- _check_outcome ----------------------------------------------------------


def test_check_outcome_answerable_matches_when_not_abstained(script: types.ModuleType) -> None:
    assert script._check_outcome("answerable", False)["matches_expected"] is True


def test_check_outcome_answerable_fails_when_abstained(script: types.ModuleType) -> None:
    assert script._check_outcome("answerable", True)["matches_expected"] is False


def test_check_outcome_abstain_matches_when_abstained(script: types.ModuleType) -> None:
    assert script._check_outcome("abstain", True)["matches_expected"] is True


def test_check_outcome_abstain_fails_when_answered(script: types.ModuleType) -> None:
    assert script._check_outcome("abstain", False)["matches_expected"] is False


# --- _check_citation_structure ----------------------------------------------


def test_citation_structure_valid_when_citation_is_in_retrieved(script: types.ModuleType) -> None:
    retrieved = [_chunk("A:1.0:0", "A", 0.1)]
    citations = [_citation("A:1.0:0")]

    result = script._check_citation_structure(citations, retrieved)

    assert result == {
        "citations_checked": 1,
        "citations_from_retrieved": True,
        "invalid_citation_chunk_ids": [],
    }


def test_citation_structure_invalid_when_citation_is_not_in_retrieved(
    script: types.ModuleType,
) -> None:
    retrieved = [_chunk("A:1.0:0", "A", 0.1)]
    citations = [_citation("Z:1.0:0", "Z")]

    result = script._check_citation_structure(citations, retrieved)

    assert result["citations_from_retrieved"] is False
    assert result["invalid_citation_chunk_ids"] == ["Z:1.0:0"]


def test_citation_structure_with_no_citations_at_all(script: types.ModuleType) -> None:
    result = script._check_citation_structure([], [_chunk("A:1.0:0", "A", 0.1)])

    assert result == {
        "citations_checked": 0,
        "citations_from_retrieved": True,
        "invalid_citation_chunk_ids": [],
    }


# --- _load_eval_questions ----------------------------------------------------


def test_loads_the_real_eval_file(script: types.ModuleType) -> None:
    questions = script._load_eval_questions(script.EVAL_QUESTIONS_PATH)

    assert len(questions) == 20
    assert sum(q["expected_outcome"] == "answerable" for q in questions) == 14
    assert sum(q["expected_outcome"] == "abstain" for q in questions) == 6


# --- --run safety guard -------------------------------------------------------


def test_parse_args_defaults_to_no_run(script: types.ModuleType) -> None:
    assert script._parse_args([]).run is False


def test_parse_args_run_flag_enables_run(script: types.ModuleType) -> None:
    assert script._parse_args(["--run"]).run is True


def test_main_without_run_flag_never_touches_the_real_pipeline(
    script: types.ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without --run, main() must return after loading and validating the
    dataset alone — never constructing the embedding model, opening a
    database connection, or building a Claude generator. Each of those is
    monkeypatched to raise if called at all, so any accidental code path
    that reaches them fails this test immediately rather than silently
    making a real (billed) call.
    """

    def _boom(*args: object, **kwargs: object) -> None:
        raise AssertionError("must not be called without --run")

    monkeypatch.setattr(script, "LocalBgeM3EmbeddingModel", _boom)
    monkeypatch.setattr(script, "admin_connection", _boom)
    monkeypatch.setattr(script, "app_connection", _boom)
    monkeypatch.setattr(script, "ClaudeAnswerGenerator", _boom)

    script.main([])


# --- _sha256_hex --------------------------------------------------------------


def test_sha256_hex_matches_a_direct_hash_of_the_same_file(
    script: types.ModuleType, tmp_path: Path
) -> None:
    file_path = tmp_path / "sample.yaml"
    file_path.write_text("questions: []\n", encoding="utf-8")

    assert script._sha256_hex(file_path) == hashlib.sha256(file_path.read_bytes()).hexdigest()


# --- _check_compatible ---------------------------------------------------------


def _settings(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "variant": "rag",
        "questions_hash": "abc123",
        "embedding_model": {"model_id": "BAAI/bge-m3", "revision": "rev1", "dimensions": 1024},
        "generation_model": {"model": "claude-sonnet-5", "disable_thinking": True},
        "top_k": 5,
    }
    base.update(overrides)
    return base


def test_check_compatible_accepts_matching_settings(script: types.ModuleType) -> None:
    script._check_compatible(
        _settings(),
        questions_hash="abc123",
        embedding_model={"model_id": "BAAI/bge-m3", "revision": "rev1", "dimensions": 1024},
        generation_model={"model": "claude-sonnet-5", "disable_thinking": True},
        top_k=5,
    )


def test_check_compatible_rejects_a_different_questions_hash(script: types.ModuleType) -> None:
    with pytest.raises(ValueError, match="questions_hash"):
        script._check_compatible(
            _settings(questions_hash="different-hash"),
            questions_hash="abc123",
            embedding_model={"model_id": "BAAI/bge-m3", "revision": "rev1", "dimensions": 1024},
            generation_model={"model": "claude-sonnet-5", "disable_thinking": True},
            top_k=5,
        )


def test_check_compatible_rejects_a_different_embedding_model_revision(
    script: types.ModuleType,
) -> None:
    with pytest.raises(ValueError, match="embedding_model"):
        script._check_compatible(
            _settings(
                embedding_model={
                    "model_id": "BAAI/bge-m3",
                    "revision": "other-rev",
                    "dimensions": 1024,
                }
            ),
            questions_hash="abc123",
            embedding_model={"model_id": "BAAI/bge-m3", "revision": "rev1", "dimensions": 1024},
            generation_model={"model": "claude-sonnet-5", "disable_thinking": True},
            top_k=5,
        )


def test_check_compatible_rejects_a_different_top_k(script: types.ModuleType) -> None:
    with pytest.raises(ValueError, match="top_k"):
        script._check_compatible(
            _settings(top_k=10),
            questions_hash="abc123",
            embedding_model={"model_id": "BAAI/bge-m3", "revision": "rev1", "dimensions": 1024},
            generation_model={"model": "claude-sonnet-5", "disable_thinking": True},
            top_k=5,
        )


# --- _resume_state -------------------------------------------------------------


def _question(question_id: str) -> dict[str, Any]:
    return {"id": question_id, "question": "q", "expected_outcome": "answerable"}


def test_resume_state_with_no_existing_results_runs_everything(script: types.ModuleType) -> None:
    questions = [_question("eval-01"), _question("eval-02")]

    completed, pending = script._resume_state(questions, None)

    assert completed == []
    assert pending == questions


def test_resume_state_skips_already_completed_questions(script: types.ModuleType) -> None:
    questions = [_question("eval-01"), _question("eval-02"), _question("eval-03")]
    existing = {"results": [{"id": "eval-01", "answer": "..."}]}

    completed, pending = script._resume_state(questions, existing)

    assert [result["id"] for result in completed] == ["eval-01"]
    assert [question["id"] for question in pending] == ["eval-02", "eval-03"]


def test_resume_state_preserves_existing_manual_review_fields(script: types.ModuleType) -> None:
    questions = [_question("eval-01")]
    existing = {
        "results": [
            {
                "id": "eval-01",
                "manual_review": {
                    "factual_correctness": "correct",
                    "evidence_sufficiency": "sufficient",
                    "citation_support": "supported",
                    "notes": "checked by Laura",
                },
            }
        ]
    }

    completed, _pending = script._resume_state(questions, existing)

    assert completed[0]["manual_review"]["factual_correctness"] == "correct"
    assert completed[0]["manual_review"]["notes"] == "checked by Laura"


def test_resume_state_with_every_question_already_completed(script: types.ModuleType) -> None:
    questions = [_question("eval-01"), _question("eval-02")]
    existing = {"results": [{"id": "eval-01"}, {"id": "eval-02"}]}

    completed, pending = script._resume_state(questions, existing)

    assert len(completed) == 2
    assert pending == []


# --- _write_results_json (atomic, incremental save) ----------------------------


def test_write_results_json_saves_progress_after_each_question(
    script: types.ModuleType, tmp_path: Path
) -> None:
    results_path = tmp_path / "rag-eval-results.json"
    questions_path = script.EVAL_QUESTIONS_PATH

    first_result = {
        "id": "eval-01",
        "expected_outcome": "answerable",
        "evidence_recall": None,
        "generated": {"abstained": False},
        "citation_structural_check": {"citations_checked": 0, "invalid_citation_chunk_ids": []},
    }
    script._write_results_json(
        [first_result],
        script._compute_metrics([first_result]),
        path=results_path,
        model_id="BAAI/bge-m3",
        revision="rev1",
        dimensions=1024,
        top_k=5,
        questions_path=questions_path,
        questions_hash="abc123",
        total_count=20,
    )
    payload_after_first = json.loads(results_path.read_text(encoding="utf-8"))
    assert payload_after_first["completed_count"] == 1
    assert payload_after_first["total_count"] == 20
    assert [r["id"] for r in payload_after_first["results"]] == ["eval-01"]

    second_result = {**first_result, "id": "eval-02"}
    script._write_results_json(
        [first_result, second_result],
        script._compute_metrics([first_result, second_result]),
        path=results_path,
        model_id="BAAI/bge-m3",
        revision="rev1",
        dimensions=1024,
        top_k=5,
        questions_path=questions_path,
        questions_hash="abc123",
        total_count=20,
    )
    payload_after_second = json.loads(results_path.read_text(encoding="utf-8"))
    assert payload_after_second["completed_count"] == 2
    assert [r["id"] for r in payload_after_second["results"]] == ["eval-01", "eval-02"]

    # No leftover .tmp file: the atomic write always ends with a rename
    # over the real path, never stops mid-way leaving both files present.
    assert not results_path.with_suffix(results_path.suffix + ".tmp").exists()
