"""End-to-end evaluation runner — generates all summaries and saves metrics.

Imports :func:`~app.summarize.summarize_filing` directly (no HTTP server
required) and runs all three proxy metrics across all 15 synthetic filings,
then writes the consolidated output to ``evaluation/sample_summary.json``.

Usage
-----
Run from the project root:

    python evaluation/eval_runner.py

The runner prints a progress line for each filing and a summary table at the
end.  The JSON file is always overwritten with the latest results.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from app.summarize import summarize_filing  # noqa: E402  pylint: disable=wrong-import-position

__all__ = ["run_all_evaluations"]

_CORPUS_DIR: Path = _PROJECT_ROOT / "corpus" / "filings"
_GOLD_PATH: Path = _PROJECT_ROOT / "evaluation" / "gold_labels.json"
_OUTPUT_PATH: Path = _PROJECT_ROOT / "evaluation" / "sample_summary.json"
_VALID_TONES: frozenset = frozenset({"positive", "neutral", "cautious"})
_MIN_BULLET_WORDS: int = 3


# ---------------------------------------------------------------------------
# Inline metric functions (no API server required)
# ---------------------------------------------------------------------------


def _tokenize(text: str) -> list:
    """Return lowercase word tokens from *text*."""
    return re.findall(r"\w+", text.lower())


def _groundedness(summary: dict, source_text: str) -> float:
    """Token-recall of the summary against the source.

    Parameters
    ----------
    summary :
        Summary dict from :func:`~app.summarize.summarize_filing`.
    source_text :
        Full text of the source filing.

    Returns
    -------
    float
        Score in [0, 1].
    """
    text = " ".join(summary.get("highlights", []) + summary.get("risks", []))
    tokens = _tokenize(text)
    if not tokens:
        return 0.0
    source_vocab = set(_tokenize(source_text))
    return sum(1 for t in tokens if t in source_vocab) / len(tokens)


def _coherence(summary: dict) -> bool:
    """Return True when the summary satisfies all structural constraints.

    Parameters
    ----------
    summary :
        Summary dict from :func:`~app.summarize.summarize_filing`.

    Returns
    -------
    bool
        True when all structural checks pass.
    """
    highlights: List[str] = summary.get("highlights", [])
    risks: List[str] = summary.get("risks", [])
    tone: str = summary.get("tone", "")

    bullets = highlights + risks
    bullets_ok = all(
        isinstance(b, str) and len(b.split()) >= _MIN_BULLET_WORDS
        for b in bullets
    )
    return (
        len(highlights) == 2
        and 1 <= len(risks) <= 3
        and tone in _VALID_TONES
        and bullets_ok
    )


def _extract_metrics_for_analysis(source_text: str) -> dict:
    """Extract financial metrics from source text for error-case diagnosis.

    Parameters
    ----------
    source_text :
        Full text of the filing.

    Returns
    -------
    dict
        Revenue growth %, gross margin %, cash $M (any may be None).
    """
    import re as _re

    rev = _re.search(r"[Rr]evenue\s+grew\s+(\d+(?:\.\d+)?)\s*%", source_text)
    margin = _re.search(r"gross\s+margin\s+(\d+(?:\.\d+)?)\s*%", source_text, _re.IGNORECASE)
    cash = _re.search(r"[Cc]ash[:\s]+\$(\d+(?:\.\d+)?)M", source_text, _re.IGNORECASE)
    risk_bullets = len(_re.findall(r"^- ", source_text, _re.MULTILINE))

    return {
        "revenue_growth_pct": float(rev.group(1)) if rev else None,
        "gross_margin_pct": float(margin.group(1)) if margin else None,
        "cash_m": float(cash.group(1)) if cash else None,
        "risk_bullet_count": risk_bullets,
    }


def _diagnose_mismatch(
    filing_id: str,
    predicted: str,
    gold: str,
    metrics: dict,
) -> str:
    """Generate a short explanatory note for a sentiment mismatch.

    Parameters
    ----------
    filing_id :
        Filing identifier.
    predicted :
        Tone predicted by the agent.
    gold :
        Gold-label tone.
    metrics :
        Financial metrics extracted from the source filing.

    Returns
    -------
    str
        Human-readable explanation of the likely cause.
    """
    growth = metrics.get("revenue_growth_pct")
    margin = metrics.get("gross_margin_pct")
    cash = metrics.get("cash_m")
    risks = metrics.get("risk_bullet_count", 0)

    notes: list = []

    if predicted == "cautious" and gold in ("positive", "neutral"):
        if growth is not None and growth < 12:
            notes.append(
                f"Low revenue growth ({growth}%) triggers negative metric "
                f"adjustment, overriding other positive signals"
            )
        if margin is not None and margin < 65:
            notes.append(
                f"Gross margin ({margin}%) below 65% threshold adds "
                f"strong negative weight"
            )
        if not notes:
            notes.append(
                "Lexicon negative/uncertainty word counts exceed positive "
                "counts across shared boilerplate sections"
            )

    elif predicted == "positive" and gold in ("cautious", "neutral"):
        if growth is not None and growth >= 20:
            notes.append(
                f"High revenue growth ({growth}%) triggers strong positive "
                f"metric adjustment"
            )
        if margin is not None and margin >= 82:
            notes.append(
                f"High gross margin ({margin}%) adds positive weight"
            )
        if risks >= 3:
            notes.append(
                f"Gold label likely counts {risks} risk bullets as "
                f"material, but lexicon scorer does not count discrete items"
            )

    elif predicted == "neutral" and gold == "cautious":
        notes.append(
            "Balanced lexicon scores produce neutral; gold label weighs "
            "risk-factor count or outlook language more heavily"
        )

    if not notes:
        notes.append(
            "Mismatch likely due to subjective tone boundary between "
            f"'{predicted}' and '{gold}'"
        )

    return "; ".join(notes) + "."


def run_all_evaluations() -> dict:  # pylint: disable=too-many-locals
    """Run the complete evaluation suite across all corpus filings.

    For each filing:
    1. Calls :func:`~app.summarize.summarize_filing` directly.
    2. Computes groundedness, coherence, and sentiment-agreement scores.

    Saves full results to ``evaluation/sample_summary.json`` and returns the
    same dict.

    Returns
    -------
    dict
        Contains ``summaries``, ``groundedness``, ``coherence``,
        ``sentiment_agreement``, and ``aggregate_metrics`` sections.
    """
    gold_labels: Dict[str, dict] = json.loads(
        _GOLD_PATH.read_text(encoding="utf-8")
    )
    filing_ids: List[str] = sorted(p.stem for p in _CORPUS_DIR.glob("*.md"))

    summaries: Dict[str, dict] = {}
    groundedness_scores: Dict[str, Optional[float]] = {}
    coherence_results: Dict[str, Optional[bool]] = {}
    sentiment_results: Dict[str, dict] = {}

    for fid in filing_ids:
        print(f"  Processing {fid} ...", end=" ", flush=True)
        try:
            summary = summarize_filing(fid)
            summaries[fid] = summary

            source_path = _CORPUS_DIR / f"{fid}.md"
            source_text = source_path.read_text(encoding="utf-8")

            g_score = _groundedness(summary, source_text)
            groundedness_scores[fid] = round(g_score, 4)

            c_passed = _coherence(summary)
            coherence_results[fid] = c_passed

            predicted = summary.get("tone", "neutral")
            gold_tone = gold_labels.get(fid, {}).get("tone", "neutral")
            sentiment_results[fid] = {
                "predicted": predicted,
                "gold": gold_tone,
                "match": predicted == gold_tone,
            }

            symbol = "✓" if c_passed else "✗"
            agree = "=" if predicted == gold_tone else "≠"
            print(
                f"tone={predicted} {agree} gold={gold_tone}  "
                f"grd={g_score:.2f}  coherence={symbol}"
            )

        except Exception as exc:  # pylint: disable=broad-except
            print(f"ERROR — {exc}")
            summaries[fid] = {"error": str(exc)}

    # -------------------------------------------------------------------
    # Aggregate metrics
    # -------------------------------------------------------------------
    g_values = [v for v in groundedness_scores.values() if v is not None]
    s_values = [v for v in sentiment_results.values() if "match" in v]
    c_values = [v for v in coherence_results.values() if v is not None]

    aggregate: Dict[str, object] = {
        "avg_groundedness": round(sum(g_values) / len(g_values), 4) if g_values else 0.0,
        "sentiment_accuracy": (
            round(sum(1 for r in s_values if r["match"]) / len(s_values), 4)
            if s_values
            else 0.0
        ),
        "coherence_pass_rate": (
            round(sum(1 for v in c_values if v) / len(c_values), 4)
            if c_values
            else 0.0
        ),
        "total_filings": len(filing_ids),
    }

    # -------------------------------------------------------------------
    # Error case analysis — log mismatches with explanatory notes
    # -------------------------------------------------------------------
    error_cases: List[dict] = []
    for fid, sr in sentiment_results.items():
        if not sr.get("match", True):
            summary = summaries.get(fid, {})
            source_path = _CORPUS_DIR / f"{fid}.md"
            source_text = source_path.read_text(encoding="utf-8") if source_path.exists() else ""
            metrics = _extract_metrics_for_analysis(source_text)
            note = _diagnose_mismatch(
                fid, sr["predicted"], sr["gold"], metrics
            )
            error_cases.append({
                "filing_id": fid,
                "predicted": sr["predicted"],
                "gold": sr["gold"],
                "metrics": metrics,
                "note": note,
            })

    if error_cases:
        print(f"\n--- Error Case Analysis ({len(error_cases)} mismatches) ---")
        for ec in error_cases:
            print(
                f"  {ec['filing_id']}: predicted={ec['predicted']}, "
                f"gold={ec['gold']}"
            )
            print(f"    metrics: {ec['metrics']}")
            print(f"    note: {ec['note']}")

    output = {
        "summaries": summaries,
        "groundedness": groundedness_scores,
        "coherence": coherence_results,
        "sentiment_agreement": sentiment_results,
        "error_cases": error_cases,
        "aggregate_metrics": aggregate,
    }

    _OUTPUT_PATH.write_text(json.dumps(output, indent=2), encoding="utf-8")

    print(f"\n{'='*60}")
    print(f"Results saved → {_OUTPUT_PATH.relative_to(_PROJECT_ROOT)}")
    print(f"  Avg groundedness    : {aggregate['avg_groundedness']:.2f}")
    print(
        f"  Sentiment accuracy  : "
        f"{aggregate['sentiment_accuracy']:.0%}  "
        f"({sum(1 for r in s_values if r['match'])}/{len(s_values)})"
    )
    print(
        f"  Coherence pass rate : "
        f"{aggregate['coherence_pass_rate']:.0%}  "
        f"({sum(1 for v in c_values if v)}/{len(c_values)})"
    )
    print("=" * 60)

    return output


if __name__ == "__main__":
    print("Running full evaluation suite...\n")
    run_all_evaluations()
