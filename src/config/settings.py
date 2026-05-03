# ============================================================
# src/config/settings.py
# Centralized configuration using Pydantic BaseSettings.
# All paths, model names, and hyperparameters live here.
# ============================================================

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load .env from project root (two levels up from this file)
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

# ── Resolve project root once ────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """
    All application settings, sourced from environment variables
    or sensible defaults. Import the singleton `settings` object
    instead of this class directly.
    """

    # ── API Keys ─────────────────────────────────────────────
    groq_api_key: str = Field(default="", env="GROQ_API_KEY")
    huggingface_token: str = Field(default="", env="HUGGINGFACE_TOKEN")

    # ── FastAPI / CORS ────────────────────────────────────────
    # Comma-separated list of allowed origins for CORS.
    # Use "*" for development. In production set to your exact
    # Lovable domain: "https://your-app.lovable.app"
    allowed_origins: str = Field(default="*", env="ALLOWED_ORIGINS")
    # Optional API key to protect the backend from public access.
    # If set, frontend must send: Authorization: Bearer <key>
    api_secret_key: str = Field(default="", env="API_SECRET_KEY")
    # FastAPI server settings
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")

    # ── Application ──────────────────────────────────────────
    app_env: str = Field(default="development", env="APP_ENV")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # ── Directory Paths ──────────────────────────────────────
    data_raw_dir: Path = PROJECT_ROOT / "data" / "raw"
    data_processed_dir: Path = PROJECT_ROOT / "data" / "processed"
    vectorstore_dir: Path = PROJECT_ROOT / "vectorstore" / "chroma"

    # ── Embedding Models ─────────────────────────────────────
    # Primary text embedding model (HuggingFace BGE-Small to fit in memory)
    text_embedding_model: str = "BAAI/bge-small-en-v1.5"
    # Embedding dimension for BGE-Small
    text_embedding_dim: int = 384

    # CLIP model for multimodal (image + text) embeddings
    clip_model_name: str = "ViT-B-32"
    clip_pretrained: str = "openai"
    # CLIP embedding dimension (ViT-B/32 → 512)
    clip_embedding_dim: int = 512

    # ── LLM (Groq / LLaMA 3.3) ──────────────────────────────
    llm_model_name: str = "llama-3.3-70b-versatile"
    llm_temperature: float = 0.2          # Low temp for factual grounding
    llm_max_tokens: int = 2048

    # ── ChromaDB ─────────────────────────────────────────────
    chroma_text_collection: str = "climate_text_chunks"
    chroma_image_collection: str = "climate_image_chunks"

    # ── Ingestion / Chunking ─────────────────────────────────
    chunk_size: int = 512                 # tokens per chunk
    chunk_overlap: int = 128              # token overlap between chunks

    # ── Retrieval ────────────────────────────────────────────
    retrieval_top_k: int = 15            # documents to retrieve
    rerank_top_n: int = 3               # documents after reranking

    # ── Hazard Types (for metadata filtering) ────────────────
    supported_hazards: list = [
        "flood",
        "cyclone",
        "heatwave",
        "earthquake",
        "drought",
        "general",
    ]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Allow extra fields from environment without error
        extra = "ignore"

    def ensure_dirs(self) -> None:
        """Create required directories if they do not exist."""
        for d in [
            self.data_raw_dir,
            self.data_processed_dir,
            self.vectorstore_dir,
        ]:
            d.mkdir(parents=True, exist_ok=True)


# ── Singleton ─────────────────────────────────────────────────
# Import this object everywhere instead of instantiating Settings()
settings = Settings()
settings.ensure_dirs()
