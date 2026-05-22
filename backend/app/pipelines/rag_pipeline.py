import time
import logging
from typing import Optional

try:
    from app.utils.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    logger = logging.getLogger(__name__)

from app.retrieval.retriever import SemanticRetriever
from app.retrieval.graph_retriever import GraphRetriever
from app.retrieval.hybrid_retriever import HybridRetriever
from app.retrieval.context_builder import ContextBuilder
from app.reranker.reranker import Reranker
from app.llm.generator import AnswerGenerator
from app.evaluation.hallucination_checker import HallucinationChecker
from app.evaluation.confidence_score import ConfidenceScorer
from app.feedback.feedback_store import FeedbackStore
from app.pipelines.retrieval_pipeline import RetrievalPipeline


class RagPipeline:
    """
    The Ultimate AI Workflow Orchestrator with Self-Correction and Adaptive Retrieval.

    Full pipeline:
      Query → Adaptive Config → Hybrid Retrieval → Reranking → Context Building
            → LLM Generation → Hallucination Check → Confidence Scoring
            → Feedback Logging → Response
    """

    def __init__(self, store, neo4j_store, extractor):
        semantic_retriever = SemanticRetriever(store=store)
        graph_retriever = GraphRetriever(neo4j_store=neo4j_store, extractor=extractor)
        hybrid_retriever = HybridRetriever(semantic_retriever, graph_retriever)
        context_builder = ContextBuilder()
        reranker = Reranker()

        self.retrieval_pipeline = RetrievalPipeline(hybrid_retriever, context_builder, reranker)
        self.generator = AnswerGenerator()
        self.hallucination_checker = HallucinationChecker()
        self.confidence_scorer = ConfidenceScorer()
        self.feedback_store = FeedbackStore()

        # Lazy-import adaptive retriever (depends on feedback_store)
        try:
            from app.retrieval.adaptive_retriever import AdaptiveRetriever
            self.adaptive_retriever = AdaptiveRetriever(
                feedback_store=self.feedback_store
            )
        except ImportError:
            self.adaptive_retriever = None

        logger.info("RagPipeline initialized successfully")

    def execute(
        self,
        query: str,
        max_retries: int = 1,
        force_expand: bool = False
    ) -> dict:
        """
        Execute the full self-correcting RAG pipeline.

        Args:
            query: User's medical research query
            max_retries: Number of self-correction attempts on hallucination
            force_expand: Force expanded retrieval depth regardless of confidence

        Returns:
            dict with keys: answer, confidence, confidence_explanation,
                            sources, graph_paths, interaction_id,
                            adapted, adaptation_reason, is_hallucinated
        """
        pipeline_start = time.time()
        logger.info(f"[RagPipeline] Executing query: '{query[:80]}...' " if len(query) > 80 else f"[RagPipeline] Executing query: '{query}'")

        attempts = 0
        is_hallucinated = True
        adapted = False
        adaptation_reason = ""

        # Determine initial retrieval parameters via adaptive retrieval
        if self.adaptive_retriever and not force_expand:
            config = self.adaptive_retriever.get_adaptive_config(query)
            semantic_depth = config.semantic_top_k
            rerank_depth = config.rerank_top_k
            if config.expanded:
                adapted = True
                adaptation_reason = config.expansion_reason
                logger.info(f"[AdaptiveRetriever] Pre-emptive expansion: {adaptation_reason}")
        else:
            semantic_depth = 10 if force_expand else 5
            rerank_depth = 5 if force_expand else 2
            if force_expand:
                adapted = True
                adaptation_reason = "Force-expanded retrieval requested"

        retrieval_data = {}

        while attempts <= max_retries and is_hallucinated:
            attempts += 1
            if attempts > 1:
                logger.warning(
                    f"[RagPipeline] Hallucination detected — Self-Correction Loop attempt {attempts}. "
                    f"Expanding retrieval: semantic_depth={semantic_depth + 3}, rerank_depth={rerank_depth + 2}"
                )
                semantic_depth += 3
                rerank_depth += 2
                adapted = True
                adaptation_reason = f"Hallucination detected on attempt {attempts - 1} — expanded retrieval"

            # ── Step 1: Orchestrated Retrieval ─────────────────────────────
            retrieval_start = time.time()
            retrieval_data = self.retrieval_pipeline.execute(
                query,
                top_k_semantic=semantic_depth,
                top_k_rerank=rerank_depth
            )
            retrieval_latency = time.time() - retrieval_start
            logger.info(
                f"[Retrieval] Completed in {retrieval_latency:.3f}s — "
                f"vector_chunks={len(retrieval_data['vector_results'])}, "
                f"graph_paths={len(retrieval_data['graph_results'])}"
            )

            # ── Step 2: LLM Generation ─────────────────────────────────────
            gen_start = time.time()
            answer = self.generator.generate_answer(query, retrieval_data["combined_context"])
            gen_latency = time.time() - gen_start
            logger.info(f"[Generator] Answer generated in {gen_latency:.3f}s ({len(answer)} chars)")

            # ── Step 3: Hallucination Evaluation ──────────────────────────
            is_hallucinated = self.hallucination_checker.check(
                answer, retrieval_data["combined_context"]
            )
            logger.info(f"[HallucinationChecker] Result: {'HALLUCINATION' if is_hallucinated else 'CLEAN'}")

        # ── Step 4: Confidence Scoring ─────────────────────────────────────
        try:
            detailed = self.confidence_scorer.compute_detailed_score(
                vector_results=retrieval_data.get("vector_results", []),
                graph_results=retrieval_data.get("graph_results", []),
                is_hallucinated=is_hallucinated
            )
            confidence = detailed.score
            confidence_explanation = detailed.explanation
        except AttributeError:
            # Fallback to basic scorer if detailed method not yet available
            confidence = self.confidence_scorer.compute_score(
                vector_results=retrieval_data.get("vector_results", []),
                graph_results=retrieval_data.get("graph_results", []),
                is_hallucinated=is_hallucinated
            )
            confidence_explanation = ""

        logger.info(f"[ConfidenceScorer] Score: {confidence:.3f} — {confidence_explanation}")

        # ── Step 5: Adaptive feedback for next attempt ────────────────────
        if self.adaptive_retriever and confidence < 0.5:
            logger.warning(f"[AdaptiveRetriever] Low confidence ({confidence:.3f}) logged for future adaptation")

        # ── Step 6: Feedback Logging ───────────────────────────────────────
        interaction_id = None
        try:
            interaction_id = self.feedback_store.log_interaction(
                query=query,
                context=retrieval_data.get("combined_context", ""),
                answer=answer,
                is_hallucinated=is_hallucinated,
                confidence_score=confidence
            )
        except Exception as e:
            logger.error(f"[FeedbackStore] Failed to log interaction: {e}")

        total_latency = time.time() - pipeline_start
        logger.info(
            f"[RagPipeline] Complete in {total_latency:.3f}s — "
            f"confidence={confidence:.3f}, hallucinated={is_hallucinated}, "
            f"interaction_id={interaction_id}"
        )

        return {
            "answer": answer,
            "confidence": confidence,
            "confidence_explanation": confidence_explanation,
            "sources": retrieval_data.get("vector_results", []),
            "graph_paths": retrieval_data.get("graph_results", []),
            "interaction_id": interaction_id,
            "adapted": adapted,
            "adaptation_reason": adaptation_reason,
            "is_hallucinated": is_hallucinated,
            "latency_seconds": round(total_latency, 3)
        }
