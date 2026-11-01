
"""Document ingestion with extensible format-specific extractors."""

from collections.abc import Callable, Iterator
from pathlib import Path

from policy_consultant.extractors.markdown import extract_markdown
from policy_consultant.models import IngestedDocument, PolicyDocument

TextExtractor = Callable[[Path], str]

EXTRACTORS: dict[str, TextExtractor] = {
    ".md": extract_markdown,
}


def extract_text(path: Path) -> str:
    """Select an extractor based on the document's file extension."""
    extractor = EXTRACTORS.get(path.suffix.lower())

    if extractor is None:
        raise ValueError(f"Unsupported document format: {path.suffix}")

    return extractor(path)


def ingest_documents(
    documents: list[PolicyDocument],
    project_root: Path,
) -> Iterator[IngestedDocument]:
    """Lazily ingest current policies, yielding one document at a time.

    This generator never accumulates the corpus's document content in
    memory itself, regardless of whether the manifest lists 12 documents or
    10,000: the metadata list is cheap to hold in full, but document content
    is not. Overall memory use still depends on what the consumer does with
    each yielded document — this only guarantees the ingestion step itself
    doesn't hold the whole corpus at once.
    """
    for document in documents:
        if document["status"] != "current":
            continue

        file_path = project_root / document["path"]
        content = extract_text(file_path)

        yield IngestedDocument(
            metadata=document.copy(),
            content=content,
        )
