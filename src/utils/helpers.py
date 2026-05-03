# ============================================================
# src/utils/helpers.py
# Shared utility functions used across the codebase.
# ============================================================

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from loguru import logger


def compute_file_hash(file_path: Path) -> str:
    """
    Compute SHA-256 hash of a file for change detection.
    Used to skip re-ingestion of already processed files.

    Args:
        file_path: Path to the file.

    Returns:
        Hex digest string (64 characters).
    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def load_processed_hashes(hash_file: Path) -> dict[str, str]:
    """
    Load a JSON file mapping filename → SHA-256 hash.
    Used to track which PDFs have already been ingested.

    Args:
        hash_file: Path to the JSON hash registry file.

    Returns:
        Dict of {filename: hash}. Empty dict if file doesn't exist.
    """
    if not hash_file.exists():
        return {}
    try:
        with open(hash_file, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as exc:
        logger.warning(f"[Helpers] Could not load hash file: {exc}")
        return {}


def save_processed_hashes(
    hash_file: Path, hashes: dict[str, str]
) -> None:
    """
    Persist the processed hash registry to disk.

    Args:
        hash_file: Path to write the JSON file.
        hashes:    Dict of {filename: hash}.
    """
    hash_file.parent.mkdir(parents=True, exist_ok=True)
    with open(hash_file, "w") as f:
        json.dump(hashes, f, indent=2)
    logger.debug(f"[Helpers] Saved {len(hashes)} file hashes to '{hash_file}'.")


def truncate_text(text: str, max_chars: int = 500) -> str:
    """
    Truncate text to a maximum character count, appending '…'.

    Args:
        text:      Input text string.
        max_chars: Maximum allowed characters.

    Returns:
        Truncated string.
    """
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "…"


def format_metadata_for_display(metadata: dict[str, Any]) -> str:
    """
    Format a metadata dict into a readable key: value string.

    Args:
        metadata: Document or chunk metadata dict.

    Returns:
        Formatted string (one key-value pair per line).
    """
    lines = []
    for key, value in metadata.items():
        if key == "rerank_score" and value is not None:
            lines.append(f"  {key}: {float(value):.4f}")
        else:
            lines.append(f"  {key}: {value}")
    return "\n".join(lines)


def elapsed_time_str(start_time: float) -> str:
    """
    Return elapsed time since `start_time` as a human-readable string.

    Args:
        start_time: Value from time.time() at start of operation.

    Returns:
        Formatted elapsed time string, e.g. "1.23s" or "45.67s".
    """
    elapsed = time.time() - start_time
    return f"{elapsed:.2f}s"


def sanitize_query(query: str) -> str:
    """
    Sanitize a user query: strip whitespace, normalize spacing,
    and cap length to prevent overly long prompts.

    Args:
        query: Raw user input string.

    Returns:
        Cleaned query string (max 1000 chars).
    """
    query = " ".join(query.strip().split())   # normalize whitespace
    return query[:1000]                        # cap at 1000 characters


def hazard_emoji(hazard: str) -> str:
    """
    Return a display emoji for a given hazard type.

    Args:
        hazard: Hazard type string.

    Returns:
        Emoji character.
    """
    emoji_map = {
        "flood": "🌊",
        "cyclone": "🌀",
        "heatwave": "🌡️",
        "earthquake": "🏔️",
        "drought": "☀️",
        "general": "🌍",
    }
    return emoji_map.get(hazard.lower(), "🌍")
