"""Connects ingestion and chunking into a flat, lazy stream of chunks ready
for a future embedding/persistence stage.

prepare_indexable_chunks yields one IndexableChunk at a time: never a full
list of a document's chunks, nor the whole corpus. Chunks belonging to the
same document are always emitted consecutively and in their original order,
so a future consumer can batch across document boundaries (for embeddings)
or regroup by document_id (e.g. with itertools.groupby, for an atomic
per-document persistence transaction) without this module choosing one
grouping over the other.

This module does not filter by section_path: a document with no headings
at all legitimately produces a chunk with section_path=[] that carries
real content, so emptiness of that list is not a signal of anything. The
only discard rule here is empty/whitespace-only text, which is
corpus-agnostic.
"""

from collections.abc import Iterator
from pathlib import Path

from policy_consultant.chunking import chunk_document
from policy_consultant.ingestion import ingest_documents
from policy_consultant.models import DocumentChunk, IndexableChunk, PolicyDocument


def prepare_indexable_chunks(
    documents: list[PolicyDocument],
    project_root: Path,
    *,
    strategy: str,
    max_chars: int,
) -> Iterator[IndexableChunk]:
    """Ingest, chunk, and renumber every current document's chunks.

    Reuses ingest_documents (current-only, lazy across documents) and
    chunk_document (lazy within a document) without changing either. Every
    chunk in the output is paired with a reference to its document's
    PolicyDocument — the same dict for every chunk of that document, never
    copied per chunk.
    """
    for ingested in ingest_documents(documents, project_root):
        metadata = ingested["metadata"]
        raw_chunks = chunk_document(ingested, strategy, max_chars)

        for chunk in _renumber_chunks(raw_chunks, metadata["document_id"], metadata["version"]):
            yield IndexableChunk(document=metadata, chunk=chunk)


def _renumber_chunks(
    chunks: Iterator[DocumentChunk],
    document_id: str,
    version: str,
) -> Iterator[DocumentChunk]:
    """Drop empty/whitespace-only chunks and renumber the ones kept so
    ordinals stay 0-based and consecutive, rebuilding chunk_id to match.

    Lazy and local: a running counter advances only for chunks that are
    kept, with no lookahead or buffering, so this works chunk by chunk
    regardless of how many chunks a document has.
    """
    ordinal = 0
    for chunk in chunks:
        if not chunk["text"].strip():
            continue

        yield DocumentChunk(
            chunk_id=f"{document_id}:{version}:{ordinal}",
            document_id=document_id,
            ordinal=ordinal,
            section_path=chunk["section_path"],
            text=chunk["text"],
        )
        ordinal += 1
