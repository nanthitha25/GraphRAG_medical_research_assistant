from dataclasses import dataclass
from typing import List

@dataclass
class ConfidenceResult:
    score: float              # 0.0 to 1.0
    explanation: str          # human-readable breakdown
    vector_contribution: float
    graph_contribution: float
    hallucination_penalty: float

class ConfidenceScorer:
    """
    Computes a confidence score based on the volume of evidence and hallucination checks.
    """
    def compute_score(self, vector_results: list, graph_results: list, is_hallucinated: bool) -> float:
        score = 0.0
        
        # 1. Base score from vector semantic matches
        if len(vector_results) > 0:
            score += 0.4
        
        # 2. Boost score if graph relationships back it up (multi-hop reasoning successful)
        if len(graph_results) > 0:
            score += 0.4
            
        # 3. Penalize heavily if hallucination checker flagged it
        if is_hallucinated:
            score -= 0.6
        else:
            score += 0.2
            
        # Normalize to 0-1
        score = max(0.0, min(1.0, score))
        return score
    
    def compute_detailed_score(self, vector_results: list, graph_results: list, is_hallucinated: bool, rerank_scores: list = None) -> ConfidenceResult:
        vector_contribution = min(len(vector_results) * 0.10, 0.40)
        graph_contribution = min(len(graph_results) * 0.15, 0.30)
        
        hallucination_penalty = 0.0
        if is_hallucinated:
            hallucination_penalty = -0.50
        else:
            hallucination_penalty = 0.20
            
        rerank_bonus = 0.0
        if rerank_scores and sum(rerank_scores)/len(rerank_scores) > 5.0:
            rerank_bonus = 0.10
            
        score = vector_contribution + graph_contribution + hallucination_penalty + rerank_bonus
        score = max(0.0, min(1.0, score))
        
        explanation = f"Vector Evidence: {vector_contribution:.2f}, Graph Evidence: {graph_contribution:.2f}, Hallucination Penalty: {hallucination_penalty:.2f}, Rerank Bonus: {rerank_bonus:.2f}"
        
        return ConfidenceResult(
            score=score,
            explanation=explanation,
            vector_contribution=vector_contribution,
            graph_contribution=graph_contribution,
            hallucination_penalty=hallucination_penalty
        )
