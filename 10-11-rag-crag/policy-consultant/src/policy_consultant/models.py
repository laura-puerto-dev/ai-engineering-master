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
