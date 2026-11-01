"""Chunking strategies for IngestedDocument content.

Only `structured_recursive` exists today. CHUNKERS is a registry keyed by
strategy name, mirroring EXTRACTORS in ingestion.py, so a future strategy
(e.g. a `plain_recursive` fallback for documents without heading structure)
can be added without changing callers that select a strategy by name.
"""

import re
from collections.abc import Callable, Iterator

from policy_consultant.models import DocumentChunk, IngestedDocument

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")
LIST_ITEM_RE = re.compile(r"^\s*([-*]|\d+\.)\s+\S")


def structured_recursive(
    document: IngestedDocument,
    max_chars: int,
) -> Iterator[DocumentChunk]:
    """Chunk a document by its heading hierarchy, falling back to
    paragraph- and word-boundary splitting only for content that doesn't
    fit within max_chars.

    - A heading's own text runs until its next heading of any level; a
      heading with no text of its own before its first child heading
      produces no chunk, but its title still appears in its children's
      section_path.
    - Content before the first heading of level 2 or deeper (if any) is
      yielded as its own chunk with section_path=[]. This chunker does not
      discard it: a general-purpose structural chunker has no way to know
      such content is administrative metadata for this corpus. Callers
      that do know that (the Policy Consultant indexing pipeline) are
      responsible for filtering those chunks out — and, if they do, for
      renumbering the ordinals and rebuilding chunk_id for the chunks they
      keep, so indexed ordinals stay 0-based and consecutive. This
      function itself always numbers ordinals in document reading order,
      including any such leading chunk.
    - max_chars is a target for divisible content, not a hard ceiling. If
      a section's own text already fits within max_chars, it is kept as a
      single chunk exactly as written — including a table alongside other
      paragraphs, if it has one. Splitting only happens once a section's
      text exceeds max_chars, and even then: a table block is always
      emitted as its own chunk, never split regardless of size and never
      merged with neighboring blocks. A list block may be split, but only
      between items, never inside one. A plain prose block is split at
      word boundaries, falling back to a hard character cut only for a
      single word longer than max_chars. Consecutive blocks that each fit
      on their own (paragraphs, and lists that don't need splitting) are
      greedily merged into one chunk, joined by a blank line, while the
      combined length stays within max_chars, so a section isn't split
      into more, smaller pieces than it needs to be.
    - chunk_id is f"{document_id}:{version}:{ordinal}".
    """
    if max_chars <= 0:
        raise ValueError("max_chars must be greater than 0")

    return _iter_structured_recursive_chunks(document, max_chars)


ChunkerFn = Callable[[IngestedDocument, int], Iterator[DocumentChunk]]

CHUNKERS: dict[str, ChunkerFn] = {
    "structured_recursive": structured_recursive,
}


def chunk_document(
    document: IngestedDocument,
    strategy: str,
    max_chars: int,
) -> Iterator[DocumentChunk]:
    """Select a chunking strategy by name and apply it."""
    chunker = CHUNKERS.get(strategy)

    if chunker is None:
        raise ValueError(f"Unsupported chunking strategy: {strategy}")

    return chunker(document, max_chars)


def _iter_structured_recursive_chunks(
    document: IngestedDocument,
    max_chars: int,
) -> Iterator[DocumentChunk]:
    document_id = document["metadata"]["document_id"]
    version = document["metadata"]["version"]
    lines = document["content"].split("\n")
    headings = _find_headings(lines)
    section_headings = [heading for heading in headings if heading[1] >= 2]

    ordinal = 0

    leading_end = section_headings[0][0] if section_headings else len(lines)
    leading_text = "\n".join(lines[:leading_end]).strip()

    if leading_text:
        for piece in _split_body(leading_text, max_chars):
            yield DocumentChunk(
                chunk_id=f"{document_id}:{version}:{ordinal}",
                document_id=document_id,
                ordinal=ordinal,
                section_path=[],
                text=piece,
            )
            ordinal += 1

    path_stack: list[tuple[int, str]] = []

    for index, (line_no, level, title) in enumerate(section_headings):
        next_line = (
            section_headings[index + 1][0]
            if index + 1 < len(section_headings)
            else len(lines)
        )
        own_text = "\n".join(lines[line_no + 1 : next_line]).strip()

        path_stack = [entry for entry in path_stack if entry[0] < level]
        path_stack.append((level, title))
        section_path = [entry[1] for entry in path_stack]

        if not own_text:
            continue

        for piece in _split_body(own_text, max_chars):
            yield DocumentChunk(
                chunk_id=f"{document_id}:{version}:{ordinal}",
                document_id=document_id,
                ordinal=ordinal,
                section_path=list(section_path),
                text=piece,
            )
            ordinal += 1


def _find_headings(lines: list[str]) -> list[tuple[int, int, str]]:
    """Return (line_index, level, title) for every ATX heading."""
    headings = []
    for index, line in enumerate(lines):
        match = HEADING_RE.match(line)
        if match:
            headings.append((index, len(match.group(1)), match.group(2)))
    return headings


def _split_body(body: str, max_chars: int) -> list[str]:
    """If the whole section already fits within max_chars, return it as a
    single piece, unchanged — including a table alongside other
    paragraphs, if it has one. Otherwise, split it into pieces of at most
    max_chars where possible: consecutive blocks (paragraphs, and lists
    that fit on their own) are greedily merged into one piece, joined by
    a blank line, as long as the combined length stays within max_chars.
    A table block is always emitted as its own piece — never merged with
    neighboring blocks, and never split, regardless of size. A block that
    doesn't fit on its own is flushed in isolation and split internally
    (by list item, or by word for prose) rather than merged with what
    comes before or after it.
    """
    if len(body) <= max_chars:
        return [body]

    pieces: list[str] = []
    buffer: list[str] = []

    def flush() -> None:
        if buffer:
            pieces.append("\n\n".join(buffer))
            buffer.clear()

    for block in _blocks(body):
        if _is_table(block):
            flush()
            pieces.append(block)
            continue

        if len(block) > max_chars:
            flush()
            if _is_list(block):
                pieces.extend(_split_list_by_items(block, max_chars))
            else:
                pieces.extend(_split_by_words(block, max_chars))
            continue

        candidate_len = len("\n\n".join([*buffer, block]))
        if buffer and candidate_len > max_chars:
            flush()

        buffer.append(block)

    flush()
    return pieces


def _blocks(text: str) -> list[str]:
    return [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]


def _is_table(block: str) -> bool:
    return any(TABLE_ROW_RE.match(line) for line in block.split("\n"))


def _is_list(block: str) -> bool:
    return any(LIST_ITEM_RE.match(line) for line in block.split("\n"))


def _split_list_by_items(block: str, max_chars: int) -> list[str]:
    """Group a list's lines into items (a marker line plus any continuation
    lines), then greedily pack whole items into pieces up to max_chars.
    An item that alone exceeds max_chars is kept whole rather than split.
    """
    items: list[list[str]] = []
    for line in block.split("\n"):
        if LIST_ITEM_RE.match(line) or not items:
            items.append([line])
        else:
            items[-1].append(line)

    item_texts = ["\n".join(item) for item in items]

    pieces: list[str] = []
    current: list[str] = []
    current_len = 0

    for item_text in item_texts:
        added_len = len(item_text) + (1 if current else 0)
        if current and current_len + added_len > max_chars:
            pieces.append("\n".join(current))
            current = []
            current_len = 0

        current.append(item_text)
        current_len += added_len

    if current:
        pieces.append("\n".join(current))

    return pieces


def _split_by_words(block: str, max_chars: int) -> list[str]:
    """Greedily pack words into pieces up to max_chars, breaking only at
    whitespace. A single word longer than max_chars is hard-cut, since
    there is no boundary left to break on.
    """
    pieces: list[str] = []
    current: list[str] = []

    def flush() -> None:
        if current:
            pieces.append(" ".join(current))
            current.clear()

    for word in block.split():
        if len(word) > max_chars:
            flush()
            for start in range(0, len(word), max_chars):
                pieces.append(word[start : start + max_chars])
            continue

        candidate_len = len(" ".join([*current, word]))
        if current and candidate_len > max_chars:
            flush()

        current.append(word)

    flush()
    return pieces
