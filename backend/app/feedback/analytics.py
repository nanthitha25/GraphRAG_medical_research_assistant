class Analytics:
    def __init__(self, feedback_store=None):
        self.feedback_store = feedback_store
    def get_total_interactions(self):
        return 0
    def get_summary(self):
        return {
            "total_interactions": 0,
            "hallucination_rate": 0.0,
            "avg_confidence": 0.0,
            "user_satisfaction_rate": 0.0,
            "low_performing_queries": []
        }
