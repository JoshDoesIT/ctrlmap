"""Tests for coordinate-based multi-column heuristics.

TDD RED phase: Tests define the expected behavior of the layout
heuristic engine before implementation. Ref: GitHub Issue #7.
"""

from __future__ import annotations

from ctrlmap.parse.extractor import TextBlock


def _make_block(x0: float, y0: float, x1: float, y1: float, text: str, page: int = 1) -> TextBlock:
    """Helper to construct TextBlock instances for tests."""
    return TextBlock(x0=x0, y0=y0, x1=x1, y1=y1, text=text, page_number=page)


class TestLayoutDetection:
    """Tests for the detect_layout function."""

    def test_detect_dual_column_layout(self) -> None:
        """Blocks clustered in two x-ranges should be detected as dual-column."""
        from ctrlmap.parse.heuristics import LayoutType, detect_layout

        # Left column blocks (x0 ~ 72)
        # Right column blocks (x0 ~ 320)
        blocks = [
            _make_block(72, 100, 280, 118, "Left column paragraph one."),
            _make_block(72, 130, 280, 148, "Left column paragraph two."),
            _make_block(320, 100, 540, 118, "Right column paragraph one."),
            _make_block(320, 130, 540, 148, "Right column paragraph two."),
        ]

        result = detect_layout(blocks)
        assert result == LayoutType.DUAL_COLUMN

    def test_detect_single_column_layout(self) -> None:
        """Blocks all in a single x-range should be detected as single-column."""
        from ctrlmap.parse.heuristics import LayoutType, detect_layout

        blocks = [
            _make_block(72, 100, 540, 118, "Full width paragraph one."),
            _make_block(72, 130, 540, 148, "Full width paragraph two."),
            _make_block(72, 160, 540, 178, "Full width paragraph three."),
        ]

        result = detect_layout(blocks)
        assert result == LayoutType.SINGLE_COLUMN

    def test_distinguish_table_from_dual_column(self) -> None:
        """Blocks with aligned x-positions but narrow widths (table cells)
        should NOT be dual-column. They should be detected as a table."""
        from ctrlmap.parse.heuristics import LayoutType, detect_layout

        # Table-like: blocks on same row with different x-starts but narrow widths
        blocks = [
            _make_block(72, 100, 150, 115, "Cell A1"),
            _make_block(160, 100, 250, 115, "Cell B1"),
            _make_block(260, 100, 350, 115, "Cell C1"),
            _make_block(72, 120, 150, 135, "Cell A2"),
            _make_block(160, 120, 250, 135, "Cell B2"),
            _make_block(260, 120, 350, 135, "Cell C2"),
        ]

        result = detect_layout(blocks)
        assert result == LayoutType.TABLE


class TestSpannedElementDetection:
    """Tests for identifying spanned (full-width) elements."""

    def test_identify_spanned_header(self) -> None:
        """A full-width block at the top of the page should be classified as a header."""
        from ctrlmap.parse.heuristics import ElementRole, classify_block

        page_width = 612.0
        header_block = _make_block(72, 40, 540, 58, "NIST 800-53 Control Reference Guide")

        role = classify_block(header_block, page_width=page_width)
        assert role == ElementRole.HEADER

    def test_identify_spanned_footer(self) -> None:
        """A full-width block at the bottom of the page should be classified as a footer."""
        from ctrlmap.parse.heuristics import ElementRole, classify_block

        page_width = 612.0
        footer_block = _make_block(72, 750, 540, 765, "Page 1 of 1 - Confidential")

        role = classify_block(footer_block, page_width=page_width, page_height=792.0)
        assert role == ElementRole.FOOTER

    def test_classify_body_content(self) -> None:
        """A block in the middle of the page should be classified as body content."""
        from ctrlmap.parse.heuristics import ElementRole, classify_block

        page_width = 612.0
        body_block = _make_block(72, 200, 540, 218, "Regular body paragraph text.")

        role = classify_block(body_block, page_width=page_width)
        assert role == ElementRole.BODY


class TestColumnOrdering:
    """Tests for ordering blocks by column then reading order."""

    def test_order_dual_column_reads_left_then_right(self) -> None:
        """Dual-column blocks should be reordered: all left-column first, then right."""
        from ctrlmap.parse.heuristics import order_blocks_by_columns

        blocks = [
            _make_block(72, 100, 280, 118, "L1"),
            _make_block(320, 100, 540, 118, "R1"),
            _make_block(72, 130, 280, 148, "L2"),
            _make_block(320, 130, 540, 148, "R2"),
        ]

        ordered = order_blocks_by_columns(blocks)
        texts = [b.text for b in ordered]
        assert texts == ["L1", "L2", "R1", "R2"]


class TestDynamicHeaderFooterDetection:
    """Dynamic detection of headers/footers without hardcoded margins.

    Headers/footers are identified by repeating text patterns across
    pages and by vertical gap isolation from the body text cluster.
    """

    def test_repeating_footer_text_across_pages_detected(self) -> None:
        """Text that appears on multiple pages at similar y-positions → footer."""
        from ctrlmap.parse.heuristics import ElementRole, classify_blocks

        blocks = [
            # Page 1 — body + footer
            _make_block(72, 100, 540, 118, "Body text page one.", page=1),
            _make_block(72, 750, 540, 765, "Page 1 of 3 - Confidential", page=1),
            # Page 2 — body + footer (same text pattern)
            _make_block(72, 100, 540, 118, "Body text page two.", page=2),
            _make_block(72, 750, 540, 765, "Page 2 of 3 - Confidential", page=2),
        ]

        roles = classify_blocks(blocks)

        assert roles[0] == ElementRole.BODY
        assert roles[1] == ElementRole.FOOTER
        assert roles[2] == ElementRole.BODY
        assert roles[3] == ElementRole.FOOTER

    def test_body_near_bottom_not_misclassified_as_footer(self) -> None:
        """Body text at y0=730 must NOT be classified as footer.

        Reproduces the network_security_policy.pdf bug: the block at
        y0=730 contains 'installation. A wireless intrusion...' which
        is body text, but gets misclassified as footer when using a
        hardcoded 70pt margin (792 - 70 = 722 threshold).
        """
        from ctrlmap.parse.heuristics import ElementRole, classify_blocks

        blocks = [
            # Page 2 body blocks with regular ~15pt spacing
            _make_block(72, 637, 540, 652, "4  Wireless Network Security", page=2),
            _make_block(72, 668, 540, 683, "NSCs must be installed.", page=2),
            _make_block(72, 714, 540, 729, "strings must be changed", page=2),
            _make_block(72, 730, 540, 745, "A wireless IDS must be deployed.", page=2),
            _make_block(72, 746, 540, 761, "access points on a quarterly basis.", page=2),
            # Actual footer — isolated at y0=807 (gap of ~46pt from last body block)
            _make_block(72, 807, 540, 820, "Page 2/3", page=2),
            # Same footer on page 3 to enable repeating-text detection
            _make_block(72, 807, 540, 820, "Page 3/3", page=3),
            _make_block(72, 100, 540, 118, "Body text page three.", page=3),
        ]

        roles = classify_blocks(blocks)

        # The block at y0=730 must be BODY, not FOOTER
        assert roles[3] == ElementRole.BODY, f"Block at y0=730 misclassified as {roles[3]}"
        assert roles[4] == ElementRole.BODY, f"Block at y0=746 misclassified as {roles[4]}"
        # The actual footer at y0=807 should be FOOTER
        assert roles[5] == ElementRole.FOOTER

    def test_repeating_header_detected(self) -> None:
        """Text repeated at page tops → header."""
        from ctrlmap.parse.heuristics import ElementRole, classify_blocks

        blocks = [
            _make_block(72, 30, 540, 48, "Acme Corp - CONFIDENTIAL", page=1),
            _make_block(72, 100, 540, 118, "Body text.", page=1),
            _make_block(72, 30, 540, 48, "Acme Corp - CONFIDENTIAL", page=2),
            _make_block(72, 100, 540, 118, "More body text.", page=2),
        ]

        roles = classify_blocks(blocks)

        assert roles[0] == ElementRole.HEADER
        assert roles[1] == ElementRole.BODY
        assert roles[2] == ElementRole.HEADER
        assert roles[3] == ElementRole.BODY

    def test_single_page_gap_detection(self) -> None:
        """On a single-page doc, footers are detected via gap isolation."""
        from ctrlmap.parse.heuristics import ElementRole, classify_blocks

        blocks = [
            _make_block(72, 100, 540, 118, "Body line 1.", page=1),
            _make_block(72, 130, 540, 148, "Body line 2.", page=1),
            _make_block(72, 160, 540, 178, "Body line 3.", page=1),
            # Large gap then footer
            _make_block(72, 750, 540, 765, "Page 1/1", page=1),
        ]

        roles = classify_blocks(blocks)

        assert roles[0] == ElementRole.BODY
        assert roles[1] == ElementRole.BODY
        assert roles[2] == ElementRole.BODY
        assert roles[3] == ElementRole.FOOTER
