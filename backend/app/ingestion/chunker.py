"""
app/ingestion/chunker.py
-------------------------
Text chunking utilities.

Provides:
- ``split_text``               – backward-compatible simple chunker (returns list of strings).
- ``split_text_with_metadata`` – enriched chunker that returns chunks, per-chunk metadata,
                                  and stable hash-based chunk IDs.
"""

import hashlib
import logging
from typing import Dict, Any, List, Tuple

from langchain_text_splitters import RecursiveCharacterTextSplitter

try:
    from app.utils.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    logger = logging.getLogger(__name__)


def split_text(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 100,
) -> List[str]:
    """
    Split *text* into overlapping chunks using a recursive character splitter.

    This function is backward-compatible with the original ``split_text`` API
    and returns only the list of chunk strings.

    Parameters
    ----------
    text : str
        The raw text to split.
    chunk_size : int, optional
        Maximum number of characters per chunk (default 500).
    chunk_overlap : int, optional
        Number of overlapping characters between consecutive chunks (default 100).

    Returns
    -------
    List[str]
        Ordered list of text chunks.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    chunks = splitter.split_text(text)
    logger.debug("split_text produced %d chunks (size=%d, overlap=%d)", len(chunks), chunk_size, chunk_overlap)
    return chunks


def split_text_with_metadata(
    text: str,
    base_metadata: Dict[str, Any],
    chunk_size: int = 500,
    chunk_overlap: int = 100,
) -> Tuple[List[str], List[Dict[str, Any]], List[str]]:
    """
    Split *text* and attach rich per-chunk metadata including a stable chunk ID.

    Each chunk inherits all fields from *base_metadata* and adds:
    - ``chunk_index`` : zero-based position of the chunk within the document.
    - ``chunk_id``    : deterministic 12-character MD5 hex digest prefix of the
                         chunk content, prefixed with ``chunk_``.
    - ``char_start``  : approximate character offset of the chunk's first character
                         in the *original* text (best-effort; accounts for overlaps).

    Parameters
    ----------
    text : str
        The raw text to split.
    base_metadata : dict
        Metadata that applies to the entire document (e.g. ``filename``,
        ``file_path``, ``page_count``, ``ingestion_timestamp``).
    chunk_size : int, optional
        Maximum number of characters per chunk (default 500).
    chunk_overlap : int, optional
        Number of overlapping characters between consecutive chunks (default 100).

    Returns
    -------
    chunks : List[str]
        Ordered list of text chunks.
    metadatas : List[dict]
        Per-chunk metadata dicts aligned with *chunks*.
    chunk_ids : List[str]
        Stable IDs aligned with *chunks*, suitable for use as ChromaDB document IDs.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    chunks: List[str] = splitter.split_text(text)

    metadatas: List[Dict[str, Any]] = []
    chunk_ids: List[str] = []

    # Track approximate character offset through the text.
    search_start = 0

    for i, chunk in enumerate(chunks):
        chunk_id = f"chunk_{hashlib.md5(chunk.encode()).hexdigest()[:12]}"

        # Approximate char_start: find where this chunk appears after the
        # previous chunk's approximate start position.
        char_start = text.find(chunk[:min(50, len(chunk))], search_start)
        if char_start == -1:
            char_start = search_start  # fallback
        # Advance search cursor (minus overlap so next chunk can still be found).
        search_start = max(0, char_start + chunk_size - chunk_overlap)

        meta: Dict[str, Any] = {
            **base_metadata,
            "chunk_index": i,
            "chunk_id": chunk_id,
            "char_start": char_start,
        }
        metadatas.append(meta)
        chunk_ids.append(chunk_id)

    logger.debug(
        "split_text_with_metadata produced %d chunks from '%s'",
        len(chunks),
        base_metadata.get("filename", "<unknown>"),
    )
    return chunks, metadatas, chunk_ids
