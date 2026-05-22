import json
import os
import uuid
from datetime import datetime

FEEDBACK_FILE = "feedback_log.json"

def store_feedback(query, answer, confidence, hallucination_score, feedback="none"):
    """
    Logs every interaction for long-term learning and retrieval analytics.
    """
    entry = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat(),
        "query": query,
        "answer": answer,
        "confidence": confidence,
        "hallucination_score": hallucination_score,
        "feedback": feedback
    }

    try:
        data = []
        if os.path.exists(FEEDBACK_FILE):
            with open(FEEDBACK_FILE, "r") as f:
                data = json.load(f)
                
        data.append(entry)
        
        with open(FEEDBACK_FILE, "w") as f:
            json.dump(data, f, indent=2)
            
        return entry["id"]
    except Exception as e:
        print(f"Failed to store feedback: {e}")
        return None

class FeedbackStore:
    def __init__(self):
        pass
    def update_rating(self, interaction_id, rating):
        return True
    def get_recent_interactions(self, limit):
        return []
