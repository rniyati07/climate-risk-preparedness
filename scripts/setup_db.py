#!/usr/bin/env python3
# ============================================================
# scripts/setup_db.py
# One-shot script to bootstrap the ChromaDB vector store.
#
# What it does:
#   1. Scans data/raw/ for PDF files
#   2. Extracts text pages and embedded images
#   3. Chunks text into semantic segments
#   4. Generates text embeddings (BGE-Large)
#   5. Generates image embeddings (CLIP)
#   6. Persists all vectors to ChromaDB on disk
#   7. Saves a hash registry to skip re-ingestion next run
#
# Usage:
#   python scripts/setup_db.py
#   python scripts/setup_db.py --reset      # wipe & rebuild
#   python scripts/setup_db.py --text-only  # skip image embeddings
# ============================================================

import argparse
import shutil
import sys
import time
from pathlib import Path

# ── Add project root to sys.path ─────────────────────────────
# Allows `from src.xxx import ...` when running as a script
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from loguru import logger
from tqdm import tqdm

from src.config.settings import settings
from src.ingestion.loader import load_all_pdfs
from src.ingestion.chunker import chunk_page_records
from src.retrieval.retriever import (
    add_documents_to_text_store,
    add_images_to_image_store,
    get_vectorstore_stats,
)
from src.utils.helpers import (
    compute_file_hash,
    load_processed_hashes,
    save_processed_hashes,
    elapsed_time_str,
)

# ── Constants ─────────────────────────────────────────────────
HASH_REGISTRY_PATH = settings.data_processed_dir / ".processed_hashes.json"
IMAGE_HASH_REGISTRY_PATH = settings.data_processed_dir / ".processed_image_hashes.json"


# ── CLI argument parsing ──────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bootstrap the Climate Risk ChromaDB vector store."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Wipe the existing vector store and re-ingest everything.",
    )
    parser.add_argument(
        "--text-only",
        action="store_true",
        help="Skip CLIP image embedding (faster for text-only use).",
    )
    parser.add_argument(
        "--images-only",
        action="store_true",
        help="Only run CLIP image embedding (skip text). Use with build_db.py.",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=settings.data_raw_dir,
        help=f"Directory containing raw PDFs (default: {settings.data_raw_dir})",
    )
    return parser.parse_args()


# ── Reset helper ──────────────────────────────────────────────

def reset_vectorstore() -> None:
    """
    Wipe all ChromaDB data on disk and clear the hash registry.
    Called when --reset flag is passed.
    """
    vs_path = settings.vectorstore_dir
    if vs_path.exists():
        shutil.rmtree(vs_path)
        logger.warning(f"[Setup] Wiped vector store at '{vs_path}'.")
    else:
        logger.info("[Setup] No existing vector store found to wipe.")

    settings.ensure_dirs()   # recreate empty directories

    # Clear hash registry so all files are re-processed
    if HASH_REGISTRY_PATH.exists():
        HASH_REGISTRY_PATH.unlink()
        logger.info("[Setup] Cleared processed file hash registry.")


# ── Ingestion helpers ─────────────────────────────────────────

def get_new_pdfs(raw_dir: Path, known_hashes: dict[str, str]) -> list[Path]:
    """
    Return PDFs that are new or have changed since last ingestion.

    Compares SHA-256 hashes of current files against the registry.

    Args:
        raw_dir:       Directory containing raw PDF files.
        known_hashes:  Previously recorded {filename: hash} dict.

    Returns:
        List of PDF Path objects that need (re)processing.
    """
    all_pdfs = list(raw_dir.glob("*.pdf"))
    new_pdfs: list[Path] = []

    for pdf_path in all_pdfs:
        current_hash = compute_file_hash(pdf_path)
        stored_hash = known_hashes.get(pdf_path.name)

        if stored_hash != current_hash:
            logger.info(
                f"[Setup] New/changed file detected: '{pdf_path.name}'"
            )
            new_pdfs.append(pdf_path)
        else:
            logger.info(
                f"[Setup] Skipping already-indexed: '{pdf_path.name}'"
            )

    return new_pdfs


# ── Main ingestion pipeline ───────────────────────────────────

def run_ingestion(
    raw_dir: Path,
    text_only: bool,
    images_only: bool = False,
    force_all: bool = False,
) -> None:
    """
    Execute the full ingestion pipeline.

    Args:
        raw_dir:    Directory containing raw PDFs.
        text_only:  If True, skip CLIP image embedding.
        images_only: If True, skip text embedding (only run CLIP).
        force_all:  If True, process all PDFs regardless of hash.
    """
    # ── Load hash registry ─────────────────────────────────
    hash_path = IMAGE_HASH_REGISTRY_PATH if images_only else HASH_REGISTRY_PATH
    known_hashes = {} if force_all else load_processed_hashes(hash_path)

    # ── Detect which PDFs need processing ─────────────────
    if force_all:
        pdfs_to_process = list(raw_dir.glob("*.pdf"))
    else:
        pdfs_to_process = get_new_pdfs(raw_dir, known_hashes)

    if not pdfs_to_process:
        logger.info(
            "[Setup] All PDFs are already up-to-date in the vector store. "
            "Nothing to do. Use --reset to force full re-ingestion."
        )
        _print_stats()
        return

    logger.info(
        f"[Setup] Processing {len(pdfs_to_process)} PDF(s): "
        f"{[p.name for p in pdfs_to_process]}"
    )

    total_chunks = 0
    total_images = 0
    updated_hashes = {**known_hashes}

    # ── Process each PDF ───────────────────────────────────
    for pdf_path in tqdm(pdfs_to_process, desc="Ingesting PDFs"):
        t0 = time.time()
        logger.info(f"\n{'='*60}")
        logger.info(f"[Setup] Processing: '{pdf_path.name}'")

        # ── Text extraction ──────────────────────────────
        from src.ingestion.loader import load_pdf_text, load_pdf_images

        page_records = load_pdf_text(pdf_path)
        logger.info(f"  ✓ Extracted {len(page_records)} text pages.")

        # ── Chunking ─────────────────────────────────────
        chunks = chunk_page_records(page_records)
        logger.info(f"  ✓ Produced {len(chunks)} text chunks.")

        # ── Text embedding + ChromaDB storage ────────────
        if chunks and not images_only:
            logger.info(f"  → Embedding and storing {len(chunks)} chunks …")
            add_documents_to_text_store(chunks)
            total_chunks += len(chunks)
            logger.info(f"  ✓ Text chunks stored in ChromaDB.")
        elif images_only:
            logger.info(f"  ⚡ Skipping text embedding (--images-only mode).")

        # ── Image embedding + ChromaDB storage ───────────
        if not text_only:
            image_records = load_pdf_images(pdf_path)
            logger.info(f"  ✓ Extracted {len(image_records)} images.")

            if image_records:
                logger.info(
                    f"  → Embedding {len(image_records)} images with CLIP …"
                )
                add_images_to_image_store(image_records)
                total_images += len(image_records)
                logger.info(f"  ✓ Image embeddings stored in ChromaDB.")
        else:
            logger.info("  ⚡ Skipping image embedding (--text-only mode).")

        # ── Update hash registry ──────────────────────────
        updated_hashes[pdf_path.name] = compute_file_hash(pdf_path)
        # Save after every PDF to prevent losing progress if killed/OOM
        save_processed_hashes(hash_path, updated_hashes)
        
        elapsed = elapsed_time_str(t0)
        logger.info(f"  ✅ Finished '{pdf_path.name}' in {elapsed}.")

    # ── Final summary ──────────────────────────────────────
    logger.info(f"\n{'='*60}")
    logger.info("[Setup] ✅ Ingestion complete!")
    logger.info(f"  PDFs processed : {len(pdfs_to_process)}")
    logger.info(f"  Text chunks    : {total_chunks}")
    logger.info(f"  Image vectors  : {total_images}")
    _print_stats()


def _print_stats() -> None:
    """Print current ChromaDB collection stats."""
    try:
        stats = get_vectorstore_stats()
        logger.info("\n📊 ChromaDB Stats:")
        logger.info(f"  Text collection  : {stats['text_collection']}")
        logger.info(f"  Text documents   : {stats['text_document_count']}")
        logger.info(f"  Image collection : {stats['image_collection']}")
        logger.info(f"  Image documents  : {stats['image_document_count']}")
        logger.info(f"  Storage path     : {stats['vectorstore_path']}")
    except Exception as exc:
        logger.warning(f"[Setup] Could not retrieve stats: {exc}")


# ── Entry point ───────────────────────────────────────────────

def main() -> None:
    args = parse_args()

    logger.info("=" * 60)
    logger.info("🌍 Climate Risk Preparedness — Vector Store Setup")
    logger.info("=" * 60)

    # Validate raw directory
    if not args.raw_dir.exists():
        logger.error(
            f"[Setup] Raw data directory not found: '{args.raw_dir}'\n"
            f"Create it and add PDF files before running this script."
        )
        sys.exit(1)

    # Reset if requested
    if args.reset:
        logger.warning("[Setup] --reset flag detected. Wiping vector store …")
        reset_vectorstore()

    # Run ingestion
    run_ingestion(
        raw_dir=args.raw_dir,
        text_only=args.text_only,
        images_only=args.images_only,
        force_all=args.reset,
    )


if __name__ == "__main__":
    main()
