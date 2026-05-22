def calculate_confidence(
    hallucination_score
):

    confidence = 1 - hallucination_score

    return round(confidence, 2)
