"""Manual, real end-to-end smoke test for the full CRAG pipeline
(crag.answer_question_crag): PostgreSQL + pgvector + RLS, local BGE-M3
embeddings, the local Qwen3-Reranker-0.6B reranker, and real Claude calls
(grade evidence, optionally reformulate, answer or abstain) — every
component is the real implementation, never a test double. The number
of Claude calls per question is variable, not fixed: a question
resolved as sufficient on the first attempt makes one grading call and
one answer call, while a question that needs reformulation makes one
grading and one reformulation call per retrieval attempt, up to
crag.MAX_RETRIEVALS attempts, before answering or abstaining.

Not part of the pytest suite — same convention as
scripts/smoke_test_rag.py and scripts/smoke_test_reranker.py: requires
downloading/loading real model weights and making real Anthropic API
calls. Run manually after setting ANTHROPIC_API_KEY in .env and
installing the required extras:

    uv sync --extra web --extra crag
    uv run python scripts/smoke_test_crag.py

Read-only end to end: every question runs through a single
app_connection() (RLS-bound, already read-only for policy_app) — nothing
here writes anything, and CRAG never sees a chunk a profile wasn't
already authorized to retrieve.

The three scenarios below are picked to plausibly, not artificially,
exercise a sufficient answer, a corrective search with reformulation,
and a legitimate abstention — the actual route each one takes depends
on real retrieval/reranking/grading, never forced. None of the three is
part of docs/evaluation/crag-validation-questions.yaml or any future
Fase 4 evaluation set, and none repeats a fact already used there or in
the module-10 historical sets (see that file's header for what IS
already used).

Never prints the API key, any request/response header, or chunk text —
only questions, queries, scores, aspects, decisions, the final answer,
and citation metadata (document_id/version/section_path/chunk_id).
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from dotenv import load_dotenv

from policy_consultant.corpus_manifest import load_access_model
from policy_consultant.crag import answer_question_crag
from policy_consultant.db import admin_connection, app_connection
from policy_consultant.embedding import LocalBgeM3EmbeddingModel
from policy_consultant.generation import AnswerGenerationError, ClaudeAnswerGenerator
from policy_consultant.grade_evidence import ClaudeEvidenceGrader, EvidenceGradingError
from policy_consultant.models import CragResult
from policy_consultant.persistence import verify_embedding_model_compatibility
from policy_consultant.reformulate import ClaudeQueryReformulator, QueryReformulationError
from policy_consultant.reranking import LocalQwen3RerankerModel

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ACCESS_MODEL_PATH = PROJECT_ROOT / "config" / "access-model.yaml"

# (label, question, country, role) — picked to plausibly, not
# artificially, produce one sufficient answer, one corrective search
# with reformulation, and one legitimate abstention. See this module's
# docstring for why these specific three.
SCENARIOS = [
    (
        "sufficient (expected)",
        "¿Cuál es el límite diario de gasto en manutención para un viaje de trabajo "
        "dentro de España?",
        "spain",
        "employee",
    ),
    (
        "corrective search (expected)",
        "Tengo autorizado un viaje de trabajo a Portugal. ¿Puedo aprovechar y "
        "teletrabajar unos días desde allí antes de volver?",
        "spain",
        "employee",
    ),
    (
        "abstention (expected)",
        "¿Northfern ofrece algún plan de pensiones privado complementario para "
        "empleados en México?",
        "mexico",
        "employee",
    ),
]


def _print_result(result: CragResult, elapsed_seconds: float) -> None:
    print(f"  retrievals used: {result['retrieval_count']}")
    for attempt in result["attempts"]:
        print(f"\n  --- attempt {attempt['attempt']} ---")
        print(f"  query: {attempt['query']!r}")
        print("  candidates (pgvector distance -> rerank_score):")
        for candidate in attempt["candidates"]:
            print(
                f"    {candidate['chunk_id']:16} distance={candidate['distance']:.4f} "
                f"rerank_score={candidate['rerank_score']:.4f}"
            )
        print(f"  kept:      {attempt['kept_chunk_ids']}")
        print(f"  discarded: {attempt['discarded_chunk_ids']}")
        coverage = attempt["coverage"]
        print(f"  covered_aspects:  {coverage['covered_aspects']}")
        print(f"  missing_aspects:  {coverage['missing_aspects']}")
        print(f"  grader route:     {coverage['route']}  (rationale: {coverage['rationale']!r})")
        print(f"  effective route:  {attempt['route']}")

    print(f"\n  abstained: {result['answer']['abstained']}")
    print(f"  answer: {result['answer']['answer']}")
    if result["answer"]["citations"]:
        print("  citations:")
        for citation in result["answer"]["citations"]:
            print(
                f"    - {citation['document_id']} v{citation['version']} "
                f"{citation['section_path']} ({citation['chunk_id']})"
            )
    print(f"  total latency: {elapsed_seconds:.2f}s")

    # A legitimate abstention is a normal CragResult (no exception at
    # all) — this line exists only to make that distinction explicit in
    # the printed output, never inferred silently by the reader.
    if result["answer"]["abstained"]:
        print("  -> LEGITIMATE ABSTENTION (not a technical failure)")


def main() -> None:
    load_dotenv()

    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        raise ValueError(
            "ANTHROPIC_API_KEY must be set (in .env or the environment) before "
            "running this script."
        )

    access_model = load_access_model(ACCESS_MODEL_PATH)

    print("Loading local models (once, reused across all scenarios)...")
    embedding_model = LocalBgeM3EmbeddingModel(device=os.environ.get("EMBEDDING_DEVICE", "cpu"))
    print(f"  embedding model: {embedding_model.model_id} rev={embedding_model.revision}")

    with admin_connection() as conn:
        verify_embedding_model_compatibility(
            conn,
            model_id=embedding_model.model_id,
            revision=embedding_model.revision,
            dimensions=embedding_model.dimensions,
            normalized=True,
        )
    print("  index_metadata compatibility: OK")

    reranker_load_start = time.perf_counter()
    reranker = LocalQwen3RerankerModel(device=os.environ.get("RERANKER_DEVICE", "cpu"))
    reranker_load_seconds = time.perf_counter() - reranker_load_start
    print(f"  reranker model: {reranker.model_id} (loaded in {reranker_load_seconds:.2f}s)")

    grader = ClaudeEvidenceGrader(model="claude-sonnet-5")
    reformulator = ClaudeQueryReformulator(model="claude-sonnet-5")
    # Thinking disabled here for the same reason as smoke_test_rag.py:
    # effort's compatibility with thinking=disabled isn't verified
    # against a real call, so it's omitted entirely rather than guessed.
    generator = ClaudeAnswerGenerator(model="claude-sonnet-5", disable_thinking=True)
    print("Claude components ready: grader, reformulator, generator (claude-sonnet-5)\n")

    for label, question, country, role in SCENARIOS:
        print(f"{'=' * 80}\nQ ({label}): {question!r}  (country={country}, role={role})")
        start = time.perf_counter()
        try:
            with app_connection(country=country, role=role, access_model=access_model) as conn:
                result = answer_question_crag(
                    conn,
                    question,
                    embedding_model=embedding_model,
                    reranker=reranker,
                    grader=grader,
                    reformulator=reformulator,
                    generator=generator,
                )
        except (AnswerGenerationError, EvidenceGradingError, QueryReformulationError) as exc:
            # A real provider-side failure (refusal, truncation, invalid
            # structured output) — never a legitimate lack of evidence,
            # which is a normal CragResult(abstained=True) instead (see
            # _print_result below). Printed distinctly on purpose.
            print(f"  -> TECHNICAL FAILURE ({type(exc).__name__}): {exc}")
            continue
        except Exception as exc:
            # Any other failure here (DB connection, embedding/reranker
            # runtime error, ...) is also a technical failure, not an
            # abstention.
            print(f"  -> TECHNICAL FAILURE ({type(exc).__name__}): {exc}")
            continue

        elapsed = time.perf_counter() - start
        _print_result(result, elapsed)
        print()


if __name__ == "__main__":
    main()
