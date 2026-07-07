# Financial Research Analyst Agent

AI-powered equity filing summarisation and risk insight agent.  Loads annual
filings, chunks them into sections, and generates concise analyst-style reports
(**Highlights · Risks · Tone**) via a lexicon + FAISS pipeline with optional
Groq LLM enhancement.

---

## What's Inside

```
corpus/filings/   15 synthetic annual filings (5 companies × 2022–2024)
app/
  __init__.py     Public API: summarize_filing()
  loader.py       LangChain-compatible Markdown loader
  chunker.py      Fixed-size character chunker
  sentiment_risk.py  Lexicon scorer + numerical metrics extractor
  retriever.py    FAISS-backed bag-of-words semantic retriever
  llm_client.py   Groq LLM client (optional, with graceful fallback)
  summarize.py    Main pipeline orchestrator
  server.py       FastAPI REST API
evaluation/
  gold_labels.json          Hand-curated tone labels (15 filings)
  eval_groundedness.py      Token-recall proxy
  eval_sentiment_agreement.py  Tone accuracy vs. gold labels
  eval_coherence_proxy.py   Structural validation
  eval_runner.py            Full suite runner → sample_summary.json
  sample_summary.json       Generated evaluation output (with error_cases)
  EVALUATION_NOTE.md        1–2 page evaluation write-up & error analysis
tests/                      Unit tests (pytest) — loader, chunker, sentiment,
                            retriever, summarise, server
debug_runner.py             Standalone debug script exercising all modules
notebooks/agent.ipynb       Interactive exploration notebook
prompts/summary_prompt.txt  LLM system prompt
```

---

## Architecture

```
filing.md
    │
    ▼
loader.py ──── section documents ────▶ chunker.py ──── chunks
                                                           │
                     ┌─────────────────────────────────────┤
                     │                                     │
                     ▼                                     ▼
              llm_client.py                     retriever.py (FAISS)
              (Groq API)                        sentiment_risk.py
                     │                                     │
                     └──────────────┬──────────────────────┘
                                    ▼
                            summarize.py
                      {highlights, risks, tone, source}
                                    │
                                    ▼
                             server.py (FastAPI)
                          POST /summarize → JSON
```

**LLM path** (preferred): when `GROQ_API_KEY` is set the full filing text is
sent to `llama-3.1-8b-instant` and the structured JSON response is used
directly.

**Lexicon + FAISS fallback**: highlights are extracted from Business/Results
chunks; risk snippets are retrieved via FAISS inner-product search on BoW
vectors; tone is classified using lexicon counts anchored by numerical
fundamentals (revenue growth %, gross margin %, cash).

---

## Quick Start

### 1 — Install dependencies

```bash
uv sync
```

### 2 — API key (optional but recommended)

```bash
cp .env.example .env
# Edit .env and set GROQ_API_KEY=<your_key>
# Free keys: https://console.groq.com
export $(cat .env | grep -v '#' | xargs)
```

### 3 — Start the server

```bash
uv run uvicorn app.server:app --host 0.0.0.0 --port 9060 --reload
```

### 4 — Call the API

```bash
curl -s -X POST http://localhost:9060/summarize \
     -H "Content-Type: application/json" \
     -d '{"filing_id": "HLSR-2024"}' | python -m json.tool
```

Expected output (lexicon mode):

```json
{
  "filing_id": "HLSR-2024",
  "highlights": [
    "HLSR provides enterprise software and services with subscriptions and support revenue streams. (Business)",
    "Revenue grew 12% with gross margin 77% driven by cloud migrations and AI analytics. (Results)"
  ],
  "risks": [
    "Cybersecurity incidents could result in penalties. (Risk Factors)",
    "Management expects cautious macro conditions and continued AI investments. (Outlook)",
    "Cash: $688M. (Liquidity)"
  ],
  "tone": "cautious",
  "source": "lexicon"
}
```

### 5 — List all filings

```bash
curl http://localhost:9060/filings
```

---

## Evaluate

```bash
# Full evaluation suite (no server needed — runs pipeline directly)
uv run python evaluation/eval_runner.py

# Individually against the running API:
uv run python evaluation/eval_groundedness.py
uv run python evaluation/eval_sentiment_agreement.py
uv run python evaluation/eval_coherence_proxy.py HLSR-2024
```

### Sample metrics (lexicon mode, 15 filings)

| Metric | Value |
|---|---|
| Avg groundedness | 1.00 |
| Sentiment accuracy | ~53% |
| Coherence pass rate | 100% |

> **Note on sentiment accuracy**: all 15 synthetic filings share identical
> boilerplate (same risk factors, same outlook phrasing).  The lexicon
> classifier distinguishes tone primarily through extracted financial metrics
> (revenue growth %, gross margin %, cash position).  LLM mode achieves
> substantially higher agreement by reasoning about the context holistically.

For a detailed breakdown of error cases (root-cause analysis per mismatch,
confusion matrix, and limitations), see
[`evaluation/EVALUATION_NOTE.md`](evaluation/EVALUATION_NOTE.md).

---

## Debug Runner

Exercise every `app/` and `evaluation/` module in a single run (no server
needed):

```bash
uv run python debug_runner.py
```

Sections 1–9 cover all `app/` modules; sections 10–13 cover evaluation
(groundedness, sentiment agreement, coherence, full eval suite).  Set
breakpoints on any line marked `← breakpoint` for step-through debugging.

---

## Available Filing IDs

| Company | 2022 | 2023 | 2024 |
|---|---|---|---|
| HLSR | HLSR-2022 | HLSR-2023 | HLSR-2024 |
| ACMR | ACMR-2022 | ACMR-2023 | ACMR-2024 |
| ZYNT | ZYNT-2022 | ZYNT-2023 | ZYNT-2024 |
| NEOV | NEOV-2022 | NEOV-2023 | NEOV-2024 |
| LUMO | LUMO-2022 | LUMO-2023 | LUMO-2024 |

---

## Development

```bash
# Lint (target: 9+)
uv run pylint app/ evaluation/

# Tests
uv run pytest tests/ -v
```

See **RUNBOOK.md** for instructions on swapping the loader to real PDFs via
LangChain `PyPDFLoader`.
