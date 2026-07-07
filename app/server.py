"""FastAPI application for the Financial Research Analyst Agent.

Exposes:
  GET  /health    — liveness probe.
  GET  /filings   — list available filing IDs in the corpus.
  POST /summarize — generate a highlights/risks/tone report for one filing.

Start the server:
    uvicorn app.server:app --host 0.0.0.0 --port 9060 --reload
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator

from .summarize import summarize_filing

__all__ = ["app"]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
_logger = logging.getLogger(__name__)

_CORPUS_DIR = Path(__file__).parent.parent / "corpus" / "filings"

app = FastAPI(
    title="Financial Research Analyst Agent",
    version="0.2.0",
    description=(
        "Generates concise analyst-style summaries (Highlights, Risks, Tone) "
        "from synthetic annual filings using a lexicon + FAISS pipeline with "
        "optional Groq LLM enhancement.  Set GROQ_API_KEY to enable the LLM path."
    ),
)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class SummariseRequest(BaseModel):
    """Request body for POST /summarize."""

    filing_id: str

    @field_validator("filing_id")
    @classmethod
    def validate_filing_id(cls, value: str) -> str:
        """Strip whitespace and upper-case the filing identifier.

        Parameters
        ----------
        value :
            Raw filing_id string from the request body.

        Returns
        -------
        str
            Cleaned, upper-cased filing identifier.

        Raises
        ------
        ValueError
            When *value* is empty after stripping.
        """
        clean = value.strip().upper()
        if not clean:
            raise ValueError("filing_id must not be empty")
        return clean


class SummariseResponse(BaseModel):
    """Structured summary response returned by POST /summarize."""

    filing_id: str
    highlights: List[str]
    risks: List[str]
    tone: str
    source: str = "lexicon"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health", tags=["ops"])
def health_check() -> Dict[str, str]:
    """Liveness probe — always returns 200 OK when the server is up.

    Returns
    -------
    dict
        ``{"status": "ok"}``
    """
    return {"status": "ok"}


@app.get("/filings", tags=["corpus"])
def list_filings() -> Dict[str, Any]:
    """List all filing IDs available in the local corpus.

    Returns
    -------
    dict
        ``{"filings": list[str], "count": int}`` — IDs sorted alphabetically,
        without the ``.md`` extension.
    """
    filing_ids = sorted(p.stem for p in _CORPUS_DIR.glob("*.md"))
    return {"filings": filing_ids, "count": len(filing_ids)}


@app.post("/summarize", response_model=SummariseResponse, tags=["agent"])
async def summarize(req: SummariseRequest) -> Dict[str, Any]:
    """Generate an analyst summary for a single filing.

    Attempts the Groq LLM pipeline first; falls back to the lexicon + FAISS
    approach when the API key is absent or the call fails.

    Parameters
    ----------
    req :
        Request body containing ``filing_id``.

    Returns
    -------
    dict
        ``{"filing_id", "highlights", "risks", "tone", "source"}``.

    Raises
    ------
    HTTPException
        **404** when the filing ID is not found in the corpus.
        **500** on unexpected internal errors.
    """
    _logger.info("Summarising filing_id=%s", req.filing_id)
    try:
        result = summarize_filing(req.filing_id)
        return result
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # pylint: disable=broad-except
        _logger.exception("Unexpected error for filing_id=%s", req.filing_id)
        raise HTTPException(status_code=500, detail="Internal server error") from exc
