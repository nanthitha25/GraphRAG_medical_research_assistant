import statistics
from typing import Dict, Any, List

class Analytics:
    def __init__(self, feedback_store):
        self.feedback_store = feedback_store
    
    def get_summary(self) -> Dict[str, Any]:
        return {
            "total_interactions": self.get_total_interactions(),
            "hallucination_rate": self.get_hallucination_rate(),
            "avg_confidence": self.get_avg_confidence(),
            "user_satisfaction_rate": self.get_user_satisfaction_rate(),
            "low_performing_queries": self.get_low_performing_queries()
        }
    
    def get_hallucination_rate(self) -> float:
        try:
            interactions = self.feedback_store.get_recent_interactions(limit=100)
            if not interactions:
                return 0.0
            hallucinated = [i for i in interactions if i.get("is_hallucinated")]
            return len(hallucinated) / len(interactions)
        except:
            return 0.0
    
    def get_avg_confidence(self) -> float:
        try:
            interactions = self.feedback_store.get_recent_interactions(limit=100)
            if not interactions:
                return 0.0
            scores = [i.get("confidence_score", 0.0) for i in interactions]
            return statistics.mean(scores)
        except:
            return 0.0
    
    def get_low_performing_queries(self, threshold: float = 0.5) -> List[dict]:
        try:
            return self.feedback_store.get_low_confidence_queries(threshold)
        except:
            return []
    
    def get_user_satisfaction_rate(self) -> float:
        try:
            interactions = self.feedback_store.get_recent_interactions(limit=100)
            rated = [i for i in interactions if i.get("user_rating")]
            if not rated:
                return 0.0
            helpful = [i for i in rated if i.get("user_rating") == "helpful"]
            return len(helpful) / len(rated)
        except:
            return 0.0
    
    def get_total_interactions(self) -> int:
        try:
            return len(self.feedback_store.get_recent_interactions(limit=1000))
        except:
            return 0
