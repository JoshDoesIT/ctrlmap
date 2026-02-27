"""ctrlmap: PyMuPDF ingestion and semantic chunking modules.

Public API:
    extract_text_blocks: Extract layout-aware text blocks from PDFs.
    detect_layout: Detect single-column, dual-column, or table layouts.
    classify_block: Classify blocks as header, footer, or body.
    order_blocks_by_columns: Reorder blocks for column-aware reading.
    chunk_document: Full extraction to chunking pipeline.
"""

from ctrlmap.parse.chunker import chunk_document
from ctrlmap.parse.extractor import TextBlock, extract_text_blocks
from ctrlmap.parse.heuristics import (
    ElementRole,
    LayoutType,
    classify_block,
    detect_layout,
    order_blocks_by_columns,
)

__all__ = [
    "ElementRole",
    "LayoutType",
    "TextBlock",
    "chunk_document",
    "classify_block",
    "detect_layout",
    "extract_text_blocks",
    "order_blocks_by_columns",
]
