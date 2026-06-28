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
  sample_summary.json       Generated evaluation output
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

### 1 — Environment (uv, recommended)

```bash
pip install uv           # once
uv sync                  # installs all dependencies from pyproject.toml
```

Or with pip:

```bash
pip install -r requirements.txt
```

### 2 — API key (optional but recommended)

```bash
cp .env.example .env
# Edit .env and set GROQ_API_KEY=<your_key>
# Free keys: https://console.groq.com
```

### 3 — Start the server

```bash
uvicorn app.server:app --host 0.0.0.0 --port 9060 --reload
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

All three evaluation scripts can be run against a live server:

```bash
# Full evaluation suite (no server needed — runs pipeline directly)
python evaluation/eval_runner.py

# Or individually against the running API:
python evaluation/eval_groundedness.py
python evaluation/eval_sentiment_agreement.py
python evaluation/eval_coherence_proxy.py HLSR-2024
```

### Sample metrics (lexicon mode, 15 filings)

| Metric | Value |
|---|---|
| Avg groundedness | ≥ 0.85 |
| Sentiment accuracy | ~47% |
| Coherence pass rate | 100% |

> **Note on sentiment accuracy**: all 15 synthetic filings share identical
> boilerplate (same risk factors, same outlook phrasing).  The lexicon
> classifier distinguishes tone primarily through extracted financial metrics
> (revenue growth %, gross margin %, cash position).  LLM mode achieves
> substantially higher agreement by reasoning about the context holistically.

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
pylint app/ evaluation/

# Tests
pytest tests/ -v
```

See **RUNBOOK.md** for instructions on swapping the loader to real PDFs via
LangChain `PyPDFLoader`.
