"""RAG orchestration: question -> retrieval -> generation, nothing else.

answer_question() composes retrieval.retrieve_relevant_chunks() (already
RLS-bound and country/role-authorized by whatever connection the caller
passes in) with an AnswerGenerator. It never generates the query
embedding itself — that stays the caller's responsibility, the same
separation retrieve_relevant_chunks() already keeps with respect to
EmbeddingModel.

Before wiring this into a long-lived service (the future FastAPI layer,
not part of this stage), call
persistence.verify_embedding_model_compatibility() once at startup —
this function does not call it per question. That boundary was decided
in Etapa 7 for exactly this reason: opening an admin-or-app connection
just to re-check index_metadata on every single question would be
wasteful, and the check is about configuration drift, not anything that
changes between requests.
"""

from __future__ import annotations

import psycopg

from policy_consultant.generation import AnswerGenerator
from policy_consultant.language import insufficient_evidence_message
from policy_consultant.models import GeneratedAnswer
from policy_consultant.retrieval import retrieve_relevant_chunks


def answer_question(
    conn: psycopg.Connection,
    question: str,
    *,
    query_embedding: list[float],
    generator: AnswerGenerator,
    top_k: int,
) -> GeneratedAnswer:
    """Retrieve authorized evidence for `question` and generate a
    grounded answer from it.

    If retrieval returns nothing at all, the generator is never called:
    there is no evidence to ground anything in, authorized or not, and
    that is a cheaper and more certain signal than asking the model to
    notice an empty context and abstain on its own.
    """
    chunks = retrieve_relevant_chunks(conn, query_embedding, top_k=top_k)
    if not chunks:
        return GeneratedAnswer(
            answer=insufficient_evidence_message(question), citations=[], abstained=True
        )

    return generator.generate_answer(question, chunks)
