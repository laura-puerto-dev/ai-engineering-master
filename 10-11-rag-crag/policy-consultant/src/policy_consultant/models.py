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
