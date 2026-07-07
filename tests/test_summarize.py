"""Tests for app.summarize — end-to-end summarisation pipeline."""

from __future__ import annotations

import pytest

from app.summarize import summarize_filing


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_summarize_returns_required_keys() -> None:
    """Output dict contains filing_id, highlights, risks, tone, source."""
    result = summarize_filing("HLSR-2024")
    assert "filing_id" in result
    assert "highlights" in result
    assert "risks" in result
    assert "tone" in result
    assert "source" in result


def test_summarize_highlights_count() -> None:
    """Exactly 2 highlight bullets are returned."""
    result = summarize_filing("HLSR-2024")
    assert len(result["highlights"]) == 2


def test_summarize_risks_count() -> None:
    """1-3 risk bullets are returned."""
    result = summarize_filing("ACMR-2023")
    assert 1 <= len(result["risks"]) <= 3


def test_summarize_tone_valid() -> None:
    """Tone is one of the three valid labels."""
    result = summarize_filing("ZYNT-2024")
    assert result["tone"] in {"positive", "neutral", "cautious"}


def test_summarize_risk_section_citations() -> None:
    """Risk bullets contain section citations in parentheses."""
    result = summarize_filing("HLSR-2022")
    for bullet in result["risks"]:
        assert "(" in bullet and ")" in bullet, f"Missing citation in risk: {bullet}"


def test_summarize_case_insensitive() -> None:
    """Filing ID lookup is case-insensitive."""
    result = summarize_filing("hlsr-2024")
    assert result["filing_id"] == "HLSR-2024"


def test_summarize_unknown_filing() -> None:
    """FileNotFoundError for non-existent filing ID."""
    with pytest.raises(FileNotFoundError):
        summarize_filing("UNKNOWN-9999")


def test_summarize_all_corpus_filings() -> None:
    """Smoke test: every corpus filing produces a valid summary."""
    filing_ids = [
        "HLSR-2022", "HLSR-2023", "HLSR-2024",
        "ACMR-2022", "ACMR-2023", "ACMR-2024",
        "ZYNT-2022", "ZYNT-2023", "ZYNT-2024",
        "NEOV-2022", "NEOV-2023", "NEOV-2024",
        "LUMO-2022", "LUMO-2023", "LUMO-2024",
    ]
    for fid in filing_ids:
        result = summarize_filing(fid)
        assert result["filing_id"] == fid
        assert len(result["highlights"]) == 2
        assert 1 <= len(result["risks"]) <= 3
        assert result["tone"] in {"positive", "neutral", "cautious"}
