"""PDF page rendering and chunk position detection for the Document Reader.

Uses PyMuPDF (fitz) to render PDF pages as PNG images and locate chunk
text on each page, producing the data needed for the interactive
Document Reader overlay.

Ref: GitHub Issue #22.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import fitz  # type: ignore[import-untyped]

from ctrlmap.models.schemas import ParsedChunk

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class ChunkOverlay:
    """A highlighted region on a PDF page for one chunk.

    Uses a CSS ``clip-path: polygon(...)`` for pixel-precise shapes
    when a chunk starts or ends mid-line.
    """

    chunk_id: str
    x_pct: float  # 0-100 % from left
    y_pct: float  # 0-100 % from top
    w_pct: float  # width %
    h_pct: float  # height %
    clip_path: str  # CSS clip-path polygon or ""
    controls: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class RenderedPage:
    """One rendered PDF page with its overlay data."""

    page_number: int  # 1-indexed
    image_b64: str  # base64-encoded PNG
    width: int  # pixel width
    height: int  # pixel height
    overlays: list[ChunkOverlay] = field(default_factory=list)


@dataclass
class RenderedDocument:
    """All rendered pages for a single PDF."""

    document_name: str
    pages: list[RenderedPage] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

DPI = 120


def render_document(
    pdf_path: Path,
    chunks: list[ParsedChunk],
    chunk_controls: dict[str, list[dict[str, Any]]],
    *,
    dpi: int = DPI,
) -> RenderedDocument:
    """Render a PDF to page images and locate chunk positions.

    Args:
        pdf_path: Path to the PDF file.
        chunks: Chunks extracted from this document.
        chunk_controls: Mapping of ``chunk_id`` → list of control info
            dicts (each with ``id``, ``title``, ``compliance``, etc.).
        dpi: Resolution for page rendering.

    Returns:
        A ``RenderedDocument`` with base64 page images and overlay data.
    """
    doc = fitz.open(str(pdf_path))
    result = RenderedDocument(document_name=pdf_path.name)

    for page_idx in range(doc.page_count):
        page = doc[page_idx]
        page_num = page_idx + 1  # 1-indexed

        # Render page to PNG
        pix = page.get_pixmap(dpi=dpi)
        img_bytes = pix.tobytes("png")
        img_b64 = base64.b64encode(img_bytes).decode("ascii")

        # Extract line-level text data for this page
        page_lines = _extract_page_lines(page)

        rendered_page = RenderedPage(
            page_number=page_num,
            image_b64=img_b64,
            width=pix.width,
            height=pix.height,
        )

        # Try to match ALL chunks against this page's text (handles
        # cross-page chunks whose text wraps from a previous page)
        for chunk in chunks:
            overlay = _find_chunk_on_page(
                page_lines,
                page,
                chunk,
                chunk_controls,
                pix,
            )
            if overlay:
                rendered_page.overlays.append(overlay)

        result.pages.append(rendered_page)

    doc.close()
    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


@dataclass
class _PageLine:
    """One PDF text line with geometry and span-level data."""

    y0: float
    y1: float
    x0: float
    x1: float
    text: str
    # Spans: list of (span_x0, span_x1, span_text) for precise x lookup
    spans: list[tuple[float, float, str]] = field(default_factory=list)


def _extract_page_lines(page: Any) -> list[_PageLine]:
    """Extract line bounding boxes, text, and span data from a page."""
    lines: list[_PageLine] = []
    page_dict = page.get_text("dict")
    for block in page_dict.get("blocks", []):
        if block.get("type", 1) != 0:
            continue
        for line in block.get("lines", []):
            bbox = line["bbox"]
            spans_data: list[tuple[float, float, str]] = []
            for s in line.get("spans", []):
                spans_data.append((s["bbox"][0], s["bbox"][2], s["text"]))
            line_text = "".join(s[2] for s in spans_data)
            lines.append(
                _PageLine(
                    y0=bbox[1],
                    y1=bbox[3],
                    x0=bbox[0],
                    x1=bbox[2],
                    text=line_text,
                    spans=spans_data,
                )
            )
    return lines


def _norm(s: str) -> str:
    """Collapse whitespace and lowercase for fuzzy matching."""
    return " ".join(s.split()).lower()


def _find_chunk_on_page(
    page_lines: list[_PageLine],
    page: Any,
    chunk: ParsedChunk,
    chunk_controls: dict[str, list[dict[str, Any]]],
    pix: Any,
) -> ChunkOverlay | None:
    """Locate a chunk on the page, producing a single overlay with clip-path.

    Returns one ``ChunkOverlay`` with a CSS ``clip-path: polygon()`` that
    precisely traces the chunk text, even when it starts or ends mid-line.
    """
    text = chunk.raw_text.strip()
    if not text or not page_lines:
        return None

    chunk_norm = _norm(text)

    # Concatenate line texts for matching
    concat = ""
    line_ranges: list[tuple[int, int]] = []
    for line in page_lines:
        start = len(concat)
        concat += _norm(line.text) + " "
        line_ranges.append((start, len(concat)))

    # Find match — try chunk start first (normal case)
    match_pos = -1
    chunk_offset = 0  # how far into chunk_norm the page text begins
    for snippet_len in (60, 40, 25):
        search = chunk_norm[:snippet_len]
        match_pos = concat.find(search)
        if match_pos != -1:
            break

    # Sliding-window fallback for cross-page continuations:
    # The chunk might start on a previous page, so we search for
    # later portions of the chunk text on this page.
    if match_pos == -1:
        for offset in range(10, max(len(chunk_norm) - 24, 1), 10):
            snippet = chunk_norm[offset : offset + 40]
            if len(snippet) < 20:
                continue
            pos = concat.find(snippet)
            if pos != -1:
                # Find which line contains the initial match
                line_floor = 0
                for lstart, lend in line_ranges:
                    if lstart <= pos < lend:
                        line_floor = lstart
                        break
                # Extend backwards but NOT past the content line start
                actual_offset = offset
                actual_pos = pos
                while actual_offset > 0 and actual_pos > line_floor:
                    if concat[actual_pos - 1] == chunk_norm[actual_offset - 1]:
                        actual_pos -= 1
                        actual_offset -= 1
                    else:
                        break
                match_pos = actual_pos
                chunk_offset = actual_offset
                break

    if match_pos == -1:
        return None

    # Compute actual match length by comparing characters.
    # Don't naively use all available text — the page may have footer
    # text after the chunk content that shouldn't be highlighted.
    remaining_chunk = len(chunk_norm) - chunk_offset
    available = len(concat) - match_pos
    max_possible = min(remaining_chunk, available)
    match_len = 0
    for i in range(max_possible):
        if chunk_norm[chunk_offset + i] == concat[match_pos + i]:
            match_len = i + 1
        else:
            break

    # Strictness check against false positive partial matches
    if match_len < remaining_chunk * 0.95:
        # The match broke off before the chunk ended.
        # This is only valid if we hit the end of the page (i.e. it's wrapping to the next page).
        # We allow up to 250 characters of "footer" text at the end of the page.
        chars_after_match = available - match_len
        if chars_after_match > 250:
            return None

    match_end = match_pos + match_len

    # Collect touched lines with overlap ranges
    touched: list[tuple[int, int, int]] = []
    for i, (lstart, lend) in enumerate(line_ranges):
        if lstart < match_end and lend > match_pos:
            touched.append((i, max(match_pos, lstart), min(match_end, lend)))

    if not touched:
        return None

    scale = pix.width / page.rect.width
    pw = pix.width
    ph = pix.height

    def _to_pct_x(pdf_x: float) -> float:
        return float((pdf_x * scale / pw) * 100)

    def _to_pct_y(pdf_y: float) -> float:
        return float((pdf_y * scale / ph) * 100)

    def _search_boundary_x(line_idx: int, char_pos: int, is_end: bool) -> float:
        """Use page.search_for() to find exact x at a chunk boundary.

        Extracts the chunk's boundary words on this line from the
        normalized concat text, then searches the PDF page for those
        words to get pixel-precise coordinates.
        """
        line = page_lines[line_idx]
        lstart, lend = line_ranges[line_idx]

        # Get the chunk's normalized text on this specific line
        line_match_start = max(match_pos, lstart)
        line_match_end = min(match_end, lend)
        chunk_on_line = concat[line_match_start:line_match_end].strip()
        words = chunk_on_line.split()

        if not words:
            return line.x0 if not is_end else line.x1

        # Search for boundary words (try 4, 3, 2, 1 words)
        for n_words in range(min(4, len(words)), 0, -1):
            frag = " ".join(words[-n_words:]) if is_end else " ".join(words[:n_words])

            rects = page.search_for(frag)
            # Collect all rects that overlap with our target line
            line_rects = [r for r in rects if r.y0 <= (line.y0 + line.y1) / 2 <= r.y1]
            if line_rects:
                if is_end:
                    return float(max(r.x1 for r in line_rects))
                else:
                    return float(min(r.x0 for r in line_rects))

        # Fallback: line boundary
        return line.x0 if not is_end else line.x1

    # Check if first/last lines are partial
    first_idx, first_ov_start, _ = touched[0]
    last_idx, _, last_ov_end = touched[-1]
    first_is_partial = first_ov_start > line_ranges[first_idx][0] + 1
    last_is_partial = last_ov_end < line_ranges[last_idx][1] - 1

    # Compute bounding box (union of all touched lines)
    all_lines = [page_lines[t[0]] for t in touched]
    bbox_y0 = min(ln.y0 for ln in all_lines)
    bbox_y1 = max(ln.y1 for ln in all_lines)
    bbox_x0 = min(ln.x0 for ln in all_lines)
    bbox_x1 = max(ln.x1 for ln in all_lines)

    # If partial, extend bbox to include partial x ranges
    if first_is_partial:
        x_start = _search_boundary_x(first_idx, first_ov_start, is_end=False)
        bbox_x0 = min(bbox_x0, x_start)

    x_pct = _to_pct_x(bbox_x0)
    y_pct = _to_pct_y(bbox_y0)
    w_pct = _to_pct_x(bbox_x1) - x_pct
    h_pct = _to_pct_y(bbox_y1) - y_pct

    # Build clip-path if any line is partial
    clip_path = ""
    if first_is_partial or last_is_partial:
        clip_path = _build_clip_path(
            touched,
            page_lines,
            line_ranges,
            first_is_partial,
            last_is_partial,
            bbox_x0,
            bbox_y0,
            bbox_x1,
            bbox_y1,
            _search_boundary_x,
        )

    controls = chunk_controls.get(chunk.chunk_id, [])

    return ChunkOverlay(
        chunk_id=chunk.chunk_id,
        x_pct=round(max(x_pct, 0), 2),
        y_pct=round(y_pct, 2),
        w_pct=round(min(w_pct, 100), 2),
        h_pct=round(h_pct, 2),
        clip_path=clip_path,
        controls=controls,
    )


def _build_clip_path(
    touched: list[tuple[int, int, int]],
    page_lines: list[_PageLine],
    line_ranges: list[tuple[int, int]],
    first_is_partial: bool,
    last_is_partial: bool,
    bbox_x0: float,
    bbox_y0: float,
    bbox_x1: float,
    bbox_y1: float,
    _search_boundary_x: Any,
) -> str:
    """Build a CSS clip-path polygon for a non-rectangular chunk overlay.

    The polygon traces the visible area of the chunk within its bounding
    box, expressed as percentages of the overlay div.

    For a chunk that starts mid-line and ends mid-line, the shape is::

        x_start ──────── right
        │               │
        left ─── x_end  │
                 │      │
        (excluded area)

    The polygon walks clockwise around the visible region.
    """
    bw = max(bbox_x1 - bbox_x0, 0.01)
    bh = max(bbox_y1 - bbox_y0, 0.01)

    def _rel_x(pdf_x: float) -> float:
        return ((pdf_x - bbox_x0) / bw) * 100

    def _rel_y(pdf_y: float) -> float:
        return ((pdf_y - bbox_y0) / bh) * 100

    first_line = page_lines[touched[0][0]]
    last_line = page_lines[touched[-1][0]]

    # Key coordinates (relative to overlay bbox)
    left = _rel_x(bbox_x0)  # 0%
    right = _rel_x(bbox_x1)  # 100%
    top = _rel_y(bbox_y0)  # 0%
    bottom = _rel_y(bbox_y1)  # 100%

    if first_is_partial:
        x_start = _rel_x(_search_boundary_x(touched[0][0], touched[0][1], is_end=False))
        first_bottom = _rel_y(first_line.y1)
    else:
        x_start = left
        first_bottom = _rel_y(first_line.y1)

    if last_is_partial:
        x_end = _rel_x(_search_boundary_x(touched[-1][0], touched[-1][2], is_end=True))
        last_top = _rel_y(last_line.y0)
    else:
        x_end = right
        last_top = _rel_y(last_line.y0)

    # Build polygon points clockwise
    points = []

    if first_is_partial and last_is_partial:
        # Shape: indented top-left, indented bottom-right
        points = [
            (x_start, top),  # top of first line, at chunk start
            (right, top),  # top-right corner
            (right, last_top),  # down to last line top
            (x_end, last_top),  # across to chunk end on last line
            (x_end, bottom),  # down to bottom of last line
            (left, bottom),  # bottom-left
            (left, first_bottom),  # up to bottom of first line
            (x_start, first_bottom),  # across to chunk start
        ]
    elif first_is_partial:
        # Indented top-left only
        points = [
            (x_start, top),
            (right, top),
            (right, bottom),
            (left, bottom),
            (left, first_bottom),
            (x_start, first_bottom),
        ]
    elif last_is_partial:
        # Indented bottom-right only
        points = [
            (left, top),
            (right, top),
            (right, last_top),
            (x_end, last_top),
            (x_end, bottom),
            (left, bottom),
        ]

    if not points:
        return ""

    coords = ", ".join(f"{x:.1f}% {y:.1f}%" for x, y in points)
    return f"polygon({coords})"
