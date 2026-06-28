"""Coherence proxy metric: structural validation of generated summaries.

Validates that each generated report satisfies the structural contract
required by the project specification:

  * Exactly 2 highlight bullets.
  * 1–3 risk bullets.
  * Tone is one of ``positive`` / ``neutral`` / ``cautious``.
  * No bullet is empty or whitespace-only.
  * Each highlight and risk bullet contains at least 3 words.

A report passes coherence when **all** checks succeed.

Usage
-----
    python evaluation/eval_coherence_proxy.py            # all filings
    python evaluation/eval_coherence_proxy.py HLSR-2024  # single filing
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict, List

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import requests  # noqa: E402  pylint: disable=wrong-import-position

__all__ = ["coherence_check"]

_APP_BASE_URL: str = os.getenv("APP_BASE_URL", "http://localhost:9060")
_CORPUS_DIR: Path = _PROJECT_ROOT / "corpus" / "filings"
_VALID_TONES: frozenset = frozenset({"positive", "neutral", "cautious"})
_MIN_BULLET_WORDS: int = 3


def _bullets_non_empty(bullets: List[str]) -> bool:
    """Return True only when every bullet has at least *_MIN_BULLET_WORDS* words.

    Parameters
    ----------
    bullets :
        List of bullet strings to validate.

    Returns
    -------
    bool
        ``True`` when all bullets are non-empty and sufficiently long.
    """
    return all(
        isinstance(b, str) and len(b.split()) >= _MIN_BULLET_WORDS
        for b in bullets
    )


def coherence_check(filing_id: str) -> Dict[str, object]:
    """Validate the structural integrity of a single generated summary.

    Parameters
    ----------
    filing_id :
        Filing identifier, e.g. ``"HLSR-2024"``.

    Returns
    -------
    dict
        Keys:

        * ``filing_id``          — normalised ID.
        * ``highlights_ok``      — bool, exactly 2 bullets.
        * ``risks_ok``           — bool, 1–3 bullets.
        * ``tone_ok``            — bool, valid tone string.
        * ``bullets_quality_ok`` — bool, no empty / very short bullets.
        * ``passed``             — bool, all checks passed.

    Raises
    ------
    requests.HTTPError
        When the API returns a non-2xx status code.
    """
    response = requests.post(
        f"{_APP_BASE_URL}/summarize",
        json={"filing_id": filing_id},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    highlights: List[str] = data.get("highlights", [])
    risks: List[str] = data.get("risks", [])
    tone: str = data.get("tone", "")

    highlights_ok = len(highlights) == 2
    risks_ok = 1 <= len(risks) <= 3
    tone_ok = tone in _VALID_TONES
    bullets_ok = _bullets_non_empty(highlights + risks)
    passed = highlights_ok and risks_ok and tone_ok and bullets_ok

    return {
        "filing_id": filing_id,
        "highlights_ok": highlights_ok,
        "risks_ok": risks_ok,
        "tone_ok": tone_ok,
        "bullets_quality_ok": bullets_ok,
        "passed": passed,
    }


def main() -> None:
    """Run coherence checks for one or all filings."""
    if len(sys.argv) > 1:
        filing_ids = [sys.argv[1].upper()]
    else:
        filing_ids = sorted(p.stem for p in _CORPUS_DIR.glob("*.md"))

    passed_count = 0
    for fid in filing_ids:
        try:
            result = coherence_check(fid)
            status = "PASS" if result["passed"] else "FAIL"
            icon = "✓" if result["passed"] else "✗"
            print(
                f"{icon} {fid}: {status}  "
                f"highlights={result['highlights_ok']}  "
                f"risks={result['risks_ok']}  "
                f"tone={result['tone_ok']}  "
                f"quality={result['bullets_quality_ok']}"
            )
            if result["passed"]:
                passed_count += 1
        except Exception as exc:  # pylint: disable=broad-except
            print(f"  {fid}: ERROR — {exc}")

    total = len(filing_ids)
    pct = 100.0 * passed_count / total if total else 0.0
    print(f"\nCoherence pass rate: {passed_count}/{total}  ({pct:.0f}%)")


if __name__ == "__main__":
    main()
