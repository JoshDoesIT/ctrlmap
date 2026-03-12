"""Core mapping algorithm: control → vector DB → ranked chunks.

Iterates through SecurityControl objects, queries the vector database
for top-K matching policy chunks, and returns MappedResult objects
ranked by cosine similarity.

Performance:
    Builds all query texts upfront and uses ``embed_batch()`` for a
    single vectorization pass, then queries ChromaDB with pre-computed
    embeddings via ``hybrid_query()`` (BM25 + ANN fusion).

.. versionchanged:: 0.10.0
   Added GRC instruction prefix for improved embedding retrieval.
   Removed domain-aware boost/penalty heuristics.

Ref: GitHub Issue #16.
"""

from __future__ import annotations

import functools
import json
import logging
from pathlib import Path
from typing import cast

from ctrlmap.index.embedder import Embedder
from ctrlmap.index.hybrid_search import BM25Index, hybrid_query
from ctrlmap.index.query import query_by_embedding
from ctrlmap.index.vector_store import VectorStore
from ctrlmap.models.schemas import MappedResult, ParsedChunk, SecurityControl

_log = logging.getLogger(__name__)
_EXPANSION_MAP_FILE = Path(__file__).parent / "expansion_map.json"

# GRC instruction prefix: steers the embedding model toward compliance
# semantics by framing queries in the GRC domain.
_GRC_QUERY_PREFIX = (
    "Retrieve policy documentation that provides evidence of compliance "
    "with this security control requirement: "
)


@functools.cache
def _load_expansion_map() -> dict[str, str]:
    """Load the query expansion map from the JSON data file.

    Returns:
        A dict mapping abstract GRC concepts to domain-specific synonyms.
    """
    return cast(dict[str, str], json.loads(_EXPANSION_MAP_FILE.read_text(encoding="utf-8")))


def _expand_query(query_text: str) -> str:
    """Expand abstract control descriptions with domain-specific terms.

    Scans the query text for abstract GRC concepts from ``_EXPANSION_MAP``
    and appends relevant domain synonyms to improve vector search recall.

    Args:
        query_text: The original query string.

    Returns:
        The query string, possibly augmented with expansion terms.
    """
    lower = query_text.lower()
    expansions: list[str] = []

    for concept, terms in _load_expansion_map().items():
        if concept in lower:
            expansions.append(terms)

    if expansions:
        return f"{query_text} [{'; '.join(expansions)}]"
    return query_text


def _build_bm25_index(store: VectorStore, collection_name: str) -> BM25Index:
    """Build a BM25 index from all chunks in a ChromaDB collection.

    Args:
        store: The VectorStore instance.
        collection_name: Name of the ChromaDB collection.

    Returns:
        A BM25Index ready for keyword searching.
    """
    collection = store.get_or_create_collection(collection_name)
    all_data = collection.get(include=["documents", "metadatas"])

    chunk_ids = all_data.get("ids", [])
    raw_texts = all_data.get("documents", [])
    metadatas = all_data.get("metadatas", [])

    _log.info("Built BM25 index with %d chunks", len(chunk_ids))

    return BM25Index.from_chunks(
        chunk_ids=chunk_ids or [],
        raw_texts=raw_texts or [],
        metadatas=metadatas or [],  # type: ignore[arg-type]
    )


def map_controls(
    *,
    controls: list[SecurityControl],
    store: VectorStore,
    collection_name: str,
    top_k: int = 3,
    min_score: float = 0.55,
    embedder: Embedder | None = None,
) -> list[MappedResult]:
    """Map security controls to supporting policy chunks via hybrid search.

    For each control, runs hybrid BM25 + ANN search with Reciprocal Rank
    Fusion (RRF) to find the top-K most relevant policy chunks. Results
    are filtered by ``min_score``.

    Queries are prefixed with a GRC instruction to steer the embedding
    model toward compliance semantics and expanded with domain synonyms.

    Uses batch embedding for performance: all query texts are embedded
    in a single pass via ``embed_batch()``.

    Args:
        controls: List of SecurityControl objects to map.
        store: The VectorStore instance containing indexed policy chunks.
        collection_name: Name of the ChromaDB collection to search.
        top_k: Maximum number of supporting chunks per control.
        min_score: Minimum similarity score to include a chunk.
            Chunks below this threshold are dropped to avoid false matches.
        embedder: Optional Embedder instance. Creates a default one if None.

    Returns:
        A list of ``MappedResult`` objects, one per input control.
    """
    if embedder is None:
        embedder = Embedder()

    # Build BM25 index from the collection for keyword search
    bm25_index = _build_bm25_index(store, collection_name)

    # Build two query variants per control:
    # - embedding_query: with GRC prefix (steers ANN toward compliance semantics)
    # - bm25_query_text: without prefix (avoids noise keywords in BM25)
    embedding_queries: list[str] = []
    bm25_queries: list[str] = []
    for control in controls:
        raw_query = control.as_prompt_text()
        if control.requirement_family:
            raw_query = f"[{control.requirement_family}] {raw_query}"
        raw_query = _expand_query(raw_query)
        bm25_queries.append(raw_query)
        embedding_queries.append(_GRC_QUERY_PREFIX + raw_query)

    # Batch embed all queries in one pass
    embeddings = embedder.embed_batch(embedding_queries)

    results: list[MappedResult] = []

    for control, embedding, bm25_query_text in zip(
        controls, embeddings, bm25_queries, strict=True
    ):
        # Use hybrid search (BM25 + ANN fusion via RRF)
        if bm25_index.bm25 is not None:
            query_results = hybrid_query(
                store=store,
                collection_name=collection_name,
                embedding=embedding,
                query_text=bm25_query_text,
                bm25_index=bm25_index,
                top_k=top_k,
            )
        else:
            # Fallback to ANN-only if BM25 index is empty
            query_results = query_by_embedding(
                store=store,
                collection_name=collection_name,
                embedding=embedding,
                top_k=top_k,
            )

        supporting_chunks: list[ParsedChunk] = []
        for qr in query_results:
            if qr.score < min_score:
                continue
            supporting_chunks.append(
                ParsedChunk(
                    chunk_id=qr.chunk_id,
                    document_name=qr.metadata.get("document_name", ""),
                    page_number=int(qr.metadata.get("page_number", 1)),
                    raw_text=qr.raw_text,
                    section_header=qr.metadata.get("section_header") or None,
                )
            )

        results.append(
            MappedResult(
                control=control,
                supporting_chunks=supporting_chunks,
            )
        )

    return results

