"""Groundedness proxy metric for generated filing summaries.

Groundedness is defined as the token-level recall of the generated summary
(highlights + risks) against the source filing text.  A score of 1.0 means
every token in the summary also appears in the source; 0.0 means no overlap.

This is a lightweight *proxy* metric — it rewards summaries that use language
grounded in the source document rather than hallucinating facts.

Usage
-----
Run against all filings (requires the API server to be running):

    python evaluation/eval_groundedness.py

Run against a single filing:

    python evaluation/eval_groundedness.py HLSR-2024
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import requests  # noqa: E402  pylint: disable=wrong-import-position

__all__ = ["groundedness_score"]

_APP_BASE_URL: str = os.getenv("APP_BASE_URL", "http://localhost:9060")
_CORPUS_DIR: Path = _PROJECT_ROOT / "corpus" / "filings"


def _tokenize(text: str) -> list:
    """Return lowercase word tokens from *text*.

    Parameters
    ----------
    text :
        Input string.

    Returns
    -------
    list of str
        Lowercase alphanumeric tokens.
    """
    return re.findall(r"\w+", text.lower())


def groundedness_score(filing_id: str) -> float:
    """Compute the groundedness proxy for a single filing.

    Calls the ``POST /summarize`` endpoint and measures what fraction of
    tokens in the generated summary (highlights + risks) appear in the source
    filing.

    Parameters
    ----------
    filing_id :
        Filing identifier, e.g. ``"HLSR-2024"``.

    Returns
    -------
    float
        Groundedness score in [0, 1].  Returns 0.0 for empty summaries.

    Raises
    ------
    requests.HTTPError
        When the API returns a non-2xx status code.
    FileNotFoundError
        When the source filing file does not exist locally.
    """
    response = requests.post(
        f"{_APP_BASE_URL}/summarize",
        json={"filing_id": filing_id},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    summary_text = " ".join(
        data.get("highlights", []) + data.get("risks", [])
    )

    source_path = _CORPUS_DIR / f"{filing_id.upper()}.md"
    if not source_path.exists():
        raise FileNotFoundError(f"Source not found: {source_path}")
    source_text = source_path.read_text(encoding="utf-8")

    source_vocab = set(_tokenize(source_text))
    summary_tokens = _tokenize(summary_text)
    if not summary_tokens:
        return 0.0

    hits = sum(1 for t in summary_tokens if t in source_vocab)
    return hits / len(summary_tokens)


def main() -> None:
    """Run groundedness evaluation for one or all filings."""
    if len(sys.argv) > 1:
        filing_ids = [sys.argv[1].upper()]
    else:
        filing_ids = sorted(p.stem for p in _CORPUS_DIR.glob("*.md"))

    scores: list = []
    for fid in filing_ids:
        try:
            score = groundedness_score(fid)
            scores.append(score)
            print(f"{fid}: groundedness = {score:.2f}")
        except Exception as exc:  # pylint: disable=broad-except
            print(f"{fid}: ERROR — {exc}")

    if scores:
        avg = sum(scores) / len(scores)
        print(f"\nAverage groundedness: {avg:.2f}  (n={len(scores)})")


if __name__ == "__main__":
    main()
