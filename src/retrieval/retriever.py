# ============================================================
# src/retrieval/retriever.py
# ChromaDB integration for vector storage and retrieval.
# Handles both text and image collections with:
#   - Similarity search (cosine distance)
#   - Metadata filtering by hazard type
#   - MMR (maximal marginal relevance) for diversity
# ============================================================

from functools import lru_cache
from pathlib import Path

import chromadb
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_community.vectorstores.utils import filter_complex_metadata
from loguru import logger

from src.config.settings import settings
from src.ingestion.embedder import get_text_embedder, get_clip_embedder
from src.ingestion.loader import ImageRecord


# ── ChromaDB client factory ───────────────────────────────────

@lru_cache(maxsize=1)
def _get_chroma_client() -> chromadb.PersistentClient:
    """
    Return a persistent ChromaDB client (singleton).
    Data is stored on disk at vectorstore_dir.
    """
    client = chromadb.PersistentClient(
        path=str(settings.vectorstore_dir)
    )
    logger.info(
        f"[Retriever] ChromaDB client initialized at "
        f"'{settings.vectorstore_dir}'"
    )
    return client


# ── Text vector store ─────────────────────────────────────────

def get_text_vectorstore() -> Chroma:
    """
    Load (or create) the Chroma text collection backed by
    HuggingFace BGE-Large embeddings.

    Returns:
        LangChain Chroma vector store for text chunks.
    """
    embedder = get_text_embedder()
    vectorstore = Chroma(
        client=_get_chroma_client(),
        collection_name=settings.chroma_text_collection,
        embedding_function=embedder,
        collection_metadata={"hnsw:space": "cosine"},
    )
    return vectorstore


def add_documents_to_text_store(documents: list[Document]) -> None:
    """
    Embed and persist a list of LangChain Documents into ChromaDB.

    Args:
        documents: Chunked text documents with metadata.
    """
    if not documents:
        logger.warning("[Retriever] No documents to add to text store.")
        return

    # ChromaDB metadata values must be str | int | float | bool
    # filter_complex_metadata removes unsupported types (e.g. lists)
    clean_docs = filter_complex_metadata(documents)

    vectorstore = get_text_vectorstore()
    vectorstore.add_documents(clean_docs)

    logger.info(
        f"[Retriever] Added {len(clean_docs)} text chunks to ChromaDB."
    )


# ── Image vector store (raw ChromaDB collection) ──────────────

def _get_image_collection() -> chromadb.Collection:
    """
    Get or create a raw ChromaDB collection for image embeddings.
    We use the raw client API here because LangChain Chroma
    doesn't natively support CLIP-dimension vectors.
    """
    client = _get_chroma_client()
    collection = client.get_or_create_collection(
        name=settings.chroma_image_collection,
        metadata={"hnsw:space": "cosine"},
    )
    return collection


def add_images_to_image_store(image_records: list[ImageRecord]) -> None:
    """
    Embed PIL images with CLIP and persist them to ChromaDB.
    Each image is stored with its caption and metadata.

    Args:
        image_records: ImageRecord objects from the loader.
    """
    if not image_records:
        logger.warning("[Retriever] No images to add to image store.")
        return

    clip = get_clip_embedder()
    collection = _get_image_collection()

    ids, embeddings, documents, metadatas = [], [], [], []

    for idx, record in enumerate(image_records):
        try:
            # CLIP image embedding (512-dim)
            vec = clip.embed_image(record.image)

            unique_id = (
                f"{record.source}_p{record.page_num}_i{record.image_index}"
            )
            ids.append(unique_id)
            embeddings.append(vec)
            documents.append(record.caption)
            metadatas.append(record.metadata)

        except Exception as exc:
            logger.warning(
                f"[Retriever] Skipped image record {idx}: {exc}"
            )

    if ids:
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        logger.info(
            f"[Retriever] Added {len(ids)} image embeddings to ChromaDB."
        )


# ── Retrieval functions ───────────────────────────────────────

def retrieve_text_chunks(
    query: str,
    hazard_filter: str | None = None,
    top_k: int | None = None,
) -> list[Document]:
    """
    Retrieve the most relevant text chunks for a query.

    Uses cosine similarity search with optional metadata filtering
    on hazard type. Falls back to unfiltered search if filtered
    results are insufficient.

    Args:
        query:         User query string.
        hazard_filter: Optional hazard type to filter by
                       (e.g., "flood", "cyclone").
        top_k:         Number of documents to retrieve.

    Returns:
        List of LangChain Documents (ranked by relevance).
    """
    k = top_k or settings.retrieval_top_k
    vectorstore = get_text_vectorstore()

    # Build metadata filter dict for ChromaDB's `where` clause
    where_filter = None
    if hazard_filter and hazard_filter != "general":
        where_filter = {"hazard": {"$eq": hazard_filter}}

    try:
        if where_filter:
            docs = vectorstore.similarity_search(
                query=query,
                k=k,
                filter=where_filter,
            )
            # If filtered search returns nothing, fall back to unfiltered
            if not docs:
                logger.warning(
                    f"[Retriever] No results for hazard='{hazard_filter}'. "
                    "Falling back to unfiltered search."
                )
                docs = vectorstore.similarity_search(query=query, k=k)
        else:
            docs = vectorstore.similarity_search(query=query, k=k)

    except Exception as exc:
        logger.error(f"[Retriever] Text retrieval failed: {exc}")
        docs = []

    logger.info(
        f"[Retriever] Retrieved {len(docs)} text chunks "
        f"(hazard='{hazard_filter}', k={k})."
    )
    return docs


def retrieve_similar_images(
    query: str,
    hazard_filter: str | None = None,
    top_k: int = 3,
) -> list[dict]:
    """
    Retrieve the most relevant image records for a text query
    using CLIP's cross-modal alignment.

    Args:
        query:         Text query to match against image embeddings.
        hazard_filter: Optional hazard type filter.
        top_k:         Number of image results to return.

    Returns:
        List of dicts with keys: id, document (caption), metadata, distance.
    """
    clip = get_clip_embedder()
    collection = _get_image_collection()

    # Encode text query into CLIP's shared embedding space
    query_vec = clip.embed_text(query)

    # Build optional where clause
    where_clause = None
    if hazard_filter and hazard_filter != "general":
        where_clause = {"hazard": {"$eq": hazard_filter}}

    try:
        results = collection.query(
            query_embeddings=[query_vec],
            n_results=min(top_k, collection.count() or 1),
            where=where_clause,
            include=["documents", "metadatas", "distances"],
        )

        # Flatten the nested result lists
        image_hits = []
        for i, doc_id in enumerate(results["ids"][0]):
            image_hits.append(
                {
                    "id": doc_id,
                    "caption": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i],
                }
            )

        logger.info(
            f"[Retriever] Retrieved {len(image_hits)} image results "
            f"for query (CLIP)."
        )
        return image_hits

    except Exception as exc:
        logger.warning(f"[Retriever] Image retrieval failed: {exc}")
        return []


def get_vectorstore_stats() -> dict:
    """
    Return basic statistics about the ChromaDB collections.
    Useful for debugging and monitoring.
    """
    client = _get_chroma_client()
    text_col = client.get_or_create_collection(settings.chroma_text_collection)
    image_col = client.get_or_create_collection(settings.chroma_image_collection)

    return {
        "text_collection": settings.chroma_text_collection,
        "text_document_count": text_col.count(),
        "image_collection": settings.chroma_image_collection,
        "image_document_count": image_col.count(),
        "vectorstore_path": str(settings.vectorstore_dir),
    }
