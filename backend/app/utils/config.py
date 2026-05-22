"""
app/utils/config.py
-------------------
Centralized application configuration using python-dotenv and dataclasses.

Values are read from environment variables (populated from a ``.env`` file
in the backend root directory) with sensible defaults so the server can
start cleanly even without a ``.env`` file present.

Usage
-----
    from app.utils.config import get_config
    cfg = get_config()
    print(cfg.neo4j_uri)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# Resolve the backend root: app/utils/config.py → app/utils/ → app/ → backend/
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _BACKEND_ROOT / ".env"

# Load .env from the backend root (silently ignored if the file is absent).
load_dotenv(dotenv_path=_ENV_FILE, override=False)


@dataclass(frozen=True)
class Settings:
    """Immutable application settings resolved from environment variables.

    All path-like settings are stored as plain strings so they can be used
    directly with libraries that do not accept :class:`pathlib.Path` objects.
    """

    # ------------------------------------------------------------------ #
    # LLM / OpenAI
    # ------------------------------------------------------------------ #
    openai_api_key: str = field(default="")

    # ------------------------------------------------------------------ #
    # Neo4j Graph Database
    # ------------------------------------------------------------------ #
    neo4j_uri: str = field(default="bolt://localhost:7687")
    neo4j_user: str = field(default="neo4j")
    neo4j_password: str = field(default="password")

    # ------------------------------------------------------------------ #
    # ChromaDB Vector Store
    # ------------------------------------------------------------------ #
    chroma_path: str = field(default="data/chroma")
    chroma_collection: str = field(default="medical_research")

    # ------------------------------------------------------------------ #
    # Feedback / SQLite
    # ------------------------------------------------------------------ #
    feedback_db_path: str = field(default="data/feedback.db")

    # ------------------------------------------------------------------ #
    # Logging
    # ------------------------------------------------------------------ #
    log_level: str = field(default="INFO")
    log_file: str = field(default="logs/graphrag.log")

    # ------------------------------------------------------------------ #
    # Retrieval
    # ------------------------------------------------------------------ #
    max_retrieval_top_k: int = field(default=10)
    min_confidence_threshold: float = field(default=0.5)

    # ------------------------------------------------------------------ #
    # Legacy / additional fields kept for backwards compatibility
    # ------------------------------------------------------------------ #
    upload_dir: str = field(default="data/uploads")
    api_version: str = field(default="2.0.0")
    cors_origins: list = field(default_factory=lambda: ["*"])


@lru_cache(maxsize=1)
def get_config() -> Settings:
    """Return the singleton :class:`Settings` instance.

    The instance is built once from environment variables (which are
    themselves populated by the :func:`load_dotenv` call at module import
    time) and then cached for the lifetime of the process.

    Note
    ----
    ``OPENAI_API_KEY`` is **not** validated here so that the rest of the
    application can boot and surface a more targeted error at the call
    site that actually needs the key.

    Returns
    -------
    Settings
        Frozen dataclass holding all application configuration values.
    """
    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
        neo4j_password=os.getenv("NEO4J_PASSWORD", "password"),
        chroma_path=os.getenv("CHROMA_PATH", "data/chroma"),
        chroma_collection=os.getenv("CHROMA_COLLECTION", "medical_research"),
        feedback_db_path=os.getenv("FEEDBACK_DB_PATH", "data/feedback.db"),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        log_file=os.getenv("LOG_FILE", "logs/graphrag.log"),
        max_retrieval_top_k=int(os.getenv("MAX_RETRIEVAL_TOP_K", "10")),
        min_confidence_threshold=float(os.getenv("MIN_CONFIDENCE_THRESHOLD", "0.5")),
        upload_dir=os.getenv("UPLOAD_DIR", "data/uploads"),
        api_version=os.getenv("API_VERSION", "2.0.0"),
    )
