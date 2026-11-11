"""Manual, real-provider smoke test for the Etapa 8 RAG pipeline.

Not part of the pytest suite — same convention as
scripts/smoke_test_embedding.py: requires downloading/loading the real
BGE-M3 weights, and here, a real Anthropic API call per question. Run
manually after setting ANTHROPIC_API_KEY in .env (see .env.example) and
installing the required extras:

    uv sync --extra embeddings --extra persistence --extra generation
    uv run python scripts/smoke_test_rag.py

Read-only end to end. The embedding-model compatibility check and the
cited-chunk-text lookups both use admin_connection() for SELECTs only;
every question itself runs through app_connection(), which is RLS-bound
and already read-only for policy_app. Nothing here writes anything —
the corpus is never touched.

Never prints the API key or any request/response header — only the
question, context, generated answer, and resolved citations.
"""

from __future__ import annotations

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

from policy_consultant.corpus_manifest import load_access_model
from policy_consultant.db import admin_connection, app_connection
from policy_consultant.embedding import LocalBgeM3EmbeddingModel
from policy_consultant.generation import ClaudeAnswerGenerator
from policy_consultant.persistence import verify_embedding_model_compatibility
from policy_consultant.rag import answer_question

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ACCESS_MODEL_PATH = PROJECT_ROOT / "config" / "access-model.yaml"
TOP_K = 5

# (question, country, role) — covers Spain/Mexico/England, role
# restriction on the same question (ES-007 is hr-only), an English
# query, and a global document from a non-Spain country.
#
# The last scenario has no chunk anywhere in the corpus that actually
# answers it — but retrieve_relevant_chunks() always returns its top_k
# nearest neighbors regardless of relevance (see retrieval.py), so this
# does NOT exercise rag.answer_question's zero-evidence short-circuit.
# It exercises ClaudeAnswerGenerator's own abstention: whether it
# recognizes that the retrieved (but irrelevant) context doesn't support
# an answer and sets abstain=true rather than guessing.
SCENARIOS = [
    ("¿Cuántos días de vacaciones tengo en España?", "spain", "employee"),
    ("What is my vacation entitlement?", "england", "employee"),
    ("¿Cuántos días de vacaciones tengo en México?", "mexico", "employee"),
    ("¿Cuál es la política de teletrabajo?", "spain", "employee"),
    ("What are the internal HR exception-handling procedures?", "spain", "employee"),
    ("What are the internal HR exception-handling procedures?", "spain", "hr"),
    ("¿Cuáles son las normas de conducta de la empresa?", "mexico", "employee"),
    ("¿La empresa paga una suscripción a Netflix?", "spain", "employee"),
]


def _fetch_chunk_texts(conn: psycopg.Connection, chunk_ids: list[str]) -> dict[str, str]:
    """Read-only lookup, purely for this script's own display — citations
    deliberately don't carry the full chunk text (see models.Citation),
    so re-fetching it here is the simplest way to let a human check
    groundedness without changing that contract.
    """
    if not chunk_ids:
        return {}
    rows = conn.execute(
        "SELECT chunk_id, text FROM chunks WHERE chunk_id = ANY(%s)",
        (chunk_ids,),
    ).fetchall()
    return {row[0]: row[1] for row in rows}


def main() -> None:
    load_dotenv()

    # This project uses the ANTHROPIC_API_KEY path (see .env.example), so
    # that's what this check validates. An `ant auth login` profile also
    # works with ClaudeAnswerGenerator/anthropic.Anthropic() even without
    # this variable set — this is a friendly early exit for the setup
    # this project actually uses, not a requirement the SDK itself has.
    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        raise ValueError(
            "ANTHROPIC_API_KEY must be set (in .env or the environment) before "
            "running this script."
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
    print("index_metadata compatibility: OK\n")

    # Thinking disabled for this first validation run: effort's
    # compatibility with thinking=disabled isn't verified against a real
    # call (see ClaudeAnswerGenerator's docstring), so it's omitted
    # entirely rather than guessed at.
    generator = ClaudeAnswerGenerator(model="claude-sonnet-5", disable_thinking=True)
    print("Generator: claude-sonnet-5, thinking disabled, effort not sent\n")

    for question, country, role in SCENARIOS:
        query_embedding = embedding_model.embed_batch([question])[0]

        with app_connection(country=country, role=role, access_model=access_model) as conn:
            result = answer_question(
                conn,
                question,
                query_embedding=query_embedding,
                generator=generator,
                top_k=TOP_K,
            )
            chunk_texts = _fetch_chunk_texts(
                conn, [citation["chunk_id"] for citation in result["citations"]]
            )

        print(f"Q: {question!r}  (country={country}, role={role})")
        print(f"  abstained: {result['abstained']}")
        print(f"  answer: {result['answer']}")
        if result["citations"]:
            print("  citations:")
            for citation in result["citations"]:
                text = chunk_texts.get(citation["chunk_id"], "<text not found>")
                print(
                    f"    - {citation['document_id']} v{citation['version']} "
                    f"{citation['section_path']}"
                )
                # Full text, not a snippet — needed to actually judge
                # groundedness, not just confirm a citation exists.
                print(f"      text: {text}")
        print()


if __name__ == "__main__":
    main()
