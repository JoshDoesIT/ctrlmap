"""Tests for hybrid structural + semantic chunking pipeline.

TDD RED phase: Tests define the expected behavior of the two-phase
chunking pipeline before implementation. Ref: GitHub Issue #8.
"""

from __future__ import annotations

from ctrlmap.parse.extractor import TextBlock


def _make_block(x0: float, y0: float, x1: float, y1: float, text: str, page: int = 1) -> TextBlock:
    """Helper to construct TextBlock instances for tests."""
    return TextBlock(x0=x0, y0=y0, x1=x1, y1=y1, text=text, page_number=page)


class TestStructuralChunking:
    """Tests for phase 1: structural header-based splitting."""

    def test_structural_chunking_splits_on_headers(self) -> None:
        """Blocks with section headers should produce separate chunks per section."""
        from ctrlmap.parse.chunker import structural_chunk

        blocks = [
            _make_block(72, 100, 540, 118, "Section 1: Access Control"),
            _make_block(72, 130, 540, 148, "All users must authenticate before accessing systems."),
            _make_block(72, 160, 540, 178, "Passwords must be at least 12 characters long."),
            _make_block(72, 220, 540, 238, "Section 2: Encryption"),
            _make_block(72, 250, 540, 268, "Data at rest must be encrypted using AES-256."),
        ]

        sections = structural_chunk(blocks)

        # Should produce 2 sections split at the header boundary
        assert len(sections) == 2
        assert any("Access Control" in s.header for s in sections if s.header)
        assert any("Encryption" in s.header for s in sections if s.header)

    def test_structural_chunking_no_headers_returns_single_section(self) -> None:
        """When no headers are detected, all blocks should form a single section."""
        from ctrlmap.parse.chunker import structural_chunk

        blocks = [
            _make_block(72, 100, 540, 118, "All users must authenticate before accessing systems."),
            _make_block(72, 130, 540, 148, "Passwords must be at least 12 characters long."),
            _make_block(
                72,
                160,
                540,
                178,
                "Multi-factor authentication is required for privileged accounts.",
            ),
        ]

        sections = structural_chunk(blocks)
        assert len(sections) == 1


class TestSemanticChunking:
    """Tests for phase 2: sentence-level semantic similarity chunking."""

    def test_semantic_chunking_groups_similar_sentences(self) -> None:
        """Semantically similar sentences should be grouped into the same chunk."""
        from ctrlmap.parse.chunker import semantic_chunk

        sentences = [
            "All user accounts must be reviewed quarterly by management.",
            "Account reviews should be documented and retained for audit.",
            "Privileged accounts require additional oversight and approval.",
        ]

        chunks = semantic_chunk(sentences, similarity_threshold=0.3)

        # All sentences are about account management — should stay together
        assert len(chunks) <= 2
        # At minimum, the first two highly related sentences should be together
        assert any("reviewed quarterly" in c and "documented" in c for c in chunks)

    def test_semantic_chunking_splits_on_topic_change(self) -> None:
        """A significant topic shift should produce a split between chunks."""
        from ctrlmap.parse.chunker import semantic_chunk

        sentences = [
            "All user accounts must be reviewed quarterly by management.",
            "Account access should be revoked upon employee termination.",
            "The fire suppression system must be tested annually.",
            "Emergency exits should be clearly marked and illuminated.",
        ]

        chunks = semantic_chunk(sentences, similarity_threshold=0.3)

        # Topic shifts from access control to physical security —
        # should produce at least 2 chunks
        assert len(chunks) >= 2

    def test_configurable_similarity_threshold(self) -> None:
        """Higher thresholds should produce more (smaller) chunks."""
        from ctrlmap.parse.chunker import semantic_chunk

        sentences = [
            "All user accounts must be reviewed quarterly by management.",
            "Account reviews should be documented and retained for audit.",
            "Privileged accounts require additional oversight and approval.",
            "The fire suppression system must be tested annually.",
        ]

        low_threshold_chunks = semantic_chunk(sentences, similarity_threshold=0.1)
        high_threshold_chunks = semantic_chunk(sentences, similarity_threshold=0.8)

        assert len(high_threshold_chunks) >= len(low_threshold_chunks)


class TestChunkDocument:
    """Tests for the full pipeline: structural + semantic → ParsedChunk."""

    def test_chunking_never_splits_mid_sentence(self) -> None:
        """No chunk should contain a sentence fragment."""
        from ctrlmap.parse.chunker import chunk_document

        blocks = [
            _make_block(72, 100, 540, 118, "Section 1: Requirements"),
            _make_block(
                72,
                130,
                540,
                170,
                "All user accounts must be reviewed quarterly. "
                "Privileged accounts require MFA. "
                "Service accounts must be rotated every 90 days.",
            ),
        ]

        chunks = chunk_document(blocks, document_name="test.pdf")

        for chunk in chunks:
            # Every chunk text should end with a sentence-ending character
            text = chunk.raw_text.strip()
            assert text[-1] in ".!?", f"Chunk appears split mid-sentence: '{text[-30:]}'"

    def test_chunks_conform_to_parsed_chunk_model(self) -> None:
        """Every output must be a valid ParsedChunk Pydantic model."""
        from ctrlmap.models.schemas import ParsedChunk
        from ctrlmap.parse.chunker import chunk_document

        blocks = [
            _make_block(72, 100, 540, 118, "Section 1: Access Control"),
            _make_block(
                72,
                130,
                540,
                170,
                "All user accounts must be reviewed quarterly by the security team. "
                "This includes both standard and privileged account types.",
            ),
        ]

        chunks = chunk_document(blocks, document_name="policy.pdf")

        assert len(chunks) >= 1
        for chunk in chunks:
            assert isinstance(chunk, ParsedChunk)
            assert chunk.document_name == "policy.pdf"
            assert chunk.page_number >= 1
            assert len(chunk.raw_text) >= 10
