"""
app/ingestion/pdf_loader.py
----------------------------
PDF loading utilities that return both extracted text and structured metadata.
Provides a full-document loader and a page-level generator for fine-grained
ingestion workflows.
"""

import os
import logging
from datetime import datetime, timezone
from typing import Tuple, Dict, Any, Generator

from pypdf import PdfReader

try:
    from app.utils.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    logger = logging.getLogger(__name__)


def load_pdf(file_path: str) -> Tuple[str, Dict[str, Any]]:
    """
    Load a PDF file and return its full text together with document-level metadata.

    Parameters
    ----------
    file_path : str
        Absolute or relative path to the PDF file.

    Returns
    -------
    full_text : str
        Concatenated text from every page (pages separated by newlines).
    metadata : dict
        Dictionary containing:
        - ``filename``           : basename of the file
        - ``file_path``          : resolved path string
        - ``page_count``         : total number of pages
        - ``ingestion_timestamp``: UTC ISO-8601 timestamp of when the file was loaded

    Raises
    ------
    FileNotFoundError
        If *file_path* does not point to an existing file.
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"PDF not found: {file_path}")

    reader = PdfReader(file_path)

    pages_text = []
    for page_num, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        pages_text.append(text)

    full_text = "\n".join(pages_text)

    metadata: Dict[str, Any] = {
        "filename": os.path.basename(file_path),
        "file_path": str(file_path),
        "page_count": len(reader.pages),
        "ingestion_timestamp": datetime.now(timezone.utc).isoformat(),
    }

    logger.debug(
        "Loaded PDF '%s': %d pages, %d characters",
        metadata["filename"],
        metadata["page_count"],
        len(full_text),
    )

    return full_text, metadata


def load_pdf_pages(
    file_path: str,
) -> Generator[Tuple[str, Dict[str, Any]], None, None]:
    """
    Generator that yields ``(page_text, page_metadata)`` for each page in the PDF.

    This is useful when you want to process large documents page-by-page without
    loading the entire text into memory at once.

    Parameters
    ----------
    file_path : str
        Absolute or relative path to the PDF file.

    Yields
    ------
    page_text : str
        Extracted text for the current page (empty string if extraction fails).
    page_metadata : dict
        Dictionary containing:
        - ``filename``           : basename of the file
        - ``file_path``          : resolved path string
        - ``page_number``        : 1-based page index
        - ``ingestion_timestamp``: UTC ISO-8601 timestamp (per-page snapshot)

    Raises
    ------
    FileNotFoundError
        If *file_path* does not point to an existing file.
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"PDF not found: {file_path}")

    reader = PdfReader(file_path)
    filename = os.path.basename(file_path)

    for page_num, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        page_metadata: Dict[str, Any] = {
            "filename": filename,
            "file_path": str(file_path),
            "page_number": page_num + 1,
            "ingestion_timestamp": datetime.now(timezone.utc).isoformat(),
        }
        yield text, page_metadata
