"""Corpus synchronization: reconcile config/corpus-manifest.yaml against
PostgreSQL, calling persist_document() for real content changes and a
lightweight metadata-only UPDATE for changes that don't need a new
embedding. Never generates embeddings for a document whose version
hasn't changed.

Definitive retirement (deleting a document_id no longer in the manifest)
is explicitly out of scope this stage — not just deferred, but currently
unreachable: corpus_manifest.validate_version_history requires every
document_id appearing anywhere in the manifest to have exactly one
current version, so a document_id with only `superseded` entries and no
`current` one already fails validate_manifest before sync_corpus could
ever plan a retirement for it (verified directly: validate_manifest
raises "must have exactly one current version, found 0" for such a
case). A document_id that disappears from the manifest entirely is
invisible to that check (it just never appears in the documents list),
which is exactly why it is treated here as a review-worthy absence, not
evidence of an intentional retirement — PostgreSQL is never modified for
it. Enabling real retirement would mean changing validate_manifest's
invariant or introducing a distinct "retired" status — either is a
decision for a future stage, not something to introduce as a side effect
of this one.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import NamedTuple

import psycopg

from policy_consultant.corpus_manifest import validate_manifest
from policy_consultant.embedding import EmbeddingModel, embed_indexable_chunks
from policy_consultant.indexing_prep import prepare_indexable_chunks
from policy_consultant.models import AccessModel, PolicyDocument, SyncPlan, SyncReport
from policy_consultant.persistence import persist_document


class _StoredDocument(NamedTuple):
    """One row of what is currently in the documents table — just the
    columns _plan_sync needs to compare against the manifest. Private to
    this module: SyncPlan/SyncReport (in models.py) are the only shapes
    this module exposes publicly.
    """

    version: str
    country: str
    language: str
    allowed_roles: list[str]
    effective_from: date
    path: str


def sync_corpus(
    conn: psycopg.Connection,
    manifest_documents: list[PolicyDocument],
    project_root: Path,
    access_model: AccessModel,
    embedding_model: EmbeddingModel,
    *,
    chunking_strategy: str,
    max_chars: int,
    embedding_batch_size: int,
    embedding_model_revision: str,
    embeddings_normalized: bool,
) -> SyncReport:
    """Reconcile manifest_documents (the full, already-loaded manifest —
    current and superseded) against what PostgreSQL currently has.

    Two things abort the whole run immediately, before any document is
    touched, because they mean the inputs can't be trusted enough to plan
    anything: validate_manifest raising (the manifest itself is
    internally inconsistent), and this run's embedding configuration not
    matching what index_metadata already has registered. Everything else
    — a single document's extraction/embedding/persistence failure, a
    stale version, a metadata conflict, a document missing from the
    manifest — is a per-document, expected operational outcome: it is
    recorded in the returned SyncReport and never stops the rest of the
    run.
    """
    validate_manifest(manifest_documents, project_root, access_model)
    _check_global_embedding_model_compatibility(
        conn,
        model_id=embedding_model.model_id,
        revision=embedding_model_revision,
        dimensions=embedding_model.dimensions,
        normalized=embeddings_normalized,
    )

    stored_documents = _read_stored_documents(conn)
    plan = _plan_sync(manifest_documents, stored_documents)

    report = SyncReport(
        inserted=[],
        updated=[],
        updated_metadata=[],
        unchanged=list(plan["unchanged"]),
        rejected_stale=list(plan["rejected_stale"]),
        metadata_conflict=list(plan["metadata_conflict"]),
        missing_from_manifest=list(plan["missing_from_manifest"]),
        failed=[],
    )

    for document in plan["to_insert"]:
        document_id = document["document_id"]
        try:
            _embed_and_persist(
                conn,
                document,
                project_root,
                embedding_model,
                chunking_strategy=chunking_strategy,
                max_chars=max_chars,
                embedding_batch_size=embedding_batch_size,
                embedding_model_revision=embedding_model_revision,
                embeddings_normalized=embeddings_normalized,
            )
        except Exception as exc:
            # Intentional per-document fault isolation (see module/function
            # docstrings): one bad document must never stop the others.
            report["failed"].append((document_id, str(exc)))
        else:
            report["inserted"].append(document_id)

    for document in plan["to_update"]:
        document_id = document["document_id"]
        try:
            _embed_and_persist(
                conn,
                document,
                project_root,
                embedding_model,
                chunking_strategy=chunking_strategy,
                max_chars=max_chars,
                embedding_batch_size=embedding_batch_size,
                embedding_model_revision=embedding_model_revision,
                embeddings_normalized=embeddings_normalized,
            )
        except Exception as exc:
            report["failed"].append((document_id, str(exc)))
        else:
            report["updated"].append(document_id)

    for document in plan["to_update_metadata"]:
        document_id = document["document_id"]
        try:
            updated = _update_document_metadata(
                conn,
                document_id,
                document["version"],
                document["allowed_roles"],
                document["path"],
            )
        except Exception as exc:
            report["failed"].append((document_id, str(exc)))
            continue

        if updated:
            report["updated_metadata"].append(document_id)
        else:
            report["failed"].append(
                (document_id, "metadata update matched no row: version changed concurrently")
            )

    return report


def _plan_sync(
    manifest_documents: list[PolicyDocument],
    stored_documents: dict[str, _StoredDocument],
) -> SyncPlan:
    """Pure, DB-free: decide what should happen to each document_id, given
    the manifest's current documents and a snapshot of what's stored.

    allowed_roles is compared as a set, not a list: its order carries no
    meaning, unlike e.g. section_path on a chunk.
    """
    plan = SyncPlan(
        to_insert=[],
        to_update=[],
        to_update_metadata=[],
        unchanged=[],
        rejected_stale=[],
        metadata_conflict=[],
        missing_from_manifest=[],
    )

    current_documents = [doc for doc in manifest_documents if doc["status"] == "current"]
    current_ids = {doc["document_id"] for doc in current_documents}

    for document in current_documents:
        document_id = document["document_id"]
        stored = stored_documents.get(document_id)

        if stored is None:
            plan["to_insert"].append(document)
            continue

        if document["version"] != stored.version:
            if document["effective_from"] > stored.effective_from:
                plan["to_update"].append(document)
            else:
                plan["rejected_stale"].append(document_id)
            continue

        unsafe_changed = (
            document["country"] != stored.country
            or document["language"] != stored.language
            or document["effective_from"] != stored.effective_from
        )
        if unsafe_changed:
            plan["metadata_conflict"].append(document_id)
            continue

        safe_changed = (
            set(document["allowed_roles"]) != set(stored.allowed_roles)
            or document["path"] != stored.path
        )
        if safe_changed:
            plan["to_update_metadata"].append(document)
        else:
            plan["unchanged"].append(document_id)

    for document_id in stored_documents:
        if document_id not in current_ids:
            plan["missing_from_manifest"].append(document_id)

    return plan


def _read_stored_documents(conn: psycopg.Connection) -> dict[str, _StoredDocument]:
    rows = conn.execute(
        """
        SELECT document_id, version, country, language, allowed_roles, effective_from, path
        FROM documents
        """
    ).fetchall()
    return {
        row[0]: _StoredDocument(
            version=row[1],
            country=row[2],
            language=row[3],
            allowed_roles=row[4],
            effective_from=row[5],
            path=row[6],
        )
        for row in rows
    }


def _check_global_embedding_model_compatibility(
    conn: psycopg.Connection,
    *,
    model_id: str,
    revision: str,
    dimensions: int,
    normalized: bool,
) -> None:
    """Read-only pre-check: abort the whole run early if index_metadata
    already disagrees with the model this run is configured to use,
    instead of discovering that the hard way after embedding every
    document only to have persist_document reject each one individually.

    Deliberately not shared with persistence._check_or_register_embedding_
    model: that function also performs the bootstrap INSERT, which this
    read-only pre-check must not do (bootstrapping stays persist_document's
    job on the first real write).
    """
    row = conn.execute(
        """
        SELECT embedding_model_id, embedding_model_revision, embedding_dimensions,
               embeddings_normalized
        FROM index_metadata
        """
    ).fetchone()
    if row is None:
        return

    stored = tuple(row)
    requested = (model_id, revision, dimensions, normalized)
    if stored != requested:
        raise ValueError(
            "Embedding model mismatch: index_metadata is registered as "
            f"model_id={stored[0]!r} revision={stored[1]!r} dimensions={stored[2]} "
            f"normalized={stored[3]}, but this sync run uses model_id={model_id!r} "
            f"revision={revision!r} dimensions={dimensions} normalized={normalized}"
        )


def _embed_and_persist(
    conn: psycopg.Connection,
    document: PolicyDocument,
    project_root: Path,
    embedding_model: EmbeddingModel,
    *,
    chunking_strategy: str,
    max_chars: int,
    embedding_batch_size: int,
    embedding_model_revision: str,
    embeddings_normalized: bool,
) -> None:
    """Run one document through the existing chunking/embedding pipeline
    and persist it. One document at a time, not the whole changed subset
    as one shared lazy stream: prepare_indexable_chunks/embed_indexable_
    chunks have no per-document error isolation, so a single bad file
    would otherwise abort every document still pending in the same
    stream. The trade-off is losing cross-document embedding batching,
    accepted given this corpus's real size (a dozen documents, not
    thousands).
    """
    chunks = list(
        embed_indexable_chunks(
            prepare_indexable_chunks(
                [document], project_root, strategy=chunking_strategy, max_chars=max_chars
            ),
            embedding_model,
            batch_size=embedding_batch_size,
        )
    )
    persist_document(
        conn,
        document,
        chunks,
        embedding_model_revision=embedding_model_revision,
        embeddings_normalized=embeddings_normalized,
    )


def _update_document_metadata(
    conn: psycopg.Connection,
    document_id: str,
    version: str,
    allowed_roles: list[str],
    path: str,
) -> bool:
    """Update only allowed_roles/path, scoped to the exact version the
    planner observed (WHERE document_id AND version). Returns False
    (changing nothing) if that row no longer matches — e.g. concurrently
    updated or no longer current — instead of blindly overwriting state
    the planner never saw. No general concurrency control is introduced:
    this only detects the mismatch and reports it as a failure.
    """
    with conn.transaction():
        cursor = conn.execute(
            """
            UPDATE documents
            SET allowed_roles = %s, path = %s, updated_at = now()
            WHERE document_id = %s AND version = %s
            """,
            (allowed_roles, path, document_id, version),
        )
        return cursor.rowcount == 1
