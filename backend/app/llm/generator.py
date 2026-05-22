import os
import logging
from typing import List

try:
    from app.utils.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
    _openai_available = True
except ImportError:
    _openai_available = False


class AnswerGenerator:
    """
    Generates grounded, evidence-based medical answers using an LLM.
    Falls back to a mock response when no API key is configured.
    """

    SYSTEM_PROMPT = (
        "You are a highly accurate, evidence-based medical research assistant. "
        "You ONLY answer using information explicitly present in the provided context. "
        "You NEVER fabricate information. When uncertain, say so clearly."
    )

    USER_PROMPT_TEMPLATE = """\
Answer the following medical query using ONLY the provided context below.

Rules:
1. Base your answer strictly on the "MEDICAL EVIDENCE" sections.
2. Use the "KNOWLEDGE GRAPH RELATIONSHIPS" to perform multi-hop reasoning.
3. Explain how the relevant concepts are connected.
4. If the context does not contain sufficient information, explicitly state:
   "I don't have enough information in the provided evidence to answer this query."
5. Do NOT fabricate clinical statistics, drug names, or dosages not mentioned in the context.

Context:
{context}

Query: {query}

Answer:"""

    def __init__(self):
        self.api_key = os.environ.get("OPENAI_API_KEY")
        self.client = None

        if self.api_key and _openai_available:
            try:
                self.client = OpenAI(api_key=self.api_key)
                logger.info("[AnswerGenerator] OpenAI client initialized")
            except Exception as e:
                logger.warning(f"[AnswerGenerator] Failed to initialize OpenAI client: {e}")
        else:
            logger.warning(
                "[AnswerGenerator] OPENAI_API_KEY not found or openai not installed. "
                "Using mock generation."
            )

    def generate_answer(self, query: str, context: str) -> str:
        """
        Generate a grounded answer using the LLM or mock fallback.

        Args:
            query: The user's medical research query
            context: Structured context string from ContextBuilder

        Returns:
            Generated answer string
        """
        if not self.client:
            return self._mock_generation(query, context)

        prompt = self.USER_PROMPT_TEMPLATE.format(context=context, query=query)

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                max_tokens=800
            )
            answer = response.choices[0].message.content.strip()
            logger.info(f"[AnswerGenerator] Generated answer ({len(answer)} chars) via OpenAI")
            return answer
        except Exception as e:
            logger.error(f"[AnswerGenerator] OpenAI generation failed: {e}")
            return f"Error during answer generation: {e}"

    def _mock_generation(self, query: str, context: str) -> str:
        """
        Mock generation for demonstration when OPENAI_API_KEY is absent.
        Uses simple keyword matching to return relevant pre-written answers.
        """
        q = query.lower()

        if ("diabetes" in q or "diabetic" in q) and ("kidney" in q or "renal" in q):
            return (
                "Based on the provided medical evidence, diabetes damages the kidney's "
                "blood vessels — a condition known as diabetic nephropathy. Uncontrolled "
                "hyperglycemia causes progressive glomerular damage, reducing the kidneys' "
                "ability to filter waste products, which can culminate in chronic kidney "
                "disease (CKD) and end-stage renal disease (ESRD).\n\n"
                "According to the knowledge graph relationships: Diabetes → CAUSES → "
                "Kidney Disease, and ACE Inhibitors → TREATS → Kidney Disease by reducing "
                "intraglomerular pressure. Therefore, early glycemic control and antihypertensive "
                "therapy with ACE Inhibitors are key interventions."
            )

        if "diabetes" in q and ("treatment" in q or "treat" in q or "manage" in q):
            return (
                "Based on the provided evidence, diabetes is managed through a combination "
                "of lifestyle modifications and pharmacological interventions including insulin "
                "therapy, metformin, and other glucose-lowering agents. Regular blood glucose "
                "monitoring and HbA1c tracking are essential for long-term management."
            )

        if "hypertension" in q or "blood pressure" in q:
            return (
                "Based on the provided evidence, hypertension (high blood pressure) is a "
                "major risk factor for cardiovascular disease, stroke, and kidney damage. "
                "First-line treatments include lifestyle changes, ACE inhibitors, ARBs, "
                "calcium channel blockers, and thiazide diuretics."
            )

        # Generic fallback
        return (
            "Based on the provided context, I can see relevant medical evidence has been retrieved. "
            "However, to provide a specific answer to your query, please ensure an OpenAI API key "
            "is configured (set OPENAI_API_KEY environment variable) or add relevant medical "
            "documents to the knowledge base via the /upload endpoint.\n\n"
            f"Your query: '{query}'\n\n"
            "Context summary: " + (context[:200] + "..." if len(context) > 200 else context)
        )
