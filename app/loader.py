"""Markdown filing loader — LangChain-compatible document interface.

Loads a ``.md`` annual filing and splits it into one document per
``## section`` heading, preserving filing title and section name in
``metadata``.  The interface mirrors LangChain's ``PyPDFLoader`` output
(``{"page_content": str, "metadata": dict}``) so the loader can be swapped
for a PDF-based loader without touching the rest of the pipeline.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List

__all__ = ["load_markdown_as_documents"]

# LangChain-compatible document type alias
_Document = dict  # {"page_content": str, "metadata": dict}


def load_markdown_as_documents(path: str) -> List[_Document]:
    """Load a Markdown annual filing and return a list of section documents.

    Each ``## heading`` becomes one document.  The function preserves the
    filing's H1 title and the heading text as ``metadata["section"]``.

    Parameters
    ----------
    path :
        Absolute or relative path to the ``.md`` filing file.

    Returns
    -------
    list of dict
        Each element has:

        * ``page_content`` — stripped text for that section.
        * ``metadata``    — ``{"title": str, "section": str}``.

    Raises
    ------
    FileNotFoundError
        When *path* does not point to an existing file.
    ValueError
        When the file is empty or contains no parsable section content.
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Filing not found: {path}")

    text = file_path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"Filing is empty: {path}")

    # Split at every ## heading while keeping the heading in the following part
    parts = re.split(r"\n(?=## )", text)

    # Extract the H1 title from the preamble (first part before any ## heading)
    title_match = re.match(r"^#\s+(.+)", parts[0])
    title = title_match.group(1).strip() if title_match else file_path.stem

    documents: List[_Document] = []
    current_section = "Preamble"
    buffer: List[str] = []

    for part in parts:
        lines = part.splitlines()
        if lines and lines[0].startswith("## "):
            # Flush previously accumulated buffer as one document
            _flush_buffer(buffer, title, current_section, documents)
            current_section = lines[0][3:].strip()  # strip "## "
            buffer = lines[1:]
        else:
            # Lines before the first ## heading (preamble / title block)
            buffer.extend(lines[1:])  # skip the H1 line itself

    # Flush the last section
    _flush_buffer(buffer, title, current_section, documents)

    if not documents:
        raise ValueError(f"No section content found in: {path}")

    return documents


def _flush_buffer(
    buffer: List[str],
    title: str,
    section: str,
    documents: List[_Document],
) -> None:
    """Append a non-empty buffer as a new document to *documents*.

    Parameters
    ----------
    buffer :
        Accumulated text lines for the current section.
    title :
        Filing title extracted from the H1 heading.
    section :
        Current section name (from the last ``## heading``).
    documents :
        Mutable list to which the new document is appended in-place.
    """
    content = "\n".join(buffer).strip()
    if content:
        documents.append(
            {
                "page_content": content,
                "metadata": {"title": title, "section": section},
            }
        )
    buffer.clear()
