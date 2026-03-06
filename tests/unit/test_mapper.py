"""Tests for the mapping algorithm.

TDD RED phase: Story #16, control to vector DB to ranked chunks.
Ref: GitHub Issue #16.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ctrlmap.models.schemas import MappedResult, ParsedChunk, SecurityControl


@pytest.fixture()
def sample_controls() -> list[SecurityControl]:
    """Two security controls for mapping tests."""
    return [
        SecurityControl(
            control_id="AC-1",
            framework="NIST-800-53",
            title="Policy and Procedures",
            description="Develop, document, and disseminate access control policies.",
        ),
        SecurityControl(
            control_id="SC-28",
            framework="NIST-800-53",
            title="Protection of Information at Rest",
            description="Protect the confidentiality and integrity of information at rest.",
        ),
    ]


@pytest.fixture()
def populated_store(tmp_path: Path) -> MagicMock:
    """A mock VectorStore pre-populated with test chunks."""
    from ctrlmap.index.vector_store import VectorStore

    store = VectorStore(db_path=tmp_path / "map_db")

    # Index some realistic policy chunks with real embeddings
    from ctrlmap.index.embedder import Embedder

    embedder = Embedder()
    chunks = [
        ParsedChunk(
            chunk_id="ac-policy-001",
            document_name="policy.pdf",
            page_number=1,
            raw_text="All employees must follow access control policies and procedures.",
            section_header="Access Control",
            embedding=embedder.embed_text(
                "All employees must follow access control policies and procedures."
            ),
        ),
        ParsedChunk(
            chunk_id="ac-policy-002",
            document_name="policy.pdf",
            page_number=2,
            raw_text="User access reviews must be conducted quarterly by department managers.",
            section_header="Access Control",
            embedding=embedder.embed_text(
                "User access reviews must be conducted quarterly by department managers."
            ),
        ),
        ParsedChunk(
            chunk_id="enc-policy-001",
            document_name="policy.pdf",
            page_number=5,
            raw_text="All data at rest must be encrypted using AES-256 encryption standards.",
            section_header="Encryption",
            embedding=embedder.embed_text(
                "All data at rest must be encrypted using AES-256 encryption standards."
            ),
        ),
    ]
    store.index_chunks("chunks", chunks)
    return store


class TestMappingAlgorithm:
    """Story #16: Mapping algorithm (control → vector DB → ranked chunks)."""

    def test_mapping_returns_results_for_each_control(
        self,
        populated_store: MagicMock,
        sample_controls: list[SecurityControl],
    ) -> None:
        """Algorithm returns a MappedResult for every SecurityControl in the input."""
        from ctrlmap.map.mapper import map_controls

        results = map_controls(
            controls=sample_controls,
            store=populated_store,
            collection_name="chunks",
            min_score=0.0,
        )
        assert len(results) == len(sample_controls)
        assert all(isinstance(r, MappedResult) for r in results)

    def test_mapping_ranks_chunks_by_similarity(
        self,
        populated_store: MagicMock,
        sample_controls: list[SecurityControl],
    ) -> None:
        """Supporting chunks are ranked by cosine similarity (descending)."""
        from ctrlmap.map.mapper import map_controls

        results = map_controls(
            controls=sample_controls,
            store=populated_store,
            collection_name="chunks",
            top_k=3,
            min_score=0.0,
        )
        # For the encryption control (SC-28), the encryption chunk should rank highest
        sc28_result = next(r for r in results if r.control.control_id == "SC-28")
        assert len(sc28_result.supporting_chunks) > 0
        # Verify the first chunk is the most relevant (encryption-related)
        assert "encrypt" in sc28_result.supporting_chunks[0].raw_text.lower()

    def test_mapping_respects_top_k_parameter(
        self,
        populated_store: MagicMock,
        sample_controls: list[SecurityControl],
    ) -> None:
        """The top_k parameter limits the number of supporting chunks per control."""
        from ctrlmap.map.mapper import map_controls

        results = map_controls(
            controls=sample_controls,
            store=populated_store,
            collection_name="chunks",
            top_k=1,
            min_score=0.0,
        )
        for result in results:
            assert len(result.supporting_chunks) <= 1

    def test_mapping_handles_no_matches(
        self,
        tmp_path: Path,
    ) -> None:
        """Controls with no matching chunks return MappedResult with empty supporting_chunks."""
        from ctrlmap.index.vector_store import VectorStore
        from ctrlmap.map.mapper import map_controls

        # Empty store, no indexed chunks
        empty_store = VectorStore(db_path=tmp_path / "empty_db")
        empty_store.get_or_create_collection("chunks")

        controls = [
            SecurityControl(
                control_id="XX-99",
                framework="FAKE",
                title="Nonexistent Control",
                description="This control has absolutely no matching policy text.",
            ),
        ]
        results = map_controls(
            controls=controls,
            store=empty_store,
            collection_name="chunks",
        )
        assert len(results) == 1
        assert results[0].supporting_chunks == []

    def test_default_min_score_is_0_35(self) -> None:
        """The default min_score should be 0.35 to filter noise without losing relevance."""
        import inspect

        from ctrlmap.map.mapper import map_controls

        sig = inspect.signature(map_controls)
        default = sig.parameters["min_score"].default
        assert default == 0.35, f"Expected min_score default 0.35, got {default}"


class TestQueryExpansion:
    """Query expansion should add domain-specific synonyms to abstract controls."""

    def test_expand_query_adds_domain_terms(self) -> None:
        """Abstract control descriptions should be augmented with GRC synonyms."""
        from ctrlmap.map.mapper import _expand_query

        expanded = _expand_query(
            "SC-28: Protection of Information at Rest. "
            "Protect the confidentiality and integrity of information at rest."
        )
        # Should add encryption-related terms
        assert "encryption" in expanded.lower() or "aes" in expanded.lower(), (
            f"Expected encryption terms in: {expanded}"
        )

    def test_expand_query_noop_for_specific_terms(self) -> None:
        """Queries that already contain specific terms should pass through unchanged."""
        from ctrlmap.map.mapper import _expand_query

        original = (
            "AC-2: Account Management. "
            "Manage system accounts, group memberships, and authorizations."
        )
        expanded = _expand_query(original)
        # Should still contain the original text
        assert "Account Management" in expanded
