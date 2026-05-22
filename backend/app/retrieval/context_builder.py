import logging
from typing import List

try:
    from app.utils.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    logger = logging.getLogger(__name__)


class ContextBuilder:
    """
    Constructs highly structured, evidence-based LLM context to
    drastically reduce hallucinations by separating semantic evidence
    from knowledge graph relationships.
    """

    def build_context(self, hybrid_results: dict) -> str:
        """
        Builds a structured context string from hybrid retrieval results.

        Args:
            hybrid_results: dict with 'vector_context' and 'graph_context' keys

        Returns:
            A formatted context string ready for LLM prompting
        """
        vector_context = hybrid_results.get("vector_context", [])
        graph_context = hybrid_results.get("graph_context", [])

        lines = ["=" * 60, "MEDICAL EVIDENCE (Semantic Search)", "=" * 60]

        if not vector_context:
            lines.append("• No direct semantic evidence found in the knowledge base.")
        else:
            for i, chunk in enumerate(vector_context, 1):
                # Normalize whitespace for cleaner prompting
                clean_chunk = " ".join(chunk.split())
                lines.append(f"[Evidence {i}] {clean_chunk}")

        lines += ["", "=" * 60, "KNOWLEDGE GRAPH RELATIONSHIPS (Multi-hop Reasoning)", "=" * 60]

        if not graph_context:
            lines.append("• No connected knowledge graph relationships found.")
        else:
            for rel in graph_context:
                lines.append(f"• {rel}")

        context_string = "\n".join(lines)
        logger.info(
            f"[ContextBuilder] Built context with {len(vector_context)} evidence chunks "
            f"and {len(graph_context)} graph relationships ({len(context_string)} chars)"
        )
        return context_string
