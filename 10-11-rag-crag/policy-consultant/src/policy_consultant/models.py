from datetime import date
from typing import TypedDict


class PolicyDocument(TypedDict):
    document_id: str
    path: str
    country: str
    language: str
    allowed_roles: list[str]
    version: str
    effective_from: date
    effective_to: date | None
    status: str


class IngestedDocument(TypedDict):
    metadata: PolicyDocument
    content: str


class AccessModel(TypedDict):
    """A deployment's access-control vocabulary: which countries, languages,
    and roles its documents may declare. Loaded from config/access-model.yaml
    so a new value in an existing dimension (e.g. a country) is a
    configuration change, not a code change. Adding a new *dimension*
    (e.g. department) is still a schema change to PolicyDocument and to
    validate_fields, by design — this only covers values, not shape.
    """

    countries: set[str]
    languages: set[str]
    roles: set[str]


class DocumentChunk(TypedDict):
    """A chunk produced by the chunker from an IngestedDocument's content.

    Deliberately excludes country/language/allowed_roles/version: the
    indexing pipeline receives the originating IngestedDocument and this
    chunk's document_id in the same call, so those fields are always
    available via that document's PolicyDocument without duplicating them
    on every chunk. The persistence layer (documents/chunks tables) is a
    separate concern from this contract.
    """

    chunk_id: str  # f"{document_id}:{version}:{ordinal}"
    document_id: str
    ordinal: int
    section_path: list[str]
    text: str


class IndexableChunk(TypedDict):
    """One chunk paired with its originating document's full metadata, as
    produced by indexing_prep.prepare_indexable_chunks.

    A flat record rather than a per-document grouping: document and chunk
    carry everything needed to batch across document boundaries (e.g. for
    embeddings) or to regroup by document["document_id"] later (e.g. with
    itertools.groupby, for an atomic per-document persistence transaction)
    without this type favoring one over the other.
    """

    document: PolicyDocument
    chunk: DocumentChunk


class EmbeddedChunk(IndexableChunk):
    """An IndexableChunk paired with its embedding vector.

    model_id is a simple descriptive string (e.g. "BAAI/bge-m3") and does
    not by itself guarantee exact reproducibility: the model's weight
    revision, normalization setting, and other inference parameters can
    all change the resulting vector without changing this string. A
    future persistence layer must record those details explicitly as
    indexing metadata — this field alone is not enough to tell two
    embedding configurations apart.
    """

    embedding: list[float]
    model_id: str


class SyncPlan(TypedDict):
    """The pure decision output of sync._plan_sync: what to do with each
    manifest/stored document_id, before anything touches PostgreSQL.

    to_insert/to_update/to_update_metadata carry full PolicyDocument
    records (everything the next step needs); the other categories only
    need the document_id, since nothing further is done with them this
    stage. See sync.sync_corpus for how each category is executed.
    """

    to_insert: list[PolicyDocument]
    to_update: list[PolicyDocument]
    to_update_metadata: list[PolicyDocument]
    unchanged: list[str]
    rejected_stale: list[str]
    metadata_conflict: list[str]
    missing_from_manifest: list[str]


class SyncReport(TypedDict):
    """What sync.sync_corpus actually did, returned after execution.

    Categories mirror SyncPlan's, except to_insert/to_update/
    to_update_metadata become inserted/updated/updated_metadata (past
    tense: these succeeded). failed collects every document whose
    attempted operation raised, regardless of which planned category it
    came from.
    """

    inserted: list[str]
    updated: list[str]
    updated_metadata: list[str]
    unchanged: list[str]
    rejected_stale: list[str]
    metadata_conflict: list[str]
    missing_from_manifest: list[str]
    failed: list[tuple[str, str]]


class RetrievedChunk(TypedDict):
    """One chunk returned by retrieval.retrieve_relevant_chunks, carrying
    everything a future citation needs to point back to its exact source:
    which document, which version, which section, and the chunk itself.

    version comes from a join against documents (chunks doesn't store it
    — see migrations/001_schema.sql), so it always reflects the document's
    current row, never a stale value baked in at embedding time.

    distance is pgvector's raw cosine distance (<=>) for this chunk
    against the query embedding: 0 is identical, 2 is opposite, lower is
    more relevant. Not stored as a "similarity" score to avoid a second,
    derived field that could drift from this one — a caller that wants
    similarity computes 1 - distance.
    """

    chunk_id: str
    document_id: str
    version: str
    section_path: list[str]
    text: str
    distance: float


class Citation(TypedDict):
    """One chunk the answer generator actually used, resolved from the
    caller's own chunk list by index — never built from free text the
    model wrote. See generation.py's module docstring for why: the model
    may only pick a position from a fixed, already-authorized list, so it
    cannot cite a document/section it was never given.
    """

    document_id: str
    version: str
    section_path: list[str]
    chunk_id: str


class GeneratedAnswer(TypedDict):
    """The result of generation.AnswerGenerator.generate_answer (or
    rag.answer_question short-circuiting before calling it).

    citations is always [] when abstained is True — an abstention never
    carries a grounding claim, even if the model tried to attach one. A
    non-empty answer with abstained=False always has at least one
    citation; see generation.py for how that invariant is enforced.
    """

    answer: str
    citations: list[Citation]
    abstained: bool
