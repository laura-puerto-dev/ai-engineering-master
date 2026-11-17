"""Measures real cosine-distance retrieval scores for the calibration
question set (docs/evaluation/calibration-questions.yaml), using real
BGE-M3 embeddings and real PostgreSQL/pgvector retrieval under each
question's own RLS-bound profile.

Reuses the existing pipeline as-is: embedding.LocalBgeM3EmbeddingModel,
db.app_connection, retrieval.retrieve_relevant_chunks, and
web.app.DEMO_PROFILES/TOP_K — the exact top_k the RAG currently uses.
There is no second retrieval implementation here, and rag.py/retrieval.py
are not touched: this script only measures, it never decides or applies
a threshold.

Never touches docs/evaluation/eval-questions.yaml (the held-out set) and
never calls Claude or any other LLM — manual script, same category as
scripts/smoke_test_embedding.py and scripts/smoke_test_rag.py, never part
of the automated pytest suite, since it loads the real BGE-M3 model.

Run with:

    uv run python scripts/calibrate_threshold.py

Writes a single, overwritten results file at
docs/evaluation/calibration-results.json for later reference/comparison.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import yaml
from dotenv import load_dotenv

# `uv run python scripts/calibrate_threshold.py` only puts this file's own
# directory on sys.path, not the project root — unlike pytest (pythonpath
# = ["."] in pyproject.toml) or `uvicorn web.app:app` (which inserts the
# cwd itself). web/ is deliberately not an installed package (see
# web/app.py's own docstring), so reusing DEMO_PROFILES/TOP_K from it
# instead of duplicating them here requires this one-line bootstrap.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from policy_consultant.corpus_manifest import load_access_model  # noqa: E402
from policy_consultant.db import admin_connection, app_connection  # noqa: E402
from policy_consultant.embedding import EmbeddingModel, LocalBgeM3EmbeddingModel  # noqa: E402
from policy_consultant.models import AccessModel, RetrievedChunk  # noqa: E402
from policy_consultant.persistence import verify_embedding_model_compatibility  # noqa: E402
from policy_consultant.retrieval import retrieve_relevant_chunks  # noqa: E402
from web.app import DEMO_PROFILES, TOP_K  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ACCESS_MODEL_PATH = PROJECT_ROOT / "config" / "access-model.yaml"
CALIBRATION_QUESTIONS_PATH = PROJECT_ROOT / "docs" / "evaluation" / "calibration-questions.yaml"
RESULTS_PATH = PROJECT_ROOT / "docs" / "evaluation" / "calibration-results.json"


def _load_calibration_questions(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as file:
        data: object = yaml.safe_load(file)

    if not isinstance(data, dict) or not isinstance(data.get("questions"), list):
        raise TypeError("Calibration file must be a mapping with a 'questions' list")

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


def _run_calibration(
    questions: list[dict[str, Any]],
    *,
    embedding_model: EmbeddingModel,
    access_model: AccessModel,
    top_k: int,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    for question in questions:
        profile = DEMO_PROFILES[question["profile_id"]]
        query_embedding = embedding_model.embed_batch([question["question"]])[0]

        with app_connection(
            country=profile["country"], role=profile["role"], access_model=access_model
        ) as conn:
            retrieved = retrieve_relevant_chunks(conn, query_embedding, top_k=top_k)

        expected_evidence = question.get("expected_evidence") or []
        evidence_matches = _find_expected_evidence(retrieved, expected_evidence)

        results.append(
            {
                "id": question["id"],
                "question": question["question"],
                "profile_id": question["profile_id"],
                "expected_outcome": question["expected_outcome"],
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
            }
        )

    return results


def _format_evidence(matches: list[dict[str, Any]]) -> str:
    if not matches:
        return "-"
    parts = []
    for match in matches:
        if match["found"]:
            parts.append(f"{match['chunk_id']} @rank{match['rank']} dist={match['distance']:.4f}")
        else:
            parts.append(f"{match['chunk_id']} NOT FOUND in top_k")
    return "; ".join(parts)


def _print_report(results: list[dict[str, Any]]) -> None:
    for result in results:
        first = result["first_result_distance"]
        first_str = f"{first:.4f}" if first is not None else "n/a"
        print(
            f"{result['id']} [{result['expected_outcome']}"
            f"{', ' + result['abstain_reason'] if result['abstain_reason'] else ''}] "
            f"profile={result['profile_id']} first_result_distance={first_str}"
        )
        print(f"  expected evidence: {_format_evidence(result['expected_evidence_matches'])}")
        for chunk in result["retrieved"]:
            print(f"    [{chunk['rank']}] {chunk['chunk_id']:16} dist={chunk['distance']:.4f}")
        print()


def _write_results_json(
    results: list[dict[str, Any]],
    *,
    path: Path,
    model_id: str,
    revision: str,
    dimensions: int,
    top_k: int,
    questions_path: Path,
) -> None:
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "embedding_model": {"model_id": model_id, "revision": revision, "dimensions": dimensions},
        "top_k": top_k,
        "questions_file": str(questions_path.relative_to(PROJECT_ROOT)),
        "results": results,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    load_dotenv()

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

    questions = _load_calibration_questions(CALIBRATION_QUESTIONS_PATH)
    print(f"Loaded {len(questions)} calibration questions (top_k={TOP_K})\n")

    results = _run_calibration(
        questions, embedding_model=embedding_model, access_model=access_model, top_k=TOP_K
    )

    _print_report(results)

    _write_results_json(
        results,
        path=RESULTS_PATH,
        model_id=embedding_model.model_id,
        revision=embedding_model.revision,
        dimensions=embedding_model.dimensions,
        top_k=TOP_K,
        questions_path=CALIBRATION_QUESTIONS_PATH,
    )
    print(f"Wrote results to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
