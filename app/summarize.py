"""Orchestrates the full filing → structured analyst report pipeline.

Pipeline (per filing):
1. Load the ``.md`` filing via :func:`~app.loader.load_markdown_as_documents`.
2. Chunk sections via :func:`~app.chunker.chunk_documents`.
3. **LLM path** (preferred): call :func:`~app.llm_client.summarize_with_llm`
   when ``GROQ_API_KEY`` is set.
4. **Lexicon + FAISS fallback**: extract highlights from Business/Results
   chunks, retrieve risk snippets via :class:`~app.retriever.FaissRetriever`,
   and classify tone using lexicon counts + financial metric anchors.

The returned dict always contains ``filing_id``, ``highlights``, ``risks``,
``tone``, and a ``source`` field (``"llm"`` or ``"lexicon"``) for traceability.
"""

from __future__ import annotations

import logging
import os
from typing import List

from .chunker import chunk_documents
from .llm_client import summarize_with_llm
from .loader import load_markdown_as_documents
from .retriever import FaissRetriever
from .sentiment_risk import (
    extract_financial_metrics,
    extract_risk_snippets,
    label_from_scores,
    score_sentiment,
)

__all__ = ["summarize_filing"]

_logger = logging.getLogger(__name__)

_CORPUS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "corpus", "filings"
)
_HIGHLIGHT_SECTIONS: frozenset = frozenset({"Business", "Results"})
_MAX_CHUNK_CHARS: int = 800
_RISK_QUERY = (
    "cybersecurity regulatory risk breach penalties volatility churn "
    "litigation adverse uncertainty compliance"
)


def _build_highlights(chunks: List[dict]) -> List[str]:
    """Extract up to 2 highlight bullets from Business/Results chunks.

    Takes the first complete sentence from each qualifying chunk.  A section
    citation ``(section_name)`` is appended so readers can trace the source.

    Parameters
    ----------
    chunks :
        All document chunks for the filing.

    Returns
    -------
    list of str
        Up to 2 bullet strings with section citations.
    """
    highlights: List[str] = []
    for chunk in chunks:
        section: str = chunk["metadata"].get("section", "")
        if section in _HIGHLIGHT_SECTIONS and len(highlights) < 2:
            first_sentence = chunk["page_content"].split(".")[0].strip()
            if first_sentence:
                highlights.append(f"{first_sentence}. ({section})")
    return highlights


def _build_risks(chunks: List[dict]) -> List[str]:
    """Extract up to 3 risk bullets, preferring semantically diverse sections.

    Uses :class:`~app.retriever.FaissRetriever` for semantic re-ranking and
    de-duplicates by section to ensure broad coverage.  Falls back to pure
    keyword-score ranking via
    :func:`~app.sentiment_risk.extract_risk_snippets` on any retriever error.

    Parameters
    ----------
    chunks :
        All document chunks for the filing.

    Returns
    -------
    list of str
        Up to 3 risk bullet strings with section citations.
    """
    try:
        retriever = FaissRetriever(chunks)
        candidate_chunks = retriever.query(_RISK_QUERY, k=8)
    except Exception as exc:  # pylint: disable=broad-except
        _logger.debug("FaissRetriever error (%s); using keyword fallback.", exc)
        candidate_chunks = extract_risk_snippets(chunks, k=8)

    seen_sections: set = set()
    risks: List[str] = []
    for chunk in candidate_chunks:
        section = chunk["metadata"].get("section", "")
        first_sentence = chunk["page_content"].split(".")[0].strip()
        if first_sentence and section not in seen_sections:
            risks.append(f"{first_sentence}. ({section})")
            seen_sections.add(section)
        if len(risks) >= 3:
            break

    return risks


def summarize_filing(filing_id: str) -> dict:
    """Load a filing and return a structured analyst report.

    Tries the LLM-powered pipeline first (requires ``GROQ_API_KEY``).  On any
    LLM failure — missing key, missing package, or API error — automatically
    falls back to the lexicon + FAISS pipeline.

    Parameters
    ----------
    filing_id :
        Filing identifier, e.g. ``"HLSR-2024"`` (without ``.md`` extension).
        Case-insensitive; internally normalised to upper-case.

    Returns
    -------
    dict
        ``{"filing_id": str, "highlights": list[str], "risks": list[str],
        "tone": str, "source": str}``

        ``source`` is ``"llm"`` when Groq was used, ``"lexicon"`` otherwise.

    Raises
    ------
    FileNotFoundError
        When no corpus file matches *filing_id*.
    """
    normalised_id = filing_id.strip().upper()
    path = os.path.join(_CORPUS_DIR, f"{normalised_id}.md")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Unknown filing_id: '{filing_id}'. "
            f"Check corpus/filings/ for available files."
        )

    docs = load_markdown_as_documents(path)
    chunks = chunk_documents(docs, _MAX_CHUNK_CHARS)

    # Build a single concatenated text block for the LLM
    full_text = "\n\n".join(
        f"## {d['metadata']['section']}\n{d['page_content']}"
        for d in docs
    )

    # ---------------------------------------------------------------
    # LLM path
    # ---------------------------------------------------------------
    llm_result = summarize_with_llm(full_text)
    if llm_result is not None:
        return {
            "filing_id": normalised_id,
            "highlights": llm_result["highlights"],
            "risks": llm_result["risks"],
            "tone": llm_result["tone"],
            "source": "llm",
        }

    # ---------------------------------------------------------------
    # Lexicon + FAISS fallback
    # ---------------------------------------------------------------
    return _lexicon_report(normalised_id, chunks, full_text)


def _aggregate_sentiment(chunks: List[dict]) -> tuple:
    """Sum lexicon scores across all chunks.

    Parameters
    ----------
    chunks :
        List of document chunk dicts.

    Returns
    -------
    tuple of int
        ``(total_pos, total_neg, total_unc)``
    """
    total_pos = total_neg = total_unc = 0
    for chunk in chunks:
        cp, cn, cu = score_sentiment(chunk["page_content"])
        total_pos += cp
        total_neg += cn
        total_unc += cu
    return total_pos, total_neg, total_unc


def _lexicon_report(
    filing_id: str,
    chunks: List[dict],
    full_text: str,
) -> dict:
    """Build the lexicon + FAISS report for a single filing.

    Parameters
    ----------
    filing_id :
        Normalised filing identifier.
    chunks :
        All document chunks for the filing.
    full_text :
        Concatenated section text (used for metric extraction).

    Returns
    -------
    dict
        ``{"filing_id", "highlights", "risks", "tone", "source"}``.
    """
    highlights = _build_highlights(chunks)
    risks = _build_risks(chunks)
    total_pos, total_neg, total_unc = _aggregate_sentiment(chunks)
    metrics = extract_financial_metrics(full_text)
    tone = label_from_scores(total_pos, total_neg, total_unc, metrics)

    return {
        "filing_id": filing_id,
        "highlights": highlights[:2],
        "risks": risks[:3],
        "tone": tone,
        "source": "lexicon",
    }
