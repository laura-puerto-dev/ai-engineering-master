"""CLI entry point: synchronize config/corpus-manifest.yaml with
PostgreSQL using sync_corpus(). Safe to run repeatedly — documents whose
version hasn't changed are never re-embedded.

Requires both optional dependency groups:

    uv sync --extra embeddings --extra persistence
    uv run python scripts/sync_corpus.py

Exit codes:
    0 - sync completed with nothing requiring attention.
    1 - sync completed, but something needs human review (a failed
        document, a rejected stale version, a metadata conflict, or a
        document missing from the manifest).
    2 - sync aborted before (or without) producing a report at all (an
        invalid manifest, an embedding model incompatible with what
        index_metadata already has registered, or any other
        configuration-level failure).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from policy_consultant.corpus_manifest import load_access_model, load_documents
from policy_consultant.db import admin_connection
from policy_consultant.embedding import LocalBgeM3EmbeddingModel
from policy_consultant.models import SyncReport
from policy_consultant.sync import sync_corpus

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = PROJECT_ROOT / "config" / "corpus-manifest.yaml"
ACCESS_MODEL_PATH = PROJECT_ROOT / "config" / "access-model.yaml"

CHUNKING_STRATEGY = "structured_recursive"
MAX_CHARS = 1000
EMBEDDING_BATCH_SIZE = 32

def _format_category(label: str, document_ids: list[str]) -> str:
    if not document_ids:
        return f"  {label} (0): -"
    return f"  {label} ({len(document_ids)}): {', '.join(document_ids)}"


def _format_report(report: SyncReport) -> str:
    lines = [
        "Sync complete.",
        _format_category("Inserted", report["inserted"]),
        _format_category("Updated", report["updated"]),
        _format_category("Updated metadata", report["updated_metadata"]),
        _format_category("Unchanged", report["unchanged"]),
        _format_category("Rejected (stale version)", report["rejected_stale"]),
        _format_category("Metadata conflicts", report["metadata_conflict"]),
        _format_category("Missing from manifest", report["missing_from_manifest"]),
    ]

    failed = report["failed"]
    if failed:
        details = "; ".join(f"{document_id}: {message}" for document_id, message in failed)
        lines.append(f"  Failed ({len(failed)}): {details}")
    else:
        lines.append("  Failed (0): -")

    return "\n".join(lines)


def _exit_code_for(report: SyncReport) -> int:
    # missing_from_manifest is included deliberately: a document absent
    # from the manifest is never deleted (see sync.py), but it is still
    # something a human should look at, not a silent no-op.
    needs_attention = (
        report["failed"]
        or report["rejected_stale"]
        or report["metadata_conflict"]
        or report["missing_from_manifest"]
    )
    return 1 if needs_attention else 0


def main() -> int:
    load_dotenv()
    device = os.environ.get("EMBEDDING_DEVICE", "cpu")

    try:
        documents = load_documents(MANIFEST_PATH)
        access_model = load_access_model(ACCESS_MODEL_PATH)
        model = LocalBgeM3EmbeddingModel(device=device)

        with admin_connection() as conn:
            report = sync_corpus(
                conn,
                documents,
                PROJECT_ROOT,
                access_model,
                model,
                chunking_strategy=CHUNKING_STRATEGY,
                max_chars=MAX_CHARS,
                embedding_batch_size=EMBEDDING_BATCH_SIZE,
                embedding_model_revision=model.revision,
                embeddings_normalized=True,
            )
    except Exception as exc:
        print(f"Sync aborted: {exc}", file=sys.stderr)
        return 2

    print(_format_report(report))
    return _exit_code_for(report)


if __name__ == "__main__":
    sys.exit(main())
