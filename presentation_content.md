# Presentation Content — Slide by Slide

Use this to fill the BIA PowerPoint template (8 slide layouts).

---

## Slide 1 — Title Slide

**Title:** AI-Powered Equity Filings Summarization & Risk Insight Agent

**Subtitle:** Capstone Project — Generative AI & Agentic AI Development

**Name:** Sourav Tat

**Repository:** github.com/souravtat/Equity_Summarization_Risk_Insight_Agent

---

## Slide 2 — Agenda

- Problem Statement & Context
- Architecture & Pipeline Design
- Summarization Engine (Highlights, Risks, Tone)
- Sentiment & Risk Agent
- Evaluation Results & Error Analysis
- Demo & Sample Output
- Future Work & PDF Swap Path
- Questions

---

## Slide 3 — Problem Statement & Context

**Title:** Why This Project?

- Equity analysts spend hours reading 10-K/10-Q filings (50–200 pages each)
- Manual extraction of highlights, risks, and tone is slow and inconsistent
- Goal: build a compact agent that produces grounded, analyst-style summaries in seconds
- Runs on a synthetic corpus (15 filings, 5 companies x 3 years)
- LangChain-compatible loader interface — swap to real PDFs without changing the pipeline

---

## Slide 4 — Architecture (Split Layout)

**Left side content:**

**Pipeline Flow:**

1. Markdown filing loaded via LangChain-compatible loader
2. Sections split into fixed-size chunks (800 chars)
3. Dual-path summarization:
   - **LLM path** (Groq llama-3.1-8b) — preferred when API key is set
   - **Lexicon + FAISS fallback** — works offline, no API needed
4. Output: `{highlights, risks, tone, source}`
5. Served via FastAPI `POST /summarize`

**Right side (diagram text):**

```
filing.md → loader.py → chunker.py → chunks
                                        |
                    ┌───────────────────┤
                    |                   |
              llm_client.py    retriever.py (FAISS)
              (Groq API)       sentiment_risk.py
                    |                   |
                    └─────┬─────────────┘
                          v
                    summarize.py
              {highlights, risks, tone}
                          |
                    server.py (FastAPI)
                    POST /summarize
```

---

## Slide 5 — Section Divider

**Title:** Core Components Deep Dive

---

## Slide 6 — Summarization Output Format

**Title:** What the Agent Produces

**Content:**

**Highlights** (exactly 2 bullets):
- Key business facts extracted from Business/Results sections
- Each bullet grounded with verbatim source phrases + section citation

**Risks** (2-3 bullets):
- Top risk snippets retrieved via FAISS semantic search
- De-duplicated across sections for broad coverage
- Each bullet ends with section citation, e.g. (Risk Factors)

**Tone** (1 word):
- `positive` — strong growth (>=15%) AND high margin (>=75%)
- `cautious` — material risk factors OR low margin (<65%) OR low growth (<8%)
- `neutral` — mixed signals

**Sample output (HLSR-2024):**
```json
{
  "filing_id": "HLSR-2024",
  "highlights": [
    "HLSR provides enterprise software... (Business)",
    "Revenue grew 12% with gross margin 77%... (Results)"
  ],
  "risks": [
    "Cybersecurity incidents could result in penalties. (Risk Factors)",
    "Management expects cautious macro conditions... (Outlook)",
    "Cash: $688M. (Liquidity)"
  ],
  "tone": "neutral",
  "source": "lexicon"
}
```

---

## Slide 7 — Sentiment & Risk Agent (Bullet Layout)

**Title:** Sentiment & Risk Scoring Engine

- **Lexicon-based scorer** — curated word sets for positive (29 words), negative (28 words), and uncertainty (11 words)
- **Financial metric anchors** — regex extraction of revenue growth %, gross margin %, cash position from filing text
- **Combined classification** — lexicon counts + metric adjustments determine tone; metrics act as tiebreakers when boilerplate dominates
- **FAISS retriever** — bag-of-words vectors, L2-normalised, cosine similarity via IndexFlatIP; ranks chunks by relevance to risk query
- **Keyword fallback** — pure-Python overlap scoring when FAISS is unavailable

---

## Slide 8 — Evaluation Results (Title + Content)

**Title:** Evaluation Metrics (Lexicon Mode, 15 Filings)

| Metric               | Result          | What It Measures                          |
|----------------------|-----------------|-------------------------------------------|
| Avg Groundedness     | **1.00**        | Token-recall of summary words in source   |
| Sentiment Accuracy   | **53%** (8/15)  | Predicted tone vs. gold labels            |
| Coherence Pass Rate  | **100%** (15/15)| Structural validity (bullet counts, tone) |

**Key finding:** 100% groundedness confirms all summary content is traceable to source text — no hallucination in lexicon mode.

**Sentiment accuracy note:** 7 mismatches are systematic and well-understood (see next slide).

---

## Slide 9 — Error Analysis (Bullet Layout)

**Title:** Sentiment Mismatch Root Causes

**Pattern 1 — Low-growth override (4 cases):**
- Revenue growth <12% triggers negative adjustment, overriding strong margins (80%+)
- Examples: NEOV-2022 (growth 6%, margin 84%), ZYNT-2023 (growth 9%, margin 86%)
- Fix: adjust growth threshold from 7% to 5%, or add high-margin override

**Pattern 2 — Risk-factor count blindness (3 cases):**
- All filings have 5 identical risk bullets, but lexicon counts risk *words* not discrete items
- Gold labels weigh the number of enumerated risks more heavily
- Fix: count `- ` prefixed lines in Risk Factors section as a feature

**Confusion Matrix:**

| Gold \ Predicted | positive | neutral | cautious |
|------------------|----------|---------|----------|
| positive         | 1        | 0       | 3        |
| neutral          | 1        | 2       | 1        |
| cautious         | 1        | 1       | 5        |

---

## Slide 10 — Demo / Sample Output (Title + Content)

**Title:** Live Demo & API Endpoints

**API endpoints:**
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

**Run evaluation (no server needed):**
```bash
uv run python evaluation/eval_runner.py
```

**Repository:** https://github.com/souravtat/Equity_Summarization_Risk_Insight_Agent

---

## Slide 11 — Deliverables Checklist (Bullet Layout)

**Title:** Deliverables — All Complete

- **Working API** — FastAPI server with `POST /summarize` + Jupyter notebook runner (`notebooks/agent.ipynb`)
- **Sample outputs** — `evaluation/sample_summary.json` with all 15 summaries, metrics, and error case analysis
- **Evaluation note** — `evaluation/EVALUATION_NOTE.md` (1-2 pages: metrics, confusion matrix, root-cause notes, limitations)
- **README + RUNBOOK** — architecture diagram, quick start, step-by-step PDF swap guide (LangChain PyPDFLoader), RAG migration path
- **Bonus:** 46 unit tests (pytest), standalone debug runner, `GETTING_STARTED.md` for first-time users

**Repository:** https://github.com/souravtat/Equity_Summarization_Risk_Insight_Agent

---

## Slide 12 — Future Work (Split Layout)

**Title:** Future Work & Production Path

**Left side:**

- Swap to real 10-K PDFs via LangChain `PyPDFLoader` (3-step process documented in RUNBOOK.md)
- Replace bag-of-words with dense embeddings (e.g., sentence-transformers)
- Add NLI-based groundedness (SummaC / TRUE) for factual accuracy checking
- RAG integration for large corpora (FAISS persistent index + top-k retrieval)
- Add inter-annotator agreement (Cohen's kappa) for gold label quality

**Right side:**

**PDF Swap — 3 Steps:**
1. `uv add langchain langchain-community pypdf`
2. Create `app/pdf_loader.py` with `PyPDFLoader` adapter
3. Change one import in `summarize.py`

No pipeline changes needed.

---

## Slide 13 — Questions?

(Use template slide 7 — "Questions?" layout, no content changes needed)

---

## Slide 14 — Thank You!

(Use template slide 8 — "Thank You!" layout, no content changes needed)
