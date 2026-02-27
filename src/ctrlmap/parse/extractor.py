"""PyMuPDF layout-aware PDF text extraction.

Extracts text blocks with bounding-box coordinates and page metadata
from PDF documents using PyMuPDF (fitz). Preserves spatial layout
information for downstream column detection and chunking.

Ref: GitHub Issue #6.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz  # type: ignore[import-untyped]


@dataclass(frozen=True)
class TextBlock:
    """A text block extracted from a PDF page with bounding-box metadata.

    Attributes:
        x0: Left edge of the bounding box.
        y0: Top edge of the bounding box.
        x1: Right edge of the bounding box.
        y1: Bottom edge of the bounding box.
        text: The extracted text content.
        page_number: 1-indexed page number.
    """

    x0: float
    y0: float
    x1: float
    y1: float
    text: str
    page_number: int


def extract_text_blocks(path: Path) -> list[TextBlock]:
    """Extract text blocks with bounding-box metadata from a PDF.

    Uses PyMuPDF's ``get_text("blocks")`` to retrieve layout-aware text
    blocks. Each block preserves its spatial coordinates for downstream
    column detection and header/footer isolation.

    Args:
        path: Path to the PDF file.

    Returns:
        A list of ``TextBlock`` instances sorted by page, then top-to-bottom.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    if not path.exists():
        msg = f"PDF file not found: {path}"
        raise FileNotFoundError(msg)

    doc = fitz.open(str(path))
    blocks: list[TextBlock] = []

    try:
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            # get_text("blocks") returns (x0, y0, x1, y1, text, block_no, block_type)
            # block_type 0 = text, 1 = image
            raw_blocks = page.get_text("blocks")

            for raw in raw_blocks:
                x0, y0, x1, y1, text, _block_no, block_type = raw

                # Skip image blocks (type 1) and empty text
                if block_type != 0 or not text.strip():
                    continue

                blocks.append(
                    TextBlock(
                        x0=x0,
                        y0=y0,
                        x1=x1,
                        y1=y1,
                        text=text.strip(),
                        page_number=page_idx + 1,
                    )
                )
    finally:
        doc.close()

    # Sort by page number, then by vertical position (top-to-bottom)
    blocks.sort(key=lambda b: (b.page_number, b.y0))

    return blocks
