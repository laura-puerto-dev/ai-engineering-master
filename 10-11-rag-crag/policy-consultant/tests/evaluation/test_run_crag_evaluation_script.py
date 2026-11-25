"""Tests for the pure parts of scripts/evaluation/run_crag_evaluation.py:
dataset validation, outcome/citation/evidence checks, metric
aggregation, and the --run safety guard.

Real embeddings, local reranking, PostgreSQL retrieval, and Claude calls
(_run_question, main() called with --run) are exercised manually when
the script is actually run — same category as scripts/smoke_test_crag.py
— and are not covered here.

scripts/ is deliberately not an importable package (see
test_sync_corpus_script.py's own docstring) — the module is loaded
straight from its file path instead of adding scripts/ to sys.path or
giving it an __init__.py.
"""

from __future__ import annotations

import importlib.util
import types
from pathlib import Path
from typing import Any

import pytest

SCRIPT_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "scripts"
    / "evaluation"
    / "run_crag_evaluation.py"
)


def _load_script() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("run_crag_evaluation_script", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def script() -> types.ModuleType:
    return _load_script()


def _evidence(chunk_id: str, document_id: str = "A") -> dict[str, Any]:
    return {
        "document_id": document_id,
        "version": "1.0",
        "chunk_id": chunk_id,
        "section_path": ["1. Section"],
    }


def _question(
    question_id: str = "val-01",
    *,
    category: str = "direct_evidence",
    profile_id: str = "spain-employee",
    expected_outcome: str = "answerable",
    abstain_reason: str | None = None,
    expected_evidence: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "id": question_id,
        "category": category,
        "profile_id": profile_id,
        "question": "question text",
        "expected_outcome": expected_outcome,
        "expected_answer_summary": "summary",
        "expected_aspects": ["aspect"],
        "expected_evidence": expected_evidence if expected_evidence is not None else [],
        "abstain_reason": abstain_reason,
        "justification": "justification text",
    }


def _candidate(
    chunk_id: str, *, distance: float = 0.1, rerank_score: float = 0.9
) -> dict[str, Any]:
    return {"chunk_id": chunk_id, "distance": distance, "rerank_score": rerank_score}


def _coverage(route: str, *, rationale: str = "r") -> dict[str, Any]:
    return {
        "route": route,
        "covered_aspects": [],
        "missing_aspects": [],
        "useful_chunk_ids": [],
        "rationale": rationale,
    }


def _attempt(
    attempt: int,
    *,
    query: str = "q",
    candidates: list[dict[str, Any]] | None = None,
    kept_chunk_ids: list[str] | None = None,
    discarded_chunk_ids: list[str] | None = None,
    coverage_route: str = "sufficient",
    effective_route: str | None = None,
) -> dict[str, Any]:
    return {
        "attempt": attempt,
        "query": query,
        "candidates": candidates if candidates is not None else [],
        "kept_chunk_ids": kept_chunk_ids if kept_chunk_ids is not None else [],
        "discarded_chunk_ids": discarded_chunk_ids if discarded_chunk_ids is not None else [],
        "coverage": _coverage(coverage_route),
        "route": effective_route if effective_route is not None else coverage_route,
    }


def _executed_result(
    question_id: str = "val-01",
    *,
    expected_outcome: str = "answerable",
    expected_evidence: list[dict[str, Any]] | None = None,
    abstained: bool = False,
    citations: list[dict[str, Any]] | None = None,
    attempts: list[dict[str, Any]] | None = None,
    elapsed_seconds: float = 1.0,
) -> dict[str, Any]:
    final_attempts = attempts if attempts is not None else [_attempt(1)]
    final_evidence = expected_evidence if expected_evidence is not None else []
    ever_seen = {c["chunk_id"] for attempt in final_attempts for c in attempt["candidates"]}
    delivered = set() if abstained else set(final_attempts[-1]["kept_chunk_ids"])
    citations = citations if citations is not None else []
    invalid_retrieved = [c["chunk_id"] for c in citations if c["chunk_id"] not in ever_seen]
    invalid_final_context = [c["chunk_id"] for c in citations if c["chunk_id"] not in delivered]
    return {
        "id": question_id,
        "category": "direct_evidence",
        "profile_id": "spain-employee",
        "question": "question text",
        "expected_outcome": expected_outcome,
        "expected_answer_summary": "summary",
        "expected_aspects": ["aspect"],
        "expected_evidence": final_evidence,
        "abstain_reason": None,
        "elapsed_seconds": elapsed_seconds,
        "technical_error": None,
        "crag": {
            "abstained": abstained,
            "answer": "answer text",
            "citations": citations,
            "retrieval_count": len(final_attempts),
            "attempts": final_attempts,
        },
        "outcome_check": {
            "expected_outcome": expected_outcome,
            "actual_abstained": abstained,
            "matches_expected": (not abstained) if expected_outcome == "answerable" else abstained,
        },
        "citation_structural_check": {
            "citations_checked": len(citations),
            "citations_from_retrieved": len(invalid_retrieved) == 0,
            "invalid_citation_chunk_ids": invalid_retrieved,
            "citations_from_final_context": len(invalid_final_context) == 0,
            "invalid_citation_chunk_ids_not_in_final_context": invalid_final_context,
        },
        "expected_evidence_matches": None,
        "evidence_coverage_summary": None,
        "manual_review": {
            "factual_correctness": None,
            "evidence_sufficiency": None,
            "citation_support": None,
            "notes": "",
        },
    }


def _errored_result(
    question_id: str = "val-09",
    *,
    expected_outcome: str = "abstain",
    error_type: str = "EvidenceGradingError",
    elapsed_seconds: float = 0.5,
) -> dict[str, Any]:
    return {
        "id": question_id,
        "category": "no_information",
        "profile_id": "spain-employee",
        "question": "question text",
        "expected_outcome": expected_outcome,
        "expected_answer_summary": None,
        "expected_aspects": [],
        "expected_evidence": [],
        "abstain_reason": "no_information" if expected_outcome == "abstain" else None,
        "elapsed_seconds": elapsed_seconds,
        "technical_error": {"type": error_type, "message": "boom"},
        "crag": None,
        "outcome_check": None,
        "citation_structural_check": None,
        "expected_evidence_matches": None,
        "evidence_coverage_summary": None,
        "manual_review": {
            "factual_correctness": None,
            "evidence_sufficiency": None,
            "citation_support": None,
            "notes": "",
        },
    }


# --- _validate_dataset ----------------------------------------------------------


def test_validate_dataset_accepts_a_well_formed_dataset(script: types.ModuleType) -> None:
    questions = [
        _question("val-01", expected_outcome="answerable"),
        _question("val-02", expected_outcome="abstain", abstain_reason="no_information"),
    ]
    script._validate_dataset(questions, known_profile_ids={"spain-employee"})


def test_validate_dataset_rejects_an_empty_dataset(script: types.ModuleType) -> None:
    with pytest.raises(ValueError, match="no questions"):
        script._validate_dataset([], known_profile_ids={"spain-employee"})


def test_validate_dataset_rejects_a_missing_required_field(script: types.ModuleType) -> None:
    question = _question("val-01")
    del question["question"]
    with pytest.raises(ValueError, match="missing or empty required field 'question'"):
        script._validate_dataset([question], known_profile_ids={"spain-employee"})


def test_validate_dataset_rejects_a_duplicate_id(script: types.ModuleType) -> None:
    questions = [_question("val-01"), _question("val-01")]
    with pytest.raises(ValueError, match="duplicate id"):
        script._validate_dataset(questions, known_profile_ids={"spain-employee"})


def test_validate_dataset_rejects_an_unknown_profile_id(script: types.ModuleType) -> None:
    question = _question("val-01", profile_id="atlantis-employee")
    with pytest.raises(ValueError, match="unknown profile_id"):
        script._validate_dataset([question], known_profile_ids={"spain-employee"})


def test_validate_dataset_rejects_an_invalid_expected_outcome(script: types.ModuleType) -> None:
    question = _question("val-01", expected_outcome="maybe")
    with pytest.raises(ValueError, match="expected_outcome must be"):
        script._validate_dataset([question], known_profile_ids={"spain-employee"})


def test_validate_dataset_rejects_abstain_without_a_reason(script: types.ModuleType) -> None:
    question = _question("val-01", expected_outcome="abstain", abstain_reason=None)
    with pytest.raises(ValueError, match="abstain_reason is missing"):
        script._validate_dataset([question], known_profile_ids={"spain-employee"})


def test_validate_dataset_rejects_answerable_with_an_abstain_reason_set(
    script: types.ModuleType,
) -> None:
    question = _question("val-01", expected_outcome="answerable", abstain_reason="no_information")
    with pytest.raises(ValueError, match="abstain_reason is set"):
        script._validate_dataset([question], known_profile_ids={"spain-employee"})


def test_validate_dataset_rejects_expected_evidence_that_is_not_a_list(
    script: types.ModuleType,
) -> None:
    question = _question("val-01")
    question["expected_evidence"] = "ES-001:1.0:0"
    with pytest.raises(ValueError, match="expected_evidence must be a list"):
        script._validate_dataset([question], known_profile_ids={"spain-employee"})


def test_validate_dataset_rejects_an_incomplete_expected_evidence_entry(
    script: types.ModuleType,
) -> None:
    question = _question("val-01", expected_evidence=[{"chunk_id": "ES-001:1.0:0"}])
    with pytest.raises(ValueError, match="must have document_id/version/chunk_id/section_path"):
        script._validate_dataset([question], known_profile_ids={"spain-employee"})


def test_validate_dataset_collects_every_error_before_raising(script: types.ModuleType) -> None:
    questions = [
        _question("val-01", profile_id="atlantis-employee"),
        _question("val-01", expected_outcome="maybe"),  # duplicate id, bad outcome
    ]
    with pytest.raises(ValueError) as exc_info:
        script._validate_dataset(questions, known_profile_ids={"spain-employee"})

    message = str(exc_info.value)
    assert "unknown profile_id" in message
    assert "duplicate id" in message
    assert "expected_outcome must be" in message


# --- _check_outcome ---------------------------------------------------------------


def test_check_outcome_answerable_matches_when_not_abstained(script: types.ModuleType) -> None:
    assert script._check_outcome("answerable", False)["matches_expected"] is True


def test_check_outcome_answerable_fails_when_abstained(script: types.ModuleType) -> None:
    assert script._check_outcome("answerable", True)["matches_expected"] is False


def test_check_outcome_abstain_matches_when_abstained(script: types.ModuleType) -> None:
    assert script._check_outcome("abstain", True)["matches_expected"] is True


def test_check_outcome_abstain_fails_when_answered(script: types.ModuleType) -> None:
    assert script._check_outcome("abstain", False)["matches_expected"] is False


# --- _check_citation_structure -----------------------------------------------------


def test_citation_structure_valid_when_citation_was_ever_retrieved_and_in_final_context(
    script: types.ModuleType,
) -> None:
    citations = [{"chunk_id": "A:1.0:0"}]
    result = script._check_citation_structure(citations, {"A:1.0:0"}, {"A:1.0:0"})

    assert result == {
        "citations_checked": 1,
        "citations_from_retrieved": True,
        "invalid_citation_chunk_ids": [],
        "citations_from_final_context": True,
        "invalid_citation_chunk_ids_not_in_final_context": [],
    }


def test_citation_structure_invalid_when_citation_was_never_retrieved(
    script: types.ModuleType,
) -> None:
    citations = [{"chunk_id": "Z:1.0:0"}]
    result = script._check_citation_structure(citations, {"A:1.0:0"}, {"A:1.0:0"})

    assert result["citations_from_retrieved"] is False
    assert result["invalid_citation_chunk_ids"] == ["Z:1.0:0"]


def test_citation_structure_invalid_when_citation_was_retrieved_but_not_in_final_context(
    script: types.ModuleType,
) -> None:
    """A citation whose chunk_id was retrieved at some point but is not
    part of the exact context actually delivered to the generator would
    indicate a real wiring bug (generation._resolve_citations only ever
    resolves an index into the list it was given) — this check exists to
    catch that even though it should never happen in practice.
    """
    citations = [{"chunk_id": "A:1.0:0"}]
    result = script._check_citation_structure(citations, {"A:1.0:0"}, set())

    assert result["citations_from_retrieved"] is True
    assert result["citations_from_final_context"] is False
    assert result["invalid_citation_chunk_ids_not_in_final_context"] == ["A:1.0:0"]


def test_citation_structure_with_no_citations_at_all(script: types.ModuleType) -> None:
    result = script._check_citation_structure([], {"A:1.0:0"}, {"A:1.0:0"})

    assert result == {
        "citations_checked": 0,
        "citations_from_retrieved": True,
        "invalid_citation_chunk_ids": [],
        "citations_from_final_context": True,
        "invalid_citation_chunk_ids_not_in_final_context": [],
    }


# --- _check_expected_evidence: ever_retrieved vs in_final_context -----------------


def test_expected_evidence_found_in_final_context(script: types.ModuleType) -> None:
    attempts = [_attempt(1, candidates=[_candidate("A")], kept_chunk_ids=["A"])]
    matches = script._check_expected_evidence(attempts, [_evidence("A")], {"A"})

    assert matches == [
        {"chunk_id": "A", "document_id": "A", "ever_retrieved": True, "in_final_context": True}
    ]


def test_expected_evidence_retrieved_but_lost_between_attempts(
    script: types.ModuleType,
) -> None:
    """A chunk retrieved in attempt 1 but discarded by grading, never
    carried into attempt 2's final kept set — the "lost evidence between
    attempts" case the Fase 3B brief asks to watch for.
    """
    attempts = [
        _attempt(1, candidates=[_candidate("A")], kept_chunk_ids=[], discarded_chunk_ids=["A"]),
        _attempt(2, candidates=[_candidate("B")], kept_chunk_ids=["B"]),
    ]
    matches = script._check_expected_evidence(attempts, [_evidence("A")], {"B"})

    assert matches[0]["ever_retrieved"] is True
    assert matches[0]["in_final_context"] is False


def test_expected_evidence_never_retrieved_at_all(script: types.ModuleType) -> None:
    attempts = [_attempt(1, candidates=[_candidate("B")], kept_chunk_ids=["B"])]
    matches = script._check_expected_evidence(attempts, [_evidence("A")], {"B"})

    assert matches[0]["ever_retrieved"] is False
    assert matches[0]["in_final_context"] is False


def test_expected_evidence_with_no_attempts_at_all(script: types.ModuleType) -> None:
    matches = script._check_expected_evidence([], [_evidence("A")], set())

    assert matches[0]["ever_retrieved"] is False
    assert matches[0]["in_final_context"] is False


def test_expected_evidence_retrieved_and_kept_but_not_delivered_on_abstention(
    script: types.ModuleType,
) -> None:
    """Even if the last attempt's kept_chunk_ids still contains the
    expected chunk, the caller (_run_question) must pass an EMPTY
    delivered_to_generator_chunk_ids when the question ended in
    abstention — crag.abstain_node never touches kept_chunks, so nothing
    actually reached the generator. This is exactly the Fase 3B.2 fix:
    "si existe abstención, no se ha entregado contexto al generador".
    """
    attempts = [_attempt(1, candidates=[_candidate("A")], kept_chunk_ids=["A"])]
    matches = script._check_expected_evidence(attempts, [_evidence("A")], set())

    assert matches[0]["ever_retrieved"] is True
    assert matches[0]["in_final_context"] is False


# --- _evidence_coverage_summary ----------------------------------------------------


def test_evidence_coverage_summary_is_none_without_expected_evidence(
    script: types.ModuleType,
) -> None:
    assert script._evidence_coverage_summary([]) is None


def test_evidence_coverage_summary_all_found(script: types.ModuleType) -> None:
    matches = [{"chunk_id": "A", "ever_retrieved": True, "in_final_context": True}]
    summary = script._evidence_coverage_summary(matches)

    assert summary == {
        "expected_count": 1,
        "found_in_final_context": 1,
        "all_found_in_final_context": True,
        "found_ever_retrieved": 1,
        "all_found_ever_retrieved": True,
    }


def test_evidence_coverage_summary_partial(script: types.ModuleType) -> None:
    matches = [
        {"chunk_id": "A", "ever_retrieved": True, "in_final_context": True},
        {"chunk_id": "B", "ever_retrieved": True, "in_final_context": False},
    ]
    summary = script._evidence_coverage_summary(matches)

    assert summary["found_in_final_context"] == 1
    assert summary["all_found_in_final_context"] is False
    assert summary["found_ever_retrieved"] == 2


# --- _collect_outcome_metrics -------------------------------------------------------


def test_collect_outcome_metrics_separates_answerable_and_abstain(
    script: types.ModuleType,
) -> None:
    results = [
        _executed_result("val-01", expected_outcome="answerable", abstained=False),
        _executed_result(
            "val-02", expected_outcome="answerable", abstained=True
        ),  # false abstention
        _executed_result("val-03", expected_outcome="abstain", abstained=True),
        _executed_result("val-04", expected_outcome="abstain", abstained=False),  # false answer
    ]

    metrics = script._collect_outcome_metrics(results)

    assert metrics["answerable_total"] == 2
    assert metrics["answerable_executed"] == 2
    assert metrics["answerable_answered"] == 1
    assert metrics["answerable_answered_rate"] == pytest.approx(0.5)
    assert metrics["false_abstentions"] == 1
    assert metrics["false_abstention_ids"] == ["val-02"]
    assert metrics["abstain_total"] == 2
    assert metrics["abstain_correct"] == 1
    assert metrics["abstain_correct_rate"] == pytest.approx(0.5)
    assert metrics["false_answers"] == 1
    assert metrics["false_answer_ids"] == ["val-04"]


def test_collect_outcome_metrics_excludes_technical_errors_from_rate_denominators(
    script: types.ModuleType,
) -> None:
    """A technically-failed question is never counted as a right or
    wrong outcome, but its existence must still be visible (never
    silently dropped) via the *_technical_errors counts.
    """
    results = [
        _executed_result("val-01", expected_outcome="answerable", abstained=False),
        _errored_result("val-02", expected_outcome="answerable"),
        _errored_result("val-03", expected_outcome="abstain"),
    ]

    metrics = script._collect_outcome_metrics(results)

    assert metrics["answerable_executed"] == 1
    assert metrics["answerable_technical_errors"] == 1
    assert metrics["answerable_answered_rate"] == pytest.approx(1.0)
    assert metrics["abstain_executed"] == 0
    assert metrics["abstain_technical_errors"] == 1
    assert metrics["abstain_correct_rate"] is None


# --- _collect_route_metrics ----------------------------------------------------------


def test_collect_route_metrics_counts_per_attempt_not_per_question(
    script: types.ModuleType,
) -> None:
    results = [
        _executed_result(
            "val-01",
            attempts=[
                _attempt(1, coverage_route="ambiguous"),
                _attempt(2, coverage_route="sufficient"),
            ],
        )
    ]

    metrics = script._collect_route_metrics(results)

    assert metrics["effective_route_counts"] == {"ambiguous": 1, "sufficient": 1}
    assert metrics["route_divergences"] == []


def test_collect_route_metrics_detects_grader_vs_effective_divergence(
    script: types.ModuleType,
) -> None:
    """crag._grade can downgrade a grader's raw "sufficient" to an
    effective "insufficient" when zero evidence survives the authorized
    pool filter (see crag.py) — this divergence must be surfaced
    explicitly, not hidden behind a single route count.
    """
    results = [
        _executed_result(
            "val-01",
            attempts=[_attempt(1, coverage_route="sufficient", effective_route="insufficient")],
        )
    ]

    metrics = script._collect_route_metrics(results)

    assert metrics["grader_route_counts"] == {"sufficient": 1}
    assert metrics["effective_route_counts"] == {"insufficient": 1}
    assert len(metrics["route_divergences"]) == 1
    assert metrics["route_divergences"][0]["id"] == "val-01"


def test_collect_route_metrics_skips_technically_failed_questions(
    script: types.ModuleType,
) -> None:
    metrics = script._collect_route_metrics([_errored_result("val-01")])

    assert metrics["effective_route_counts"] == {}
    assert metrics["grader_route_counts"] == {}


# --- _collect_retrieval_metrics -----------------------------------------------------


def test_collect_retrieval_metrics_distribution_and_mean(script: types.ModuleType) -> None:
    results = [
        _executed_result("val-01", attempts=[_attempt(1)]),
        _executed_result("val-02", attempts=[_attempt(1), _attempt(2)]),
        _executed_result("val-03", attempts=[_attempt(1), _attempt(2), _attempt(3)]),
    ]

    metrics = script._collect_retrieval_metrics(results)

    assert metrics["distribution"] == {1: 1, 2: 1, 3: 1}
    assert metrics["mean"] == pytest.approx(2.0)
    assert metrics["questions_needing_reformulation"] == 2


def test_collect_retrieval_metrics_with_no_executed_questions(script: types.ModuleType) -> None:
    metrics = script._collect_retrieval_metrics([_errored_result("val-01")])

    assert metrics["distribution"] == {}
    assert metrics["mean"] is None
    assert metrics["questions_needing_reformulation"] == 0


# --- _collect_latency_metrics --------------------------------------------------------


def test_collect_latency_metrics_excludes_technical_errors(script: types.ModuleType) -> None:
    results = [
        _executed_result("val-01", elapsed_seconds=1.0),
        _executed_result("val-02", elapsed_seconds=3.0),
        _errored_result("val-03", elapsed_seconds=100.0),  # must not pollute the aggregate
    ]

    metrics = script._collect_latency_metrics(results)

    assert metrics["count"] == 2
    assert metrics["mean"] == pytest.approx(2.0)
    assert metrics["median"] == pytest.approx(2.0)
    assert metrics["max"] == pytest.approx(3.0)


def test_collect_latency_metrics_with_no_executed_questions(script: types.ModuleType) -> None:
    metrics = script._collect_latency_metrics([_errored_result("val-01")])

    assert metrics == {"mean": None, "median": None, "max": None, "count": 0}


# --- _collect_citation_metrics --------------------------------------------------------


def test_collect_citation_metrics_aggregates_across_questions(script: types.ModuleType) -> None:
    results = [
        _executed_result(
            "val-01",
            attempts=[_attempt(1, candidates=[_candidate("A")], kept_chunk_ids=["A"])],
            citations=[{"chunk_id": "A"}],
        ),
        _executed_result(
            "val-02",
            attempts=[_attempt(1, candidates=[_candidate("B")], kept_chunk_ids=["B"])],
            citations=[{"chunk_id": "Z"}],  # invalid: never retrieved
        ),
    ]

    metrics = script._collect_citation_metrics(results)

    assert metrics["total_citations_checked"] == 2
    assert metrics["citations_structurally_valid_rate"] == pytest.approx(0.5)
    assert metrics["citations_from_final_context_rate"] == pytest.approx(0.5)


def test_collect_citation_metrics_flags_a_citation_outside_the_final_context(
    script: types.ModuleType,
) -> None:
    """A citation that was retrieved at some point but is not part of
    the context actually delivered to the generator — e.g. the question
    ended in abstention, so nothing was delivered at all — must lower
    citations_from_final_context_rate without affecting
    citations_structurally_valid_rate (that one only cares about
    "ever retrieved").
    """
    results = [
        _executed_result(
            "val-01",
            attempts=[_attempt(1, candidates=[_candidate("A")], kept_chunk_ids=[])],
            citations=[{"chunk_id": "A"}],
            abstained=False,
        )
    ]

    metrics = script._collect_citation_metrics(results)

    assert metrics["citations_structurally_valid_rate"] == pytest.approx(1.0)
    assert metrics["citations_from_final_context_rate"] == pytest.approx(0.0)


# --- _collect_evidence_coverage_metrics ------------------------------------------------


def test_collect_evidence_coverage_metrics_micro_averages_across_questions(
    script: types.ModuleType,
) -> None:
    result_one = _executed_result("val-01")
    result_one["evidence_coverage_summary"] = {
        "expected_count": 2,
        "found_in_final_context": 2,
        "all_found_in_final_context": True,
        "found_ever_retrieved": 2,
        "all_found_ever_retrieved": True,
    }
    result_two = _executed_result("val-02")
    result_two["evidence_coverage_summary"] = {
        "expected_count": 1,
        "found_in_final_context": 0,
        "all_found_in_final_context": False,
        "found_ever_retrieved": 1,
        "all_found_ever_retrieved": True,
    }

    metrics = script._collect_evidence_coverage_metrics([result_one, result_two])

    assert metrics["answerable_with_evidence"] == 2
    assert metrics["coverage_in_final_context_at_k"] == pytest.approx(2 / 3)
    assert metrics["coverage_ever_retrieved_at_k"] == pytest.approx(1.0)
    assert metrics["pct_all_found_in_final_context"] == pytest.approx(0.5)


def test_collect_evidence_coverage_metrics_with_no_applicable_questions(
    script: types.ModuleType,
) -> None:
    metrics = script._collect_evidence_coverage_metrics([_executed_result("val-01")])

    assert metrics["answerable_with_evidence"] == 0
    assert metrics["coverage_in_final_context_at_k"] is None


# --- _compute_metrics (integration of the above) ---------------------------------------


def test_compute_metrics_counts_technical_errors_and_executed_separately(
    script: types.ModuleType,
) -> None:
    results = [_executed_result("val-01"), _errored_result("val-02")]

    metrics = script._compute_metrics(results, total_count=2)

    assert metrics["total_questions"] == 2
    assert metrics["technical_errors"] == {"count": 1, "ids": ["val-02"]}
    assert metrics["executed_successfully"] == {"count": 1, "ids": ["val-01"]}


# --- CLI / --run safety guard -----------------------------------------------------------


def test_parse_args_defaults_to_no_run(script: types.ModuleType) -> None:
    args = script._parse_args(["--results-json", "a.json", "--results-md", "a.md"])
    assert args.run is False


def test_parse_args_run_flag_enables_run(script: types.ModuleType) -> None:
    args = script._parse_args(["--results-json", "a.json", "--results-md", "a.md", "--run"])
    assert args.run is True


def test_parse_args_requires_results_paths(script: types.ModuleType) -> None:
    with pytest.raises(SystemExit):
        script._parse_args([])


def test_main_without_run_flag_never_touches_the_real_pipeline(
    script: types.ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Without --run, main() must return after loading and validating the
    dataset alone — never constructing a local model, opening a database
    connection, or building a Claude component. Each is monkeypatched to
    raise if called at all, so any accidental code path that reaches
    them fails this test immediately rather than silently making a real
    (billed) call.
    """

    def _boom(*args: object, **kwargs: object) -> None:
        raise AssertionError("must not be called without --run")

    monkeypatch.setattr(script, "LocalBgeM3EmbeddingModel", _boom)
    monkeypatch.setattr(script, "LocalQwen3RerankerModel", _boom)
    monkeypatch.setattr(script, "ClaudeEvidenceGrader", _boom)
    monkeypatch.setattr(script, "ClaudeQueryReformulator", _boom)
    monkeypatch.setattr(script, "ClaudeAnswerGenerator", _boom)
    monkeypatch.setattr(script, "admin_connection", _boom)
    monkeypatch.setattr(script, "app_connection", _boom)

    script.main(
        ["--results-json", str(tmp_path / "r.json"), "--results-md", str(tmp_path / "r.md")]
    )


def test_main_with_run_refuses_to_overwrite_an_existing_results_file(
    script: types.ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The overwrite guard must fire before any model is loaded — heavy
    constructors are boomed here too, so this test fails loudly if the
    guard is ever moved after them.
    """

    def _boom(*args: object, **kwargs: object) -> None:
        raise AssertionError("must not be called: the overwrite guard should fire first")

    monkeypatch.setattr(script, "LocalBgeM3EmbeddingModel", _boom)
    monkeypatch.setattr(script, "admin_connection", _boom)

    results_json = tmp_path / "r.json"
    results_json.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="already exists"):
        script.main(
            [
                "--results-json",
                str(results_json),
                "--results-md",
                str(tmp_path / "r.md"),
                "--run",
            ]
        )


# --- _load_questions ----------------------------------------------------------------------


def test_loads_the_real_crag_validation_file(script: types.ModuleType) -> None:
    questions = script._load_questions(script.DEFAULT_QUESTIONS_PATH)

    assert len(questions) == 12
    assert sum(q["expected_outcome"] == "answerable" for q in questions) == 6
    assert sum(q["expected_outcome"] == "abstain" for q in questions) == 6


def test_the_real_crag_validation_file_passes_validation(script: types.ModuleType) -> None:
    from web.app import DEMO_PROFILES

    questions = script._load_questions(script.DEFAULT_QUESTIONS_PATH)
    script._validate_dataset(questions, known_profile_ids=set(DEMO_PROFILES))
