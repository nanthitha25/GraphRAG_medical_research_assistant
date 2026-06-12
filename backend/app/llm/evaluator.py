import json

from app.llm.client import client
from app.llm.prompts import EVALUATOR_PROMPT

def evaluate_answer(
    query,
    context,
    answer
):

    prompt = f"""
    {EVALUATOR_PROMPT}

    Question:
    {query}

    Retrieved Evidence:
    {context}

    Generated Answer:
    {answer}

    Return ONLY valid JSON.
    """

    response = client.chat.completions.create(
        model="gemini-3.5-flash",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0,
        response_format={ "type": "json_object" }
    )

    content = response.choices[0].message.content

    return json.loads(content)
