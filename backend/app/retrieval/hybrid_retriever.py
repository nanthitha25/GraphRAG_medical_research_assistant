import time
import logging

try:
    from app.utils.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    logger = logging.getLogger(__name__)

from app.retrieval.retriever import SemanticRetriever
from app.retrieval.graph_retriever import GraphRetriever


class HybridRetriever:
    """
    Orchestrates both Semantic Vector Search and Multi-Hop Graph Reasoning
    from Neo4j to compile a unified evidence context.
    """

    def __init__(self, semantic_retriever: SemanticRetriever, graph_retriever: GraphRetriever):
        self.semantic_retriever = semantic_retriever
        self.graph_retriever = graph_retriever

    def retrieve(self, query: str, top_k: int = 5, graph_depth: int = 2) -> dict:
        """
        Returns a dictionary containing both vector similarity results
        and graph traversal results.

        Args:
            query: User's medical research query
            top_k: Number of semantic chunks to retrieve
            graph_depth: Depth of graph traversal

        Returns:
            dict with keys: vector_context (list[str]), graph_context (list[str])
        """
        # ── 1. Vector Search: "What sounds semantically similar?" ──────────
        t0 = time.time()
        vector_results = self.semantic_retriever.retrieve(query, top_k)
        vector_latency = time.time() - t0
        logger.info(f"[SemanticRetriever] Retrieved {len(vector_results)} chunks in {vector_latency:.3f}s")

        # ── 2. Graph DB: "What is logically connected?" ────────────────────
        # Check if Neo4j is running; gracefully fall back to mock results
        t1 = time.time()
        is_neo4j_running = self.graph_retriever.neo4j_store.verify_connection()
        if is_neo4j_running:
            graph_results = self.graph_retriever.retrieve(query)
            logger.info(f"[GraphRetriever] Retrieved {len(graph_results)} paths from Neo4j in {time.time() - t1:.3f}s")
        else:
            graph_results = self.graph_retriever.get_mock_graph_results(query)
            logger.warning(
                f"[GraphRetriever] Neo4j unavailable — using mock graph results "
                f"({len(graph_results)} paths) in {time.time() - t1:.3f}s"
            )

        return {
            "vector_context": vector_results,
            "graph_context": graph_results
        }
