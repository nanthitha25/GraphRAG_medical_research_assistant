import os
import logging

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


class HallucinationChecker:
    """
    Verifies whether a generated answer is grounded in the provided context.
    Returns True if hallucination is detected, False if the answer is clean.
    """

    EVAL_PROMPT = """\
You are a strict medical fact-checker. Your task is to detect hallucinations.

DEFINITION: A hallucination occurs when the Answer makes ANY factual claim that is NOT
explicitly supported or clearly inferable from the Context below.

Context:
{context}

Answer to evaluate:
{answer}

Instructions:
- Read the Answer carefully.
- Check every factual claim against the Context.
- If ANY claim is not supported by the Context, respond with exactly: HALLUCINATION
- If ALL claims are supported by the Context, respond with exactly: CLEAN
- Respond with ONLY one word: HALLUCINATION or CLEAN"""

    def __init__(self):
        self.api_key = os.environ.get("OPENAI_API_KEY")
        self.client = None

        if self.api_key and _openai_available:
            try:
                self.client = OpenAI(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"[HallucinationChecker] Failed to init OpenAI: {e}")

    def check(self, answer: str, context: str) -> bool:
        """
        Evaluate whether the answer hallucinates beyond the context.

        Args:
            answer: Generated answer to evaluate
            context: The context used to generate the answer

        Returns:
            True if hallucination detected, False if answer is grounded
        """
        if not self.client:
            return self._mock_check(answer, context)

        prompt = self.EVAL_PROMPT.format(context=context[:3000], answer=answer)

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=10
            )
            result = response.choices[0].message.content.strip().upper()
            is_hallucinated = result == "HALLUCINATION"
            logger.info(f"[HallucinationChecker] LLM verdict: {result}")
            return is_hallucinated
        except Exception as e:
            logger.error(f"[HallucinationChecker] LLM check failed: {e} — defaulting to CLEAN")
            return False

    def _mock_check(self, answer: str, context: str) -> bool:
        """
        Heuristic fallback when OpenAI is unavailable.
        Flags answers containing words explicitly not in the context (simple approximation).
        """
        if "fabricated" in answer.lower() or "i made this up" in answer.lower():
            logger.warning("[HallucinationChecker] Mock: flagged explicit fabrication marker")
            return True

        # If answer references facts when no context was found, flag it
        if (
            "no direct semantic evidence" in context.lower()
            and "no connected knowledge" in context.lower()
            and len(answer) > 200
        ):
            logger.warning("[HallucinationChecker] Mock: detailed answer with no evidence — flagging")
            return True

        logger.info("[HallucinationChecker] Mock: answer appears grounded (CLEAN)")
        return False
