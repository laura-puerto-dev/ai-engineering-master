"""Evaluates the real CRAG pipeline (crag.answer_question_crag) end to end
against a YAML question set, using the real pipeline as-is: embedding.
LocalBgeM3EmbeddingModel, db.app_connection, reranking.
LocalQwen3RerankerModel, grade_evidence.ClaudeEvidenceGrader, reformulate.
ClaudeQueryReformulator, generation.ClaudeAnswerGenerator, and
web.app.DEMO_PROFILES. There is no second CRAG implementation here.

Dataset- and output-path-agnostic on purpose: --questions/--results-json/
--results-md are CLI arguments, not hardcoded to
docs/evaluation/crag-validation-questions.yaml — this same script is
meant to run again in Fase 4 against a different question file without
any code change. --results-json/--results-md have no default: the
caller must always say explicitly where results land, so a later run
can never silently overwrite a historical one (this script also refuses
outright if the target file already exists — see main()).

A question's own expected_outcome/expected_evidence/expected_aspects/
justification/abstain_reason are read only by this script's own scoring
helpers (_check_outcome, _check_expected_evidence, ...), AFTER
answer_question_crag has already returned — they are never passed into
answer_question_crag itself, which only ever receives the question's raw
text. Only the real, blind pipeline output is scored against them.

Never computes or claims factual correctness or evidence sufficiency:
those automatic checks are structural (did an answer get produced, does
a citation point at something actually retrieved, did an expected chunk
reach the context the generator saw) — never "is the answer right". Each
result's manual_review block is left blank for a human to fill in later,
same convention as scripts/evaluation/run_evaluation.py.

A QueryReformulationError raised by the real ClaudeQueryReformulator
(including the identical-after-normalization case — see reformulate.py)
propagates out of answer_question_crag uncaught by crag.py itself, and
is caught here as a technical_error like any other provider-side
failure — never recorded as a legitimate abstention.

Run with:

    uv run python scripts/evaluation/run_crag_evaluation.py \\
        --results-json docs/evaluation/crag-validation-initial-results.json \\
        --results-md docs/evaluation/crag-validation-initial-report.md
        # dry run: loads and validates the dataset only

    uv run python scripts/evaluation/run_crag_evaluation.py --run \\
        --results-json docs/evaluation/crag-validation-initial-results.json \\
        --results-md docs/evaluation/crag-validation-initial-report.md
        # the real thing: real embeddings, real local reranking, real
        # PostgreSQL retrieval, and multiple real (billed) Claude API
        # calls per question (grade evidence, optionally reformulate,
        # answer) — see crag.MAX_RETRIEVALS for the per-question cap.

Without --run, this script never loads a local model, opens a database
connection, or calls Claude — only --questions is read. --results-json/
--results-md are still required even for a dry run, so the same command
line can be reused unchanged with --run added, but nothing is written
until --run is passed.

A single question that raises is caught and recorded as that question's
own technical_error; every other question still runs. Unlike
run_evaluation.py, this script does not resume a partially-completed
run — if --results-json already exists, it refuses to proceed (see
main()) rather than silently extending or overwriting it. Results are
still saved atomically (a sibling .tmp file, then Path.replace()) after
every question, so a crash mid-run never leaves a half-written file.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import yaml
from dotenv import load_dotenv

# See scripts/evaluation/run_evaluation.py's identical comment: this
# script lives two levels below the project root (scripts/evaluation/),
# and web/ is deliberately not an installed package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from policy_consultant.corpus_manifest import load_access_model  # noqa: E402
from policy_consultant.crag import MAX_RETRIEVALS, answer_question_crag  # noqa: E402
from policy_consultant.db import admin_connection, app_connection  # noqa: E402
from policy_consultant.embedding import EmbeddingModel, LocalBgeM3EmbeddingModel  # noqa: E402
from policy_consultant.generation import (  # noqa: E402
    AnswerGenerationError,
    AnswerGenerator,
    ClaudeAnswerGenerator,
)
from policy_consultant.grade_evidence import (  # noqa: E402
    ClaudeEvidenceGrader,
    EvidenceGrader,
    EvidenceGradingError,
)
from policy_consultant.models import AccessModel  # noqa: E402
from policy_consultant.persistence import verify_embedding_model_compatibility  # noqa: E402
from policy_consultant.reformulate import (  # noqa: E402
    ClaudeQueryReformulator,
    QueryReformulationError,
    QueryReformulator,
)
from policy_consultant.reranking import MAX_CANDIDATES, LocalQwen3RerankerModel, Reranker  # noqa: E402
from web.app import DEMO_PROFILES  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ACCESS_MODEL_PATH = PROJECT_ROOT / "config" / "access-model.yaml"
DEFAULT_QUESTIONS_PATH = PROJECT_ROOT / "docs" / "evaluation" / "crag-validation-questions.yaml"

GENERATION_MODEL = "claude-sonnet-5"
GRADER_MODEL = "claude-sonnet-5"
REFORMULATOR_MODEL = "claude-sonnet-5"

_TECHNICAL_ERROR_TYPES: tuple[type[Exception], ...] = (
    AnswerGenerationError,
    EvidenceGradingError,
    QueryReformulationError,
)


# --- dataset loading and validation --------------------------------------------


def _load_questions(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as file:
        data: object = yaml.safe_load(file)

    if not isinstance(data, dict) or not isinstance(data.get("questions"), list):
        raise TypeError("Question file must be a mapping with a 'questions' list")

    return cast("list[dict[str, Any]]", data["questions"])


def _validate_dataset(questions: list[dict[str, Any]], *, known_profile_ids: set[str]) -> None:
    """Structural validation only — never re-verifies a question's
    evidence against the real corpus (that already happened when the
    dataset was authored; see docs/evaluation/crag-validation-questions.yaml's
    own header). Collects every problem found instead of stopping at the
    first one, so a single run reports the full picture. Deliberately
    generic (field presence/shape, not specific ids/categories/profiles
    beyond checking profile_id is real) so this same check works
    unchanged against a future Fase 4 dataset that follows the same
    schema with different content.
    """
    if not questions:
        raise ValueError("Dataset contains no questions")

    errors: list[str] = []
    seen_ids: set[str] = set()

    for index, question in enumerate(questions):
        label = question.get("id") if isinstance(question.get("id"), str) else f"<index {index}>"

        for field in ("id", "category", "profile_id", "question", "expected_outcome"):
            value = question.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{label}: missing or empty required field '{field}'")

        question_id = question.get("id")
        if isinstance(question_id, str):
            if question_id in seen_ids:
                errors.append(f"{label}: duplicate id '{question_id}'")
            seen_ids.add(question_id)

        profile_id = question.get("profile_id")
        if isinstance(profile_id, str) and profile_id not in known_profile_ids:
            errors.append(f"{label}: unknown profile_id {profile_id!r} (not in DEMO_PROFILES)")

        outcome = question.get("expected_outcome")
        if outcome not in ("answerable", "abstain"):
            errors.append(
                f"{label}: expected_outcome must be 'answerable' or 'abstain', got {outcome!r}"
            )

        abstain_reason = question.get("abstain_reason")
        if outcome == "abstain" and not (
            isinstance(abstain_reason, str) and abstain_reason.strip()
        ):
            errors.append(f"{label}: expected_outcome is 'abstain' but abstain_reason is missing")
        if outcome == "answerable" and abstain_reason is not None:
            errors.append(
                f"{label}: expected_outcome is 'answerable' but abstain_reason is set "
                f"({abstain_reason!r})"
            )

        evidence = question.get("expected_evidence")
        if not isinstance(evidence, list):
            errors.append(f"{label}: expected_evidence must be a list (use [] when none)")
        else:
            for evidence_index, entry in enumerate(evidence):
                required_keys = ("document_id", "version", "chunk_id", "section_path")
                if not isinstance(entry, dict) or not all(key in entry for key in required_keys):
                    errors.append(
                        f"{label}: expected_evidence[{evidence_index}] must have "
                        "document_id/version/chunk_id/section_path"
                    )

    if errors:
        raise ValueError("Dataset validation failed:\n  " + "\n  ".join(errors))


# --- per-question scoring helpers (pure) ---------------------------------------


def _check_outcome(expected_outcome: str, abstained: bool) -> dict[str, Any]:
    matches_expected = (not abstained) if expected_outcome == "answerable" else abstained
    return {
        "expected_outcome": expected_outcome,
        "actual_abstained": abstained,
        "matches_expected": matches_expected,
    }


def _check_citation_structure(
    citations: list[dict[str, Any]],
    ever_seen_chunk_ids: set[str],
    delivered_to_generator_chunk_ids: set[str],
) -> dict[str, Any]:
    """Two independent structural checks. citations_from_retrieved: was
    this citation's chunk_id retrieved by this question's run at some
    point (any attempt, not just the last one) — i.e. a real,
    RLS-authorized fragment, never one the model invented.
    citations_from_final_context: was it actually part of the exact
    context handed to the generator (see delivered_to_generator_chunk_ids
    below) — generation._resolve_citations only ever resolves an index
    into the list it was given, so a citation should satisfy this by
    construction; failing it despite passing the first check would mean
    a real wiring bug, not just a loose evidentiary chain. Neither check
    re-verifies generation._resolve_citations' own by-index resolution;
    both check the real end-to-end output.
    """
    invalid_retrieved = [
        citation["chunk_id"]
        for citation in citations
        if citation["chunk_id"] not in ever_seen_chunk_ids
    ]
    invalid_final_context = [
        citation["chunk_id"]
        for citation in citations
        if citation["chunk_id"] not in delivered_to_generator_chunk_ids
    ]
    return {
        "citations_checked": len(citations),
        "citations_from_retrieved": len(invalid_retrieved) == 0,
        "invalid_citation_chunk_ids": invalid_retrieved,
        "citations_from_final_context": len(invalid_final_context) == 0,
        "invalid_citation_chunk_ids_not_in_final_context": invalid_final_context,
    }


def _check_expected_evidence(
    attempts: list[dict[str, Any]],
    expected_evidence: list[dict[str, Any]],
    delivered_to_generator_chunk_ids: set[str],
) -> list[dict[str, Any]]:
    """For each expected-evidence entry, reports two independent facts:
    ever_retrieved (did ANY attempt's candidate list contain this
    chunk_id — pure retrieval recall, regardless of what happened to it
    afterwards) and in_final_context (was it part of
    delivered_to_generator_chunk_ids — the exact context
    answer_question_crag actually handed to the generator, which is
    empty on abstention: crag.abstain_node never touches kept_chunks at
    all — see _run_question for how that set is derived). A chunk
    retrieved but later discarded is ever_retrieved=True,
    in_final_context=False — exactly the "lost evidence between
    attempts" case the Fase 3B brief asks to watch for.
    """
    ever_seen = {
        candidate["chunk_id"] for attempt in attempts for candidate in attempt["candidates"]
    }

    return [
        {
            "chunk_id": evidence["chunk_id"],
            "document_id": evidence["document_id"],
            "ever_retrieved": evidence["chunk_id"] in ever_seen,
            "in_final_context": evidence["chunk_id"] in delivered_to_generator_chunk_ids,
        }
        for evidence in expected_evidence
    ]


def _evidence_coverage_summary(matches: list[dict[str, Any]]) -> dict[str, Any] | None:
    """None when the question has no expected evidence at all (every
    abstain question in this dataset) — there is nothing to compute
    coverage over; callers must exclude None entries from any aggregate.
    """
    if not matches:
        return None

    total = len(matches)
    found_final = sum(1 for match in matches if match["in_final_context"])
    found_ever = sum(1 for match in matches if match["ever_retrieved"])
    return {
        "expected_count": total,
        "found_in_final_context": found_final,
        "all_found_in_final_context": found_final == total,
        "found_ever_retrieved": found_ever,
        "all_found_ever_retrieved": found_ever == total,
    }


# --- running one question against the real pipeline ----------------------------


def _run_question(
    question: dict[str, Any],
    *,
    embedding_model: EmbeddingModel,
    reranker: Reranker,
    grader: EvidenceGrader,
    reformulator: QueryReformulator,
    generator: AnswerGenerator,
    access_model: AccessModel,
    top_k: int,
) -> dict[str, Any]:
    profile = DEMO_PROFILES[question["profile_id"]]
    start = time.perf_counter()
    technical_error: dict[str, str] | None = None
    crag_result: dict[str, Any] | None = None

    try:
        with app_connection(
            country=profile["country"], role=profile["role"], access_model=access_model
        ) as conn:
            # Only the question's own text ever reaches the real
            # pipeline — expected_outcome/expected_evidence/
            # expected_aspects/justification/abstain_reason are read by
            # this script's own scoring helpers below, never passed in
            # here (see this module's docstring).
            result = answer_question_crag(
                conn,
                question["question"],
                embedding_model=embedding_model,
                reranker=reranker,
                grader=grader,
                reformulator=reformulator,
                generator=generator,
                top_k=top_k,
            )
            crag_result = cast("dict[str, Any]", result)
    except _TECHNICAL_ERROR_TYPES as exc:
        technical_error = {"type": type(exc).__name__, "message": str(exc)}
    except Exception as exc:  # noqa: BLE001 - any other failure (DB, local
        # model runtime, ...) is also a technical error, never an
        # abstention; see this module's docstring.
        technical_error = {"type": type(exc).__name__, "message": str(exc)}

    elapsed_seconds = time.perf_counter() - start

    record: dict[str, Any] = {
        "id": question["id"],
        "category": question["category"],
        "profile_id": question["profile_id"],
        "question": question["question"],
        "expected_outcome": question["expected_outcome"],
        "expected_answer_summary": question.get("expected_answer_summary"),
        "expected_aspects": question.get("expected_aspects"),
        "expected_evidence": question.get("expected_evidence") or [],
        "abstain_reason": question.get("abstain_reason"),
        "elapsed_seconds": elapsed_seconds,
        "technical_error": technical_error,
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

    if crag_result is None:
        return record

    attempts = cast("list[dict[str, Any]]", crag_result["attempts"])
    ever_seen_chunk_ids = {
        candidate["chunk_id"] for attempt in attempts for candidate in attempt["candidates"]
    }
    answer = cast("dict[str, Any]", crag_result["answer"])

    # The exact context answer_question_crag actually handed to the
    # generator — never the generic "last attempt's kept_chunk_ids" on
    # its own, since on abstention crag.abstain_node never touches
    # kept_chunks and the generator is never called at all (see crag.py).
    delivered_to_generator_chunk_ids: set[str] = (
        set() if answer["abstained"] or not attempts else set(attempts[-1]["kept_chunk_ids"])
    )
    evidence_matches = _check_expected_evidence(
        attempts, question.get("expected_evidence") or [], delivered_to_generator_chunk_ids
    )

    record["crag"] = {
        "abstained": answer["abstained"],
        "answer": answer["answer"],
        "citations": answer["citations"],
        "retrieval_count": crag_result["retrieval_count"],
        "attempts": attempts,
    }
    record["outcome_check"] = _check_outcome(question["expected_outcome"], answer["abstained"])
    record["citation_structural_check"] = _check_citation_structure(
        answer["citations"], ever_seen_chunk_ids, delivered_to_generator_chunk_ids
    )
    record["expected_evidence_matches"] = evidence_matches
    record["evidence_coverage_summary"] = _evidence_coverage_summary(evidence_matches)
    return record


# --- aggregate metrics (pure) ---------------------------------------------------


def _collect_outcome_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Answerable and abstain questions are reported as separate rates on
    purpose (same reasoning as run_evaluation.py's
    _aggregate_abstention_metrics): mixing them would let a false
    abstention hide inside an otherwise-good abstain rate. Technical
    errors are split out of each rate's denominator (a question that
    never produced an abstained=True/False value cannot be scored as a
    correct or incorrect outcome) but are still counted and listed
    explicitly here — never silently dropped.
    """

    def _split(
        questions: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        errored = [q for q in questions if q["technical_error"] is not None]
        executed = [q for q in questions if q["technical_error"] is None]
        return errored, executed

    answerable = [r for r in results if r["expected_outcome"] == "answerable"]
    abstain_q = [r for r in results if r["expected_outcome"] == "abstain"]
    answerable_errored, answerable_executed = _split(answerable)
    abstain_errored, abstain_executed = _split(abstain_q)

    answerable_answered = [r for r in answerable_executed if not r["crag"]["abstained"]]
    false_abstentions = [r for r in answerable_executed if r["crag"]["abstained"]]
    abstain_correct = [r for r in abstain_executed if r["crag"]["abstained"]]
    false_answers = [r for r in abstain_executed if not r["crag"]["abstained"]]

    return {
        "answerable_total": len(answerable),
        "answerable_executed": len(answerable_executed),
        "answerable_technical_errors": len(answerable_errored),
        "answerable_answered": len(answerable_answered),
        "answerable_answered_rate": (
            len(answerable_answered) / len(answerable_executed) if answerable_executed else None
        ),
        "false_abstentions": len(false_abstentions),
        "false_abstention_ids": [r["id"] for r in false_abstentions],
        "abstain_total": len(abstain_q),
        "abstain_executed": len(abstain_executed),
        "abstain_technical_errors": len(abstain_errored),
        "abstain_correct": len(abstain_correct),
        "abstain_correct_rate": (
            len(abstain_correct) / len(abstain_executed) if abstain_executed else None
        ),
        "false_answers": len(false_answers),
        "false_answer_ids": [r["id"] for r in false_answers],
    }


def _collect_route_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Counts routes per ATTEMPT, not per question: a question with 3
    retrieval attempts contributes 3 route observations. grader_route is
    EvidenceGrader's raw decision (attempt["coverage"]["route"]);
    effective_route is what crag._grade actually used after its own
    defense-in-depth check (attempt["route"]) — the two can diverge
    exactly when a grader says "sufficient" but zero evidence survives
    the authorized-pool filter (see crag.py). Counting that divergence
    directly surfaces "evidence considered sufficient too early".
    """
    grader_routes: Counter[str] = Counter()
    effective_routes: Counter[str] = Counter()
    divergences: list[dict[str, Any]] = []

    for result in results:
        if result["crag"] is None:
            continue
        for attempt in result["crag"]["attempts"]:
            grader_route = attempt["coverage"]["route"]
            effective_route = attempt["route"]
            grader_routes[grader_route] += 1
            effective_routes[effective_route] += 1
            if grader_route != effective_route:
                divergences.append(
                    {
                        "id": result["id"],
                        "attempt": attempt["attempt"],
                        "grader_route": grader_route,
                        "effective_route": effective_route,
                    }
                )

    return {
        "grader_route_counts": dict(grader_routes),
        "effective_route_counts": dict(effective_routes),
        "route_divergences": divergences,
    }


def _collect_retrieval_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    counts = [r["crag"]["retrieval_count"] for r in results if r["crag"] is not None]
    distribution: Counter[int] = Counter(counts)
    return {
        "distribution": dict(sorted(distribution.items())),
        "mean": statistics.mean(counts) if counts else None,
        "questions_needing_reformulation": sum(1 for count in counts if count > 1),
    }


def _collect_latency_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Only over questions that executed successfully — a technical
    failure's elapsed time (recorded per-question regardless, in
    "elapsed_seconds") measures time-to-failure, not a comparable
    end-to-end latency, and mixing the two would distort the aggregate.
    """
    values = [r["elapsed_seconds"] for r in results if r["technical_error"] is None]
    if not values:
        return {"mean": None, "median": None, "max": None, "count": 0}
    return {
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "max": max(values),
        "count": len(values),
    }


def _collect_citation_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    checks = [r["citation_structural_check"] for r in results if r["citation_structural_check"]]
    total = sum(check["citations_checked"] for check in checks)
    invalid_retrieved = sum(len(check["invalid_citation_chunk_ids"]) for check in checks)
    invalid_final_context = sum(
        len(check["invalid_citation_chunk_ids_not_in_final_context"]) for check in checks
    )
    return {
        "total_citations_checked": total,
        "citations_structurally_valid_rate": (
            (total - invalid_retrieved) / total if total else None
        ),
        "citations_from_final_context_rate": (
            (total - invalid_final_context) / total if total else None
        ),
    }


def _collect_evidence_coverage_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Micro-averaged (total chunks found / total chunks expected across
    all applicable questions combined), same convention as
    run_evaluation.py's evidence_recall_at_k — a question with two
    expected chunks counts twice as much as one with a single chunk.
    """
    summaries = [r["evidence_coverage_summary"] for r in results if r["evidence_coverage_summary"]]
    if not summaries:
        return {
            "answerable_with_evidence": 0,
            "coverage_in_final_context_at_k": None,
            "coverage_ever_retrieved_at_k": None,
            "pct_all_found_in_final_context": None,
        }

    total_expected = sum(summary["expected_count"] for summary in summaries)
    total_final = sum(summary["found_in_final_context"] for summary in summaries)
    total_ever = sum(summary["found_ever_retrieved"] for summary in summaries)
    return {
        "answerable_with_evidence": len(summaries),
        "coverage_in_final_context_at_k": total_final / total_expected,
        "coverage_ever_retrieved_at_k": total_ever / total_expected,
        "pct_all_found_in_final_context": (
            sum(1 for summary in summaries if summary["all_found_in_final_context"])
            / len(summaries)
        ),
    }


def _compute_metrics(results: list[dict[str, Any]], *, total_count: int) -> dict[str, Any]:
    technical_errors = [r for r in results if r["technical_error"] is not None]
    executed = [r for r in results if r["technical_error"] is None]
    return {
        "total_questions": total_count,
        "technical_errors": {
            "count": len(technical_errors),
            "ids": [r["id"] for r in technical_errors],
        },
        "executed_successfully": {"count": len(executed), "ids": [r["id"] for r in executed]},
        "outcome": _collect_outcome_metrics(results),
        "routes": _collect_route_metrics(results),
        "retrievals": _collect_retrieval_metrics(results),
        "latency_seconds": _collect_latency_metrics(results),
        "citations": _collect_citation_metrics(results),
        "evidence_coverage": _collect_evidence_coverage_metrics(results),
    }


# --- reporting -------------------------------------------------------------------


def _format_route_sequence(result: dict[str, Any]) -> str:
    if result["technical_error"] is not None:
        return "ERROR"
    return " -> ".join(attempt["route"] for attempt in result["crag"]["attempts"])


def _incidents(result: dict[str, Any]) -> str:
    notes: list[str] = []
    if result["technical_error"] is not None:
        notes.append(f"technical_error:{result['technical_error']['type']}")
        return "; ".join(notes)
    if not result["outcome_check"]["matches_expected"]:
        notes.append("outcome mismatch")
    citation_check = result["citation_structural_check"]
    if not citation_check["citations_from_retrieved"]:
        notes.append("invalid citation (never retrieved)")
    if not citation_check["citations_from_final_context"]:
        notes.append("invalid citation (not in final context)")
    coverage = result["evidence_coverage_summary"]
    if coverage is not None and not coverage["all_found_in_final_context"]:
        notes.append("expected evidence missing from final context")
    return "; ".join(notes) if notes else "-"


def _print_report(results: list[dict[str, Any]], metrics: dict[str, Any]) -> None:
    for result in results:
        outcome = (
            "ERROR"
            if result["technical_error"] is not None
            else ("abstain" if result["crag"]["abstained"] else "answerable")
        )
        print(
            f"{result['id']} [{result['category']}] expected={result['expected_outcome']} "
            f"got={outcome} routes={_format_route_sequence(result)} "
            f"retrievals={result['crag']['retrieval_count'] if result['crag'] else '-'} "
            f"latency={result['elapsed_seconds']:.2f}s incidents={_incidents(result)}"
        )

    print("\n--- Metrics ---")
    for key in (
        "technical_errors",
        "executed_successfully",
        "outcome",
        "routes",
        "retrievals",
        "latency_seconds",
        "citations",
        "evidence_coverage",
    ):
        print(f"{key}: {metrics[key]}")


def _write_results_json(
    results: list[dict[str, Any]],
    metrics: dict[str, Any],
    *,
    path: Path,
    embedding_model_info: dict[str, Any],
    reranker_model_id: str,
    grader_info: dict[str, Any],
    reformulator_info: dict[str, Any],
    generator_info: dict[str, Any],
    top_k: int,
    max_retrievals: int,
    questions_path: Path,
    total_count: int,
) -> None:
    """Atomic write (sibling .tmp file, then Path.replace()) after every
    question — same convention as run_evaluation.py, so an interruption
    never leaves a half-written file and only ever costs the question
    currently in progress.
    """
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "variant": "crag",
        "embedding_model": embedding_model_info,
        "reranker_model_id": reranker_model_id,
        "grader_model": grader_info,
        "reformulator_model": reformulator_info,
        "generator_model": generator_info,
        "top_k": top_k,
        "max_retrievals": max_retrievals,
        "questions_file": str(questions_path.resolve().relative_to(PROJECT_ROOT)),
        "completed_count": len(results),
        "total_count": total_count,
        "metrics": metrics,
        "results": results,
    }
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp_path.replace(path)


def _write_markdown_report(
    results: list[dict[str, Any]],
    metrics: dict[str, Any],
    *,
    path: Path,
    questions_path: Path,
    top_k: int,
) -> None:
    lines = [
        "# CRAG Evaluation Report",
        "",
        f"- Generated: {datetime.now(UTC).isoformat()}",
        "- Variant: crag",
        f"- Dataset: {questions_path.resolve().relative_to(PROJECT_ROOT)}",
        f"- top_k: {top_k}  ·  max_retrievals: {MAX_RETRIEVALS}",
        "",
        "These automatic metrics describe technical execution, outcome "
        "(answered vs. abstained), route distribution, retrieval counts, "
        "latency, and structural validity. They never claim an answer is "
        "factually correct or that its evidence is actually sufficient — "
        "see the manual_review fields below and in the JSON results file "
        "for that. An answer being produced (not abstained) is not the "
        "same thing as that answer being correct.",
        "",
        "## Summary table",
        "",
        "| ID | Category | Expected | Got | Routes | Retrievals | Latency (s) | Citations | "
        "Incidents |",
        "|---|---|---|---|---|---|---:|---|---|",
    ]

    for result in results:
        if result["technical_error"] is not None:
            got = "ERROR"
            citations_str = "-"
            retrievals_str = "-"
        else:
            got = "abstain" if result["crag"]["abstained"] else "answerable"
            citations_str = str(len(result["crag"]["citations"]))
            retrievals_str = str(result["crag"]["retrieval_count"])
        lines.append(
            f"| {result['id']} | {result['category']} | {result['expected_outcome']} | {got} | "
            f"{_format_route_sequence(result)} | {retrievals_str} | "
            f"{result['elapsed_seconds']:.2f} | {citations_str} | {_incidents(result)} |"
        )

    lines += ["", "## Automatic metrics", "", "```json", json.dumps(metrics, indent=2), "```", ""]

    lines.append("## Per-question detail")
    lines.append("")
    for result in results:
        lines.append(
            f"### {result['id']} — {result['profile_id']} (expected: {result['expected_outcome']})"
        )
        lines.append("")
        lines.append(f"**Question:** {result['question']}")
        lines.append("")
        lines.append(f"**Expected answer summary:** {result['expected_answer_summary'] or '—'}")
        lines.append(f"**Expected aspects:** {result['expected_aspects'] or '—'}")
        lines.append("")

        if result["technical_error"] is not None:
            error = result["technical_error"]
            lines.append(f"**TECHNICAL ERROR:** `{error['type']}` — {error['message']}")
            lines.append("")
            lines.append("---")
            lines.append("")
            continue

        crag = result["crag"]
        lines.append(
            f"**Abstained:** {crag['abstained']}  ·  **Retrievals:** {crag['retrieval_count']}"
        )
        lines.append("")
        lines.append(f"**Answer:** {crag['answer']}")
        lines.append("")
        if crag["citations"]:
            lines.append("**Citations:**")
            for citation in crag["citations"]:
                section = (
                    " / ".join(citation["section_path"])
                    if citation["section_path"]
                    else "(no section)"
                )
                lines.append(
                    f"- {citation['document_id']} v{citation['version']} — {section} "
                    f"(`{citation['chunk_id']}`)"
                )
        else:
            lines.append("**Citations:** none")
        lines.append("")

        for attempt in crag["attempts"]:
            lines.append(f"**Attempt {attempt['attempt']}** — query: {attempt['query']!r}")
            lines.append("")
            lines.append("| chunk_id | distance | rerank_score |")
            lines.append("|---|---:|---:|")
            for candidate in attempt["candidates"]:
                lines.append(
                    f"| {candidate['chunk_id']} | {candidate['distance']:.4f} | "
                    f"{candidate['rerank_score']:.4f} |"
                )
            lines.append("")
            lines.append(f"- kept: {attempt['kept_chunk_ids']}")
            lines.append(f"- discarded: {attempt['discarded_chunk_ids']}")
            coverage = attempt["coverage"]
            lines.append(f"- covered_aspects: {coverage['covered_aspects']}")
            lines.append(f"- missing_aspects: {coverage['missing_aspects']}")
            lines.append(
                f"- grader route: {coverage['route']}  ·  effective route: {attempt['route']}  "
                f"·  rationale: {coverage['rationale']!r}"
            )
            lines.append("")

        evidence_matches = result["expected_evidence_matches"]
        if evidence_matches:
            lines.append("**Expected evidence:**")
            for match in evidence_matches:
                lines.append(
                    f"- {match['chunk_id']}: ever_retrieved={match['ever_retrieved']} "
                    f"in_final_context={match['in_final_context']}"
                )
            lines.append("")

        lines.append(
            f"**Outcome check:** matches_expected={result['outcome_check']['matches_expected']}"
        )
        lines.append(
            "**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] "
            "citation_support=[ ] notes: ___"
        )
        lines.append("")
        lines.append("---")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


# --- CLI / main ------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--questions",
        type=Path,
        default=DEFAULT_QUESTIONS_PATH,
        help="Path to the YAML question file (default: the Fase 3A validation set).",
    )
    parser.add_argument(
        "--results-json",
        type=Path,
        required=True,
        help="Output path for the structured JSON results.",
    )
    parser.add_argument(
        "--results-md",
        type=Path,
        required=True,
        help="Output path for the human-readable Markdown report.",
    )
    parser.add_argument(
        "--top-k", type=int, default=MAX_CANDIDATES, help="Retrieval top_k per attempt."
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help=(
            "Actually execute the evaluation: real BGE-M3 embeddings, real local "
            "reranking, real PostgreSQL retrieval, and multiple real (billed) Claude "
            "API calls per question. Without this flag, the script only loads and "
            "validates the question file."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)

    questions = _load_questions(args.questions)
    _validate_dataset(questions, known_profile_ids=set(DEMO_PROFILES))
    answerable_count = sum(question["expected_outcome"] == "answerable" for question in questions)
    abstain_count = sum(question["expected_outcome"] == "abstain" for question in questions)
    print(
        f"Loaded and validated {len(questions)} questions from {args.questions} "
        f"({answerable_count} answerable, {abstain_count} abstain)"
    )

    if not args.run:
        print(
            "\nDry run only: no models were loaded and no Claude API calls were made.\n"
            "Pass --run to execute the full evaluation (this makes multiple real, "
            "billed Claude API calls per question)."
        )
        return

    if args.results_json.exists() or args.results_md.exists():
        raise ValueError(
            f"{args.results_json} or {args.results_md} already exists. This script never "
            "overwrites or resumes a previous run — pass different --results-json/"
            "--results-md paths, or move/delete the existing files first."
        )

    load_dotenv()
    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        raise ValueError(
            "ANTHROPIC_API_KEY must be set (in .env or the environment) before running "
            "the evaluation with --run."
        )

    access_model = load_access_model(ACCESS_MODEL_PATH)
    embedding_model = LocalBgeM3EmbeddingModel(device=os.environ.get("EMBEDDING_DEVICE", "cpu"))
    print(f"Embedding model: {embedding_model.model_id} rev={embedding_model.revision}")

    with admin_connection() as conn:
        verify_embedding_model_compatibility(
            conn,
            model_id=embedding_model.model_id,
            revision=embedding_model.revision,
            dimensions=embedding_model.dimensions,
            normalized=True,
        )
    print("index_metadata compatibility: OK")

    reranker = LocalQwen3RerankerModel(device=os.environ.get("RERANKER_DEVICE", "cpu"))
    grader = ClaudeEvidenceGrader(model=GRADER_MODEL)
    reformulator = ClaudeQueryReformulator(model=REFORMULATOR_MODEL)
    generator = ClaudeAnswerGenerator(model=GENERATION_MODEL, disable_thinking=True)
    print(
        f"Reranker: {reranker.model_id}  ·  Grader: {GRADER_MODEL}  ·  "
        f"Reformulator: {REFORMULATOR_MODEL}  ·  Generator: {GENERATION_MODEL} "
        f"(thinking disabled)  ·  top_k={args.top_k}  ·  max_retrievals={MAX_RETRIEVALS}\n"
    )

    results: list[dict[str, Any]] = []
    for question in questions:
        result = _run_question(
            question,
            embedding_model=embedding_model,
            reranker=reranker,
            grader=grader,
            reformulator=reformulator,
            generator=generator,
            access_model=access_model,
            top_k=args.top_k,
        )
        results.append(result)

        status = "ERROR" if result["technical_error"] is not None else "ok"
        print(f"[{len(results)}/{len(questions)}] {question['id']} done ({status}) and saved")

        _write_results_json(
            results,
            _compute_metrics(results, total_count=len(questions)),
            path=args.results_json,
            embedding_model_info={
                "model_id": embedding_model.model_id,
                "revision": embedding_model.revision,
                "dimensions": embedding_model.dimensions,
            },
            reranker_model_id=reranker.model_id,
            grader_info={"model": GRADER_MODEL},
            reformulator_info={"model": REFORMULATOR_MODEL},
            generator_info={"model": GENERATION_MODEL, "disable_thinking": True},
            top_k=args.top_k,
            max_retrievals=MAX_RETRIEVALS,
            questions_path=args.questions,
            total_count=len(questions),
        )

    metrics = _compute_metrics(results, total_count=len(questions))
    _print_report(results, metrics)
    _write_markdown_report(
        results, metrics, path=args.results_md, questions_path=args.questions, top_k=args.top_k
    )
    print(f"\nWrote {args.results_json} and {args.results_md}")


if __name__ == "__main__":
    main()
