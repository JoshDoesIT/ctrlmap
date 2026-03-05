"""Tests for the ChromaDB vector store.

TDD for Stories #12, #13, #14.
Ref: GitHub Issues #12, #13, #14.
"""

from __future__ import annotations

import pytest

from ctrlmap.index.vector_store import VectorStore
from ctrlmap.models.schemas import ParsedChunk


class TestVectorStoreInit:
    """Story #12: ChromaDB initialization tests."""

    def test_initialize_chromadb_creates_local_directory(self, tmp_path: object) -> None:
        """ChromaDB initializes and creates the local persistence directory."""
        from pathlib import Path

        db_path = Path(str(tmp_path)) / "test_db"
        store = VectorStore(db_path=db_path)
        assert store is not None
        assert db_path.exists()

    def test_chromadb_persists_across_sessions(self, tmp_path: object) -> None:
        """Data stored in one session is retrievable in a new session."""
        from pathlib import Path

        db_path = Path(str(tmp_path)) / "persist_db"

        # Session 1: create a collection and add data
        store1 = VectorStore(db_path=db_path)
        store1.get_or_create_collection("test_collection")

        # Session 2: new VectorStore instance, same path
        store2 = VectorStore(db_path=db_path)
        collections = store2.list_collections()
        assert "test_collection" in collections

    def test_chromadb_create_collection(self, tmp_path: object) -> None:
        """Creating a collection returns a usable collection object."""
        from pathlib import Path

        db_path = Path(str(tmp_path)) / "col_db"
        store = VectorStore(db_path=db_path)
        collection = store.get_or_create_collection("my_collection")
        assert collection is not None

    def test_chromadb_invalid_path_raises_error(self) -> None:
        """An invalid database path raises a clear error."""
        from pathlib import Path

        with pytest.raises((OSError, ValueError)):
            VectorStore(db_path=Path("/nonexistent/impossible/path/db"))


class TestVectorStoreIndexing:
    """Story #13: Rich metadata indexing tests."""

    @pytest.fixture()
    def store(self, tmp_path: object) -> VectorStore:
        """Create a fresh VectorStore for indexing tests."""
        from pathlib import Path

        return VectorStore(db_path=Path(str(tmp_path)) / "index_db")

    def _make_chunk(
        self,
        chunk_id: str = "chunk-001",
        document_name: str = "policy.pdf",
        page_number: int = 1,
        raw_text: str = "Organizations shall implement access control policies and procedures.",
        section_header: str | None = "Access Control",
        embedding: list[float] | None = None,
    ) -> ParsedChunk:
        """Helper to create a ParsedChunk with default values."""
        return ParsedChunk(
            chunk_id=chunk_id,
            document_name=document_name,
            page_number=page_number,
            raw_text=raw_text,
            section_header=section_header,
            embedding=embedding or [0.1] * 384,
        )

    def test_index_parsed_chunks_stores_vectors(self, store: VectorStore) -> None:
        """Indexing stores chunk embeddings in the collection."""
        chunks = [self._make_chunk(chunk_id=f"c-{i}") for i in range(3)]
        count = store.index_chunks("test_col", chunks)
        assert count == 3

        collection = store.get_or_create_collection("test_col")
        assert collection.count() == 3

    def test_index_stores_metadata(self, store: VectorStore) -> None:
        """Each indexed chunk retains its metadata fields."""
        chunk = self._make_chunk(
            chunk_id="meta-001",
            document_name="soc2.pdf",
            page_number=5,
            section_header="Logging",
        )
        store.index_chunks("meta_col", [chunk])

        collection = store.get_or_create_collection("meta_col")
        result = collection.get(ids=["meta-001"], include=["metadatas"])
        metadata = result["metadatas"][0]
        assert metadata["document_name"] == "soc2.pdf"
        assert metadata["page_number"] == 5
        assert metadata["section_header"] == "Logging"

    def test_index_handles_duplicate_chunk_ids(self, store: VectorStore) -> None:
        """Duplicate chunk_ids are upserted (updated, not duplicated)."""
        chunk_v1 = self._make_chunk(
            chunk_id="dup-001",
            raw_text="Original access control text content for compliance testing.",
        )
        chunk_v2 = self._make_chunk(
            chunk_id="dup-001",
            raw_text="Updated access control text content for compliance testing.",
        )
        store.index_chunks("dup_col", [chunk_v1])
        store.index_chunks("dup_col", [chunk_v2])

        collection = store.get_or_create_collection("dup_col")
        assert collection.count() == 1

        result = collection.get(ids=["dup-001"], include=["documents"])
        assert (
            result["documents"][0] == "Updated access control text content for compliance testing."
        )

    def test_index_large_batch_completes_within_limits(self, store: VectorStore) -> None:
        """Indexing a large batch completes successfully."""
        chunks = [
            self._make_chunk(
                chunk_id=f"batch-{i:04d}",
                raw_text=f"Control requirement number {i} for compliance testing verification.",
            )
            for i in range(100)
        ]
        count = store.index_chunks("batch_col", chunks)
        assert count == 100

        collection = store.get_or_create_collection("batch_col")
        assert collection.count() == 100


class TestVectorStoreQuery:
    """Story #14: ANN query with metadata filtering tests."""

    @pytest.fixture()
    def populated_store(self, tmp_path: object) -> VectorStore:
        """Create a VectorStore populated with test data for query tests."""
        from pathlib import Path

        from ctrlmap.index.embedder import Embedder

        store = VectorStore(db_path=Path(str(tmp_path)) / "query_db")
        embedder = Embedder()

        chunks = [
            ParsedChunk(
                chunk_id="ac-001",
                document_name="nist_policy.pdf",
                page_number=1,
                raw_text="Multi-factor authentication must be enabled for all system users.",
                section_header="Access Control",
                embedding=embedder.embed_text(
                    "Multi-factor authentication must be enabled for all system users."
                ),
            ),
            ParsedChunk(
                chunk_id="ac-002",
                document_name="nist_policy.pdf",
                page_number=2,
                raw_text="Role-based access control restricts user permissions by function.",
                section_header="Access Control",
                embedding=embedder.embed_text(
                    "Role-based access control restricts user permissions by function."
                ),
            ),
            ParsedChunk(
                chunk_id="au-001",
                document_name="nist_policy.pdf",
                page_number=5,
                raw_text="Audit logs must be retained for at least one full calendar year.",
                section_header="Audit & Accountability",
                embedding=embedder.embed_text(
                    "Audit logs must be retained for at least one full calendar year."
                ),
            ),
            ParsedChunk(
                chunk_id="soc-001",
                document_name="soc2_report.pdf",
                page_number=1,
                raw_text="Authentication mechanisms include password and biometric controls.",
                section_header="Logical Access",
                embedding=embedder.embed_text(
                    "Authentication mechanisms include password and biometric controls."
                ),
            ),
        ]
        store.index_chunks("controls", chunks)
        return store

    def test_query_returns_top_k_results(self, populated_store: VectorStore) -> None:
        """Query returns at most top-K results."""
        from ctrlmap.index.query import query

        results = query(
            store=populated_store,
            collection_name="controls",
            query_text="authentication requirements",
            top_k=2,
        )
        assert len(results) == 2

    def test_query_results_include_similarity_scores(self, populated_store: VectorStore) -> None:
        """Each query result includes a cosine similarity score."""
        from ctrlmap.index.query import query

        results = query(
            store=populated_store,
            collection_name="controls",
            query_text="access control",
            top_k=3,
        )
        assert all(hasattr(r, "score") for r in results)
        assert all(isinstance(r.score, float) for r in results)

    def test_query_filters_by_document_name(self, populated_store: VectorStore) -> None:
        """Metadata filter constrains results to a specific document."""
        from ctrlmap.index.query import query

        results = query(
            store=populated_store,
            collection_name="controls",
            query_text="authentication",
            top_k=10,
            filters={"document_name": "soc2_report.pdf"},
        )
        assert len(results) >= 1
        assert all(r.metadata["document_name"] == "soc2_report.pdf" for r in results)

    def test_query_filters_by_section_header(self, populated_store: VectorStore) -> None:
        """Metadata filter constrains results to a specific section."""
        from ctrlmap.index.query import query

        results = query(
            store=populated_store,
            collection_name="controls",
            query_text="access",
            top_k=10,
            filters={"section_header": "Access Control"},
        )
        assert len(results) >= 1
        assert all(r.metadata["section_header"] == "Access Control" for r in results)

    def test_query_with_no_matches_returns_empty(self, populated_store: VectorStore) -> None:
        """Query against an empty collection returns an empty list gracefully."""
        from ctrlmap.index.query import query

        # Query a collection that doesn't have relevant data
        results = query(
            store=populated_store,
            collection_name="controls",
            query_text="chocolate cake recipe baking",
            top_k=2,
            filters={"document_name": "nonexistent_doc.pdf"},
        )
        assert results == []
