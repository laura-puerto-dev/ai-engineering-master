"""Manual, real-model smoke test for reranking.LocalQwen3RerankerModel.

Not part of the pytest suite — same convention as
scripts/smoke_test_embedding.py and scripts/smoke_test_rag.py: requires
downloading/loading the real Qwen3-Reranker-0.6B weights (~1.2 GB,
cached by Hugging Face after the first run) and a real PostgreSQL/RLS
retrieval. Never calls Claude — reranking.py has no dependency on it.

Run with:

    uv sync --extra embeddings --extra persistence --extra reranking
    uv run python scripts/smoke_test_reranker.py

Read-only end to end: retrieve_relevant_chunks() is called exactly as
retrieval.py already defines it, through a normal RLS-bound
app_connection() — nothing here writes anything, and the reranker never
sees a chunk this profile wasn't already authorized to retrieve.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from dotenv import load_dotenv

from policy_consultant.corpus_manifest import load_access_model
from policy_consultant.db import app_connection
from policy_consultant.embedding import LocalBgeM3EmbeddingModel
from policy_consultant.reranking import DEFAULT_RERANKER_MODEL_ID, LocalQwen3RerankerModel
from policy_consultant.retrieval import retrieve_relevant_chunks

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ACCESS_MODEL_PATH = PROJECT_ROOT / "config" / "access-model.yaml"
TOP_K = 10  # the CRAG plan's max candidates per retrieval

# (question, country, role) — a real question with a real, single-chunk
# answer in the corpus, so pgvector-vs-reranker agreement/disagreement at
# the top is easy to read by eye.
QUESTION = "¿Cuántos días de teletrabajo a la semana puede hacer un empleado elegible en España?"
COUNTRY = "spain"
ROLE = "employee"


def main() -> None:
    load_dotenv()

    access_model = load_access_model(ACCESS_MODEL_PATH)
    embedding_model = LocalBgeM3EmbeddingModel(device=os.environ.get("EMBEDDING_DEVICE", "cpu"))
    query_embedding = embedding_model.embed_batch([QUESTION])[0]

    with app_connection(country=COUNTRY, role=ROLE, access_model=access_model) as conn:
        candidates = retrieve_relevant_chunks(conn, query_embedding, top_k=TOP_K)

    print(f"Question: {QUESTION!r} (country={COUNTRY}, role={ROLE})")
    print(f"Retrieved {len(candidates)} candidates (top_k={TOP_K}):")
    for rank, chunk in enumerate(candidates):
        print(f"  pgvector[{rank}] {chunk['chunk_id']:16} distance={chunk['distance']:.4f}")

    model_id = os.environ.get("RERANKER_MODEL_ID", DEFAULT_RERANKER_MODEL_ID)
    device = os.environ.get("RERANKER_DEVICE", "cpu")
    print(f"\nLoading reranker: {model_id} (device={device})")
    load_start = time.perf_counter()
    reranker = LocalQwen3RerankerModel(device=device, model_id=model_id)
    print(f"Loaded in {time.perf_counter() - load_start:.2f}s")

    rerank_start = time.perf_counter()
    ranked = reranker.rerank(QUESTION, candidates)
    rerank_seconds = time.perf_counter() - rerank_start
    print(f"\nReranked {len(ranked)} candidates in {rerank_seconds:.3f}s")

    pgvector_rank = {chunk["chunk_id"]: rank for rank, chunk in enumerate(candidates)}
    print("\nReranked order (most relevant first) vs. original pgvector rank:")
    for new_rank, chunk in enumerate(ranked):
        print(
            f"  reranker[{new_rank}] pgvector[{pgvector_rank[chunk['chunk_id']]}] "
            f"{chunk['chunk_id']:16} rerank_score={chunk['rerank_score']:.4f} "
            f"distance={chunk['distance']:.4f}"
        )


if __name__ == "__main__":
    main()
