CREATE EXTENSION IF NOT EXISTS vector;

-- One row per policy, reflecting only the currently live state of the
-- corpus. There is no historical row here: superseded versions remain in
-- config/corpus-manifest.yaml, data/archive/, and git history (see
-- docs/corpus-inventory.md).
CREATE TABLE documents (
    document_id     TEXT PRIMARY KEY,
    version         TEXT NOT NULL,
    country         TEXT NOT NULL,
    language        TEXT NOT NULL,
    allowed_roles   TEXT[] NOT NULL,
    effective_from  DATE NOT NULL,
    path            TEXT NOT NULL,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT documents_country_non_blank CHECK (country <> ''),
    CONSTRAINT documents_language_non_blank CHECK (language <> ''),
    CONSTRAINT documents_allowed_roles_non_empty CHECK (cardinality(allowed_roles) > 0)
);

-- country/language/allowed_roles/version are deliberately not repeated
-- here: authorization is applied by joining chunks to documents, so those
-- fields live in exactly one place.
CREATE TABLE chunks (
    chunk_id        TEXT PRIMARY KEY,
    document_id     TEXT NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
    ordinal         INTEGER NOT NULL,
    section_path    TEXT[] NOT NULL,
    text            TEXT NOT NULL,
    embedding       VECTOR(1024) NOT NULL,
    model_id        TEXT NOT NULL,
    CONSTRAINT chunks_ordinal_non_negative CHECK (ordinal >= 0),
    CONSTRAINT chunks_chunk_id_matches_document CHECK (starts_with(chunk_id, document_id || ':')),
    CONSTRAINT chunks_document_ordinal_unique UNIQUE (document_id, ordinal)
);

-- Singleton row describing the embedding configuration the live index was
-- built with. A different model/revision/dimensionality is a full reindex,
-- not an incremental update; enforcing that is a later persistence-layer
-- concern — this migration only defines the shape.
CREATE TABLE index_metadata (
    id                        BOOLEAN PRIMARY KEY DEFAULT true CHECK (id),
    embedding_model_id        TEXT NOT NULL,
    embedding_model_revision  TEXT NOT NULL,
    embedding_dimensions      INTEGER NOT NULL,
    embeddings_normalized     BOOLEAN NOT NULL,
    updated_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT index_metadata_model_id_non_blank CHECK (embedding_model_id <> ''),
    CONSTRAINT index_metadata_dimensions_positive CHECK (embedding_dimensions > 0)
);
