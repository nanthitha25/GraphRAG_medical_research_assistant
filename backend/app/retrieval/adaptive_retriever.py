from dataclasses import dataclass
from typing import Optional

@dataclass  
class AdaptiveConfig:
    semantic_top_k: int = 5
    rerank_top_k: int = 3
    graph_depth: int = 2
    expanded: bool = False
    expansion_reason: str = ""

class AdaptiveRetriever:
    def __init__(self, feedback_store, min_confidence: float = 0.5):
        self.feedback_store = feedback_store
        self.min_confidence = min_confidence
    
    def get_adaptive_config(self, query: str, previous_confidence: Optional[float] = None) -> AdaptiveConfig:
        config = AdaptiveConfig()
        
        if previous_confidence is not None and previous_confidence < self.min_confidence:
            config.semantic_top_k = 10
            config.rerank_top_k = 5
            config.graph_depth = 3
            config.expanded = True
            config.expansion_reason = f"Low confidence ({previous_confidence:.2f}) — expanded retrieval depth"
        
        try:
            past_low = self.feedback_store.get_low_confidence_queries(threshold=self.min_confidence)
            query_words = set(query.lower().split())
            for past in past_low[:5]:
                past_words = set(past.get('query', '').lower().split())
                overlap = len(query_words & past_words) / max(len(query_words), 1)
                if overlap > 0.5 and not config.expanded:
                    config.semantic_top_k = 8
                    config.rerank_top_k = 4
                    config.graph_depth = 3
                    config.expanded = True
                    config.expansion_reason = "Similar past query had low confidence — pre-emptively expanded"
                    break
        except Exception:
            pass
        
        return config
