"""Tests for app.server — FastAPI endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.server import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_health() -> None:
    """GET /health returns 200 with status ok."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_list_filings() -> None:
    """GET /filings returns a list of filing IDs."""
    resp = client.get("/filings")
    assert resp.status_code == 200
    data = resp.json()
    assert "filings" in data
    assert "count" in data
    assert data["count"] == 15
    assert "HLSR-2024" in data["filings"]


def test_summarize_valid() -> None:
    """POST /summarize with a valid filing_id returns 200."""
    resp = client.post("/summarize", json={"filing_id": "HLSR-2024"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["filing_id"] == "HLSR-2024"
    assert len(data["highlights"]) == 2
    assert 1 <= len(data["risks"]) <= 3
    assert data["tone"] in {"positive", "neutral", "cautious"}


def test_summarize_not_found() -> None:
    """POST /summarize with unknown filing_id returns 404."""
    resp = client.post("/summarize", json={"filing_id": "FAKE-9999"})
    assert resp.status_code == 404


def test_summarize_empty_id() -> None:
    """POST /summarize with empty filing_id returns 422."""
    resp = client.post("/summarize", json={"filing_id": "  "})
    assert resp.status_code == 422


def test_summarize_missing_body() -> None:
    """POST /summarize with no body returns 422."""
    resp = client.post("/summarize")
    assert resp.status_code == 422
