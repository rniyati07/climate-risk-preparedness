# ============================================================
# src/retrieval/reranker.py
# Cross-encoder reranking of retrieved text chunks.
# Uses FlashRank (a lightweight, fast cross-encoder) to
# reorder candidate documents by relevance to the query.
#
# Reranking improves precision: the vector search casts a
# wide net (top_k=5), then the cross-encoder picks the best
# top_n=3 passages for the LLM context window.
# ============================================================

from functools import lru_cache
from pathlib import Path

from flashrank import Ranker, RerankRequest
from langchain_core.documents import Document
from loguru import logger

from src.config.settings import settings


# ── Reranker singleton ────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_ranker() -> Ranker:
    """
    Load and cache the FlashRank cross-encoder model.

    FlashRank's default model (ms-marco-MiniLM-L-12-v2) is a
    compact, high-quality cross-encoder fine-tuned on MS MARCO
    passage ranking — well-suited for retrieval reranking.

    Returns:
        Initialized FlashRank Ranker instance.
    """
    logger.info("[Reranker] Loading FlashRank cross-encoder model...")
    # cache_dir prevents repeated downloads
    ranker = Ranker(cache_dir=str(Path(__file__).resolve().parents[2] / ".cache" / "flashrank"))
    logger.info("[Reranker] Reranker model loaded successfully.")
    return ranker


# ── Reranking logic ───────────────────────────────────────────

def rerank_documents(
    query: str,
    documents: list[Document],
    top_n: int | None = None,
) -> list[Document]:
    """
    Rerank a list of LangChain Documents using a cross-encoder.

    The cross-encoder scores each (query, document) pair jointly,
    producing more accurate relevance estimates than bi-encoder
    cosine similarity alone.

    Args:
        query:     The user's original question.
        documents: Candidate documents from vector retrieval.
        top_n:     Number of top documents to return after reranking.
                   Defaults to settings.rerank_top_n.

    Returns:
        Reranked list of Documents (most relevant first),
        trimmed to top_n. Returns original list if reranking fails.
    """
    n = top_n or settings.rerank_top_n

    if not documents:
        logger.warning("[Reranker] No documents to rerank.")
        return []

    # If we have fewer docs than top_n, return them as-is
    if len(documents) <= n:
        logger.info(
            f"[Reranker] {len(documents)} docs ≤ top_n={n}, "
            "skipping reranker."
        )
        return documents

    try:
        ranker = _get_ranker()

        # FlashRank expects a list of dicts with an 'id' and 'text' key
        passages = [
            {"id": idx, "text": doc.page_content}
            for idx, doc in enumerate(documents)
        ]

        rerank_request = RerankRequest(query=query, passages=passages)
        reranked = ranker.rerank(rerank_request)

        # reranked is a list of dicts sorted by score descending
        # Each dict has: id (original index), text, score
        top_docs: list[Document] = []
        for result in reranked[:n]:
            original_idx = result["id"]
            original_doc = documents[original_idx]

            # Attach rerank score to metadata for traceability
            enriched_metadata = {
                **original_doc.metadata,
                "rerank_score": float(result.get("score", 0.0)),
            }

            top_docs.append(
                Document(
                    page_content=original_doc.page_content,
                    metadata=enriched_metadata,
                )
            )

        logger.info(
            f"[Reranker] Reranked {len(documents)} → top {len(top_docs)} docs."
        )
        return top_docs

    except Exception as exc:
        logger.error(
            f"[Reranker] Reranking failed ({exc}). "
            "Returning original docs (top_n slice)."
        )
        # Graceful fallback: return first top_n documents unchanged
        return documents[:n]
