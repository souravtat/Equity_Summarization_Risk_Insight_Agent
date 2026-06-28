## Project Title: AI-Powered Equity Filings Summarization & Risk Insight Agent
## Description:
Build a compact agent that loads a filing, chunks it into sections, generates a concise analyst-style report (Highlights, Risks, Tone), and evaluates results with simple metrics (groundedness, sentiment agreement, coherence). Development uses a synthetic corpus and a LangChain-like loader so you can swap to real PDFs later without changing the pipeline.

## Background / Context

Equity analysts spend hours reading 10-K/10-Q PDFs. This project creates a safe, prototype that produces quick, grounded summaries from long filings, highlights top risks, and flags overall tone (positive/neutral/cautious). It runs entirely on a synthetic corpus and a mock, LangChain-like loader interface.

## Tasks

### Phase 1 — Setup & Exploration

Run the API and explore synthetic filings (Business, Results, Risk Factors, Liquidity, Outlook).

Inspect loader and chunker behavior; verify chunk sizes and metadata.

### Phase 2 — Summarization

Implement a concise report:

Highlights (2 bullets)

Risks (2–3 bullets, grounded with phrases from source + section citation)

Tone (positive/neutral/cautious — 1 word)

Keep outputs concise, factual, and section-cited.

### Phase 3 — Sentiment & Risk Agent

Build/extend a simple lexicon-based tone+uncertainty scorer.

Extract risk-heavy snippets from the corpus for the “Risks” section.

### Phase 4 — Evaluation

Groundedness proxy (substring coverage of summary in source).

Sentiment agreement vs. gold labels (tone).

Coherence proxy (bullet counts/length checks).

Log error cases and short notes on why they failed.

### Phase 5 — Polish & Handoff

Finalize API/notebook, README, and RUNBOOK (how to swap to real PDFs via LangChain PyPDFLoader).

Optional: 2-minute demo video showing before/after metrics and sample outputs.

### Deliverables

Working API (POST /summarize) or a notebook runner for local tests.

Sample outputs (JSON) saved to evaluation/sample_summary.json.

Short evaluation note (1–2 pages) with groundedness, sentiment agreement, and coherence results.

README + RUNBOOK (how to switch loaders to real PDFs or a retrieval gateway).

### Provided Resources
- app
- corpus
- evaluation
- notebooks
- prompts
- README.md
- requirements.txt
- RUNBOOK.md

