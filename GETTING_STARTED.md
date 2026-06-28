# Getting Started — Zero to Running in 10 Minutes

> **Who is this for?** Anyone seeing this project for the first time with no prior context.

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
notebooks/          ← interactive Jupyter walkthrough
prompts/            ← the instruction given to the AI model
requirements.txt    ← Python packages needed
README.md           ← full technical reference
RUNBOOK.md          ← how to swap to real PDFs / deploy
```

---

## Step 0 — Prerequisites

You need:
- Python 3.10 or later → check with `python --version`
- A terminal (Terminal on Mac, Command Prompt / PowerShell on Windows)
- (Optional) A free Groq API key for AI-powered summaries → https://console.groq.com

---

## Step 1 — Open the project folder

```bash
cd path/to/Equity_Summarization_Risk_Insight_Agent
```

---

## Step 2 — Install Python packages

```bash
pip install -r requirements.txt
```

> If you see errors about `faiss-cpu` on Apple Silicon Mac, run:
> `pip install faiss-cpu --no-binary faiss-cpu`

---

## Step 3 — (Optional) Enable AI summaries

By default the project uses a rule-based approach (no internet needed).
For better summaries, get a free Groq key and set it up:

```bash
cp .env.example .env
```

Open `.env` in any text editor and replace `your_groq_api_key_here` with your actual key.

Then load it before running:
```bash
# Mac / Linux
export $(cat .env | grep -v '#' | xargs)

# Windows PowerShell
Get-Content .env | ForEach-Object { if ($_ -notmatch '^#') { $var = $_ -split '=', 2; [System.Environment]::SetEnvironmentVariable($var[0], $var[1]) } }
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
python -c "
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
    ...
  ],
  "tone": "cautious",
  "source": "lexicon"
}
```

---

## Step 6 — Run the full evaluation

This tests all 15 filings and saves results to `evaluation/sample_summary.json`:

```bash
python evaluation/eval_runner.py
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
| Groundedness | Are summary words found in the source? | ≥ 0.85 |
| Sentiment accuracy | Does predicted tone match the gold label? | ~53% (rule-based) |
| Coherence | Does output have exactly 2 highlights, 1-3 risks, valid tone? | 100% |

---

## Step 7 — Start the REST API (optional)

```bash
uvicorn app.server:app --host 0.0.0.0 --port 9060 --reload
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

API docs are auto-generated at: http://localhost:9060/docs

---

## Step 8 — Explore interactively (Jupyter notebook)

```bash
pip install jupyter
jupyter notebook notebooks/agent.ipynb
```

The notebook walks through all 5 project phases with explanations and live output.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'app'` | Run commands from the project root folder |
| `faiss-cpu` install fails | See Step 2 note above |
| `"source": "lexicon"` even with API key | Make sure you ran the `export` command in Step 3 |
| Port 9060 already in use | Change to another port: `--port 9061` |
| Want to try a different filing | Replace `HLSR-2024` with any ID from `corpus/filings/` |

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
