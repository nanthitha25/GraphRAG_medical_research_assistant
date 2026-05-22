"""
app/pipelines/ingestion_pipeline.py
-------------------------------------
End-to-end PDF ingestion pipeline for the GraphRAG Medical Research Assistant.

Workflow
--------
PDF file → load text → chunk → embed → store in ChromaDB
                             ↓
                  entity extraction → store in Neo4j

The pipeline is designed to degrade gracefully:
- Missing Neo4j connection → graph step is skipped, vector step still runs.
- Missing OpenAI key → EntityExtractor returns mock / empty extraction.
"""

import os
import time
import logging
from dataclasses import dataclass, field
from typing import Optional

try:
    from app.utils.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    logger = logging.getLogger(__name__)

from app.ingestion.pdf_loader import load_pdf
from app.ingestion.chunker import split_text_with_metadata
from app.embeddings.embedder import create_embeddings
from app.vectordb.chroma_store import ChromaStore
from app.graph.entity_extractor import EntityExtractor
from app.graph.neo4j_store import Neo4jStore


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class IngestionResult:
    """
    Summary of a completed ingestion run.

    Attributes
    ----------
    filename:
        Basename of the ingested PDF file.
    chunks_indexed:
        Number of text chunks stored in ChromaDB.
    entities_found:
        Total entities extracted across all chunks.
    relationships_found:
        Total relationships extracted across all chunks.
    graph_nodes_created:
        Estimated nodes written to Neo4j (0 if Neo4j unavailable).
    duration_seconds:
        Wall-clock time for the entire ingestion run.
    success:
        *True* if at least the vector-indexing step succeeded.
    error:
        Human-readable error message when *success* is *False*.
    """

    filename: str = ""
    chunks_indexed: int = 0
    entities_found: int = 0
    relationships_found: int = 0
    graph_nodes_created: int = 0
    duration_seconds: float = 0.0
    success: bool = False
    error: Optional[str] = None


# ── Pipeline ──────────────────────────────────────────────────────────────────

class IngestionPipeline:
    """
    Orchestrates the full PDF → vector + graph ingestion workflow.

    Parameters
    ----------
    chroma_store:
        An initialised :class:`~app.vectordb.chroma_store.ChromaStore`.
    neo4j_store:
        An initialised :class:`~app.graph.neo4j_store.Neo4jStore`.
        Graph steps are skipped gracefully if Neo4j is unavailable.
    extractor:
        An initialised :class:`~app.graph.entity_extractor.EntityExtractor`.
    """

    def __init__(
        self,
        chroma_store: ChromaStore,
        neo4j_store: Optional[Neo4jStore] = None,
        extractor: Optional[EntityExtractor] = None,
    ) -> None:
        self.chroma_store = chroma_store
        self.neo4j_store = neo4j_store
        self.extractor = extractor or EntityExtractor()
        logger.info("[IngestionPipeline] Initialised")

    # ── Public API ────────────────────────────────────────────────────────────

    def ingest_pdf(self, file_path: str) -> IngestionResult:
        """
        Ingest a single PDF file into ChromaDB and (optionally) Neo4j.

        Parameters
        ----------
        file_path:
            Absolute or relative path to the PDF file.

        Returns
        -------
        IngestionResult
            Detailed summary of what was processed.
        """
        start = time.time()
        filename = os.path.basename(file_path)
        logger.info("[IngestionPipeline] Starting ingestion for '%s'", filename)

        result = IngestionResult(filename=filename)

        # ── Step 1: Load PDF ──────────────────────────────────────────────────
        try:
            full_text, pdf_metadata = load_pdf(file_path)
        except FileNotFoundError as exc:
            result.error = str(exc)
            result.duration_seconds = round(time.time() - start, 3)
            logger.error("[IngestionPipeline] %s", exc)
            return result
        except Exception as exc:
            result.error = f"PDF load error: {exc}"
            result.duration_seconds = round(time.time() - start, 3)
            logger.error("[IngestionPipeline] PDF load failed: %s", exc)
            return result

        logger.info(
            "[IngestionPipeline] Loaded '%s': %d chars, %d pages",
            filename,
            len(full_text),
            pdf_metadata.get("page_count", 0),
        )

        # ── Step 2: Chunk with metadata ───────────────────────────────────────
        try:
            chunks, chunk_metadatas, chunk_ids = split_text_with_metadata(
                full_text, pdf_metadata
            )
        except Exception as exc:
            result.error = f"Chunking error: {exc}"
            result.duration_seconds = round(time.time() - start, 3)
            logger.error("[IngestionPipeline] Chunking failed: %s", exc)
            return result

        if not chunks:
            result.error = "No text extracted from PDF — file may be empty or image-only"
            result.duration_seconds = round(time.time() - start, 3)
            logger.warning("[IngestionPipeline] %s", result.error)
            return result

        logger.info("[IngestionPipeline] Created %d chunks", len(chunks))

        # ── Step 3: Embed ─────────────────────────────────────────────────────
        try:
            embeddings = create_embeddings(chunks)
        except Exception as exc:
            result.error = f"Embedding error: {exc}"
            result.duration_seconds = round(time.time() - start, 3)
            logger.error("[IngestionPipeline] Embedding failed: %s", exc)
            return result

        # ── Step 4: Store in ChromaDB ─────────────────────────────────────────
        try:
            self.chroma_store.add_chunks(
                chunks=chunks,
                embeddings=embeddings,
                metadatas=chunk_metadatas,  # rich per-chunk metadata
                ids=chunk_ids,              # stable MD5-based IDs
            )
            result.chunks_indexed = len(chunks)
            logger.info(
                "[IngestionPipeline] Indexed %d chunks into ChromaDB", len(chunks)
            )
        except Exception as exc:
            result.error = f"ChromaDB storage error: {exc}"
            result.duration_seconds = round(time.time() - start, 3)
            logger.error("[IngestionPipeline] ChromaDB storage failed: %s", exc)
            return result

        # ── Step 5: Entity extraction + Graph storage ─────────────────────────
        total_entities = 0
        total_relationships = 0
        total_nodes_created = 0

        neo4j_available = (
            self.neo4j_store is not None and self.neo4j_store.verify_connection()
        )
        if not neo4j_available:
            logger.warning(
                "[IngestionPipeline] Neo4j unavailable — skipping graph ingestion"
            )

        # Process every chunk for entity extraction (batch in groups of 10)
        batch_size = 10
        for batch_start in range(0, len(chunks), batch_size):
            batch = chunks[batch_start : batch_start + batch_size]
            batch_text = " ".join(batch)

            try:
                extraction = self.extractor.extract(batch_text)
            except Exception as exc:
                logger.warning(
                    "[IngestionPipeline] Entity extraction failed for batch %d: %s",
                    batch_start // batch_size,
                    exc,
                )
                continue

            entities = extraction.get("entities", [])
            relationships = extraction.get("relationships", [])
            total_entities += len(entities)
            total_relationships += len(relationships)

            if neo4j_available and (entities or relationships):
                try:
                    self.neo4j_store.insert_graph_data(extraction)  # type: ignore[union-attr]
                    total_nodes_created += len(entities)
                except Exception as exc:
                    logger.warning(
                        "[IngestionPipeline] Graph write failed for batch %d: %s",
                        batch_start // batch_size,
                        exc,
                    )

        result.entities_found = total_entities
        result.relationships_found = total_relationships
        result.graph_nodes_created = total_nodes_created
        result.success = True
        result.duration_seconds = round(time.time() - start, 3)

        logger.info(
            "[IngestionPipeline] Completed '%s' in %.3fs — "
            "chunks=%d, entities=%d, relationships=%d, graph_nodes=%d",
            filename,
            result.duration_seconds,
            result.chunks_indexed,
            result.entities_found,
            result.relationships_found,
            result.graph_nodes_created,
        )
        return result
