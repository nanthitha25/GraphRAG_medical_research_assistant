import time
import logging

try:
    from app.utils.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    logger = logging.getLogger(__name__)

from app.retrieval.hybrid_retriever import HybridRetriever
from app.retrieval.context_builder import ContextBuilder
from app.reranker.reranker import Reranker


class RetrievalPipeline:
    """
    Orchestrates the retrieval phase:
    Vector Search → Graph Traversal → Reranking → Context Assembly.
    """

    def __init__(
        self,
        hybrid_retriever: HybridRetriever,
        context_builder: ContextBuilder,
        reranker: Reranker
    ):
        self.hybrid_retriever = hybrid_retriever
        self.context_builder = context_builder
        self.reranker = reranker

    def execute(
        self,
        query: str,
        top_k_semantic: int = 5,
        top_k_rerank: int = 2,
        graph_depth: int = 2
    ) -> dict:
        """
        Execute the full retrieval pipeline.

        Args:
            query: User's medical research query
            top_k_semantic: Number of semantic chunks to retrieve initially
            top_k_rerank: Number of top chunks to keep after reranking
            graph_depth: Depth of graph traversal

        Returns:
            dict with: vector_results, graph_results, combined_context
        """
        logger.info(
            f"[RetrievalPipeline] Starting — query='{query[:60]}', "
            f"top_k_semantic={top_k_semantic}, top_k_rerank={top_k_rerank}, graph_depth={graph_depth}"
        )

        # ── Step 1: Hybrid Retrieval (Vector + Graph) ──────────────────────
        t0 = time.time()
        results = self.hybrid_retriever.retrieve(query, top_k=top_k_semantic, graph_depth=graph_depth)
        hybrid_latency = time.time() - t0
        logger.info(
            f"[HybridRetriever] Done in {hybrid_latency:.3f}s — "
            f"vector_chunks={len(results.get('vector_context', []))}, "
            f"graph_paths={len(results.get('graph_context', []))}"
        )

        # ── Step 2: Reranking Phase ────────────────────────────────────────
        t1 = time.time()
        top_vector_chunks = self.reranker.rerank(
            query,
            results.get("vector_context", []),
            top_k=top_k_rerank
        )
        rerank_latency = time.time() - t1
        results["vector_context"] = top_vector_chunks
        logger.info(
            f"[Reranker] Done in {rerank_latency:.3f}s — "
            f"kept {len(top_vector_chunks)}/{top_k_semantic} chunks after reranking"
        )

        # ── Step 3: Context Assembly ───────────────────────────────────────
        combined_context = self.context_builder.build_context(results)
        context_length = len(combined_context)
        logger.info(f"[ContextBuilder] Built context: {context_length} chars")

        return {
            "vector_results": results.get("vector_context", []),
            "graph_results": results.get("graph_context", []),
            "combined_context": combined_context
        }
