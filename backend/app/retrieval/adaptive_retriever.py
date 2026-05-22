import logging
from typing import Dict, Any

from app.llm.client import client

try:
    from app.utils.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    logger = logging.getLogger(__name__)


def expand_query(query: str) -> str:
    """
    Strategy 3: Query Expansion.
    Uses a fast LLM call to append medical synonyms and broader context.
    """
    prompt = f"""
    You are a medical search expert.
    Rewrite the following query to include medical synonyms, related clinical terms, and broader disease categories to improve vector search retrieval.
    Do NOT answer the query. Only return the expanded search string.

    Original Query: {query}
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        expanded = response.choices[0].message.content.strip()
        logger.info(f"[AdaptiveRetrieval] Query Expanded: '{query}' -> '{expanded}'")
        return expanded
    except Exception as e:
        logger.warning(f"[AdaptiveRetrieval] Query expansion failed: {e}")
        return query


class AdaptiveRetriever:
    """
    Intercepts failed retrievals (high hallucination score) and applies
    dynamic strategies to improve evidence gathering.
    """
    
    def __init__(self, retrieval_pipeline):
        self.retrieval_pipeline = retrieval_pipeline

    def retrieve_with_strategies(self, query: str) -> Dict[str, Any]:
        """
        Strategy 1 & 2: Increase Retrieval Count & Graph Depth
        """
        logger.info("[AdaptiveRetrieval] Triggering adaptive strategies (Increased depth, expanded query)")
        
        # Strategy 3: Query Expansion
        expanded_query = expand_query(query)

        # Execute retrieval with aggressively scaled parameters
        # (Assuming the retrieval_pipeline accepts these kwargs or we just hardcode the bump)
        retrieval_data = self.retrieval_pipeline.execute(
            expanded_query,
            top_k_semantic=10,  # Strategy 1: Increase Count (was 5)
            top_k_rerank=5,     # Increased rerank count
            graph_depth=3       # Strategy 2: Expand graph depth (was 2)
        )
        
        return retrieval_data
