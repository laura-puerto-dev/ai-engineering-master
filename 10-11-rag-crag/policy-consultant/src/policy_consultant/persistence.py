"""Atomic per-document persistence into PostgreSQL.

persist_document() is a trusted administrative write path, not an
end-user-facing operation: it never generates embeddings (the caller
already ran the document through chunking/embedding and hands it fully
vectorized), and it never decides whether a given (document_id, version)
should be the one that's live — that decision belongs to the caller (a
future ingestion/corpus-sync pipeline), not to this function. It must
never be reachable from a request-handling path, the same way
db.admin_connection() must never serve an end-user-facing read.

Everything — the index_metadata compatibility check, the documents
upsert, and the full chunks replacement — runs inside one explicit
transaction on an already-open admin connection (see db.admin_connection),
so a document is never left with partially replaced chunks and a failed
update never corrupts the previously persisted version.
"""

from __future__ import annotations

import psycopg

from policy_consultant.models import EmbeddedChunk, PolicyDocument


def persist_document(
    conn: psycopg.Connection,
    document: PolicyDocument,
    chunks: list[EmbeddedChunk],
    *,
    embedding_model_revision: str,
    embeddings_normalized: bool,
) -> None:
    """Persist one document's row and its full set of chunks atomically.

    `conn` must already be open in autocommit mode (db.admin_connection
    satisfies this; see migrations.apply_migrations for the same
    contract). `chunks` must all belong to `document` and already carry
    their embeddings — this function never calls an EmbeddingModel.

    model_id is read from chunks[0]["model_id"] only after validation has
    confirmed every chunk shares that same value — there is no separate
    model_id parameter, so the value checked against index_metadata can
    never drift from the value actually written to chunks.model_id.

    embedding_model_revision/embeddings_normalized are not carried on
    EmbeddedChunk (see its docstring: model_id alone does not guarantee
    reproducibility) and must be supplied explicitly by the caller, using
    the same values its EmbeddingModel instance was configured with.

    Raises ValueError before touching the database if `document` and
    `chunks` are inconsistent with each other, or if the embedding
    configuration this call describes does not match what index_metadata
    already has registered. Raises whatever psycopg raises if PostgreSQL
    itself rejects a write (e.g. an embedding of the wrong dimensionality
    for the chunks.embedding column) — either way, the transaction rolls
    back in full, including the documents upsert and any index_metadata
    bootstrap attempted earlier in the same call.
    """
    if not conn.autocommit:
        raise ValueError("persist_document requires a connection in autocommit mode")

    _validate_document_and_chunks(document, chunks, embedding_model_revision)

    model_id = chunks[0]["model_id"]
    dimensions = len(chunks[0]["embedding"])

    with conn.transaction():
        _check_or_register_embedding_model(
            conn,
            model_id=model_id,
            revision=embedding_model_revision,
            dimensions=dimensions,
            normalized=embeddings_normalized,
        )
        _upsert_document(conn, document)
        _replace_chunks(conn, document["document_id"], chunks)


def _validate_document_and_chunks(
    document: PolicyDocument,
    chunks: list[EmbeddedChunk],
    embedding_model_revision: str,
) -> None:
    """Pure, DB-free consistency checks, run before any transaction opens.

    Deliberately does not re-validate what PostgreSQL already enforces
    (e.g. the exact 1024-dimension width of chunks.embedding) or what the
    embedding pipeline already guarantees (finite values, per-batch
    dimension/count agreement — see embedding._validate_batch). This only
    catches mistakes in how document/chunks/revision were assembled for
    *this* call.
    """
    document_id = document["document_id"]
    version = document["version"]

    if not embedding_model_revision:
        raise ValueError("embedding_model_revision must be a non-empty string")

    if not chunks:
        raise ValueError(f"{document_id}: chunks must not be empty")

    if document["status"] != "current":
        raise ValueError(
            f"Refusing to persist {document_id}: status is "
            f"{document['status']!r}, not 'current'"
        )

    for item in chunks:
        chunk_document = item["document"]
        chunk = item["chunk"]

        if chunk_document["document_id"] != document_id:
            raise ValueError(
                f"Chunk's document metadata is for "
                f"{chunk_document['document_id']!r}, not {document_id!r}"
            )
        if chunk_document["version"] != version:
            raise ValueError(
                f"Chunk's document metadata has version "
                f"{chunk_document['version']!r}, expected {version!r}"
            )
        if chunk["document_id"] != document_id:
            raise ValueError(
                f"Chunk belongs to document_id {chunk['document_id']!r}, "
                f"not {document_id!r}"
            )

    ordinals = sorted(item["chunk"]["ordinal"] for item in chunks)
    if ordinals != list(range(len(chunks))):
        raise ValueError(
            f"{document_id}: chunk ordinals must be 0-based and consecutive "
            f"with no duplicates, got {ordinals}"
        )

    for item in chunks:
        chunk = item["chunk"]
        expected_chunk_id = f"{document_id}:{version}:{chunk['ordinal']}"
        if chunk["chunk_id"] != expected_chunk_id:
            raise ValueError(
                f"Chunk id {chunk['chunk_id']!r} does not match expected "
                f"{expected_chunk_id!r}"
            )

    model_ids = {item["model_id"] for item in chunks}
    if len(model_ids) != 1:
        raise ValueError(f"{document_id}: chunks carry more than one model_id: {model_ids}")

    dimensions = {len(item["embedding"]) for item in chunks}
    if len(dimensions) != 1:
        raise ValueError(
            f"{document_id}: chunks have inconsistent embedding dimensions: {dimensions}"
        )


def _check_or_register_embedding_model(
    conn: psycopg.Connection,
    *,
    model_id: str,
    revision: str,
    dimensions: int,
    normalized: bool,
) -> None:
    """Bootstrap index_metadata on the first-ever call, or verify this
    call's embedding configuration matches what is already registered.

    index_metadata.id is a boolean PRIMARY KEY fixed to true, so only one
    row can ever exist. INSERT ... ON CONFLICT DO NOTHING followed by a
    SELECT closes the bootstrap race without any explicit locking: if two
    admin connections race to insert the first row, PostgreSQL's own
    unique index serializes them, the loser's INSERT becomes a no-op, and
    the SELECT below reads whichever row actually won — which this call
    then compares its own configuration against, exactly as it would for
    any later, non-racing call. index_metadata is never updated after
    this bootstrap; later calls only ever read and compare, so there is
    no ongoing mutation race to guard against beyond this one insert.

    This correctness holds under READ COMMITTED — PostgreSQL's default,
    and what every connection in this project uses, since nothing here
    ever issues SET TRANSACTION ISOLATION LEVEL. It does not come from
    snapshot visibility rules at all: ON CONFLICT's conflict check takes
    a row-level lock, so a losing INSERT blocks until the winning
    transaction commits or rolls back, then re-checks, rather than racing
    against it. The SELECT that follows then runs in its own fresh
    READ COMMITTED snapshot and reliably sees the outcome. No retry loop
    or explicit locking is needed on top of this.
    """
    conn.execute(
        """
        INSERT INTO index_metadata
            (embedding_model_id, embedding_model_revision,
             embedding_dimensions, embeddings_normalized)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (id) DO NOTHING
        """,
        (model_id, revision, dimensions, normalized),
    )

    row = conn.execute(
        """
        SELECT embedding_model_id, embedding_model_revision,
               embedding_dimensions, embeddings_normalized
        FROM index_metadata
        """
    ).fetchone()
    assert row is not None  # the INSERT above guarantees exactly one row exists

    stored = tuple(row)
    requested = (model_id, revision, dimensions, normalized)
    if stored != requested:
        stored_model_id, stored_revision, stored_dimensions, stored_normalized = stored
        raise ValueError(
            "Embedding model mismatch: index_metadata is registered as "
            f"model_id={stored_model_id!r} revision={stored_revision!r} "
            f"dimensions={stored_dimensions} normalized={stored_normalized}, "
            f"but this call uses model_id={model_id!r} revision={revision!r} "
            f"dimensions={dimensions} normalized={normalized}"
        )


def _upsert_document(conn: psycopg.Connection, document: PolicyDocument) -> None:
    conn.execute(
        """
        INSERT INTO documents
            (document_id, version, country, language, allowed_roles, effective_from, path)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (document_id) DO UPDATE SET
            version = EXCLUDED.version,
            country = EXCLUDED.country,
            language = EXCLUDED.language,
            allowed_roles = EXCLUDED.allowed_roles,
            effective_from = EXCLUDED.effective_from,
            path = EXCLUDED.path,
            updated_at = now()
        """,
        (
            document["document_id"],
            document["version"],
            document["country"],
            document["language"],
            document["allowed_roles"],
            document["effective_from"],
            document["path"],
        ),
    )


def _replace_chunks(
    conn: psycopg.Connection,
    document_id: str,
    chunks: list[EmbeddedChunk],
) -> None:
    """Delete every existing chunk for document_id, then insert the full
    new set — a plain per-row loop, not a bulk/COPY path: real documents
    have tens of chunks, not thousands.
    """
    conn.execute("DELETE FROM chunks WHERE document_id = %s", (document_id,))

    for item in chunks:
        chunk = item["chunk"]
        conn.execute(
            """
            INSERT INTO chunks
                (chunk_id, document_id, ordinal, section_path, text, embedding, model_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                chunk["chunk_id"],
                chunk["document_id"],
                chunk["ordinal"],
                chunk["section_path"],
                chunk["text"],
                item["embedding"],
                item["model_id"],
            ),
        )
