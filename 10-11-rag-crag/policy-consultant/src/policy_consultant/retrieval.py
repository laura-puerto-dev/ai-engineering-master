"""Semantic retrieval over PostgreSQL + pgvector.

retrieve_relevant_chunks() never generates embeddings (the caller already
embedded the query text — see embedding.EmbeddingModel) and carries no
authorization logic of its own: it runs on whatever connection it is
given, and PostgreSQL's row-level security (migrations/002_security.sql)
is what actually restricts which chunks come back. Pass it a connection
opened with db.app_connection(country=..., role=..., access_model=...) —
never db.admin_connection(), which bypasses RLS entirely and would defeat
the whole point.

No query-time check against index_metadata lives here: see
persistence.verify_embedding_model_compatibility, intended to run once
when a retrieval-serving process starts, not on every query.
"""

from __future__ import annotations

import psycopg

from policy_consultant.models import RetrievedChunk


def retrieve_relevant_chunks(
    conn: psycopg.Connection,
    query_embedding: list[float],
    *,
    top_k: int,
) -> list[RetrievedChunk]:
    """Return the top_k chunks closest to query_embedding by cosine
    distance, restricted to whatever conn's RLS context authorizes.

    An empty result means there were no rows to retrieve at all under
    this connection's authorization context (e.g. nothing is indexed
    yet, or this user is authorized for zero documents) — it is not a
    judgment that nothing relevant was found. Whenever at least one
    authorized row exists, this always returns up to top_k of them,
    however distant from query_embedding they are: there is no relevance
    threshold or cutoff here. Deciding whether the closest matches are
    actually good enough to answer from — i.e. whether to abstain — is a
    future RAG/CRAG concern, not this function's.

    query_embedding's dimensionality is not checked here: PostgreSQL
    itself rejects a mismatch against the chunks.embedding column
    (verified directly: a 3-element vector raises
    psycopg.errors.DataException, "different vector dimensions").
    """
    if top_k <= 0:
        raise ValueError("top_k must be greater than 0")

    rows = conn.execute(
        """
        SELECT c.chunk_id, c.document_id, d.version, c.section_path, c.text,
               c.embedding <=> %s::vector AS distance
        FROM chunks c
        JOIN documents d ON d.document_id = c.document_id
        ORDER BY distance
        LIMIT %s
        """,
        (query_embedding, top_k),
    ).fetchall()

    return [
        RetrievedChunk(
            chunk_id=row[0],
            document_id=row[1],
            version=row[2],
            section_path=row[3],
            text=row[4],
            distance=row[5],
        )
        for row in rows
    ]
