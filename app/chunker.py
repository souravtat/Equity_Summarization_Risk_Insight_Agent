"""Document chunker — splits long sections into fixed character-size windows.

Documents shorter than *max_chars* pass through unchanged.  Longer documents
are split at *max_chars* boundaries; each chunk inherits the parent metadata
and gains a ``chunk_index`` key so downstream code can reconstruct ordering.
"""

from __future__ import annotations

from typing import List

__all__ = ["chunk_documents"]

_DEFAULT_MAX_CHARS: int = 900


def chunk_documents(
    docs: List[dict],
    max_chars: int = _DEFAULT_MAX_CHARS,
) -> List[dict]:
    """Split a list of documents into fixed-size character chunks.

    Documents whose ``page_content`` fits within *max_chars* are returned as-is.
    Longer documents are split at *max_chars* boundaries.  Every chunk in a
    split document receives a ``chunk_index`` key (0-based) appended to its
    copied metadata.

    Parameters
    ----------
    docs :
        List of document dicts (``{"page_content": str, "metadata": dict}``).
    max_chars :
        Maximum character length per output chunk.  Must be ≥ 1.

    Returns
    -------
    list of dict
        Chunked documents preserving all original metadata fields.

    Raises
    ------
    ValueError
        When *max_chars* is less than 1.
    TypeError
        When *docs* is not a list.
    """
    if not isinstance(docs, list):
        raise TypeError(f"docs must be a list, got {type(docs).__name__}")
    if max_chars < 1:
        raise ValueError(f"max_chars must be >= 1, got {max_chars}")

    output: List[dict] = []
    for doc in docs:
        text: str = doc.get("page_content", "")
        meta: dict = doc.get("metadata", {})

        if len(text) <= max_chars:
            output.append(doc)
        else:
            for idx, start in enumerate(range(0, len(text), max_chars)):
                chunk_text = text[start : start + max_chars]
                output.append(
                    {
                        "page_content": chunk_text,
                        "metadata": {**meta, "chunk_index": idx},
                    }
                )
    return output
