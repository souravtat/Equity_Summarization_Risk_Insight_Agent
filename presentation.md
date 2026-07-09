---
marp: true
theme: default
paginate: true
backgroundColor: #ffffff
color: #1a1a2e
style: |
  section {
    font-family: 'Segoe UI', Arial, sans-serif;
  }
  section.title {
    background: linear-gradient(135deg, #0d1b3e 0%, #1a3a6b 100%);
    color: white;
    text-align: center;
    display: flex;
    flex-direction: column;
    justify-content: center;
  }
  section.title h1 {
    font-size: 2.2em;
    margin-bottom: 0.2em;
  }
  section.title h3, section.title p {
    color: #a8c8ff;
  }
  section.divider {
    background: #0d1b3e;
    color: white;
    display: flex;
    flex-direction: column;
    justify-content: center;
    text-align: center;
  }
  section.divider h1 {
    font-size: 2.5em;
  }
  section.end {
    background: linear-gradient(135deg, #0d1b3e 0%, #1a3a6b 100%);
    color: white;
    text-align: center;
    display: flex;
    flex-direction: column;
    justify-content: center;
  }
  section.end h1 {
    font-size: 3em;
  }
  h1 {
    color: #0d1b3e;
  }
  h2 {
    color: #0d1b3e;
    border-bottom: 2px solid #0d1b3e;
    padding-bottom: 0.2em;
  }
  table {
    font-size: 0.85em;
  }
  code {
    background: #f0f4f8;
    color: #0d1b3e;
  }
  pre {
    font-size: 0.7em;
  }
  strong {
    color: #0d1b3e;
  }
---

<!-- _class: title -->

# AI-Powered Equity Filings Summarization & Risk Insight Agent

### Capstone Project — Generative AI & Agentic AI Development

**Sourav Tat**

github.com/souravtat/Equity_Summarization_Risk_Insight_Agent

---

## Agenda

1. Problem Statement & Context
2. Architecture & Pipeline Design
3. Summarization Engine (Highlights, Risks, Tone)
4. Sentiment & Risk Agent
5. Evaluation Results & Error Analysis
6. Demo & Sample Output
7. Deliverables Checklist
8. Future Work & PDF Swap Path

---

## Problem Statement & Context

- Equity analysts spend **hours** reading 10-K/10-Q filings (50-200 pages)
- Manual extraction of highlights, risks, and tone is **slow and inconsistent**
- **Goal:** build a compact agent that produces grounded, analyst-style summaries in seconds

**Approach:**
- Runs on a **synthetic corpus** — 15 filings (5 companies x 3 years)
- Each filing has 5 sections: Business, Results, Risk Factors, Liquidity, Outlook
- **LangChain-compatible** loader interface — swap to real PDFs without changing the pipeline

---

## Architecture & Pipeline Design

```
filing.md
    |
    v
loader.py ──── section documents ────> chunker.py ──── chunks
                                                          |
                     ┌────────────────────────────────────┤
                     |                                    |
                     v                                    v
              llm_client.py                    retriever.py (FAISS)
              (Groq API)                       sentiment_risk.py
                     |                                    |
                     └──────────────┬─────────────────────┘
                                    v
                            summarize.py
                      {highlights, risks, tone}
                                    |
                                    v
                             server.py (FastAPI)
                          POST /summarize -> JSON
```

---

## Architecture — Dual Path Design

**LLM Path (preferred):**
- Sends filing text to Groq `llama-3.1-8b-instant`
- Structured JSON response with highlights, risks, tone
- Graceful fallback when API key is absent

**Lexicon + FAISS Fallback (offline):**
- **Highlights** — first sentences from Business/Results sections
- **Risks** — FAISS semantic search on bag-of-words vectors (cosine similarity via `IndexFlatIP`)
- **Tone** — lexicon word counts + financial metric anchors (revenue growth %, gross margin %, cash)

---

<!-- _class: divider -->

# Core Components Deep Dive

---

## Summarization Output Format

**Highlights** (exactly 2 bullets):
- Key business facts from Business/Results sections + section citation

**Risks** (2-3 bullets):
- Top risk snippets retrieved via FAISS semantic search
- De-duplicated across sections, each with section citation

**Tone** (1 word):

| Tone | Criteria |
|---|---|
| `positive` | Revenue growth >= 15% AND gross margin >= 75% |
| `cautious` | >= 3 material risks OR margin < 65% OR growth < 8% |
| `neutral` | Mixed signals / everything in between |

---

## Sample Output — HLSR-2024

```json
{
  "filing_id": "HLSR-2024",
  "highlights": [
    "HLSR provides enterprise software and services
     with subscriptions and support revenue streams. (Business)",
    "Revenue grew 12% with gross margin 77%
     driven by cloud migrations and AI analytics. (Results)"
  ],
  "risks": [
    "Cybersecurity incidents could result in penalties. (Risk Factors)",
    "Management expects cautious macro conditions
     and continued AI investments. (Outlook)",
    "Cash: $688M. (Liquidity)"
  ],
  "tone": "neutral",
  "source": "lexicon"
}
```

---

## Sentiment & Risk Scoring Engine

**Lexicon Scorer** (`sentiment_risk.py`):
- **29** positive words (grew, strong, profit, milestone...)
- **28** negative words (risk, breach, penalties, decline...)
- **11** uncertainty words (may, could, uncertain, potentially...)

**Financial Metric Anchors** (regex extraction):
- Revenue growth % → strong positive if >= 20%, negative if < 7%
- Gross margin % → positive if >= 82%, strong negative if < 60%
- Cash position → positive if >= $700M, negative if < $300M

**FAISS Retriever** (`retriever.py`):
- Bag-of-words vectors, L2-normalised
- `IndexFlatIP` (inner product = cosine on unit vectors)
- Ranks chunks by relevance to risk keywords

---

## Evaluation Results

### Aggregate Metrics (Lexicon Mode, 15 Filings)

| Metric | Result | What It Measures |
|---|---|---|
| Avg Groundedness | **1.00** | Token-recall of summary words in source |
| Sentiment Accuracy | **53%** (8/15) | Predicted tone vs. gold labels |
| Coherence Pass Rate | **100%** (15/15) | Structural validity |

- **Groundedness 1.00** — every summary word is traceable to source (no hallucination)
- **Coherence 100%** — all outputs have exactly 2 highlights, 1-3 risks, valid tone
- **Sentiment 53%** — 7 systematic mismatches (analyzed next slide)

---

## Error Analysis — Sentiment Mismatches

**Pattern 1 — Low-growth override (4 cases):**
- Revenue growth < 12% triggers negative adjustment, overriding strong margins
- E.g., NEOV-2022: growth 6%, margin 84% → predicted cautious, gold positive

**Pattern 2 — Risk-count blindness (3 cases):**
- All filings share 5 identical risk bullets; lexicon counts risk *words* not discrete items
- E.g., ACMR-2023: growth 20%, margin 84% → predicted positive, gold neutral

| Gold \ Predicted | positive | neutral | cautious |
|---|---|---|---|
| **positive** | 1 | 0 | 3 |
| **neutral** | 1 | 2 | 1 |
| **cautious** | 1 | 1 | 5 |

---

## Demo & API Endpoints

**REST API:**
```
GET  /health     → {"status": "ok"}
GET  /filings    → list of 15 filing IDs
POST /summarize  → analyst report (highlights, risks, tone)
```

**Run locally:**
```bash
uv sync
uv run uvicorn app.server:app --port 9060 --reload
curl -X POST http://localhost:9060/summarize \
     -H "Content-Type: application/json" \
     -d '{"filing_id": "HLSR-2024"}'
```

**Auto-generated API docs:** http://localhost:9060/docs

**Repo:** https://github.com/souravtat/Equity_Summarization_Risk_Insight_Agent

---

## Deliverables — All Complete

| # | Deliverable | Location |
|---|---|---|
| 1 | Working API (`POST /summarize`) | `app/server.py` |
| 2 | Notebook runner | `notebooks/agent.ipynb` |
| 3 | Sample outputs (JSON) | `evaluation/sample_summary.json` |
| 4 | Evaluation note (1-2 pages) | `evaluation/EVALUATION_NOTE.md` |
| 5 | README | `README.md` |
| 6 | RUNBOOK (PDF swap guide) | `RUNBOOK.md` |

**Bonus:** 46 unit tests, standalone debug runner, `GETTING_STARTED.md`

**Repo:** https://github.com/souravtat/Equity_Summarization_Risk_Insight_Agent

---

## Future Work & Production Path

**Short-term improvements:**
- Adjust growth/margin thresholds to fix 4 of 7 sentiment mismatches
- Add risk-bullet count as a classification feature
- Enable LLM mode (Groq) for ~80%+ sentiment accuracy

**Production path (documented in RUNBOOK.md):**
1. Swap to real PDFs — `uv add langchain langchain-community pypdf`
2. Create `app/pdf_loader.py` with `PyPDFLoader` adapter
3. Change one import in `summarize.py` — pipeline unchanged

**Longer-term:**
- Dense embeddings (sentence-transformers) replacing bag-of-words
- NLI-based groundedness (SummaC) for factual accuracy
- RAG integration for large corpora (persistent FAISS index)

---

<!-- _class: divider -->

# Questions?

---

<!-- _class: end -->

# Thank You!

**Sourav Tat**

https://github.com/souravtat/Equity_Summarization_Risk_Insight_Agent
