# 🌍 Climate Risk Preparedness Advisor

> **Production-grade Agentic Multimodal RAG system** for climate hazard preparedness,
> powered by LLaMA 3.1 (Groq), BGE-Large embeddings, ChromaDB, CLIP, and RAGAS evaluation.

---

## 📋 Table of Contents

- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Module Guide](#module-guide)
- [Running the App](#running-the-app)
- [Running Tests](#running-tests)
- [RAGAS Evaluation](#ragas-evaluation)
- [Adding New Documents](#adding-new-documents)
- [Environment Variables](#environment-variables)

---

## Architecture

```
User Query
    │
    ▼
┌─────────────────┐
│   Risk Agent    │  ← Detects hazard type (flood/cyclone/heatwave/…)
│  (rule + LLM)   │    and query intent (preparedness/information/emergency)
└────────┬────────┘
         │ RiskContext (hazard, intent, confidence)
         ▼
┌─────────────────┐
│   Retriever     │  ← ChromaDB vector similarity search
│ (BGE-Large +    │    with hazard metadata filtering
│   CLIP MMDAL)   │    top_k = 5 text chunks + 2 images
└────────┬────────┘
         │ Candidate documents
         ▼
┌─────────────────┐
│   Reranker      │  ← FlashRank cross-encoder reranking
│ (cross-encoder) │    Returns top_n = 3 most relevant chunks
└────────┬────────┘
         │ Reranked context
         ▼
┌─────────────────┐
│  RAG Pipeline   │  ← LCEL chain: prompt | LLM | parser
│  (LLaMA 3.1)    │    Structured (Before/During/After) or freeform output
└────────┬────────┘
         │ Answer + Sources
         ▼
┌─────────────────┐
│ RAGAS Evaluation│  ← Faithfulness, Relevancy, Precision, Recall
└─────────────────┘
```

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| **LLM** | Groq LLaMA 3.1 70B Versatile |
| **Text Embeddings** | HuggingFace `BAAI/bge-large-en-v1.5` (1024-dim) |
| **Image Embeddings** | OpenCLIP `ViT-B/32` (512-dim) |
| **Vector Database** | ChromaDB (persistent, on-disk) |
| **RAG Framework** | LangChain LCEL |
| **Reranker** | FlashRank (MS-MARCO MiniLM cross-encoder) |
| **Evaluation** | RAGAS (faithfulness, relevancy, precision, recall) |
| **UI** | Gradio Blocks |

---

## Quick Start

### 1. Clone and install

```bash
git clone <your-repo-url>
cd climate-risk-preparedness
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and set:
#   GROQ_API_KEY=your_key_here
```

Get a free Groq API key at [console.groq.com](https://console.groq.com).

### 3. Add PDF documents

Place government disaster/health guideline PDFs in `data/raw/`:

```bash
mkdir -p data/raw
cp /path/to/your/pdfs/*.pdf data/raw/
```

**Filename tip**: Include the hazard name for automatic tagging:
- `flood_preparedness_guide.pdf` → tagged as `flood`
- `cyclone_response_manual.pdf` → tagged as `cyclone`
- `heatwave_advisory_2024.pdf` → tagged as `heatwave`

### 4. Build the vector store

```bash
python scripts/setup_db.py
```

Options:
```bash
python scripts/setup_db.py --reset      # Wipe and rebuild
python scripts/setup_db.py --text-only  # Skip CLIP image embeddings (faster)
```

### 5. Launch the app

```bash
python app.py
```

Open [http://localhost:7860](http://localhost:7860) in your browser.

---

## Project Structure

```
climate-risk-preparedness/
├── app.py                      # Gradio UI entry point
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
│
├── data/
│   ├── raw/                    # 📥 Place your PDFs here
│   └── processed/              # Hash registry (auto-generated)
│
├── vectorstore/
│   └── chroma/                 # ChromaDB on-disk storage (auto-generated)
│
├── src/
│   ├── config/
│   │   └── settings.py         # Centralized configuration (Pydantic)
│   │
│   ├── ingestion/
│   │   ├── loader.py           # PDF text + image extraction
│   │   ├── chunker.py          # Semantic text chunking
│   │   └── embedder.py         # BGE-Large + CLIP embedders
│   │
│   ├── retrieval/
│   │   ├── retriever.py        # ChromaDB vector store + search
│   │   └── reranker.py         # FlashRank cross-encoder reranking
│   │
│   ├── agents/
│   │   └── risk_agent.py       # Hazard detection agent
│   │
│   ├── rag/
│   │   └── pipeline.py         # Full LCEL RAG pipeline
│   │
│   ├── evaluation/
│   │   └── ragas_eval.py       # RAGAS evaluation layer
│   │
│   └── utils/
│       └── helpers.py          # Shared utilities
│
├── scripts/
│   └── setup_db.py             # One-shot DB initialization
│
└── tests/
    ├── conftest.py             # Shared pytest fixtures
    └── test_pipeline.py        # Full test suite
```

---

## Module Guide

### `src/config/settings.py`
Pydantic `BaseSettings` — all config in one place, loaded from `.env`.

### `src/ingestion/`
- **`loader.py`** — Extracts text (pypdf) and images (PyMuPDF/fitz) from PDFs. Infers hazard type from filenames.
- **`chunker.py`** — `RecursiveCharacterTextSplitter` with paragraph → sentence → word hierarchy.
- **`embedder.py`** — `get_text_embedder()` (BGE-Large singleton) and `CLIPEmbedder` (ViT-B/32 singleton).

### `src/retrieval/`
- **`retriever.py`** — ChromaDB persistent client, text + image collections, similarity search with metadata filtering.
- **`reranker.py`** — FlashRank cross-encoder reranking (`rerank_documents()`).

### `src/agents/risk_agent.py`
Two-stage classifier:
1. Fast keyword matching (no API call)
2. LLM escalation for ambiguous queries (Groq)

Returns `RiskContext` with hazard, confidence, intent, and structured output flag.

### `src/rag/pipeline.py`
LCEL chain: `ChatPromptTemplate | ChatGroq | StrOutputParser`

Two prompt templates:
- **Preparedness** (Before/During/After/Health Safety)
- **General** (freeform explanation)

### `src/evaluation/ragas_eval.py`
- `evaluate_rag()` — batch evaluation
- `evaluate_single_response()` — single-query evaluation
- `format_scores_for_display()` — markdown table rendering

---

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test class
pytest tests/test_pipeline.py::TestRiskAgent -v

# Run with coverage
pytest tests/ --cov=src --cov-report=term-missing
```

---

## RAGAS Evaluation

From the **RAG Evaluation** tab in the UI, or programmatically:

```python
from src.rag.pipeline import rag_pipeline
from src.evaluation.ragas_eval import evaluate_single_response, format_scores_for_display

result = rag_pipeline.run("How do I prepare for a flood?")

scores = evaluate_single_response(
    query=result["query"],
    answer=result["answer"],
    retrieved_docs=result["retrieved_docs"],
    ground_truth="Store emergency supplies, create evacuation plan, know flood zones.",
)

print(format_scores_for_display(scores))
```

---

## Adding New Documents

1. Place PDFs in `data/raw/`
2. Run `python scripts/setup_db.py` (only new/changed files are processed)
3. Restart the app

The hash registry at `data/processed/.processed_hashes.json` tracks which files have been indexed.

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | ✅ Yes | Groq API key for LLaMA 3.1 |
| `HUGGINGFACE_TOKEN` | ❌ Optional | HuggingFace token for private models |
| `APP_ENV` | ❌ Optional | `development` (default) or `production` |
| `LOG_LEVEL` | ❌ Optional | `INFO` (default), `DEBUG`, `WARNING` |

---

## Supported Hazard Types

| Hazard | Emoji | Trigger Keywords |
|--------|-------|-----------------|
| `flood` | 🌊 | flood, flooding, inundation, flash flood |
| `cyclone` | 🌀 | cyclone, hurricane, typhoon, tropical storm |
| `heatwave` | 🌡️ | heatwave, heat wave, extreme heat, heat stroke |
| `earthquake` | 🏔️ | earthquake, seismic, tremor, aftershock |
| `drought` | ☀️ | drought, water scarcity, dry spell |
| `general` | 🌍 | (fallback for unrecognized queries) |

---

*Built with ❤️ for climate resilience.*
