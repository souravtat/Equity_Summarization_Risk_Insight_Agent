# Getting Started — Zero to Running in 10 Minutes

> **Who is this for?** Anyone seeing this project for the first time with no prior context.
> **All commands below use `uv`.**

---

## What does this project do?

It reads annual company filings (like 10-K reports) and automatically produces a short analyst-style report:

```
Highlights : 2 key business/revenue facts
Risks      : 2-3 top risk factors (with source citation)
Tone       : positive / neutral / cautious
```

Think of it as an AI assistant that reads a 20-page filing and gives you a 5-line summary.

---

## What's in this folder?

```
corpus/filings/     ← 15 fake company reports (the "data")
app/                ← the Python code that reads and summarises them
evaluation/         ← scripts that measure how good the summaries are
  EVALUATION_NOTE.md  ← 1-2 page write-up of evaluation results & error analysis
  sample_summary.json ← generated evaluation output (all 15 filings)
tests/              ← unit tests (pytest)
notebooks/          ← interactive Jupyter walkthrough
prompts/            ← the instruction given to the AI model
pyproject.toml      ← project definition and dependencies (used by uv)
README.md           ← full technical reference
RUNBOOK.md          ← how to swap to real PDFs / deploy
```

---

## Step 0 — Prerequisites

You need:
- Python 3.10 or later → check with `python --version`
- `uv` installed → check with `uv --version`
- A terminal (Terminal on Mac, Command Prompt / PowerShell on Windows)
- (Optional) A free Groq API key for AI-powered summaries → https://console.groq.com

Install `uv` if not already installed:
```bash
pip install uv
```

---

## Step 1 — Open the project folder

```bash
cd path/to/Equity_Summarization_Risk_Insight_Agent
```

---

## Step 2 — Install all dependencies

```bash
uv sync
```

That's it. `uv` creates a `.venv` and installs everything from `pyproject.toml` automatically.
**No need to activate the virtual environment** — prefix all commands with `uv run`.

> **Apple Silicon Mac note:** if `faiss-cpu` fails, run:
> `uv run pip install faiss-cpu --no-binary faiss-cpu`

---

## Step 3 — (Optional) Enable AI summaries

By default the project uses a rule-based approach (no internet needed).
For better summaries, get a free Groq key at https://console.groq.com and set it up:

```bash
cp .env.example .env
```

Open `.env` in any text editor and replace `your_groq_api_key_here` with your actual key.

Load the key before running commands:
```bash
export $(cat .env | grep -v '#' | xargs)
```

---

## Step 4 — Look at the raw data

Open any filing to understand what the input looks like:

```bash
cat corpus/filings/HLSR-2024.md
```

You'll see sections: Business, Results, Risk Factors, Liquidity, Outlook.
This is the synthetic data the agent reads.

---

## Step 5 — Run the pipeline directly (no server needed)

```bash
uv run python -c "
from app.summarize import summarize_filing
import json
result = summarize_filing('HLSR-2024')
print(json.dumps(result, indent=2))
"
```

You should see something like:
```json
{
  "filing_id": "HLSR-2024",
  "highlights": [
    "HLSR provides enterprise software and services... (Business)",
    "Revenue grew 12% with gross margin 77%... (Results)"
  ],
  "risks": [
    "Cybersecurity incidents could result in penalties. (Risk Factors)",
    "..."
  ],
  "tone": "cautious",
  "source": "lexicon"
}
```

---

## Step 6 — Run the full evaluation

Tests all 15 filings and saves results to `evaluation/sample_summary.json`:

```bash
uv run python evaluation/eval_runner.py
```

You'll see a table like:
```
  Processing HLSR-2024 ... tone=cautious = gold=cautious  grd=1.00  coherence=✓
  ...
  Avg groundedness    : 1.00
  Sentiment accuracy  : 53%
  Coherence pass rate : 100%
```

| Metric | Meaning | Expected |
|---|---|---|
| Groundedness | Are summary words found in the source? | 1.00 |
| Sentiment accuracy | Does predicted tone match the gold label? | ~53% (rule-based) |
| Coherence | Exactly 2 highlights, 1-3 risks, valid tone? | 100% |

---

## Step 7 — Read the evaluation note

After running the evaluation, review the detailed write-up:

```bash
cat evaluation/EVALUATION_NOTE.md
```

This 1-2 page document covers:
- Aggregate metrics (groundedness, sentiment accuracy, coherence)
- Per-filing error analysis with root-cause notes for each mismatch
- Confusion matrix for tone classification
- Limitations and future work

The eval runner also logs error cases with diagnostic notes directly in
`evaluation/sample_summary.json` under the `error_cases` key.

---

## Step 8 — Run the unit tests

```bash
uv sync --extra dev
uv run pytest tests/ -v
```

You should see all tests pass (46 tests covering loader, chunker, sentiment
scorer, retriever, summarisation pipeline, and API endpoints).

---

## Step 9 — Start the REST API (optional)

```bash
uv run uvicorn app.server:app --host 0.0.0.0 --port 9060 --reload
```

Then in a **new terminal**:

```bash
# See all available filings
curl http://localhost:9060/filings

# Get a summary
curl -X POST http://localhost:9060/summarize \
     -H "Content-Type: application/json" \
     -d '{"filing_id": "ACMR-2023"}'
```

API docs auto-generated at: http://localhost:9060/docs

---

## Step 10 — Explore interactively (Jupyter notebook)

```bash
uv add jupyterlab
uv run jupyter lab notebooks/agent.ipynb
```

The notebook walks through all 5 project phases with explanations and live output.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'app'` | Run from the project root folder (where `pyproject.toml` is) |
| `uv sync` build error about package name | Already fixed in `pyproject.toml` — re-run `uv sync` |
| `faiss-cpu` install fails on Apple Silicon | `uv run pip install faiss-cpu --no-binary faiss-cpu` |
| `"source": "lexicon"` even with API key set | Re-run `export $(cat .env | grep -v '#' | xargs)` in the same terminal |
| Port 9060 already in use | `uv run uvicorn app.server:app --port 9061 --reload` |
| Want to try a different filing | Replace `HLSR-2024` with any ID from the list below |

---

## Available Filing IDs

```
HLSR-2022  HLSR-2023  HLSR-2024
ACMR-2022  ACMR-2023  ACMR-2024
ZYNT-2022  ZYNT-2023  ZYNT-2024
NEOV-2022  NEOV-2023  NEOV-2024
LUMO-2022  LUMO-2023  LUMO-2024
```

---

## Next steps after this works

- Read **README.md** for the full architecture diagram
- Read **RUNBOOK.md** to learn how to plug in real PDF filings
- Modify `prompts/summary_prompt.txt` to change what the AI produces
- Add your own filing to `corpus/filings/` and re-run the evaluation
