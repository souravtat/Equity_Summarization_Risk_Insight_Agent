"""Tests for app.retriever — FAISS-backed semantic chunk retriever."""

from __future__ import annotations

import pytest

from app.retriever import FaissRetriever


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_SAMPLE_CHUNKS = [
    {"page_content": "Revenue grew 21% driven by cloud migrations.", "metadata": {"section": "Results"}},
    {"page_content": "Cybersecurity risk breach penalties regulatory.", "metadata": {"section": "Risk Factors"}},
    {"page_content": "Cash position is strong at $800M.", "metadata": {"section": "Liquidity"}},
    {"page_content": "Management expects cautious macro conditions.", "metadata": {"section": "Outlook"}},
]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_query_returns_list() -> None:
    """Query returns a list of chunk dicts."""
    retriever = FaissRetriever(_SAMPLE_CHUNKS)
    results = retriever.query("cybersecurity risk breach", k=2)
    assert isinstance(results, list)
    assert len(results) <= 2


def test_query_relevance() -> None:
    """Risk-related query should rank the Risk Factors chunk highest."""
    retriever = FaissRetriever(_SAMPLE_CHUNKS)
    results = retriever.query("cybersecurity risk breach penalties", k=1)
    assert len(results) == 1
    assert results[0]["metadata"]["section"] == "Risk Factors"


def test_query_k_exceeds_chunks() -> None:
    """When k > len(chunks), all chunks are returned."""
    retriever = FaissRetriever(_SAMPLE_CHUNKS)
    results = retriever.query("test", k=100)
    assert len(results) == len(_SAMPLE_CHUNKS)


def test_empty_chunks_raises() -> None:
    """ValueError for empty chunk list."""
    with pytest.raises(ValueError, match="empty"):
        FaissRetriever([])


def test_invalid_k_raises() -> None:
    """ValueError when k < 1."""
    retriever = FaissRetriever(_SAMPLE_CHUNKS)
    with pytest.raises(ValueError, match="k must be"):
        retriever.query("test", k=0)
