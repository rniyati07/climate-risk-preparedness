# ============================================================
# src/ingestion/loader.py
# Loads PDFs from the raw data directory.
# Extracts text pages via pypdf and images via PyMuPDF (fitz).
# Returns structured page/image records ready for chunking.
# ============================================================

import io
from pathlib import Path
from typing import Generator

import fitz  # PyMuPDF
from loguru import logger
from PIL import Image
from pypdf import PdfReader

from src.config.settings import settings


# ── Data structures ───────────────────────────────────────────

class PageRecord:
    """Represents a single text page extracted from a PDF."""

    def __init__(
        self,
        source: str,
        page_num: int,
        text: str,
        metadata: dict,
    ):
        self.source = source          # filename (stem)
        self.page_num = page_num
        self.text = text.strip()
        self.metadata = metadata      # extra metadata (hazard type, etc.)

    def __repr__(self) -> str:
        return f"<PageRecord source={self.source} page={self.page_num} chars={len(self.text)}>"


class ImageRecord:
    """Represents an image extracted from a PDF page."""

    def __init__(
        self,
        source: str,
        page_num: int,
        image_index: int,
        image: Image.Image,
        caption: str,
        metadata: dict,
    ):
        self.source = source
        self.page_num = page_num
        self.image_index = image_index
        self.image = image            # PIL.Image object
        self.caption = caption        # Derived caption (filename + page info)
        self.metadata = metadata

    def __repr__(self) -> str:
        return (
            f"<ImageRecord source={self.source} "
            f"page={self.page_num} idx={self.image_index}>"
        )


# ── Hazard keyword mapping ────────────────────────────────────

# Map filename keywords → hazard type for automatic metadata tagging
_HAZARD_KEYWORDS: dict[str, str] = {
    "flood": "flood",
    "cyclone": "cyclone",
    "hurricane": "cyclone",
    "typhoon": "cyclone",
    "heat": "heatwave",
    "heatwave": "heatwave",
    "earthquake": "earthquake",
    "seismic": "earthquake",
    "drought": "drought",
}


def _infer_hazard(filename: str) -> str:
    """
    Infer hazard type from filename using keyword matching.
    Falls back to 'general' if no keyword matched.
    """
    lower = filename.lower()
    for keyword, hazard in _HAZARD_KEYWORDS.items():
        if keyword in lower:
            return hazard
    return "general"


# ── Core loader functions ─────────────────────────────────────

def load_pdf_text(pdf_path: Path) -> list[PageRecord]:
    """
    Extract text from every page of a PDF using pypdf.

    Args:
        pdf_path: Absolute path to the PDF file.

    Returns:
        List of PageRecord objects, one per page with text content.
    """
    records: list[PageRecord] = []
    source_name = pdf_path.stem
    hazard = _infer_hazard(source_name)

    try:
        reader = PdfReader(str(pdf_path))
        for page_num, page in enumerate(reader.pages, start=1):
            raw_text = page.extract_text() or ""
            if not raw_text.strip():
                # Skip blank pages
                continue

            record = PageRecord(
                source=source_name,
                page_num=page_num,
                text=raw_text,
                metadata={
                    "source": source_name,
                    "page": page_num,
                    "hazard": hazard,
                    "file_path": str(pdf_path),
                    "type": "text",
                },
            )
            records.append(record)

        logger.info(
            f"[Loader] Extracted {len(records)} text pages from '{pdf_path.name}'"
        )

    except Exception as exc:
        logger.error(f"[Loader] Failed to extract text from '{pdf_path}': {exc}")

    return records


def load_pdf_images(pdf_path: Path) -> list[ImageRecord]:
    """
    Extract embedded images from a PDF using PyMuPDF (fitz).

    Args:
        pdf_path: Absolute path to the PDF file.

    Returns:
        List of ImageRecord objects with PIL Image objects.
    """
    records: list[ImageRecord] = []
    source_name = pdf_path.stem
    hazard = _infer_hazard(source_name)

    try:
        doc = fitz.open(str(pdf_path))

        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images(full=True)

            for img_idx, img_info in enumerate(image_list):
                xref = img_info[0]  # image cross-reference number

                try:
                    base_image = doc.extract_image(xref)
                    img_bytes = base_image["image"]
                    img_ext = base_image["ext"]  # e.g., "png", "jpeg"

                    # Convert raw bytes → PIL Image
                    pil_image = Image.open(io.BytesIO(img_bytes)).convert("RGB")

                    # Skip very small images (likely icons/artifacts)
                    width, height = pil_image.size
                    if width < 50 or height < 50:
                        continue

                    # Build a descriptive caption for multimodal context
                    caption = (
                        f"Figure from '{source_name}', "
                        f"page {page_num + 1}, image {img_idx + 1}. "
                        f"Related to {hazard} preparedness."
                    )

                    record = ImageRecord(
                        source=source_name,
                        page_num=page_num + 1,
                        image_index=img_idx,
                        image=pil_image,
                        caption=caption,
                        metadata={
                            "source": source_name,
                            "page": page_num + 1,
                            "hazard": hazard,
                            "image_format": img_ext,
                            "width": width,
                            "height": height,
                            "type": "image",
                        },
                    )
                    records.append(record)

                except Exception as img_exc:
                    logger.warning(
                        f"[Loader] Skipped image xref={xref} "
                        f"on page {page_num + 1}: {img_exc}"
                    )

        doc.close()
        logger.info(
            f"[Loader] Extracted {len(records)} images from '{pdf_path.name}'"
        )

    except Exception as exc:
        logger.error(
            f"[Loader] Failed to extract images from '{pdf_path}': {exc}"
        )

    return records


def load_all_pdfs(
    raw_dir: Path | None = None,
) -> tuple[list[PageRecord], list[ImageRecord]]:
    """
    Scan the raw data directory and load all PDFs.

    Args:
        raw_dir: Directory containing raw PDF files.
                 Defaults to settings.data_raw_dir.

    Returns:
        Tuple of (all page records, all image records).
    """
    raw_dir = raw_dir or settings.data_raw_dir
    pdf_files = list(raw_dir.glob("*.pdf"))

    if not pdf_files:
        logger.warning(f"[Loader] No PDF files found in '{raw_dir}'.")
        return [], []

    logger.info(f"[Loader] Found {len(pdf_files)} PDF(s) in '{raw_dir}'.")

    all_pages: list[PageRecord] = []
    all_images: list[ImageRecord] = []

    for pdf_path in pdf_files:
        pages = load_pdf_text(pdf_path)
        images = load_pdf_images(pdf_path)
        all_pages.extend(pages)
        all_images.extend(images)

    logger.info(
        f"[Loader] Total: {len(all_pages)} text pages, "
        f"{len(all_images)} images loaded."
    )

    return all_pages, all_images
