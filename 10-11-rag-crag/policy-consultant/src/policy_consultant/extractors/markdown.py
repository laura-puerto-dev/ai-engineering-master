"""Text extraction from Markdown documents."""

from pathlib import Path


def extract_markdown(path: Path) -> str:
    """Read a Markdown document, preserving its original structure."""
    return path.read_text(encoding="utf-8")
