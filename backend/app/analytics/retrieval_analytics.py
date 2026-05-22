import json
import os
from collections import defaultdict

try:
    from app.feedback.feedback_store import FEEDBACK_FILE
except ImportError:
    FEEDBACK_FILE = "feedback_log.json"

def calculate_metrics():
    """
    Computes rolling metrics (hallucination rate, failures) from the feedback store.
    """
    if not os.path.exists(FEEDBACK_FILE):
        return {"total_queries": 0, "hallucination_rate": 0.0, "average_confidence": 0.0}
        
    try:
        with open(FEEDBACK_FILE, "r") as f:
            data = json.load(f)
            
        if not data:
            return {"total_queries": 0, "hallucination_rate": 0.0, "average_confidence": 0.0}
            
        total_queries = len(data)
        high_hallucinations = sum(1 for entry in data if entry.get("hallucination_score", 0.0) > 0.4)
        total_confidence = sum(entry.get("confidence", 0.0) for entry in data)
        
        return {
            "total_queries": total_queries,
            "hallucination_rate": round(high_hallucinations / total_queries, 2),
            "average_confidence": round(total_confidence / total_queries, 2)
        }
    except Exception as e:
        print(f"Analytics calculation failed: {e}")
        return {"error": str(e)}
