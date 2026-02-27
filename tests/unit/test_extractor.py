"""Tests for PyMuPDF layout-aware PDF extraction.

TDD RED phase: These tests define the expected behavior of the extractor
module before implementation. Ref: GitHub Issue #6.
"""

from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"


class TestExtractTextBlocks:
    """Tests for the extract_text_blocks function."""

    def test_extract_single_column_preserves_reading_order(self) -> None:
        """Text blocks from a single-column PDF should follow top-to-bottom reading order."""
        from ctrlmap.parse.extractor import extract_text_blocks

        blocks = extract_text_blocks(FIXTURE_DIR / "single_column.pdf")

        # Blocks must be sorted by y-coordinate (top-to-bottom reading order)
        texts = [b.text for b in blocks if b.text.strip()]
        assert len(texts) >= 4
        # First substantive text should be the title or first paragraph
        assert any("Access Control" in t for t in texts[:2])
        # Verify monotonically increasing y-coordinates for same-page blocks
        page1_blocks = [b for b in blocks if b.page_number == 1 and b.text.strip()]
        y_coords = [b.y0 for b in page1_blocks]
        assert y_coords == sorted(y_coords), "Blocks must be in top-to-bottom reading order"

    def test_extract_multi_column_separates_columns(self) -> None:
        """Multi-column PDF must produce blocks that separate left and right columns."""
        from ctrlmap.parse.extractor import extract_text_blocks

        blocks = extract_text_blocks(FIXTURE_DIR / "two_column_footer.pdf")

        texts = [b.text.strip() for b in blocks if b.text.strip()]
        assert len(texts) >= 4

        # The two columns should appear in the block list without horizontal merging
        has_ac1 = any("AC-1" in t for t in texts)
        has_ac2 = any("AC-2" in t for t in texts)
        assert has_ac1, "Should extract column 1 content (AC-1)"
        assert has_ac2, "Should extract column 2 content (AC-2)"

    def test_extract_isolates_headers_and_footers(self) -> None:
        """Header and footer text should be present but distinguishable via coordinates."""
        from ctrlmap.parse.extractor import extract_text_blocks

        blocks = extract_text_blocks(FIXTURE_DIR / "two_column_footer.pdf")

        # Header is at top of page (y0 < 60)
        header_blocks = [b for b in blocks if b.y0 < 60 and b.text.strip()]
        assert len(header_blocks) >= 1, "Should have at least one header block"
        assert any("Reference Guide" in b.text for b in header_blocks)

        # Footer is at bottom of page (y0 > 700)
        footer_blocks = [b for b in blocks if b.y0 > 700 and b.text.strip()]
        assert len(footer_blocks) >= 1, "Should have at least one footer block"
        assert any("Confidential" in b.text for b in footer_blocks)

    def test_extract_returns_page_metadata(self) -> None:
        """Each block must include page_number, and bounding box coordinates."""
        from ctrlmap.parse.extractor import extract_text_blocks

        blocks = extract_text_blocks(FIXTURE_DIR / "multipage.pdf")

        # Should have blocks from all 3 pages
        page_numbers = {b.page_number for b in blocks}
        assert page_numbers == {1, 2, 3}, f"Expected pages 1-3, got {page_numbers}"

        # Each block must have bounding box coordinates
        for block in blocks:
            assert hasattr(block, "x0")
            assert hasattr(block, "y0")
            assert hasattr(block, "x1")
            assert hasattr(block, "y1")
            assert block.x1 > block.x0, "x1 must be greater than x0"
            assert block.y1 > block.y0, "y1 must be greater than y0"

    def test_extract_handles_empty_pdf(self) -> None:
        """An empty (no-text) PDF should return an empty list, not raise."""
        # Create an empty PDF in temp
        import tempfile

        import fitz

        from ctrlmap.parse.extractor import extract_text_blocks

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            doc = fitz.open()
            doc.new_page()
            doc.save(f.name)
            doc.close()

            result = extract_text_blocks(Path(f.name))
            assert result == []

    def test_extract_rejects_nonexistent_file(self) -> None:
        """Attempting to extract from a non-existent file should raise FileNotFoundError."""
        from ctrlmap.parse.extractor import extract_text_blocks

        with pytest.raises(FileNotFoundError):
            extract_text_blocks(Path("/nonexistent/path/to/file.pdf"))
