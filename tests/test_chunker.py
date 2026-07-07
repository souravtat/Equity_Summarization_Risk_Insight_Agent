"""Tests for app.chunker — fixed-size character chunking."""

from __future__ import annotations

import pytest

from app.chunker import chunk_documents


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_short_doc_passes_through() -> None:
    """Documents shorter than max_chars are returned unchanged."""
    docs = [{"page_content": "Short text.", "metadata": {"section": "A"}}]
    result = chunk_documents(docs, max_chars=100)
    assert len(result) == 1
    assert result[0]["page_content"] == "Short text."


def test_long_doc_is_split() -> None:
    """Documents exceeding max_chars are split into multiple chunks."""
    text = "A" * 250
    docs = [{"page_content": text, "metadata": {"section": "B"}}]
    result = chunk_documents(docs, max_chars=100)
    assert len(result) == 3  # 250 / 100 = 3 chunks
    assert result[0]["metadata"]["chunk_index"] == 0
    assert result[1]["metadata"]["chunk_index"] == 1
    assert result[2]["metadata"]["chunk_index"] == 2


def test_metadata_preserved_on_split() -> None:
    """Original metadata keys are preserved in each chunk."""
    docs = [{"page_content": "X" * 200, "metadata": {"section": "Risk", "title": "T"}}]
    result = chunk_documents(docs, max_chars=100)
    for chunk in result:
        assert chunk["metadata"]["section"] == "Risk"
        assert chunk["metadata"]["title"] == "T"
        assert "chunk_index" in chunk["metadata"]


def test_invalid_max_chars() -> None:
    """ValueError when max_chars < 1."""
    with pytest.raises(ValueError, match="max_chars"):
        chunk_documents([], max_chars=0)


def test_invalid_docs_type() -> None:
    """TypeError when docs is not a list."""
    with pytest.raises(TypeError, match="list"):
        chunk_documents("not a list", max_chars=100)  # type: ignore[arg-type]


def test_empty_list() -> None:
    """Empty input produces empty output."""
    assert chunk_documents([], max_chars=100) == []
