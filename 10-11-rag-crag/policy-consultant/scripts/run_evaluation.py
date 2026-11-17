"""Evaluates the current RAG pipeline (variant "rag") end to end against
the held-out set docs/evaluation/eval-questions.yaml (20 questions: 14
answerable + 6 abstain), using the real pipeline as-is: embedding.
LocalBgeM3EmbeddingModel, db.app_connection, retrieval.
retrieve_relevant_chunks, rag.answer_question, generation.
ClaudeAnswerGenerator, and web.app.DEMO_PROFILES/TOP_K — the exact top_k
the RAG currently uses. There is no second RAG implementation here:
retrieve_relevant_chunks is called directly (in addition to the call
already inside answer_question) purely to capture retrieval-quality
metrics — ranks and distances for the *candidate* set — which
rag.answer_question does not expose; both calls run inside the very
same connection and transaction, against an unchanging corpus, so they
are guaranteed to see the same rows.

Never touches docs/evaluation/calibration-questions.yaml (the
calibration set) and duplicates a couple of small pure helpers
(_find_expected_evidence, the YAML loader) from scripts/
calibrate_threshold.py rather than importing them from it — scripts/ is
deliberately not an importable package (see
tests/test_sync_corpus_script.py's own docstring), and coupling two
independent manual scripts together is worse than a few duplicated
lines.

Run with:

    uv run python scripts/run_evaluation.py           # dry run: loads and
                                                        # validates the
                                                        # dataset only
    uv run python scripts/run_evaluation.py --run      # the real thing

Without --run, this script never embeds a question, never opens a
database connection, and never calls Claude. --run is required because
the full run makes one real, billed Claude API call per question (20
calls for the full set) — a stricter default than
scripts/smoke_test_rag.py's, since this is the first script in this
project whose bare invocation (no arguments at all) must be inert.

Writes two files to docs/evaluation/: rag-eval-results.json (full
structured data — retrieved chunks, distances, evidence matches,
generated answers, citations, automatic metrics, and blank fields for
later manual review) and rag-eval-report.md (a human-readable
per-question view for that manual review, deliberately omitting the raw
distance/chunk detail that only the JSON carries, to avoid duplicating
the same data twice). The Markdown report is only (re)written once, at
the end of a --run; the JSON results file is saved after *every*
individual question — see "Resuming" below.

Resuming: if rag-eval-results.json already exists when --run starts,
this script loads it, skips whatever question ids it already contains
(their manual_review fields are kept exactly as found — never rebuilt),
and only runs the remaining ones, appending to the same file. If all
questions are already present, it exits without calling Claude at all.
Each save is atomic (written to a sibling .tmp file, then
Path.replace()'d over the real path), so an interruption mid-write
never leaves a corrupt or half-written results file — at worst, the
*next* question's result is lost, never an already-saved one. Before
reusing an existing file, its questions_hash/embedding_model/
generation_model/top_k are checked against this run's own; any
mismatch aborts with an error rather than silently mixing incompatible
results (e.g. from a different embedding model revision) in one file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import yaml
from dotenv import load_dotenv

# `uv run python scripts/run_evaluation.py` only puts this file's own
# directory on sys.path, not the project root — unlike pytest (pythonpath
# = ["."] in pyproject.toml) or `uvicorn web.app:app` (which inserts the
# cwd itself). web/ is deliberately not an installed package (see
# web/app.py's own docstring), so reusing DEMO_PROFILES/TOP_K from it
# instead of duplicating them here requires this one-line bootstrap (same
# fix already applied in scripts/calibrate_threshold.py).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from policy_consultant.corpus_manifest import load_access_model  # noqa: E402
from policy_consultant.db import admin_connection, app_connection  # noqa: E402
from policy_consultant.embedding import EmbeddingModel, LocalBgeM3EmbeddingModel  # noqa: E402
from policy_consultant.generation import AnswerGenerator, ClaudeAnswerGenerator  # noqa: E402
from policy_consultant.models import AccessModel, Citation, RetrievedChunk  # noqa: E402
from policy_consultant.persistence import verify_embedding_model_compatibility  # noqa: E402
from policy_consultant.rag import answer_question  # noqa: E402
from policy_consultant.retrieval import retrieve_relevant_chunks  # noqa: E402
from web.app import DEMO_PROFILES, TOP_K  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ACCESS_MODEL_PATH = PROJECT_ROOT / "config" / "access-model.yaml"
EVAL_QUESTIONS_PATH = PROJECT_ROOT / "docs" / "evaluation" / "eval-questions.yaml"
RESULTS_JSON_PATH = PROJECT_ROOT / "docs" / "evaluation" / "rag-eval-results.json"
RESULTS_MD_PATH = PROJECT_ROOT / "docs" / "evaluation" / "rag-eval-report.md"

GENERATION_MODEL = "claude-sonnet-5"


def _load_eval_questions(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as file:
        data: object = yaml.safe_load(file)

    if not isinstance(data, dict) or not isinstance(data.get("questions"), list):
        raise TypeError("Evaluation file must be a mapping with a 'questions' list")

    return cast("list[dict[str, Any]]", data["questions"])


def _find_expected_evidence(
    retrieved: list[RetrievedChunk], expected_evidence: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """For each expected-evidence entry, locate it by chunk_id among
    `retrieved` (already ordered closest-first by retrieve_relevant_chunks).

    Matching is by chunk_id, not document_id: only the exact fragment that
    actually contains the fact counts as "the evidence was retrieved" — a
    different chunk from the same document is not a match.
    """
    rank_by_chunk_id = {chunk["chunk_id"]: rank for rank, chunk in enumerate(retrieved)}

    matches: list[dict[str, Any]] = []
    for evidence in expected_evidence:
        chunk_id = evidence["chunk_id"]
        rank = rank_by_chunk_id.get(chunk_id)
        matches.append(
            {
                "chunk_id": chunk_id,
                "document_id": evidence["document_id"],
                "found": rank is not None,
                "rank": rank,
                "distance": retrieved[rank]["distance"] if rank is not None else None,
            }
        )
    return matches


def _evidence_recall_summary(matches: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Summarize one question's evidence matches.

    Returns None when there is no expected evidence at all (every abstain
    question in this dataset): there is nothing to compute recall over,
    and a 0/0 result would silently claim a measurement this question was
    never designed to produce. Callers must exclude None entries from any
    aggregate, not treat them as either a success or a failure.
    """
    if not matches:
        return None

    found_count = sum(1 for match in matches if match["found"])
    total_count = len(matches)
    return {
        "expected_count": total_count,
        "found_count": found_count,
        "all_found": found_count == total_count,
        "any_found": found_count > 0,
    }


def _aggregate_retrieval_metrics(
    evidence_summaries: list[dict[str, Any] | None],
) -> dict[str, Any]:
    """Aggregate over the answerable questions that actually have expected
    evidence (every abstain-question summary is None and is skipped, never
    counted as 0/0 success or failure — see _evidence_recall_summary).

    evidence_recall_at_k is micro-averaged: total evidence chunks found
    divided by total evidence chunks expected, across all applicable
    questions combined — not an average of each question's own ratio —
    so a question with two expected chunks counts twice as much as one
    with a single expected chunk.
    """
    applicable = [summary for summary in evidence_summaries if summary is not None]
    if not applicable:
        return {
            "answerable_with_evidence": 0,
            "evidence_recall_at_k": None,
            "pct_all_evidence_found": None,
            "pct_any_evidence_found": None,
        }

    total_expected = sum(summary["expected_count"] for summary in applicable)
    total_found = sum(summary["found_count"] for summary in applicable)
    return {
        "answerable_with_evidence": len(applicable),
        "evidence_recall_at_k": total_found / total_expected,
        "pct_all_evidence_found": (
            sum(1 for summary in applicable if summary["all_found"]) / len(applicable)
        ),
        "pct_any_evidence_found": (
            sum(1 for summary in applicable if summary["any_found"]) / len(applicable)
        ),
    }


def _aggregate_abstention_metrics(records: list[tuple[str, bool]]) -> dict[str, Any]:
    """records is one (expected_outcome, actual_abstained) pair per
    question. Answerable and abstain questions are reported as two
    separate rates on purpose (see the module-level task brief): mixing
    them into one "accuracy" number would let an incorrect abstention on
    an answerable question hide inside an otherwise-good abstain rate.
    """
    answerable = [abstained for outcome, abstained in records if outcome == "answerable"]
    abstain = [abstained for outcome, abstained in records if outcome == "abstain"]

    return {
        "answerable_questions": len(answerable),
        "answerable_answered_rate": (
            sum(1 for abstained in answerable if not abstained) / len(answerable)
            if answerable
            else None
        ),
        "abstain_questions": len(abstain),
        "abstain_correct_rate": (
            sum(1 for abstained in abstain if abstained) / len(abstain) if abstain else None
        ),
    }


def _check_outcome(expected_outcome: str, abstained: bool) -> dict[str, Any]:
    matches_expected = (not abstained) if expected_outcome == "answerable" else abstained
    return {
        "expected_outcome": expected_outcome,
        "actual_abstained": abstained,
        "matches_expected": matches_expected,
    }


def _check_citation_structure(
    citations: list[Citation], retrieved: list[RetrievedChunk]
) -> dict[str, Any]:
    """A citation is structurally valid here if its chunk_id is one of
    the chunks this same question's retrieval step actually returned
    under this RLS-bound connection — i.e. it references a real,
    retrieved, already-authorized fragment, never a document or section
    the model invented. Because retrieval is RLS-filtered before
    anything reaches the generator, "retrieved" and "authorized" are the
    same check here; there is no separate authorization property left to
    verify independently of retrieval.

    This does not re-verify generation.py's own by-index citation
    resolution (see generation._resolve_citations) — it checks that the
    same invariant actually held, end to end, for this run's real
    output, which is a different (if related) thing to confirm.
    """
    retrieved_chunk_ids = {chunk["chunk_id"] for chunk in retrieved}
    invalid = [
        citation["chunk_id"]
        for citation in citations
        if citation["chunk_id"] not in retrieved_chunk_ids
    ]
    return {
        "citations_checked": len(citations),
        "citations_from_retrieved": len(invalid) == 0,
        "invalid_citation_chunk_ids": invalid,
    }


def _sha256_hex(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_existing_results(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return cast("dict[str, Any]", json.loads(path.read_text(encoding="utf-8")))


def _check_compatible(
    existing: dict[str, Any],
    *,
    questions_hash: str,
    embedding_model: dict[str, Any],
    generation_model: dict[str, Any],
    top_k: int,
) -> None:
    """Refuse to extend an existing results file produced under different
    settings. Mixing distances from one embedding model/revision (or
    answers from a different generation model or top_k) into the same
    results list would silently produce a meaningless aggregate — this
    is the one thing resuming must never do.
    """
    mismatched = [
        name
        for name, matches in (
            ("variant", existing.get("variant") == "rag"),
            ("questions_hash", existing.get("questions_hash") == questions_hash),
            ("embedding_model", existing.get("embedding_model") == embedding_model),
            ("generation_model", existing.get("generation_model") == generation_model),
            ("top_k", existing.get("top_k") == top_k),
        )
        if not matches
    ]
    if mismatched:
        raise ValueError(
            f"{RESULTS_JSON_PATH.name} already exists but was generated under "
            f"different settings ({', '.join(mismatched)}); refusing to overwrite or "
            "extend it. Move or delete the file first if you intend to start a fresh "
            "evaluation run."
        )


def _resume_state(
    questions: list[dict[str, Any]], existing: dict[str, Any] | None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split `questions` into what's already done and what's still
    pending, based on `existing`'s own "results" (or no prior run at all,
    if `existing` is None).

    Already-completed entries are returned exactly as loaded — including
    any manual_review values already filled in — never rebuilt.
    pending_questions keeps the dataset's own order.
    """
    completed_results = list(existing["results"]) if existing is not None else []
    completed_ids = {result["id"] for result in completed_results}
    pending_questions = [question for question in questions if question["id"] not in completed_ids]
    return completed_results, pending_questions


def _run_question(
    question: dict[str, Any],
    *,
    embedding_model: EmbeddingModel,
    generator: AnswerGenerator,
    access_model: AccessModel,
    top_k: int,
) -> dict[str, Any]:
    profile = DEMO_PROFILES[question["profile_id"]]
    query_embedding = embedding_model.embed_batch([question["question"]])[0]

    with app_connection(
        country=profile["country"], role=profile["role"], access_model=access_model
    ) as conn:
        retrieved = retrieve_relevant_chunks(conn, query_embedding, top_k=top_k)
        generated = answer_question(
            conn,
            question["question"],
            query_embedding=query_embedding,
            generator=generator,
            top_k=top_k,
        )

    # Citation text is read from this same `retrieved` list rather than
    # re-queried from the database: generation.py only ever cites a chunk
    # it was handed from an identical retrieve_relevant_chunks call inside
    # answer_question, made on the same connection/transaction/corpus a
    # moment earlier — so it is guaranteed to already be in `retrieved`
    # (and _check_citation_structure below independently confirms that
    # for this run's real output, rather than just assuming it).
    text_by_chunk_id = {chunk["chunk_id"]: chunk["text"] for chunk in retrieved}

    expected_evidence = question.get("expected_evidence") or []
    evidence_matches = _find_expected_evidence(retrieved, expected_evidence)

    return {
        "id": question["id"],
        "question": question["question"],
        "profile_id": question["profile_id"],
        "expected_outcome": question["expected_outcome"],
        "expected_answer_summary": question.get("expected_answer_summary"),
        "abstain_reason": question.get("abstain_reason"),
        "retrieved": [
            {
                "rank": rank,
                "chunk_id": chunk["chunk_id"],
                "document_id": chunk["document_id"],
                "distance": chunk["distance"],
            }
            for rank, chunk in enumerate(retrieved)
        ],
        "first_result_distance": retrieved[0]["distance"] if retrieved else None,
        "expected_evidence_matches": evidence_matches,
        "evidence_recall": _evidence_recall_summary(evidence_matches),
        "generated": {
            "abstained": generated["abstained"],
            "answer": generated["answer"],
            "citations": [
                {
                    "document_id": citation["document_id"],
                    "version": citation["version"],
                    "section_path": citation["section_path"],
                    "chunk_id": citation["chunk_id"],
                    "text": text_by_chunk_id.get(citation["chunk_id"]),
                }
                for citation in generated["citations"]
            ],
        },
        "outcome_check": _check_outcome(question["expected_outcome"], generated["abstained"]),
        "citation_structural_check": _check_citation_structure(generated["citations"], retrieved),
        "manual_review": {
            "factual_correctness": None,
            "evidence_sufficiency": None,
            "citation_support": None,
            "notes": "",
        },
    }


def _compute_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    retrieval = _aggregate_retrieval_metrics([result["evidence_recall"] for result in results])
    abstention = _aggregate_abstention_metrics(
        [(result["expected_outcome"], result["generated"]["abstained"]) for result in results]
    )

    citation_checks = [result["citation_structural_check"] for result in results]
    total_citations = sum(check["citations_checked"] for check in citation_checks)
    total_invalid = sum(len(check["invalid_citation_chunk_ids"]) for check in citation_checks)
    citations = {
        "total_citations_checked": total_citations,
        "citations_from_retrieved_rate": (
            (total_citations - total_invalid) / total_citations if total_citations else None
        ),
    }

    return {"retrieval": retrieval, "abstention": abstention, "citations": citations}


def _print_report(results: list[dict[str, Any]], metrics: dict[str, Any]) -> None:
    for result in results:
        check = result["outcome_check"]
        print(
            f"{result['id']} [{result['expected_outcome']}] profile={result['profile_id']} "
            f"abstained={check['actual_abstained']} matches_expected={check['matches_expected']}"
        )
        recall = result["evidence_recall"]
        if recall is not None:
            print(f"  evidence recall: {recall['found_count']}/{recall['expected_count']}")
        print(f"  citations: {result['citation_structural_check']['citations_checked']}")

    print("\n--- Metrics ---")
    print(f"Retrieval: {metrics['retrieval']}")
    print(f"Abstention: {metrics['abstention']}")
    print(f"Citations: {metrics['citations']}")


def _write_results_json(
    results: list[dict[str, Any]],
    metrics: dict[str, Any],
    *,
    path: Path,
    model_id: str,
    revision: str,
    dimensions: int,
    top_k: int,
    questions_path: Path,
    questions_hash: str,
    total_count: int,
) -> None:
    """Writes the full results payload atomically: to a sibling .tmp file
    first, then Path.replace() over the real path. Path.replace() is a
    single filesystem rename, so a reader (or a crash) never observes a
    half-written file — only the old complete version or the new
    complete version, never something in between. Called once per
    successfully completed question (see main()), not just at the end,
    so an interruption only ever costs the question in progress, never
    the ones already saved.
    """
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "variant": "rag",
        "embedding_model": {"model_id": model_id, "revision": revision, "dimensions": dimensions},
        "generation_model": {"model": GENERATION_MODEL, "disable_thinking": True},
        "top_k": top_k,
        "questions_file": str(questions_path.relative_to(PROJECT_ROOT)),
        "questions_hash": questions_hash,
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
        "# RAG Baseline Evaluation Report",
        "",
        f"- Generated: {datetime.now(UTC).isoformat()}",
        "- Variant: rag",
        f"- Dataset: {questions_path.relative_to(PROJECT_ROOT)}",
        f"- top_k: {top_k}",
        "",
        "## Automatic metrics",
        "",
        f"- Evidence recall@k (micro-averaged, answerable only): "
        f"{metrics['retrieval']['evidence_recall_at_k']}",
        f"- Answerable questions with ALL expected evidence retrieved: "
        f"{metrics['retrieval']['pct_all_evidence_found']}",
        f"- Answerable questions with ANY expected evidence retrieved: "
        f"{metrics['retrieval']['pct_any_evidence_found']}",
        f"- Answerable questions actually answered (not abstained): "
        f"{metrics['abstention']['answerable_answered_rate']}",
        f"- Abstain questions correctly abstained: {metrics['abstention']['abstain_correct_rate']}",
        f"- Citations structurally valid (reference a retrieved chunk): "
        f"{metrics['citations']['citations_from_retrieved_rate']}",
        "",
        "These automatic metrics describe retrieval coverage, abstention "
        "behavior, and citation structure. They do not determine whether an "
        "answer is factually correct or whether its evidence is actually "
        "sufficient — see the manual review fields below and in the JSON "
        "results file for that.",
        "",
        "## Per-question review",
        "",
    ]

    for result in results:
        section = result["generated"]["citations"]
        lines.append(
            f"### {result['id']} — {result['profile_id']} (expected: {result['expected_outcome']})"
        )
        lines.append("")
        lines.append(f"**Question:** {result['question']}")
        lines.append("")
        lines.append(f"**Expected answer summary:** {result['expected_answer_summary'] or '—'}")
        lines.append("")
        lines.append(
            f"**Actual answer (abstained={result['generated']['abstained']}):** "
            f"{result['generated']['answer']}"
        )
        lines.append("")
        if section:
            lines.append("**Citations:**")
            for citation in section:
                path_str = (
                    " / ".join(citation["section_path"])
                    if citation["section_path"]
                    else "(no section)"
                )
                lines.append(
                    f"- {citation['document_id']} v{citation['version']} — {path_str} "
                    f"(`{citation['chunk_id']}`)"
                )
        else:
            lines.append("**Citations:** none")
        lines.append("")

        recall = result["evidence_recall"]
        recall_str = (
            f"{recall['found_count']}/{recall['expected_count']} (all_found={recall['all_found']})"
            if recall is not None
            else "n/a (no expected evidence for this question)"
        )
        lines.append(f"**Evidence recall:** {recall_str}")
        matches_expected = result["outcome_check"]["matches_expected"]
        lines.append(f"**Outcome check:** matches_expected={matches_expected}")
        lines.append("")
        lines.append(
            "**Manual review:** factual_correctness=[ ] evidence_sufficiency=[ ] "
            "citation_support=[ ] notes: ___"
        )
        lines.append("")
        lines.append("---")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run",
        action="store_true",
        help=(
            "Actually execute the evaluation: real BGE-M3 embeddings, real "
            "PostgreSQL retrieval, and one real (billed) Claude API call per "
            "question. Without this flag, the script only loads and "
            "validates the question file."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)

    questions = _load_eval_questions(EVAL_QUESTIONS_PATH)
    answerable_count = sum(question["expected_outcome"] == "answerable" for question in questions)
    abstain_count = sum(question["expected_outcome"] == "abstain" for question in questions)
    print(
        f"Loaded {len(questions)} evaluation questions "
        f"({answerable_count} answerable, {abstain_count} abstain)"
    )

    if not args.run:
        print(
            "\nDry run only: no embeddings, database connection, or Claude API calls "
            "were made.\nPass --run to execute the full evaluation (this makes one "
            "real, billed Claude API call per question)."
        )
        return

    load_dotenv()
    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        raise ValueError(
            "ANTHROPIC_API_KEY must be set (in .env or the environment) before "
            "running the evaluation with --run."
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

    generator = ClaudeAnswerGenerator(model=GENERATION_MODEL, disable_thinking=True)
    print(f"Generator: {GENERATION_MODEL}, thinking disabled, effort not sent\n")

    questions_hash = _sha256_hex(EVAL_QUESTIONS_PATH)
    embedding_model_info = {
        "model_id": embedding_model.model_id,
        "revision": embedding_model.revision,
        "dimensions": embedding_model.dimensions,
    }
    generation_model_info = {"model": GENERATION_MODEL, "disable_thinking": True}

    existing = _load_existing_results(RESULTS_JSON_PATH)
    if existing is not None:
        _check_compatible(
            existing,
            questions_hash=questions_hash,
            embedding_model=embedding_model_info,
            generation_model=generation_model_info,
            top_k=TOP_K,
        )

    results, pending = _resume_state(questions, existing)
    print(f"{len(results)}/{len(questions)} already completed; {len(pending)} pending\n")

    for question in pending:
        try:
            result = _run_question(
                question,
                embedding_model=embedding_model,
                generator=generator,
                access_model=access_model,
                top_k=TOP_K,
            )
        except Exception as exc:
            print(f"\nQuestion {question['id']} failed: {exc}")
            print(
                f"Preserved {len(results)}/{len(questions)} previously completed "
                f"results in {RESULTS_JSON_PATH}"
            )
            raise

        results.append(result)
        _write_results_json(
            results,
            _compute_metrics(results),
            path=RESULTS_JSON_PATH,
            model_id=embedding_model.model_id,
            revision=embedding_model.revision,
            dimensions=embedding_model.dimensions,
            top_k=TOP_K,
            questions_path=EVAL_QUESTIONS_PATH,
            questions_hash=questions_hash,
            total_count=len(questions),
        )
        print(f"[{len(results)}/{len(questions)}] {question['id']} done and saved")

    metrics = _compute_metrics(results)
    _print_report(results, metrics)
    _write_markdown_report(
        results, metrics, path=RESULTS_MD_PATH, questions_path=EVAL_QUESTIONS_PATH, top_k=TOP_K
    )
    print(f"\nWrote {RESULTS_JSON_PATH} and {RESULTS_MD_PATH}")


if __name__ == "__main__":
    main()
