import logging
from typing import List

try:
    from app.utils.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    logger = logging.getLogger(__name__)

try:
    from sentence_transformers import SentenceTransformer
    _model = SentenceTransformer("all-MiniLM-L6-v2")
    logger.info("[Embedder] SentenceTransformer 'all-MiniLM-L6-v2' loaded")
except Exception as e:
    _model = None
    logging.getLogger(__name__).warning(f"[Embedder] Could not load SentenceTransformer: {e}")


def create_embeddings(chunks: List[str]) -> List:
    """
    Generate embedding vectors for a list of text chunks.

    Args:
        chunks: List of text strings to embed

    Returns:
        List of embedding vectors (numpy arrays or lists)

    Raises:
        RuntimeError: If no embedding model is available
    """
    if _model is None:
        raise RuntimeError(
            "SentenceTransformer model not available. "
            "Install sentence-transformers: pip install sentence-transformers"
        )
    if not chunks:
        return []

    embeddings = _model.encode(chunks, show_progress_bar=False)
    logger.info(f"[Embedder] Created {len(embeddings)} embeddings of dim {embeddings.shape[1]}")
    return embeddings
