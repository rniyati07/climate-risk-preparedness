#!/usr/bin/env python3
# ============================================================
# server.py
# Climate Risk Preparedness Advisor — FastAPI Backend
#
# Usage:
#   python server.py
#   # or:
#   venv\Scripts\python.exe server.py
#
# Endpoints:
#   POST /query            — Ask a climate risk question
#   GET  /health           — Health check
#   GET  /stats            — Vector store statistics
# ============================================================

import sys
import time
from pathlib import Path
from contextlib import asynccontextmanager

# ── Ensure src/ is importable ─────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from loguru import logger

from src.config.settings import settings


# ── Ready flag ───────────────────────────────────────────────
# Prevents queries from hitting a half-loaded pipeline.
_server_ready = False


# ── Pydantic models ──────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000,
                          description="Climate risk preparedness question")


class SourceCitation(BaseModel):
    source: str
    page: str | int
    hazard: str
    rerank_score: float | None = None


class RiskInfo(BaseModel):
    hazard: str
    intent: str
    confidence: float | None = None


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceCitation]
    risk_context: dict
    image_count: int
    query: str
    elapsed_seconds: float


class HealthResponse(BaseModel):
    status: str
    ready: bool
    vectorstore: str
    llm_model: str
    embedding_model: str


class StatsResponse(BaseModel):
    text_chunks: int
    image_chunks: int
    vectorstore_path: str
    pdfs_indexed: int


# ── App lifecycle ────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize pipeline and pre-warm all models on startup."""
    global _server_ready

    logger.info("=" * 60)
    logger.info("🌍 Climate Risk Preparedness Advisor — Backend Starting")
    logger.info("=" * 60)

    settings.ensure_dirs()

    # ── Step 1: Load RAG pipeline (imports BGE text embedder) ──
    print("[STARTUP] Step 1/3: Loading RAG pipeline + text embedder...", flush=True)
    logger.info("⏳ Step 1/3: Loading RAG pipeline + text embedder...")
    from src.rag.pipeline import rag_pipeline  # noqa: F811
    app.state.pipeline = rag_pipeline
    logger.info("✅ Step 1/3: RAG pipeline ready.")

    # ── Step 2: Skip CLIP Pre-warming (Lazy load only if needed) ──
    logger.info("⏭️ Step 2/3: Skipping CLIP pre-warming (lazy load to save memory).")

    # ── Step 3: Pre-warm FlashRank reranker ────────────────────
    print("[STARTUP] Step 3/3: Pre-warming reranker...", flush=True)
    logger.info("⏳ Step 3/3: Pre-warming FlashRank reranker...")
    from src.retrieval.reranker import _get_ranker
    _get_ranker()
    logger.info("✅ Step 3/3: Reranker warmed.")

    # ── All models loaded — accept requests ────────────────────
    _server_ready = True
    logger.info("🚀 All models loaded. Server is ready.")
    print("[STARTUP] All models loaded. Server ready!", flush=True)

    yield

    logger.info("🛑 Shutting down")


# ── FastAPI app ──────────────────────────────────────────────

app = FastAPI(
    title="Climate Risk Preparedness Advisor API",
    description="Agentic Multimodal RAG backend for Tamil Nadu climate hazard preparedness",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Endpoints ────────────────────────────────────────────────

@app.post("/query", response_model=QueryResponse)
async def query_advisor(req: QueryRequest):
    """
    Submit a climate risk preparedness question.

    The pipeline will:
    1. Detect the hazard type (flood, cyclone, earthquake, etc.)
    2. Retrieve relevant chunks from the vector store
    3. Rerank with a cross-encoder
    4. Generate a structured response via LLaMA 3.1
    """
    # ── Guard: reject if models are still loading ─────────────
    if not _server_ready:
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Server is still loading models. Please wait and try again in a minute."
            },
        )

    start = time.time()
    pipeline = app.state.pipeline

    try:
        result = pipeline.run(req.question)
    except Exception as exc:
        logger.error(f"Pipeline error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

    elapsed = round(time.time() - start, 2)

    return QueryResponse(
        answer=result["answer"],
        sources=result.get("sources", []),
        risk_context=result.get("risk_context", {}),
        image_count=len(result.get("image_results", [])),
        query=result["query"],
        elapsed_seconds=elapsed,
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check if the backend is running and models are loaded."""
    return HealthResponse(
        status="ok" if _server_ready else "loading",
        ready=_server_ready,
        vectorstore=str(settings.vectorstore_dir),
        llm_model=settings.llm_model_name,
        embedding_model=settings.text_embedding_model,
    )


@app.get("/stats", response_model=StatsResponse)
async def vectorstore_stats():
    """Return vector store collection statistics."""
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(settings.vectorstore_dir))
        collections = client.list_collections()

        text_count = 0
        image_count = 0
        for c in collections:
            if "text" in c.name:
                text_count = c.count()
            elif "image" in c.name:
                image_count = c.count()

        # Count indexed PDFs from hash registry
        import json
        hash_file = settings.data_processed_dir / ".processed_hashes.json"
        pdf_count = 0
        if hash_file.exists():
            with open(hash_file) as f:
                pdf_count = len(json.load(f))

        return StatsResponse(
            text_chunks=text_count,
            image_chunks=image_count,
            vectorstore_path=str(settings.vectorstore_dir),
            pdfs_indexed=pdf_count,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── Run ──────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
        log_level="info",
    )
