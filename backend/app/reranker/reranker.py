import logging
from typing import List

try:
    from app.utils.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    logger = logging.getLogger(__name__)


class Reranker:
    """
    Reranks retrieved chunks by true semantic relevance to the query
    using a CrossEncoder model. Falls back to naive ordering if the
    model is unavailable.
    """

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model = None
        self.model_name = model_name
        try:
            from sentence_transformers import CrossEncoder
            self.model = CrossEncoder(model_name)
            logger.info(f"[Reranker] CrossEncoder '{model_name}' loaded successfully")
        except Exception as e:
            logger.warning(
                f"[Reranker] Could not load CrossEncoder model '{model_name}': {e}. "
                "Falling back to naive ordering."
            )

    def rerank(self, query: str, context_chunks: List[str], top_k: int = 3) -> List[str]:
        """
        Reranks chunks by relevance to the query.

        Args:
            query: The user query
            context_chunks: Retrieved text chunks
            top_k: Number of top chunks to return

        Returns:
            Top-k chunks sorted by relevance (highest first)
        """
        if not context_chunks:
            return []

        # If CrossEncoder model unavailable, return first top_k chunks
        if self.model is None:
            logger.warning("[Reranker] No model available — returning first top_k chunks without reranking")
            return context_chunks[:top_k]

        try:
            # Create (query, chunk) pairs for the cross-encoder
            sentence_combinations = [[query, chunk] for chunk in context_chunks]

            # Score all pairs
            scores = self.model.predict(sentence_combinations)

            # Sort by score descending and return top_k
            scored_chunks = sorted(
                zip(scores, context_chunks),
                key=lambda x: x[0],
                reverse=True
            )

            top_chunks = [chunk for score, chunk in scored_chunks[:top_k]]
            top_scores = [float(score) for score, chunk in scored_chunks[:top_k]]

            logger.info(
                f"[Reranker] Reranked {len(context_chunks)} chunks → top {len(top_chunks)} | "
                f"top scores: {[f'{s:.2f}' for s in top_scores]}"
            )
            return top_chunks

        except Exception as e:
            logger.error(f"[Reranker] Reranking failed: {e} — falling back to naive ordering")
            return context_chunks[:top_k]
