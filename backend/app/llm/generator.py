from app.llm.client import client
from app.llm.prompts import GENERATOR_PROMPT

def generate_answer(query, context):

    prompt = f"""
    {GENERATOR_PROMPT}

    Context:
    {context}

    Question:
    {query}
    """

    response = client.chat.completions.create(
        model="gemini-3.5-flash",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2
    )

    return response.choices[0].message.content
