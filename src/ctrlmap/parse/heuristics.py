"""Coordinate-based layout heuristics for multi-column detection.

Analyzes x/y coordinate clusters from PyMuPDF text blocks to differentiate
dual-column layouts from single-column text, tables, and spanned elements
(headers, footers). All thresholds are configurable.

Ref: GitHub Issue #7.
"""

from __future__ import annotations

from enum import Enum

from ctrlmap.parse.extractor import TextBlock


class LayoutType(Enum):
    """Detected page layout type."""

    SINGLE_COLUMN = "single_column"
    DUAL_COLUMN = "dual_column"
    TABLE = "table"


class ElementRole(Enum):
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


# --- Column Ordering ---


def order_blocks_by_columns(
    blocks: list[TextBlock],
    *,
    column_gap_threshold: float = 100.0,
) -> list[TextBlock]:
    """Reorder blocks so left-column blocks come first, then right-column.

    Within each column, blocks are sorted top-to-bottom by y-coordinate.

    Args:
        blocks: Text blocks to reorder.
        column_gap_threshold: Minimum gap between column x-clusters.

    Returns:
        Reordered list with left-column blocks first.
    """
    if not blocks:
        return []

    # Find the split point between columns via x0 clustering
    x_starts = sorted({round(b.x0) for b in blocks})

    if len(x_starts) <= 1:
        return sorted(blocks, key=lambda b: b.y0)

    # Find the first gap that exceeds the threshold
    split_x: float | None = None
    for i in range(1, len(x_starts)):
        if x_starts[i] - x_starts[i - 1] >= column_gap_threshold:
            split_x = (x_starts[i - 1] + x_starts[i]) / 2
            break

    if split_x is None:
        return sorted(blocks, key=lambda b: b.y0)

    left = sorted([b for b in blocks if b.x0 < split_x], key=lambda b: b.y0)
    right = sorted([b for b in blocks if b.x0 >= split_x], key=lambda b: b.y0)

    return left + right
