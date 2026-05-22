from dataclasses import dataclass
from typing import List, Optional

@dataclass
class EvaluationResult:
    is_hallucinated: bool
    confidence: float
    confidence_explanation: str
    evidence_coverage: float  # 0-1: fraction of answer concepts found in context
    answer_length: int
    context_length: int
    evaluation_method: str    # "llm" or "mock"

class Evaluator:
    def __init__(self):
        try:
            from app.evaluation.hallucination_checker import HallucinationChecker
            from app.evaluation.confidence_score import ConfidenceScorer
            self.hallucination_checker = HallucinationChecker()
            self.confidence_scorer = ConfidenceScorer()
        except ImportError:
            pass

    def evaluate(self, query: str, answer: str, context: str, 
                 vector_results: list, graph_results: list) -> EvaluationResult:
        is_hallucinated = self.hallucination_checker.check(answer, context)
        confidence_result = self.confidence_scorer.compute_detailed_score(vector_results, graph_results, is_hallucinated)
        
        answer_words = set([word.lower() for word in answer.split() if len(word) > 3])
        context_words = set([word.lower() for word in context.split() if len(word) > 3])
        
        overlap = len(answer_words.intersection(context_words))
        evidence_coverage = overlap / max(len(answer_words), 1)
        
        return EvaluationResult(
            is_hallucinated=is_hallucinated,
            confidence=confidence_result.score,
            confidence_explanation=confidence_result.explanation,
            evidence_coverage=evidence_coverage,
            answer_length=len(answer),
            context_length=len(context),
            evaluation_method="llm" if self.hallucination_checker.client else "mock"
        )
