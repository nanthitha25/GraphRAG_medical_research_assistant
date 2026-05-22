def format_graph_paths(graph_results):
    """
    Step 5: Explainable Medical Reasoning.
    Converts raw Neo4j paths into readable steps.
    """
    formatted_paths = []
    for path in graph_results:
        # Example naive formatting, actual implementation depends on raw Neo4j output
        formatted_paths.append(f"Reasoning Path: {path}")
    return formatted_paths

def rank_sources(vector_results):
    """
    Step 4: Source Ranking.
    Ranks sources by relevance/trust score.
    """
    # Assuming vector_results are dicts with 'text', 'source', 'score'
    # For now, just format them cleanly
    ranked = []
    for chunk in vector_results:
        if isinstance(chunk, dict):
            ranked.append({"paper": chunk.get("source", "unknown"), "score": chunk.get("score", 0.90)})
        else:
            ranked.append({"paper": "Unknown Context", "score": 0.90})
    return ranked

def build_final_response(
    answer: str,
    confidence: float,
    hallucination_score: float,
    supported: bool,
    vector_results: list,
    graph_results: list,
    retrieval_stats: dict
) -> dict:
    """
    Step 7: Standardize API Response.
    """
    return {
        "answer": answer,
        "confidence": confidence,
        "hallucination_score": hallucination_score,
        "supported": supported,
        "sources": rank_sources(vector_results),
        "graph_paths": format_graph_paths(graph_results),
        "retrieval_stats": retrieval_stats
    }
