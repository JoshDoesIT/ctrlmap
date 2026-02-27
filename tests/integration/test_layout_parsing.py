"""Integration test: Layout-aware parsing (Test Spec 1 from SDD).

Ref: GitHub Issue #10.

Goal: Ensure multi-column documents are parsed linearly without
horizontal merging.

Given: A PDF document containing a two-column text layout alongside
a spanned footer.

When: The parse module processes the document using the structural
heuristic engine.

Then: The parser must return sequential text blocks from column 1,
followed by sequential text blocks from column 2, without merging
sentences across the horizontal visual axis. The footer must be
isolated and assigned as metadata, not injected into the primary
text payload.
"""

from __future__ import annotations

from pathlib import Path

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"


class TestLayoutAwareParsing:
    """Integration test implementing Test Spec 1 from the SDD."""

    def test_column1_text_precedes_column2_in_output(self) -> None:
        """After column-aware ordering, left-column text should precede right-column text."""
        from ctrlmap.parse.extractor import extract_text_blocks
        from ctrlmap.parse.heuristics import ElementRole, classify_block, order_blocks_by_columns

        blocks = extract_text_blocks(FIXTURE_DIR / "two_column_footer.pdf")

        # Filter to body content only
        body_blocks = [b for b in blocks if classify_block(b) == ElementRole.BODY]

        # Reorder by columns
        ordered = order_blocks_by_columns(body_blocks)
        texts = [b.text for b in ordered]

        # Find positions of AC-1 (left column) and AC-2 (right column) content
        ac1_indices = [i for i, t in enumerate(texts) if "AC-1" in t]
        ac2_indices = [i for i, t in enumerate(texts) if "AC-2" in t]

        assert ac1_indices, "Column 1 content (AC-1) not found"
        assert ac2_indices, "Column 2 content (AC-2) not found"

        # All AC-1 references must appear before all AC-2 references
        assert max(ac1_indices) < min(ac2_indices), (
            f"Column 1 text (AC-1 at {ac1_indices}) should precede "
            f"column 2 text (AC-2 at {ac2_indices})"
        )

    def test_no_horizontal_merging_across_columns(self) -> None:
        """No single text block should contain text from both columns."""
        from ctrlmap.parse.extractor import extract_text_blocks
        from ctrlmap.parse.heuristics import ElementRole, classify_block

        blocks = extract_text_blocks(FIXTURE_DIR / "two_column_footer.pdf")
        body_blocks = [b for b in blocks if classify_block(b) == ElementRole.BODY]

        for block in body_blocks:
            # No block should contain both AC-1 and AC-2 content
            has_col1 = "AC-1" in block.text or "access control policies" in block.text.lower()
            has_col2 = "AC-2" in block.text or "conditions for use" in block.text.lower()
            assert not (has_col1 and has_col2), (
                f"Block merges text from both columns: '{block.text}'"
            )

    def test_footer_isolated_as_metadata(self) -> None:
        """Footer text must be classified separately, not injected into body."""
        from ctrlmap.parse.extractor import extract_text_blocks
        from ctrlmap.parse.heuristics import ElementRole, classify_block

        blocks = extract_text_blocks(FIXTURE_DIR / "two_column_footer.pdf")

        footer_blocks = [b for b in blocks if classify_block(b) == ElementRole.FOOTER]
        body_blocks = [b for b in blocks if classify_block(b) == ElementRole.BODY]

        # Footer must be isolated
        assert len(footer_blocks) >= 1, "Footer not detected"
        assert any("Confidential" in b.text for b in footer_blocks)

        # Footer text must NOT appear in body blocks
        for block in body_blocks:
            assert "Confidential" not in block.text, f"Footer text leaked into body: '{block.text}'"

    def test_full_pipeline_produces_valid_chunks(self) -> None:
        """End-to-end: extraction → heuristics → chunking produces valid ParsedChunks."""
        from ctrlmap.models.schemas import ParsedChunk
        from ctrlmap.parse.chunker import chunk_document
        from ctrlmap.parse.extractor import extract_text_blocks
        from ctrlmap.parse.heuristics import ElementRole, classify_block, order_blocks_by_columns

        blocks = extract_text_blocks(FIXTURE_DIR / "two_column_footer.pdf")
        body_blocks = [b for b in blocks if classify_block(b) == ElementRole.BODY]
        ordered = order_blocks_by_columns(body_blocks)
        chunks = chunk_document(ordered, document_name="two_column_footer.pdf")

        assert len(chunks) >= 1
        for chunk in chunks:
            assert isinstance(chunk, ParsedChunk)
            assert chunk.document_name == "two_column_footer.pdf"
            assert len(chunk.raw_text) >= 10
