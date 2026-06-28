"""Sentiment agreement metric: predicted tone vs. gold-label tone.

Computes exact-match accuracy between the tone predicted by the agent and the
hand-curated gold labels in ``evaluation/gold_labels.json``.

Usage
-----
Run against all filings:

    python evaluation/eval_sentiment_agreement.py

Run against a single filing:

    python evaluation/eval_sentiment_agreement.py HLSR-2024
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Dict, List

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import requests  # noqa: E402  pylint: disable=wrong-import-position

__all__ = ["sentiment_agreement"]

_APP_BASE_URL: str = os.getenv("APP_BASE_URL", "http://localhost:9060")
_GOLD_PATH: Path = _PROJECT_ROOT / "evaluation" / "gold_labels.json"


def sentiment_agreement(filing_id: str, gold_labels: Dict[str, dict]) -> dict:
    """Check the predicted tone against the gold label for *filing_id*.

    Parameters
    ----------
    filing_id :
        Filing identifier, e.g. ``"HLSR-2024"``.
    gold_labels :
        Dict mapping filing IDs to ``{"tone": str}`` gold annotations.

    Returns
    -------
    dict
        ``{"filing_id": str, "predicted": str, "gold": str, "agreement": int}``
        where ``agreement`` is 1 (match) or 0 (mismatch).

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

    predicted: str = data.get("tone", "neutral")
    gold_tone: str = gold_labels.get(filing_id, {}).get("tone", "neutral")

    return {
        "filing_id": filing_id,
        "predicted": predicted,
        "gold": gold_tone,
        "agreement": int(predicted == gold_tone),
    }


def _confusion_summary(results: List[dict]) -> None:
    """Print a compact confusion table for the three tone classes.

    Parameters
    ----------
    results :
        List of dicts from :func:`sentiment_agreement`.
    """
    labels = ["positive", "neutral", "cautious"]
    # confusion[gold][pred]
    confusion: Dict[str, Dict[str, int]] = {
        g: {p: 0 for p in labels} for g in labels
    }
    for r in results:
        g = r.get("gold", "neutral")
        p = r.get("predicted", "neutral")
        if g in confusion and p in confusion[g]:
            confusion[g][p] += 1

    header = f"{'gold \\ pred':<12}" + "".join(f"{p:>12}" for p in labels)
    print("\n" + header)
    print("-" * len(header))
    for g in labels:
        row = f"{g:<12}" + "".join(f"{confusion[g][p]:>12}" for p in labels)
        print(row)


def main() -> None:
    """Run sentiment agreement for one or all filings."""
    gold_labels: Dict[str, dict] = json.loads(
        _GOLD_PATH.read_text(encoding="utf-8")
    )

    if len(sys.argv) > 1:
        filing_ids = [sys.argv[1].upper()]
    else:
        filing_ids = sorted(gold_labels.keys())

    results: List[dict] = []
    for fid in filing_ids:
        try:
            res = sentiment_agreement(fid, gold_labels)
            results.append(res)
            icon = "✓" if res["agreement"] else "✗"
            print(
                f"{icon} {fid}: predicted={res['predicted']:<10} "
                f"gold={res['gold']}"
            )
        except Exception as exc:  # pylint: disable=broad-except
            print(f"  {fid}: ERROR — {exc}")

    if results:
        total = sum(r["agreement"] for r in results)
        pct = 100.0 * total / len(results)
        print(f"\nAccuracy: {total}/{len(results)}  ({pct:.0f}%)")
        if len(results) > 1:
            _confusion_summary(results)


if __name__ == "__main__":
    main()
