"""Groq LLM client for analyst-style equity filing summarisation.

Wraps the Groq chat-completions API to produce a structured JSON report
(highlights, risks, tone) from a filing text excerpt.  The function returns
``None`` gracefully whenever the API key is absent, the ``groq`` package is
missing, or the API call fails — allowing callers to fall back to the
lexicon-based pipeline without any changes.

Environment variables
---------------------
GROQ_API_KEY
    Groq API key.  When unset the LLM path is silently skipped.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Optional

__all__ = ["summarize_with_llm"]

_logger = logging.getLogger(__name__)

_GROQ_MODEL = "llama-3.1-8b-instant"
_MAX_TOKENS = 512
_TEMPERATURE = 0.2

# Maximum characters of filing text sent to the LLM (avoids token overflow)
_MAX_FILING_CHARS = 3_000

_SYSTEM_PROMPT = """You are a concise equity research analyst. Given an annual \
filing excerpt, produce a JSON object with exactly these three keys:

  "highlights": list of exactly 2 short strings (key business / revenue facts)
  "risks":      list of 2–3 short strings (top risk factors with section citation)
  "tone":       one of "positive", "neutral", or "cautious"

Rules:
- Each bullet must be ≤ 20 words.
- Risk bullets must end with the section name in parentheses, e.g. (Risk Factors).
- Tone classification:
    positive  → strong revenue growth (≥ 15 %) AND gross margin ≥ 75 %
    cautious  → ≥ 3 material risk factors OR gross margin < 65 % OR growth < 8 %
    neutral   → everything in between
- Return ONLY the JSON object — no preamble, no explanation."""


def _extract_json_object(text: str) -> Optional[dict]:
    """Extract and parse the first JSON object found in *text*.

    Parameters
    ----------
    text :
        Raw string that may contain surrounding prose.

    Returns
    -------
    dict or None
        Parsed dict on success, ``None`` when no valid JSON object is found.
    """
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except json.JSONDecodeError as exc:
        _logger.debug("JSON parse failed: %s", exc)
        return None


def _validate_llm_output(parsed: dict) -> Optional[dict]:
    """Validate and normalise the parsed LLM JSON output.

    Parameters
    ----------
    parsed :
        Dict extracted from the LLM response.

    Returns
    -------
    dict or None
        Normalised ``{"highlights": list, "risks": list, "tone": str}`` or
        ``None`` when the structure is invalid.
    """
    highlights = parsed.get("highlights")
    risks = parsed.get("risks")
    tone = parsed.get("tone", "neutral")

    if not isinstance(highlights, list) or not isinstance(risks, list):
        _logger.warning("LLM output missing list fields; falling back.")
        return None

    if tone not in {"positive", "neutral", "cautious"}:
        _logger.warning("LLM returned unknown tone '%s'; defaulting to neutral.", tone)
        tone = "neutral"

    return {
        "highlights": [str(h) for h in highlights[:2]],
        "risks": [str(r) for r in risks[:3]],
        "tone": str(tone),
    }


def summarize_with_llm(filing_text: str) -> Optional[dict]:
    """Call the Groq API to generate a structured filing summary.

    Sends the first :data:`_MAX_FILING_CHARS` characters of *filing_text* to
    the Groq ``llama-3.1-8b-instant`` model and parses the JSON response into
    a highlights / risks / tone structure.

    Parameters
    ----------
    filing_text :
        Full or condensed text of the filing sections to summarise.

    Returns
    -------
    dict or None
        ``{"highlights": list[str], "risks": list[str], "tone": str}`` on
        success; ``None`` on any error or missing dependency/API key.
    """
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        _logger.debug("GROQ_API_KEY not set; skipping LLM summarisation.")
        return None

    try:
        from groq import Groq  # type: ignore[import-not-found]  # pylint: disable=import-outside-toplevel
    except ImportError:
        _logger.warning("groq package not installed; falling back to lexicon mode.")
        return None

    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model=_GROQ_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": filing_text[:_MAX_FILING_CHARS]},
            ],
            max_tokens=_MAX_TOKENS,
            temperature=_TEMPERATURE,
        )
        raw_content: str = response.choices[0].message.content or ""
        parsed = _extract_json_object(raw_content)
        if parsed is None:
            _logger.warning("LLM returned non-JSON response; falling back.")
            return None
        return _validate_llm_output(parsed)

    except Exception as exc:  # pylint: disable=broad-except
        _logger.error("LLM call failed: %s", exc)
        return None
