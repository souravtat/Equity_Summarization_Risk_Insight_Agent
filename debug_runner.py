"""
debug_runner.py — standalone debug script (no HTTP server needed).

Run via F5 using the "Debug Runner (no server)" launch config,
or directly:  python debug_runner.py

Every public function in every app/ and evaluation/ module is exercised here.
Set a breakpoint on any line marked  ← breakpoint  and step in.

Sections
--------
  1.  health_check          GET /health
  2.  list_filings          GET /filings
  3.  summarize (full)      POST /summarize  — end-to-end via summarize_filing()
  4.  loader                load_markdown_as_documents()
  5.  chunker               chunk_documents()
  6.  sentiment_risk        score_sentiment / extract_financial_metrics /
                            label_from_scores / extract_risk_snippets
  7.  retriever             FaissRetriever.query()
  8.  llm_client            summarize_with_llm()  (returns None without GROQ_API_KEY)
  9.  error path            FileNotFoundError for unknown filing_id
  10. eval_groundedness      groundedness token-recall proxy
  11. eval_sentiment_agreement  tone accuracy vs. gold labels
  12. eval_coherence_proxy   structural validation
  13. eval_runner            full evaluation suite → sample_summary.json
"""

import sys
import os

# Project root on sys.path so `app.*` imports resolve.
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

FILING_ID   = "HLSR-2024"   # ← change to any ID listed in section 2
CORPUS_PATH = os.path.join(PROJECT_ROOT, "corpus", "filings", f"{FILING_ID}.md")

print("=" * 60)

# ---------------------------------------------------------------------------
# 1.  health_check  ←  GET /health
# ---------------------------------------------------------------------------
from app.server import health_check

result = health_check()                                        # ← breakpoint
print("[1] health_check →", result)

# ---------------------------------------------------------------------------
# 2.  list_filings  ←  GET /filings
# ---------------------------------------------------------------------------
from app.server import list_filings

result = list_filings()                                        # ← breakpoint
print(f"[2] list_filings → {result['count']} filings:", result["filings"])

# ---------------------------------------------------------------------------
# 3.  summarize (full pipeline)  ←  POST /summarize
# ---------------------------------------------------------------------------
from app.summarize import summarize_filing

summary = summarize_filing(FILING_ID)                          # ← breakpoint
print(f"\n[3] summarize_filing({FILING_ID!r})")
print(f"    source     : {summary['source']}")
print(f"    tone       : {summary['tone']}")
print(f"    highlights : {summary['highlights']}")
print(f"    risks      : {summary['risks']}")

# ---------------------------------------------------------------------------
# 4.  loader  —  load_markdown_as_documents()
# ---------------------------------------------------------------------------
from app.loader import load_markdown_as_documents

docs = load_markdown_as_documents(CORPUS_PATH)                 # ← breakpoint
print(f"\n[4] loader → {len(docs)} sections")
for d in docs[:3]:
    print(f"    section={d['metadata']['section']!r}  "
          f"chars={len(d['page_content'])}")

# ---------------------------------------------------------------------------
# 5.  chunker  —  chunk_documents()
# ---------------------------------------------------------------------------
from app.chunker import chunk_documents

chunks = chunk_documents(docs, max_chars=800)                  # ← breakpoint
print(f"\n[5] chunker → {len(chunks)} chunks from {len(docs)} docs")
print(f"    chunk[0] section={chunks[0]['metadata']['section']!r}  "
      f"chars={len(chunks[0]['page_content'])}")

# ---------------------------------------------------------------------------
# 6.  sentiment_risk  —  all four public functions
# ---------------------------------------------------------------------------
from app.sentiment_risk import (
    score_sentiment,
    extract_financial_metrics,
    label_from_scores,
    extract_risk_snippets,
)

# 6a. score_sentiment — lexicon counts on a single chunk
pos, neg, unc = score_sentiment(chunks[0]["page_content"])     # ← breakpoint
print(f"\n[6a] score_sentiment(chunk[0]) → pos={pos}  neg={neg}  unc={unc}")

# 6b. extract_financial_metrics — regex-based metric extraction
full_text = "\n\n".join(
    f"## {d['metadata']['section']}\n{d['page_content']}" for d in docs
)
metrics = extract_financial_metrics(full_text)                 # ← breakpoint
print(f"[6b] extract_financial_metrics → {metrics}")

# 6c. label_from_scores — tone classification
total_pos = total_neg = total_unc = 0
for chunk in chunks:
    cp, cn, cu = score_sentiment(chunk["page_content"])
    total_pos += cp; total_neg += cn; total_unc += cu

tone = label_from_scores(total_pos, total_neg, total_unc, metrics)  # ← breakpoint
print(f"[6c] label_from_scores(pos={total_pos}, neg={total_neg}, "
      f"unc={total_unc}) → {tone!r}")

# 6d. extract_risk_snippets — keyword-score risk ranking (no FAISS)
risk_chunks = extract_risk_snippets(chunks, k=5)               # ← breakpoint
print(f"[6d] extract_risk_snippets → {len(risk_chunks)} risk chunks")
for rc in risk_chunks[:2]:
    print(f"     section={rc['metadata']['section']!r}  "
          f"preview={rc['page_content'][:60]!r}")

# ---------------------------------------------------------------------------
# 7.  retriever  —  FaissRetriever.query()
# ---------------------------------------------------------------------------
from app.retriever import FaissRetriever

RISK_QUERY = (
    "cybersecurity regulatory risk breach penalties volatility "
    "churn litigation adverse uncertainty compliance"
)

retriever = FaissRetriever(chunks)                             # ← breakpoint: __init__
top_chunks = retriever.query(RISK_QUERY, k=5)                  # ← breakpoint: query
print(f"\n[7] FaissRetriever.query → {len(top_chunks)} results")
for tc in top_chunks[:2]:
    print(f"    section={tc['metadata']['section']!r}  "
          f"preview={tc['page_content'][:60]!r}")

# ---------------------------------------------------------------------------
# 8.  llm_client  —  summarize_with_llm()
#     Returns None when GROQ_API_KEY is not set (expected in dev).
#     Set GROQ_API_KEY in .env to exercise the LLM path.
# ---------------------------------------------------------------------------
from app.llm_client import summarize_with_llm

llm_result = summarize_with_llm(full_text[:3000])              # ← breakpoint
if llm_result is None:
    print("\n[8] summarize_with_llm → None  "
          "(GROQ_API_KEY not set — lexicon fallback would be used)")
else:
    print(f"\n[8] summarize_with_llm → source=llm  tone={llm_result['tone']}")
    print(f"    highlights : {llm_result['highlights']}")
    print(f"    risks      : {llm_result['risks']}")

# ---------------------------------------------------------------------------
# 9.  error path  —  FileNotFoundError for unknown filing_id
# ---------------------------------------------------------------------------
print("\n[9] error path — unknown filing_id:")
try:
    summarize_filing("UNKNOWN-9999")                           # ← breakpoint
except FileNotFoundError as exc:
    print(f"    FileNotFoundError caught: {exc}")

# ---------------------------------------------------------------------------
# 10. eval_groundedness — token-recall proxy (inline, no server)
# ---------------------------------------------------------------------------
import re as _re
import json as _json

def _groundedness_inline(summary_dict, source_text):
    """Token-recall of summary against source (same logic as eval module)."""
    text = " ".join(summary_dict.get("highlights", []) + summary_dict.get("risks", []))
    tokens = _re.findall(r"\w+", text.lower())
    if not tokens:
        return 0.0
    source_vocab = set(_re.findall(r"\w+", source_text.lower()))
    return sum(1 for t in tokens if t in source_vocab) / len(tokens)

source_text = open(CORPUS_PATH, encoding="utf-8").read()
g_score = _groundedness_inline(summary, source_text)               # ← breakpoint
print(f"\n[10] groundedness({FILING_ID}) → {g_score:.4f}")

# ---------------------------------------------------------------------------
# 11. eval_sentiment_agreement — tone vs. gold label (inline, no server)
# ---------------------------------------------------------------------------
GOLD_PATH = os.path.join(PROJECT_ROOT, "evaluation", "gold_labels.json")
gold_labels = _json.loads(open(GOLD_PATH, encoding="utf-8").read())

predicted_tone = summary["tone"]
gold_tone = gold_labels.get(FILING_ID, {}).get("tone", "neutral")
agreement = predicted_tone == gold_tone                            # ← breakpoint
icon = "✓" if agreement else "✗"
print(f"[11] sentiment_agreement({FILING_ID}) → "
      f"predicted={predicted_tone}  gold={gold_tone}  {icon}")

# ---------------------------------------------------------------------------
# 12. eval_coherence_proxy — structural validation (inline, no server)
# ---------------------------------------------------------------------------
_VALID_TONES = {"positive", "neutral", "cautious"}

highlights = summary.get("highlights", [])
risks = summary.get("risks", [])
s_tone = summary.get("tone", "")

highlights_ok = len(highlights) == 2
risks_ok = 1 <= len(risks) <= 3
tone_ok = s_tone in _VALID_TONES
bullets_ok = all(
    isinstance(b, str) and len(b.split()) >= 3
    for b in highlights + risks
)
coherence_passed = highlights_ok and risks_ok and tone_ok and bullets_ok  # ← breakpoint

print(f"[12] coherence({FILING_ID}) → "
      f"highlights={highlights_ok}  risks={risks_ok}  "
      f"tone={tone_ok}  quality={bullets_ok}  "
      f"{'PASS' if coherence_passed else 'FAIL'}")

# ---------------------------------------------------------------------------
# 13. eval_runner — full evaluation suite → sample_summary.json
# ---------------------------------------------------------------------------
from evaluation.eval_runner import run_all_evaluations

print(f"\n[13] Running full evaluation suite across all filings...")
eval_output = run_all_evaluations()                                # ← breakpoint
agg = eval_output["aggregate_metrics"]
print(f"     avg_groundedness    = {agg['avg_groundedness']:.2f}")
print(f"     sentiment_accuracy  = {agg['sentiment_accuracy']:.0%}")
print(f"     coherence_pass_rate = {agg['coherence_pass_rate']:.0%}")
print(f"     error_cases         = {len(eval_output.get('error_cases', []))}")

print("\n" + "=" * 60)
print("debug_runner complete — all app/ and evaluation/ modules exercised.")
