import os
import json
from dotenv import load_dotenv

load_dotenv()

from app.llm.generator import generate_answer
from app.llm.evaluator import evaluate_answer
from app.llm.confidence import calculate_confidence

def test_pipeline():
    print("Initializing Advanced Self-Evaluating Pipeline...")
    query = "What treats Diabetic Neuropathy?"
    context = "Pregabalin is indicated for the management of neuropathic pain associated with diabetic peripheral neuropathy. Graph Path: (Diabetic Neuropathy)-[TREATED_BY]->(Pregabalin)"

    print(f"\nQuery: {query}")
    print("Generating answer...")
    answer = generate_answer(query, context)
    print(f"Answer: {answer}")

    print("\nEvaluating answer...")
    evaluation = evaluate_answer(query, context, answer)
    print(f"Evaluation: {json.dumps(evaluation, indent=2)}")

    print("\nCalculating confidence...")
    confidence = calculate_confidence(evaluation.get("hallucination_score", 0.0))
    print(f"Confidence: {confidence}")

    print("\nSimulating Self-Healing logic...")
    if evaluation.get("hallucination_score", 0.0) > 0.4:
        print("[Self-Healing] High hallucination score detected! Retrieving more evidence and regenerating...")
    else:
        print("[Self-Healing] Answer is grounded. No self-healing required.")

if __name__ == "__main__":
    test_pipeline()
