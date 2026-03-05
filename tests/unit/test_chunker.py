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

    def test_structural_chunking_detects_numbered_headers(self) -> None:
        """Numbered headers like '1  Purpose' or '2.1  Authentication' should split sections."""
        from ctrlmap.parse.chunker import structural_chunk

        blocks = [
            _make_block(72, 82, 540, 101, "1  Purpose and Scope"),
            _make_block(
                72,
                113,
                540,
                127,
                "This policy establishes the requirements for managing access.",
            ),
            _make_block(72, 201, 540, 220, "2  User Identification and Authentication"),
            _make_block(
                72,
                235,
                540,
                250,
                "2.1  Unique User Identification",
            ),
            _make_block(
                72,
                258,
                540,
                272,
                "All users must be assigned a unique user ID before access.",
            ),
        ]

        sections = structural_chunk(blocks)

        assert len(sections) >= 2
        headers = [s.header for s in sections if s.header]
        assert any("Purpose" in h for h in headers), f"Expected 'Purpose' header, got: {headers}"
        assert any("Authentication" in h or "User Identification" in h for h in headers), (
            f"Expected 'Authentication' header, got: {headers}"
        )

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

    def test_page_boundary_splits_section(self) -> None:
        """A page change should start a new section, even without a new header.

        This prevents text from the end of page N bleeding into sections
        that begin on page N+1.
        """
        from ctrlmap.parse.chunker import structural_chunk

        blocks = [
            _make_block(72, 82, 540, 101, "1  Access Control"),
            _make_block(
                72,
                113,
                540,
                127,
                "All users must authenticate.",
                page=1,
            ),
            # page 2 — no header, but page changed
            _make_block(
                72,
                113,
                540,
                127,
                "MFA tokens must not be shared between users.",
                page=2,
            ),
            _make_block(72, 200, 540, 219, "2  Audit Logging"),
            _make_block(
                72,
                230,
                540,
                244,
                "Audit logs must capture user identification.",
                page=2,
            ),
        ]

        sections = structural_chunk(blocks)

        # Should produce at least 2 sections — page boundary
        # prevents page 1 content from merging into page 2 sections
        assert len(sections) >= 2
        # Audit Logging section should NOT contain MFA text
        for s in sections:
            if s.header and "Audit" in s.header:
                all_text = " ".join(s.sentences)
                assert "MFA" not in all_text, (
                    f"Cross-page contamination: MFA text in Audit section: {all_text}"
                )


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

        # All sentences are about account management, should stay together
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

        # Topic shifts from access control to physical security,
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
            assert len(chunk.raw_text) >= 50

    def test_short_fragments_are_filtered(self) -> None:
        """Fragments under 50 chars should not appear as standalone chunks."""
        from ctrlmap.parse.chunker import chunk_document

        blocks = [
            _make_block(72, 100, 540, 118, "Section 1: Security"),
            _make_block(72, 130, 540, 148, "current role."),  # 13 chars — fragment
            _make_block(72, 160, 540, 178, "encryption."),  # 11 chars — fragment
            _make_block(
                72,
                190,
                540,
                230,
                "All cardholder data must be encrypted using AES-256 in transit and at rest.",
            ),
        ]

        chunks = chunk_document(blocks, document_name="policy.pdf")

        for chunk in chunks:
            assert len(chunk.raw_text) >= 50, f"Fragment slipped through: '{chunk.raw_text}'"

    def test_short_sentences_merged_with_neighbors(self) -> None:
        """Short sentences should be merged with adjacent sentences, not dropped."""
        from ctrlmap.parse.chunker import chunk_document

        blocks = [
            _make_block(72, 100, 540, 118, "Section 1: Policy"),
            _make_block(
                72,
                130,
                540,
                200,
                "All access to system components and cardholder data must be logged. "
                "Logs are critical. "
                "Audit trails must be retained for a minimum of twelve months.",
            ),
        ]

        chunks = chunk_document(blocks, document_name="policy.pdf")

        # "Logs are critical." is only 18 chars — too short for a standalone chunk.
        # It should be merged with a neighbor, not dropped or isolated.
        all_text = " ".join(c.raw_text for c in chunks)
        assert "Logs are critical" in all_text, "Short sentence was dropped instead of merged"

    def test_consecutive_line_blocks_joined_into_paragraph(self) -> None:
        """PDF lines that form a single paragraph should be joined before chunking.

        PyMuPDF returns each visual line as a separate block. Lines that are
        vertically adjacent on the same page must be joined so chunks never
        end mid-sentence.
        """
        from ctrlmap.parse.chunker import chunk_document

        # Simulates 3 consecutive PDF lines — one paragraph split across lines
        blocks = [
            _make_block(72, 82, 540, 101, "1  Network Change Management"),
            _make_block(
                72,
                246,
                540,
                260,
                "All changes to network connections and to"
                " configurations of NSCs must be approved and managed in acc",
            ),
            _make_block(
                72,
                262,
                540,
                276,
                "the organizational change control process."
                " Changes must be reviewed and formally approved within",
            ),
            _make_block(
                72,
                278,
                540,
                292,
                "72 hours of implementation."
                " All changes must be tested in a staging environment first.",
            ),
        ]

        chunks = chunk_document(blocks, document_name="policy.pdf")

        # No chunk should end with a partial word like "acc" or "in a"
        for chunk in chunks:
            text = chunk.raw_text.strip()
            assert not text.endswith(" acc"), f"Mid-line cut: '{text[-40:]}'"
            assert not text.endswith(" in a"), f"Mid-line cut: '{text[-40:]}'"

        # The full sentence should be intact
        all_text = " ".join(c.raw_text for c in chunks)
        assert "72 hours of implementation" in all_text
