# ============================================================
# src/ingestion/chunker.py
# Semantic chunking of extracted PDF page text.
# Uses LangChain's RecursiveCharacterTextSplitter for clean
# sentence-boundary-aware splitting, preserving metadata from
# the original PageRecord objects.
# ============================================================

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger

from src.config.settings import settings
from src.ingestion.loader import PageRecord


def build_text_splitter(
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> RecursiveCharacterTextSplitter:
    """
    Create a RecursiveCharacterTextSplitter configured for
    climate document chunking.

    The splitter tries progressively smaller separators:
    paragraph → sentence → word → character, so chunks
    respect natural text boundaries as much as possible.

    Args:
        chunk_size:    Max characters per chunk (default from settings).
        chunk_overlap: Overlap between consecutive chunks.

    Returns:
        Configured RecursiveCharacterTextSplitter instance.
    """
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size or settings.chunk_size,
        chunk_overlap=chunk_overlap or settings.chunk_overlap,
        # Separator priority: paragraph > sentence > clause > word
        separators=["\n\n", "\n", ". ", ", ", " ", ""],
        length_function=len,
        is_separator_regex=False,
    )


def chunk_page_records(
    page_records: list[PageRecord],
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[Document]:
    """
    Convert a list of PageRecords into LangChain Documents
    (text chunks) with preserved metadata.

    Each PageRecord (one PDF page) may produce multiple chunks.
    Metadata is carried through so retrieval results always
    trace back to their original source, page, and hazard type.

    Args:
        page_records:  List of PageRecord objects from the loader.
        chunk_size:    Override default chunk size.
        chunk_overlap: Override default chunk overlap.

    Returns:
        List of LangChain Document objects ready for embedding.
    """
    if not page_records:
        logger.warning("[Chunker] Received empty page_records list.")
        return []

    splitter = build_text_splitter(chunk_size, chunk_overlap)
    all_docs: list[Document] = []

    for record in page_records:
        # Skip pages with too little content to be useful
        if len(record.text) < 50:
            continue

        # Split the page text into sub-chunks
        raw_chunks = splitter.split_text(record.text)

        for chunk_idx, chunk_text in enumerate(raw_chunks):
            # Skip whitespace-only chunks
            if not chunk_text.strip():
                continue

            # Build enriched metadata for each chunk
            chunk_metadata = {
                **record.metadata,                          # carries source, page, hazard
                "chunk_index": chunk_idx,                   # position within page
                "chunk_char_count": len(chunk_text),        # useful for debug/filtering
            }

            doc = Document(
                page_content=chunk_text.strip(),
                metadata=chunk_metadata,
            )
            all_docs.append(doc)

    logger.info(
        f"[Chunker] Produced {len(all_docs)} text chunks "
        f"from {len(page_records)} pages."
    )
    return all_docs


def chunk_text_string(
    text: str,
    base_metadata: dict | None = None,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[Document]:
    """
    Utility: chunk a raw text string directly (no PageRecord).
    Useful for ad-hoc ingestion or testing.

    Args:
        text:          Raw text to chunk.
        base_metadata: Metadata to attach to all produced chunks.
        chunk_size:    Override chunk size.
        chunk_overlap: Override chunk overlap.

    Returns:
        List of LangChain Document objects.
    """
    splitter = build_text_splitter(chunk_size, chunk_overlap)
    base_metadata = base_metadata or {}
    raw_chunks = splitter.split_text(text)

    docs = [
        Document(
            page_content=chunk.strip(),
            metadata={**base_metadata, "chunk_index": idx},
        )
        for idx, chunk in enumerate(raw_chunks)
        if chunk.strip()
    ]

    logger.info(
        f"[Chunker] Produced {len(docs)} chunks from raw text string."
    )
    return docs
