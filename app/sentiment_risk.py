"""Lexicon-based sentiment scorer and risk snippet extractor.

Provides two complementary signals for tone classification:

1. **Lexicon scoring** — counts positive, negative, and uncertainty words
   from curated word sets.
2. **Numerical fundamentals** — extracts revenue growth %, gross margin %, and
   cash position from structured text patterns and uses them as a tiebreaker.

The combined approach improves accuracy over pure-lexicon methods for filings
where all sections share identical boilerplate but differ in key metrics.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

__all__ = [
    "score_sentiment",
    "label_from_scores",
    "extract_risk_snippets",
    "extract_financial_metrics",
]

# ---------------------------------------------------------------------------
# Sentiment lexicons
# ---------------------------------------------------------------------------
_POSITIVE_WORDS: frozenset = frozenset({
    "grew", "growth", "improve", "improved", "improvement", "higher", "strong",
    "strength", "profit", "profitability", "margin", "cash", "exceed",
    "outperform", "record", "milestone", "accelerat", "expand", "robust",
    "efficient", "positive", "gain", "advance", "breakthrough", "increase",
    "solid", "momentum", "surpassed", "exceptional",
})

_NEGATIVE_WORDS: frozenset = frozenset({
    "risk", "breach", "penalties", "volatility", "churn", "decline",
    "delay", "uncertain", "cautious", "litigation", "lawsuit", "penalty",
    "deteriorat", "loss", "impairment", "headwind", "decrease", "adverse",
    "threat", "concern", "pressure", "challenging", "difficult", "regulatory",
    "compliance", "violation", "shortfall", "weakness",
})

_UNCERTAINTY_WORDS: frozenset = frozenset({
    "may", "could", "might", "uncertain", "expects", "cautious",
    "should", "if", "potentially", "possible", "subject",
})

# Numeric extraction patterns
_REVENUE_GROWTH_RE = re.compile(
    r"[Rr]evenue\s+grew\s+(\d+(?:\.\d+)?)\s*%",
    re.IGNORECASE,
)
_MARGIN_RE = re.compile(
    r"gross\s+margin\s+(\d+(?:\.\d+)?)\s*%",
    re.IGNORECASE,
)
_CASH_RE = re.compile(
    r"[Cc]ash[:\s]+\$(\d+(?:\.\d+)?)M",
    re.IGNORECASE,
)

# Risk keyword set for snippet extraction
_RISK_KEYWORDS: frozenset = frozenset({
    "risk", "breach", "regulatory", "volatility", "churn",
    "penalties", "litigation", "adversely", "uncertainty",
    "impairment", "compliance", "violation",
})


def score_sentiment(text: str) -> Tuple[int, int, int]:
    """Count positive, negative, and uncertainty word matches in *text*.

    Tokenises the text into lowercase words and tallies matches against the
    built-in lexicons.  Each word contributes at most 1 to each category per
    occurrence.

    Parameters
    ----------
    text :
        Raw filing text to analyse.

    Returns
    -------
    tuple of int
        ``(positive_count, negative_count, uncertainty_count)``
    """
    tokens = re.findall(r"\w+", text.lower())
    pos = sum(1 for t in tokens if t in _POSITIVE_WORDS)
    neg = sum(1 for t in tokens if t in _NEGATIVE_WORDS)
    unc = sum(1 for t in tokens if t in _UNCERTAINTY_WORDS)
    return pos, neg, unc


def extract_financial_metrics(text: str) -> dict:
    """Parse key financial metrics embedded in the filing text.

    Uses regex patterns to extract the first occurrence of each metric.
    Returns ``None`` for any metric that cannot be found.

    Parameters
    ----------
    text :
        Combined text of the filing (or the Results + Liquidity sections).

    Returns
    -------
    dict
        Keys:

        * ``revenue_growth_pct`` — float or ``None``
        * ``gross_margin_pct``   — float or ``None``
        * ``cash_m``             — float cash in millions, or ``None``
    """
    rev_match = _REVENUE_GROWTH_RE.search(text)
    margin_match = _MARGIN_RE.search(text)
    cash_match = _CASH_RE.search(text)

    return {
        "revenue_growth_pct": float(rev_match.group(1)) if rev_match else None,
        "gross_margin_pct": float(margin_match.group(1)) if margin_match else None,
        "cash_m": float(cash_match.group(1)) if cash_match else None,
    }


def _numeric_adjustments(metrics: Optional[dict]) -> tuple:  # pylint: disable=too-many-branches
    """Translate financial metrics into positive/negative score deltas.

    Parameters
    ----------
    metrics :
        Dict from :func:`extract_financial_metrics`, or ``None``.

    Returns
    -------
    tuple of int
        ``(num_pos_delta, num_neg_delta)``
    """
    if not metrics:
        return 0, 0

    num_pos = 0
    num_neg = 0

    growth: Optional[float] = metrics.get("revenue_growth_pct")
    if growth is not None:
        if growth >= 20:
            num_pos += 3
        elif growth >= 12:
            num_pos += 1
        elif growth < 7:
            num_neg += 1

    margin: Optional[float] = metrics.get("gross_margin_pct")
    if margin is not None:
        if margin >= 82:
            num_pos += 2
        elif margin >= 72:
            num_pos += 1
        elif margin < 60:
            num_neg += 3
        elif margin < 70:
            num_neg += 1

    cash: Optional[float] = metrics.get("cash_m")
    if cash is not None:
        if cash >= 700:
            num_pos += 1
        elif cash < 300:
            num_neg += 2

    return num_pos, num_neg


def label_from_scores(
    pos: int,
    neg: int,
    unc: int,
    metrics: Optional[dict] = None,
) -> str:
    """Determine the overall tone label from lexicon scores and financial metrics.

    Financial metrics act as anchors that override lexicon counts when
    fundamentals are unambiguously strong or weak.  Without metrics the
    function falls back to pure lexicon voting.

    Parameters
    ----------
    pos :
        Positive word count from :func:`score_sentiment`.
    neg :
        Negative word count from :func:`score_sentiment`.
    unc :
        Uncertainty word count from :func:`score_sentiment`.
    metrics :
        Optional dict from :func:`extract_financial_metrics`.  Expected keys:
        ``revenue_growth_pct``, ``gross_margin_pct``, ``cash_m``.  Pass
        ``None`` to use lexicon counts only.

    Returns
    -------
    str
        One of ``"positive"``, ``"neutral"``, or ``"cautious"``.
    """
    num_pos, num_neg = _numeric_adjustments(metrics)
    total_pos = pos + num_pos
    total_neg = neg + num_neg

    if total_neg > total_pos and total_neg >= unc:
        return "cautious"
    if total_pos > total_neg and total_pos >= unc:
        return "positive"
    return "neutral"


def extract_risk_snippets(chunks: List[dict], k: int = 3) -> List[dict]:
    """Return the *k* chunks with the highest risk-keyword density.

    Each chunk is scored by summing the occurrence count of every word in the
    risk keyword set.  Chunks with zero risk words are excluded.

    Parameters
    ----------
    chunks :
        List of document chunk dicts (``{"page_content": str, ...}``).
    k :
        Number of top-scoring chunks to return.  Must be ≥ 1.

    Returns
    -------
    list of dict
        Up to *k* chunks ordered by descending risk score.

    Raises
    ------
    ValueError
        When *k* is less than 1.
    """
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")

    scored: List[Tuple[int, dict]] = []
    for chunk in chunks:
        text = chunk.get("page_content", "").lower()
        weight = sum(text.count(word) for word in _RISK_KEYWORDS)
        if weight > 0:
            scored.append((weight, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [chunk for _, chunk in scored[:k]]
