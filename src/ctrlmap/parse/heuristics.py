"""Coordinate-based layout heuristics for multi-column detection.

Analyzes x/y coordinate clusters from PyMuPDF text blocks to differentiate
dual-column layouts from single-column text, tables, and spanned elements
(headers, footers). All thresholds are configurable.

Ref: GitHub Issue #7.
"""

from __future__ import annotations

import re
from collections import defaultdict
from enum import StrEnum

from ctrlmap.parse.extractor import TextBlock


class LayoutType(StrEnum):
    """Detected page layout type."""

    SINGLE_COLUMN = "single_column"
    DUAL_COLUMN = "dual_column"
    TABLE = "table"


class ElementRole(StrEnum):
    """Semantic role of a text block on the page."""

    HEADER = "header"
    FOOTER = "footer"
    BODY = "body"


# --- Layout Detection ---


def detect_layout(
    blocks: list[TextBlock],
    *,
    column_gap_threshold: float = 100.0,
    min_column_width: float = 150.0,
    max_table_columns: int = 2,
) -> LayoutType:
    """Detect whether blocks form a single-column, dual-column, or table layout.

    Uses x-coordinate clustering to determine layout. Two distinct x-position
    clusters with a sufficient gap indicate dual-column. More than two clusters
    with narrow block widths indicate a table.

    Args:
        blocks: Text blocks extracted from a single page.
        column_gap_threshold: Minimum horizontal gap between column clusters.
        min_column_width: Minimum width for a block to be considered a column.
        max_table_columns: Max clusters before falling back to table detection.

    Returns:
        The detected ``LayoutType``.
    """
    if not blocks:
        return LayoutType.SINGLE_COLUMN

    # Cluster blocks by x0 position
    x_starts = sorted({round(b.x0) for b in blocks})

    if len(x_starts) <= 1:
        return LayoutType.SINGLE_COLUMN

    # Find distinct clusters: groups of x-starts separated by the gap threshold
    clusters: list[list[int]] = [[x_starts[0]]]
    for x in x_starts[1:]:
        if x - clusters[-1][-1] >= column_gap_threshold:
            clusters.append([x])
        else:
            clusters[-1].append(x)

    if len(clusters) == 1:
        return LayoutType.SINGLE_COLUMN

    if len(clusters) > max_table_columns:
        return LayoutType.TABLE

    # For exactly 2 clusters: distinguish dual-column from table by block width
    block_widths = [b.x1 - b.x0 for b in blocks]
    avg_width = sum(block_widths) / len(block_widths) if block_widths else 0

    if avg_width < min_column_width:
        return LayoutType.TABLE

    return LayoutType.DUAL_COLUMN


# --- Spanned Element Classification ---


def classify_block(
    block: TextBlock,
    *,
    page_width: float = 612.0,
    page_height: float = 792.0,
    header_margin: float = 70.0,
    footer_margin: float = 70.0,
) -> ElementRole:
    """Classify a text block as header, footer, or body content.

    Uses vertical position relative to page dimensions to determine role.

    Args:
        block: The text block to classify.
        page_width: Page width in points.
        page_height: Page height in points.
        header_margin: Distance from top of page to consider as header zone.
        footer_margin: Distance from bottom of page to consider as footer zone.

    Returns:
        The block's ``ElementRole``.
    """
    if block.y0 < header_margin:
        return ElementRole.HEADER

    if block.y0 > (page_height - footer_margin):
        return ElementRole.FOOTER

    return ElementRole.BODY


def _normalize_for_comparison(text: str) -> str:
    """Normalize text for repeating-block comparison.

    Strips whitespace, lowercases, and replaces variable parts
    (page numbers, dates) with placeholders so that
    "Page 1 of 3" and "Page 2 of 3" are treated as the same pattern.
    """
    t = text.strip().lower()
    t = re.sub(r"\d+", "#", t)
    return t


def classify_blocks(blocks: list[TextBlock]) -> list[ElementRole]:
    """Classify blocks as header, footer, or body using dynamic detection.

    Unlike :func:`classify_block`, this function examines **all** blocks
    across pages to determine header/footer zones adaptively:

    1. **Repeating text**: Blocks whose normalized text appears on 2+ pages
       at similar y-positions (within ``y_tolerance``) are headers/footers.
    2. **Gap isolation**: On any page, blocks separated from the body
       cluster by a vertical gap >= 2x the median line spacing are
       classified as header (if above the body cluster) or footer
       (if below).

    Args:
        blocks: All text blocks from the document.

    Returns:
        A list of ``ElementRole`` values, one per input block (same order).
    """
    if not blocks:
        return []

    roles: list[ElementRole] = [ElementRole.BODY] * len(blocks)
    y_tolerance = 20.0  # pts — blocks at similar y are "same position"

    # --- Phase 1: Repeating text across pages ---
    # Group blocks by their normalized text + approximate y-position
    # A "signature" that recurs on 2+ pages → header or footer


    # Map: (norm_text, y_bucket) → set of page numbers
    sig_pages: dict[tuple[str, int], set[int]] = defaultdict(set)
    sig_blocks: dict[tuple[str, int], list[int]] = defaultdict(list)

    for idx, block in enumerate(blocks):
        norm = _normalize_for_comparison(block.text)
        y_bucket = round(block.y0 / y_tolerance)
        sig = (norm, y_bucket)
        sig_pages[sig].add(block.page_number)
        sig_blocks[sig].append(idx)

    # Classify repeating blocks
    all_pages = {b.page_number for b in blocks}
    min_pages_for_repeat = 2  # Must appear on 2+ pages to count as repeating
    page_midpoints: dict[int, float] = {}
    for page_num in all_pages:
        page_y_values = [b.y0 for b in blocks if b.page_number == page_num]
        if page_y_values:
            page_midpoints[page_num] = (min(page_y_values) + max(page_y_values)) / 2

    for sig, pages in sig_pages.items():
        if len(pages) >= min_pages_for_repeat:
            # Repeating text — is it in the top or bottom half?
            representative_idx = sig_blocks[sig][0]
            rep_block = blocks[representative_idx]
            page_mid = page_midpoints.get(rep_block.page_number, 400.0)
            role = ElementRole.HEADER if rep_block.y0 < page_mid else ElementRole.FOOTER

            for idx in sig_blocks[sig]:
                roles[idx] = role

    # --- Phase 2: Gap-based isolation per page ---
    # For blocks not already classified, check if they're isolated
    # from the body cluster by a large vertical gap.
    pages_dict: dict[int, list[tuple[int, TextBlock]]] = defaultdict(list)
    for idx, block in enumerate(blocks):
        pages_dict[block.page_number].append((idx, block))

    for _page_num, page_items in pages_dict.items():
        # Sort by y-position
        page_items.sort(key=lambda item: item[1].y0)

        # Get body blocks (not yet classified as header/footer)
        body_indices = [idx for idx, _ in page_items if roles[idx] == ElementRole.BODY]
        if len(body_indices) < 2:
            continue

        # Compute median line spacing from consecutive body blocks
        body_y_vals = [blocks[idx].y0 for idx in body_indices]
        spacings = [body_y_vals[i + 1] - body_y_vals[i] for i in range(len(body_y_vals) - 1)]
        if not spacings:
            continue
        spacings.sort()
        median_spacing = spacings[len(spacings) // 2]
        # Use 4x median spacing (min 50pt) to avoid catching section breaks
        gap_threshold = max(median_spacing * 4, 50.0)

        # Check for isolated blocks at the bottom (footer gap)
        for i in range(len(page_items) - 1, 0, -1):
            idx, block = page_items[i]
            if roles[idx] != ElementRole.BODY:
                continue
            _prev_idx, prev_block = page_items[i - 1]
            gap = block.y0 - prev_block.y0
            if gap >= gap_threshold:
                # Only treat as footers if few blocks below the gap
                blocks_below = len(page_items) - i
                blocks_above = i
                if blocks_below < blocks_above:
                    for j in range(i, len(page_items)):
                        footer_idx = page_items[j][0]
                        if roles[footer_idx] == ElementRole.BODY:
                            roles[footer_idx] = ElementRole.FOOTER
                break

        # Check for isolated blocks at the top (header gap)
        for i in range(len(page_items) - 1):
            idx, block = page_items[i]
            if roles[idx] != ElementRole.BODY:
                continue
            _next_idx, next_block = page_items[i + 1]
            gap = next_block.y0 - block.y0
            if gap >= gap_threshold:
                # Only treat as headers if few blocks above the gap
                blocks_above = i + 1
                blocks_below = len(page_items) - blocks_above
                if blocks_above < blocks_below:
                    for j in range(i + 1):
                        header_idx = page_items[j][0]
                        if roles[header_idx] == ElementRole.BODY:
                            roles[header_idx] = ElementRole.HEADER
                break

    return roles


# --- Column Ordering ---


def order_blocks_by_columns(
    blocks: list[TextBlock],
    *,
    column_gap_threshold: float = 100.0,
) -> list[TextBlock]:
    """Reorder blocks so left-column blocks come first, then right-column.

    Within each column, blocks are sorted top-to-bottom by y-coordinate.
    Blocks are processed **per page** to avoid interleaving text from
    different pages that happen to share similar y-coordinates.

    Args:
        blocks: Text blocks to reorder.
        column_gap_threshold: Minimum gap between column x-clusters.

    Returns:
        Reordered list with left-column blocks first, per page.
    """
    if not blocks:
        return []

    # Group blocks by page
    pages: dict[int, list[TextBlock]] = {}
    for b in blocks:
        pages.setdefault(b.page_number, []).append(b)

    result: list[TextBlock] = []

    for page_num in sorted(pages):
        page_blocks = pages[page_num]

        # Find the split point between columns via x0 clustering
        x_starts = sorted({round(b.x0) for b in page_blocks})

        if len(x_starts) <= 1:
            result.extend(sorted(page_blocks, key=lambda b: b.y0))
            continue

        # Find the first gap that exceeds the threshold
        split_x: float | None = None
        for i in range(1, len(x_starts)):
            if x_starts[i] - x_starts[i - 1] >= column_gap_threshold:
                split_x = (x_starts[i - 1] + x_starts[i]) / 2
                break

        if split_x is None:
            result.extend(sorted(page_blocks, key=lambda b: b.y0))
            continue

        left = sorted([b for b in page_blocks if b.x0 < split_x], key=lambda b: b.y0)
        right = sorted([b for b in page_blocks if b.x0 >= split_x], key=lambda b: b.y0)
        result.extend(left + right)

    return result
