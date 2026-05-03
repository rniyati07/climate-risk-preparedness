# ============================================================
# src/ingestion/embedder.py
# Generates embeddings for:
#   1. Text chunks → HuggingFace BGE-Large embeddings
#   2. Images      → OpenCLIP (ViT-B/32) embeddings
#
# Both embedder classes are singletons loaded lazily to avoid
# repeated model loading across the application lifecycle.
# ============================================================

from functools import lru_cache
from typing import List

import numpy as np
import torch
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from loguru import logger
from PIL import Image

from src.config.settings import settings


# ── 1. Text Embedder ──────────────────────────────────────────

@lru_cache(maxsize=1)
def get_text_embedder() -> HuggingFaceEndpointEmbeddings:
    """
    Connect to the HuggingFace Inference API for text embeddings.
    Offloads memory usage to HuggingFace servers (Option B).

    BGE-Small produces 384-dim embeddings.

    Returns:
        LangChain-compatible HuggingFaceEndpointEmbeddings instance.
    """
    logger.info(
        f"[Embedder] Connecting to HuggingFace Inference API for model: "
        f"'{settings.text_embedding_model}'..."
    )

    if not settings.huggingface_token:
        logger.error("[Embedder] Missing HUGGINGFACE_TOKEN.")
        raise ValueError("HUGGINGFACE_TOKEN must be set to use Inference API.")

    try:
        embedder = HuggingFaceEndpointEmbeddings(
            model=settings.text_embedding_model,
            task="feature-extraction",
            huggingfacehub_api_token=settings.huggingface_token,
        )
        
        # Validation ping to ensure the API is reachable
        _ = embedder.embed_query("ping")
        logger.info("[Embedder] HF Inference API connection successful.")
        return embedder
        
    except Exception as exc:
        logger.error(f"[Embedder] Failed to connect to HuggingFace API: {exc}")
        raise RuntimeError("HuggingFace Inference API is unavailable or timing out.") from exc


# ── 2. CLIP Image Embedder ────────────────────────────────────

class CLIPEmbedder:
    """
    Wrapper around OpenCLIP for generating image and text embeddings.

    OpenCLIP (ViT-B/32 pretrained on OpenAI WIT) produces 512-dim
    embeddings that are aligned across modalities, enabling
    cross-modal similarity search between text queries and images.

    Usage:
        embedder = CLIPEmbedder()
        img_vec  = embedder.embed_image(pil_image)
        txt_vec  = embedder.embed_text("flood evacuation map")
    """

    _instance: "CLIPEmbedder | None" = None

    def __new__(cls) -> "CLIPEmbedder":
        """Singleton pattern — model loads once per process."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def _initialize(self) -> None:
        if self._initialized:
            return

        import open_clip

        logger.info(
            f"[CLIPEmbedder] Loading CLIP model: "
            f"'{settings.clip_model_name}' ({settings.clip_pretrained})"
        )

        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            settings.clip_model_name,
            pretrained=settings.clip_pretrained,
        )
        self.model = self.model.to(self.device)
        self.model.eval()

        # Tokenizer for CLIP text encoding
        self.tokenizer = open_clip.get_tokenizer(settings.clip_model_name)

        logger.info("[CLIPEmbedder] CLIP model loaded successfully.")
        self._initialized = True

    # ── Public API ────────────────────────────────────────────

    def embed_image(self, image: Image.Image) -> List[float]:
        """
        Generate a normalized CLIP embedding for a PIL image.

        Args:
            image: PIL.Image (RGB) to embed.

        Returns:
            List of floats (512-dim normalized embedding).
        """
        self._initialize()

        # Preprocess image → tensor (1, 3, H, W)
        img_tensor = self.preprocess(image).unsqueeze(0).to(self.device)

        with torch.no_grad():
            features = self.model.encode_image(img_tensor)
            # L2-normalize for cosine similarity
            features = features / features.norm(dim=-1, keepdim=True)

        return features.squeeze(0).cpu().numpy().tolist()

    def embed_text(self, text: str) -> List[float]:
        """
        Generate a normalized CLIP embedding for a text string.

        This allows text queries to be compared with image embeddings
        in the same vector space.

        Args:
            text: Text string to embed.

        Returns:
            List of floats (512-dim normalized embedding).
        """
        self._initialize()

        tokens = self.tokenizer([text]).to(self.device)

        with torch.no_grad():
            features = self.model.encode_text(tokens)
            features = features / features.norm(dim=-1, keepdim=True)

        return features.squeeze(0).cpu().numpy().tolist()

    def embed_images_batch(
        self, images: list[Image.Image], batch_size: int = 16
    ) -> list[List[float]]:
        """
        Embed a list of images in batches for efficiency.

        Args:
            images:     List of PIL images.
            batch_size: Number of images per GPU/CPU batch.

        Returns:
            List of embedding vectors (one per image).
        """
        self._initialize()
        all_embeddings: list[List[float]] = []

        for i in range(0, len(images), batch_size):
            batch = images[i : i + batch_size]
            tensors = torch.stack(
                [self.preprocess(img) for img in batch]
            ).to(self.device)

            with torch.no_grad():
                features = self.model.encode_image(tensors)
                features = features / features.norm(dim=-1, keepdim=True)

            all_embeddings.extend(features.cpu().numpy().tolist())

        return all_embeddings


@lru_cache(maxsize=1)
def get_clip_embedder() -> CLIPEmbedder:
    """
    Return the singleton CLIPEmbedder instance (cached).
    Prefer this over direct instantiation.
    """
    return CLIPEmbedder()
