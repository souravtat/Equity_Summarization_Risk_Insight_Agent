"""Tests for app.sentiment_risk — lexicon scorer and risk extractor."""

from __future__ import annotations

import pytest

from app.sentiment_risk import (
    extract_financial_metrics,
    extract_risk_snippets,
    label_from_scores,
    score_sentiment,
)


# ---------------------------------------------------------------------------
# score_sentiment
# ---------------------------------------------------------------------------

def test_score_positive_words() -> None:
    """Positive words are counted correctly."""
    pos, neg, unc = score_sentiment("strong growth and improved profit")
    assert pos >= 3
    assert neg == 0


def test_score_negative_words() -> None:
    """Negative words are counted correctly."""
    pos, neg, unc = score_sentiment("risk of breach and penalties")
    assert neg >= 2


def test_score_uncertainty_words() -> None:
    """Uncertainty words are counted correctly."""
    pos, neg, unc = score_sentiment("may could potentially uncertain")
    assert unc >= 3


def test_score_empty_string() -> None:
    """Empty string returns all zeros."""
    assert score_sentiment("") == (0, 0, 0)


# ---------------------------------------------------------------------------
# extract_financial_metrics
# ---------------------------------------------------------------------------

def test_extract_revenue_growth() -> None:
    """Revenue growth percentage is extracted."""
    metrics = extract_financial_metrics("Revenue grew 21% year over year.")
    assert metrics["revenue_growth_pct"] == 21.0


def test_extract_gross_margin() -> None:
    """Gross margin percentage is extracted."""
    metrics = extract_financial_metrics("gross margin 82% driven by efficiency.")
    assert metrics["gross_margin_pct"] == 82.0


def test_extract_cash() -> None:
    """Cash position in millions is extracted."""
    metrics = extract_financial_metrics("Cash: $500M.")
    assert metrics["cash_m"] == 500.0


def test_extract_missing_metrics() -> None:
    """Missing metrics return None."""
    metrics = extract_financial_metrics("No numbers here.")
    assert metrics["revenue_growth_pct"] is None
    assert metrics["gross_margin_pct"] is None
    assert metrics["cash_m"] is None


# ---------------------------------------------------------------------------
# label_from_scores
# ---------------------------------------------------------------------------

def test_label_positive() -> None:
    """Strong positive signal yields 'positive'."""
    assert label_from_scores(20, 5, 3) == "positive"


def test_label_cautious() -> None:
    """Strong negative signal yields 'cautious'."""
    assert label_from_scores(5, 20, 3) == "cautious"


def test_label_neutral() -> None:
    """Balanced or uncertainty-dominated signal yields 'neutral'."""
    assert label_from_scores(10, 10, 15) == "neutral"


def test_label_with_metrics_positive_override() -> None:
    """High-growth + high-margin metrics can push tone to positive."""
    metrics = {"revenue_growth_pct": 25.0, "gross_margin_pct": 85.0, "cash_m": 800.0}
    result = label_from_scores(10, 10, 5, metrics)
    assert result == "positive"


def test_label_with_metrics_negative_override() -> None:
    """Low-margin metrics can push tone to cautious."""
    metrics = {"revenue_growth_pct": 5.0, "gross_margin_pct": 55.0, "cash_m": 200.0}
    result = label_from_scores(10, 10, 5, metrics)
    assert result == "cautious"


# ---------------------------------------------------------------------------
# extract_risk_snippets
# ---------------------------------------------------------------------------

def test_risk_snippets_returns_top_k() -> None:
    """Returns up to k chunks sorted by risk keyword density."""
    chunks = [
        {"page_content": "No risk words here at all.", "metadata": {"section": "A"}},
        {"page_content": "risk breach regulatory penalties compliance.", "metadata": {"section": "B"}},
        {"page_content": "risk volatility uncertainty.", "metadata": {"section": "C"}},
    ]
    result = extract_risk_snippets(chunks, k=2)
    assert len(result) == 2
    # Chunk B has more risk words, so it should be first
    assert result[0]["metadata"]["section"] == "B"


def test_risk_snippets_excludes_zero_risk() -> None:
    """Chunks with no risk keywords are excluded."""
    chunks = [
        {"page_content": "Everything is wonderful and profitable.", "metadata": {"section": "A"}},
    ]
    result = extract_risk_snippets(chunks, k=3)
    assert len(result) == 0


def test_risk_snippets_invalid_k() -> None:
    """ValueError when k < 1."""
    with pytest.raises(ValueError, match="k must be"):
        extract_risk_snippets([], k=0)
