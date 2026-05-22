"""
app/vectordb/chroma_store.py

Persistent ChromaDB wrapper for storing and retrieving medical research
text chunks together with their vector embeddings and metadata.
"""

import os
import logging

import chromadb

try:
    from app.utils.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    logger = logging.getLogger(__name__)


class ChromaStore:
    """Manages a persistent ChromaDB collection for medical research chunks."""

    def __init__(
        self,
        path: str = "data/chroma",
        collection_name: str = "medical_research",
    ) -> None:
        """
        Initialise the ChromaDB persistent client and get-or-create the
        target collection.

        Args:
            path: Directory path where ChromaDB persists its data.
            collection_name: Name of the ChromaDB collection to use.
        """
        self.path = path
        self.collection_name = collection_name

        # Ensure the parent directory exists (handles both relative and absolute paths)
        parent = os.path.dirname(self.path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        logger.info(
            "Initialising ChromaStore at '%s' with collection '%s'.",
            self.path,
            self.collection_name,
        )

        self.client = chromadb.PersistentClient(path=self.path)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name
        )

        logger.info(
            "ChromaStore ready — collection '%s' contains %d document(s).",
            self.collection_name,
            self.collection.count(),
        )

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def add_chunks(
        self,
        chunks: list[str],
        embeddings,
        metadatas: list[dict] | None = None,
        ids: list[str] | None = None,
    ) -> None:
        """
        Add text chunks and their embeddings to the ChromaDB collection.

        Args:
            chunks: List of raw text strings.
            embeddings: List or numpy array of embedding vectors.
            metadatas: Optional list of metadata dicts (one per chunk).
                       Defaults to ``[{"source": "unknown"}]`` per chunk.
            ids: Optional list of unique string IDs.
                 Auto-generated from position + hash when not supplied.
        """
        if not chunks:
            logger.warning("add_chunks called with an empty chunk list — nothing added.")
            return

        if ids is None:
            ids = [f"chunk_{i}_{hash(chunk)}" for i, chunk in enumerate(chunks)]

        if metadatas is None:
            metadatas = [{"source": "unknown"} for _ in chunks]

        # Normalise embeddings to plain Python lists for ChromaDB compatibility
        embeddings_list = [
            emb.tolist() if hasattr(emb, "tolist") else list(emb)
            for emb in embeddings
        ]

        try:
            self.collection.add(
                documents=chunks,
                embeddings=embeddings_list,
                metadatas=metadatas,
                ids=ids,
            )
            logger.info("Added %d chunk(s) to collection '%s'.", len(chunks), self.collection_name)
        except Exception as exc:
            logger.error(
                "Failed to add chunks to ChromaDB collection '%s': %s",
                self.collection_name,
                exc,
                exc_info=True,
            )

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def query(self, query_embedding, n_results: int = 5) -> dict:
        """
        Query the collection with a vector embedding and return the raw
        ChromaDB result dict (documents, ids, distances, metadatas).

        Args:
            query_embedding: A single embedding vector (list or numpy array).
            n_results: Number of nearest neighbours to retrieve.

        Returns:
            Raw ChromaDB result dict, or an empty dict on error.
        """
        if hasattr(query_embedding, "tolist"):
            query_embedding = query_embedding.tolist()
        elif not isinstance(query_embedding, list):
            query_embedding = list(query_embedding)

        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
            )
            logger.debug("query() returned %d result(s).", len(results.get("ids", [[]])[0]))
            return results
        except Exception as exc:
            logger.error("ChromaDB query failed: %s", exc, exc_info=True)
            return {}

    def query_with_metadata(self, query_embedding, n_results: int = 5) -> dict:
        """
        Query the collection and return documents **and** their associated
        metadata together — useful for source tracing.

        Returns a dict with keys:
            - ``documents``: list[str]
            - ``metadatas``: list[dict]
            - ``ids``:       list[str]
            - ``distances``: list[float]

        Args:
            query_embedding: A single embedding vector (list or numpy array).
            n_results: Number of nearest neighbours to retrieve.

        Returns:
            Flat dict of lists, or a dict with empty lists on error.
        """
        empty: dict = {"documents": [], "metadatas": [], "ids": [], "distances": []}

        if hasattr(query_embedding, "tolist"):
            query_embedding = query_embedding.tolist()
        elif not isinstance(query_embedding, list):
            query_embedding = list(query_embedding)

        try:
            raw = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            logger.error("query_with_metadata failed: %s", exc, exc_info=True)
            return empty

        # ChromaDB wraps results in an extra list dimension — flatten it
        docs = (raw.get("documents") or [[]])[0]
        metas = (raw.get("metadatas") or [[]])[0]
        ids_ = (raw.get("ids") or [[]])[0]
        dists = (raw.get("distances") or [[]])[0]

        logger.debug(
            "query_with_metadata() returned %d result(s) from collection '%s'.",
            len(docs),
            self.collection_name,
        )
        return {
            "documents": docs,
            "metadatas": metas,
            "ids": ids_,
            "distances": dists,
        }

    # ------------------------------------------------------------------
    # Introspection helpers
    # ------------------------------------------------------------------

    def count(self) -> int:
        """
        Return the total number of chunks stored in the collection.

        Returns:
            Integer count, or 0 on error.
        """
        try:
            total = self.collection.count()
            logger.debug("Collection '%s' contains %d document(s).", self.collection_name, total)
            return total
        except Exception as exc:
            logger.error("count() failed: %s", exc, exc_info=True)
            return 0

    def get_chunk_by_id(self, chunk_id: str) -> dict | None:
        """
        Retrieve a specific chunk and its metadata by its ChromaDB ID.

        Args:
            chunk_id: The string ID previously used when the chunk was added.

        Returns:
            Dict with keys ``id``, ``document``, and ``metadata``,
            or ``None`` if the chunk is not found or an error occurs.
        """
        try:
            result = self.collection.get(
                ids=[chunk_id],
                include=["documents", "metadatas"],
            )
        except Exception as exc:
            logger.error(
                "get_chunk_by_id('%s') failed: %s", chunk_id, exc, exc_info=True
            )
            return None

        ids_ = result.get("ids", [])
        docs = result.get("documents", [])
        metas = result.get("metadatas", [])

        if not ids_:
            logger.warning("get_chunk_by_id('%s'): chunk not found.", chunk_id)
            return None

        logger.debug("get_chunk_by_id('%s'): found chunk.", chunk_id)
        return {
            "id": ids_[0],
            "document": docs[0] if docs else None,
            "metadata": metas[0] if metas else {},
        }
