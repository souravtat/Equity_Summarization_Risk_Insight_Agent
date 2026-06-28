# RUNBOOK — Financial Research Analyst Agent

Operational procedures for deploying, running, and extending the agent.

---

## 1  Environment Setup

### Using uv (recommended)

```bash
pip install uv          # install the uv package manager once
uv sync                 # create .venv and install all dependencies
source .venv/bin/activate  # activate (Linux/macOS)
# .venv\Scripts\activate   # Windows
```

### Using pip

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### API key

```bash
cp .env.example .env
# Set GROQ_API_KEY in .env for LLM-powered summaries.
# The server reads this at startup via os.getenv("GROQ_API_KEY").
```

---

## 2  Starting the Server

```bash
uvicorn app.server:app --host 0.0.0.0 --port 9060 --reload
```

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Liveness probe |
| `/filings` | GET | List corpus filing IDs |
| `/summarize` | POST | Generate analyst report |

---

## 3  Running Evaluations

### Full suite (no server required)

```bash
python evaluation/eval_runner.py
# Writes results to evaluation/sample_summary.json
```

### Per-metric (requires running server)

```bash
python evaluation/eval_groundedness.py           # all filings
python evaluation/eval_groundedness.py ACMR-2024 # single filing

python evaluation/eval_sentiment_agreement.py
python evaluation/eval_sentiment_agreement.py ZYNT-2023

python evaluation/eval_coherence_proxy.py
```

---

## 4  Swapping the Loader to Real PDFs (LangChain PyPDFLoader)

The current `app/loader.py` implements a Markdown-based loader whose output
interface exactly matches LangChain's `PyPDFLoader`:

```python
# Current (Markdown)
{"page_content": str, "metadata": {"title": str, "section": str}}

# LangChain PyPDFLoader (PDF)
{"page_content": str, "metadata": {"source": str, "page": int}}
```

### Step-by-step swap

1. **Install LangChain PDF dependencies:**

   ```bash
   uv add langchain langchain-community pypdf
   # or: pip install langchain langchain-community pypdf
   ```

2. **Create `app/pdf_loader.py`:**

   ```python
   """LangChain PyPDFLoader adapter — drop-in replacement for loader.py."""
   from langchain_community.document_loaders import PyPDFLoader

   def load_markdown_as_documents(path: str) -> list:
       """Load a PDF filing using LangChain PyPDFLoader.

       Returns the same list-of-dicts interface as the Markdown loader.
       Metadata keys differ: 'page' (int) instead of 'section' (str).
       """
       loader = PyPDFLoader(path)
       return [
           {"page_content": doc.page_content, "metadata": dict(doc.metadata)}
           for doc in loader.load()
       ]
   ```

3. **Update `app/summarize.py`** — change the import:

   ```python
   # Before
   from .loader import load_markdown_as_documents

   # After
   from .pdf_loader import load_markdown_as_documents
   ```

4. **Update `_CORPUS_DIR`** to point at your PDF directory:

   ```python
   _CORPUS_DIR = os.getenv("CORPUS_DIR", "corpus/pdfs")
   ```

5. **Update `_HIGHLIGHT_SECTIONS`** — since PDFs use page numbers instead of
   section names, consider removing the section filter or detecting sections
   with a heading regex.

6. **Test:**

   ```bash
   curl -X POST http://localhost:9060/summarize \
        -d '{"filing_id": "path/to/filing.pdf"}'
   ```

---

## 5  Swapping to a Retrieval Gateway (RAG)

For large PDF corpora (hundreds of filings) replace the full-document approach
with a retrieval-augmented generation (RAG) pattern:

1. Ingest all filing chunks into a **FAISS** (or **Chroma**) persistent index.
2. At query time retrieve the top-k chunks matching the query.
3. Pass only retrieved chunks to the LLM.

```python
# Pseudocode for RAG integration in summarize.py
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

vectorstore = FAISS.load_local("faiss_index", OpenAIEmbeddings())

def summarize_filing(filing_id: str) -> dict:
    query = f"filing {filing_id} highlights risks tone"
    docs = vectorstore.similarity_search(query, k=6)
    context = "\n\n".join(d.page_content for d in docs)
    return summarize_with_llm(context) or _lexicon_fallback(docs)
```

---

## 6  Adding New Filings to the Corpus

1. Place the new `<TICKER>-<YEAR>.md` file in `corpus/filings/`.
2. Add a gold-label entry in `evaluation/gold_labels.json`:
   ```json
   "NEWT-2025": { "tone": "positive" }
   ```
3. Re-run the evaluation runner: `python evaluation/eval_runner.py`.

---

## 7  Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `404` on `/summarize` | Wrong filing_id | Check `/filings` for valid IDs |
| `"source": "lexicon"` despite GROQ_API_KEY being set | Key not loaded | Restart server; check `.env` |
| `faiss-cpu` install fails on Apple Silicon | Architecture mismatch | `pip install faiss-cpu --no-binary faiss-cpu` or use conda: `conda install -c conda-forge faiss-cpu` |
| Sentiment accuracy < 50% | Synthetic filings share boilerplate | Expected in lexicon mode; use Groq LLM for higher accuracy |
| Pylint score < 9 | New code missing docstrings or type hints | Run `pylint app/ --output-format=text` and address each warning |
