"""Tests for batch embedding query support.

TDD RED phase: query_by_embedding() accepts pre-computed embedding
vectors instead of raw text, enabling batch embedding.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ctrlmap.models.schemas import ParsedChunk


@pytest.fixture()
def store_with_chunks(tmp_path: Path):
    """A VectorStore populated with embedded test chunks."""
    from ctrlmap.index.embedder import Embedder
    from ctrlmap.index.vector_store import VectorStore

    store = VectorStore(db_path=tmp_path / "batch_db")
    embedder = Embedder()
    _text_1 = (
        "All employees must follow access control policies and procedures to protect resources."
    )
    _text_2 = "Data at rest must be encrypted using AES-256 encryption standards for all systems."
    chunks = [
        ParsedChunk(
            chunk_id="chunk-001",
            document_name="policy.pdf",
            page_number=1,
            raw_text=_text_1,
            embedding=embedder.embed_text(_text_1),
        ),
        ParsedChunk(
            chunk_id="chunk-002",
            document_name="policy.pdf",
            page_number=2,
            raw_text=_text_2,
            embedding=embedder.embed_text(_text_2),
        ),
    ]
    store.index_chunks("chunks", chunks)
    return store, embedder


class TestQueryByEmbedding:
    """query_by_embedding() accepts pre-computed vectors for batch query support."""

    def test_query_by_embedding_returns_results(
        self,
        store_with_chunks: tuple,
    ) -> None:
        """Querying by pre-computed embedding returns matching chunks."""
        from ctrlmap.index.query import query_by_embedding

        store, embedder = store_with_chunks
        embedding = embedder.embed_text("access control policies")

        results = query_by_embedding(
            store=store,
            collection_name="chunks",
            embedding=embedding,
            top_k=5,
        )
        assert len(results) > 0
        assert results[0].chunk_id == "chunk-001"

    def test_query_by_embedding_scores_are_valid(
        self,
        store_with_chunks: tuple,
    ) -> None:
        """Scores from query_by_embedding() are between 0 and 1."""
        from ctrlmap.index.query import query_by_embedding

        store, embedder = store_with_chunks
        embedding = embedder.embed_text("encryption AES-256")

        results = query_by_embedding(
            store=store,
            collection_name="chunks",
            embedding=embedding,
            top_k=5,
        )
        for r in results:
            assert 0.0 <= r.score <= 1.0

    def test_query_by_embedding_matches_text_query(
        self,
        store_with_chunks: tuple,
    ) -> None:
        """Pre-computed embedding query produces same results as text query."""
        from ctrlmap.index.query import query, query_by_embedding

        store, embedder = store_with_chunks
        query_text = "access control policies"
        embedding = embedder.embed_text(query_text)

        text_results = query(
            store=store,
            collection_name="chunks",
            query_text=query_text,
            top_k=5,
            embedder=embedder,
        )
        embed_results = query_by_embedding(
            store=store,
            collection_name="chunks",
            embedding=embedding,
            top_k=5,
        )

        assert len(text_results) == len(embed_results)
        for tr, er in zip(text_results, embed_results, strict=True):
            assert tr.chunk_id == er.chunk_id
            assert abs(tr.score - er.score) < 0.001
