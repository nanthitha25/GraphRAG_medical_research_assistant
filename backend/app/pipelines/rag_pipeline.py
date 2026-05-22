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
from app.pipelines.retrieval_pipeline import RetrievalPipeline

# NEW LLM FUNCTIONS
from app.llm.generator import generate_answer
from app.llm.evaluator import evaluate_answer
from app.llm.confidence import calculate_confidence

# NEW SELF-IMPROVING MODULES
from app.retrieval.adaptive_retriever import AdaptiveRetriever
from app.feedback.feedback_store import store_feedback
from app.analytics.retrieval_analytics import calculate_metrics
from app.utils.response_builder import build_final_response


class RagPipeline:
    """
    Two-LLM Self-Evaluating, Self-Improving GraphRAG Architecture.
    """

    def __init__(self, store, neo4j_store, extractor):
        semantic_retriever = SemanticRetriever(store=store)
        graph_retriever = GraphRetriever(neo4j_store=neo4j_store, extractor=extractor)
        hybrid_retriever = HybridRetriever(semantic_retriever, graph_retriever)
        context_builder = ContextBuilder()
        reranker = Reranker()

        self.retrieval_pipeline = RetrievalPipeline(hybrid_retriever, context_builder, reranker)
        self.adaptive_retriever = AdaptiveRetriever(self.retrieval_pipeline)
        
        logger.info("RagPipeline initialized successfully")

    def execute(self, query: str) -> dict:
        """
        FINAL COMPLETE FLOW:
        Hybrid Retrieval -> Generator LLM -> Evaluator LLM -> Confidence Score 
        -> Adaptive Retrieval (if needed) -> Regenerate -> Final Explainable Response
        """
        logger.info(f"[RagPipeline] Executing query: '{query}'")
        
        # Track retrieval stats
        t0 = time.time()
        
        # ── Step 1: Initial Retrieval ─────────────────────────────
        retrieval_data = self.retrieval_pipeline.execute(
            query,
            top_k_semantic=5,
            top_k_rerank=2
        )
        context = retrieval_data["combined_context"]

        # ── Step 2: LLM Generation ─────────────────────────────────────
        try:
            answer = generate_answer(query, context)
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            answer = f"Error generating answer: {e}"

        # ── Step 3: Hallucination Evaluation ──────────────────────────
        try:
            evaluation = evaluate_answer(query, context, answer)
        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            evaluation = {"hallucination_score": 1.0, "supported": False, "reasoning": "Evaluator crashed."}
        
        # ── Step 4 & 6: Adaptive Retry Pipeline ─────────────────────────
        if evaluation.get("hallucination_score", 0.0) > 0.4:
            logger.warning("[Self-Healing] High hallucination score. Triggering Adaptive Retrieval.")
            
            # Log the failure before retrying
            store_feedback(query, answer, 0.0, evaluation.get("hallucination_score", 1.0), "failed")
            
            # Use AdaptiveRetriever to expand query and get new context
            retrieval_data = self.adaptive_retriever.retrieve_with_strategies(query)
            context = retrieval_data["combined_context"]
            
            # Regenerate answer
            try:
                answer = generate_answer(query, context)
            except Exception as e:
                logger.error(f"Regeneration failed: {e}")
                answer = f"Error generating answer: {e}"
            
            # Re-evaluate
            try:
                evaluation = evaluate_answer(query, context, answer)
            except Exception as e:
                logger.error(f"Re-Evaluation failed: {e}")
                evaluation = {"hallucination_score": 1.0, "supported": False, "reasoning": "Evaluator crashed."}
            
        # ── Step 5: Confidence Scoring ─────────────────────────────────────
        confidence = calculate_confidence(evaluation.get("hallucination_score", 0.0))
        
        # Log final interaction for analytics
        store_feedback(query, answer, confidence, evaluation.get("hallucination_score", 0.0), "success" if confidence > 0.6 else "weak")
        
        # ── Step 7: Build Final Response ───────────────────────────────────
        retrieval_stats = {
            "latency": round(time.time() - t0, 3),
            "analytics_summary": calculate_metrics()
        }
        
        return build_final_response(
            answer=answer,
            confidence=confidence,
            hallucination_score=evaluation.get("hallucination_score", 0.0),
            supported=evaluation.get("supported", True),
            vector_results=retrieval_data.get("vector_results", []),
            graph_results=retrieval_data.get("graph_results", []),
            retrieval_stats=retrieval_stats
        )
