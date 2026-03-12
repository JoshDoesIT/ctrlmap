"""Hybrid search combining BM25 keyword matching with ANN vector search.

Uses Reciprocal Rank Fusion (RRF) to merge BM25 and vector search results
into a single ranked list. BM25 excels at exact terminology matches
("AES-256", "MFA", "RBAC") while vectors handle paraphrasing.

.. versionadded:: 0.9.0
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from rank_bm25 import BM25Okapi  # type: ignore[import-untyped]

from ctrlmap.index.query import QueryResult, query_by_embedding
from ctrlmap.index.vector_store import VectorStore

# Default RRF constant (controls how much rank position matters)
_RRF_K = 60


@dataclass
class BM25Index:
    """In-memory BM25 index over chunk texts.

    Attributes:
        chunk_ids: Ordered list of chunk IDs matching the BM25 corpus.
        raw_texts: Ordered list of raw chunk texts.
        bm25: The BM25Okapi instance.
    """

    chunk_ids: list[str] = field(default_factory=list)
    raw_texts: list[str] = field(default_factory=list)
    metadatas: list[dict[str, object]] = field(default_factory=list)
    bm25: BM25Okapi | None = None

    @classmethod
    def from_chunks(
        cls,
        chunk_ids: list[str],
        raw_texts: list[str],
        metadatas: list[dict[str, object]] | None = None,
    ) -> BM25Index:
        """Build a BM25 index from chunk texts.

        Args:
            chunk_ids: Unique identifiers for each chunk.
            raw_texts: Raw text content of each chunk.
            metadatas: Optional metadata dicts for each chunk.

        Returns:
            A populated BM25Index instance.
        """
        tokenized = [_tokenize(text) for text in raw_texts]
        bm25 = BM25Okapi(tokenized) if tokenized else None
        return cls(
            chunk_ids=list(chunk_ids),
            raw_texts=list(raw_texts),
            metadatas=list(metadatas) if metadatas else [{} for _ in raw_texts],
            bm25=bm25,
        )


def _tokenize(text: str) -> list[str]:
    """Simple whitespace + punctuation tokenizer for BM25."""
    return re.findall(r"\w+", text.lower())


def bm25_query(
    index: BM25Index,
    query_text: str,
    top_k: int = 10,
) -> list[QueryResult]:
    """Query the BM25 index and return ranked results.

    Args:
        index: The BM25 index to search.
        query_text: The query text.
        top_k: Maximum results to return.

    Returns:
        A list of QueryResult objects ranked by BM25 score.
    """
    if index.bm25 is None or not index.chunk_ids:
        return []

    tokenized_query = _tokenize(query_text)
    scores = index.bm25.get_scores(tokenized_query)

    # Get top-k by score
    scored = sorted(
        enumerate(scores),
        key=lambda x: x[1],
        reverse=True,
    )[:top_k]

    return [
        QueryResult(
            chunk_id=index.chunk_ids[idx],
            raw_text=index.raw_texts[idx],
            score=float(score),
            metadata=dict(index.metadatas[idx]),
        )
        for idx, score in scored
        if score > 0
    ]


def hybrid_query(
    *,
    store: VectorStore,
    collection_name: str,
    embedding: list[float],
    query_text: str,
    bm25_index: BM25Index,
    top_k: int = 5,
    rrf_k: int = _RRF_K,
) -> list[QueryResult]:
    """Combine ANN vector search with BM25 using Reciprocal Rank Fusion.

    Runs both searches independently, then merges results using RRF:
    ``score(d) = 1/(k + rank_vector(d)) + 1/(k + rank_bm25(d))``

    Args:
        store: VectorStore for ANN search.
        collection_name: ChromaDB collection name.
        embedding: Pre-computed query embedding.
        query_text: Raw query text for BM25.
        bm25_index: Pre-built BM25 index.
        top_k: Number of final results to return.
        rrf_k: RRF constant (default: 60).

    Returns:
        Merged and re-ranked list of QueryResult objects.
    """
    # Get ANN results (fetch more than needed for better fusion)
    ann_results = query_by_embedding(
        store=store,
        collection_name=collection_name,
        embedding=embedding,
        top_k=top_k * 2,
    )

    # Get BM25 results
    bm25_results = bm25_query(bm25_index, query_text, top_k=top_k * 2)

    # Build rank maps (chunk_id → rank position, 1-indexed)
    ann_ranks: dict[str, int] = {r.chunk_id: i + 1 for i, r in enumerate(ann_results)}
    bm25_ranks: dict[str, int] = {r.chunk_id: i + 1 for i, r in enumerate(bm25_results)}

    # Collect all unique chunk IDs
    all_ids = set(ann_ranks.keys()) | set(bm25_ranks.keys())

    # Build a lookup for the actual QueryResult data
    result_lookup: dict[str, QueryResult] = {}
    for r in ann_results:
        result_lookup[r.chunk_id] = r
    for r in bm25_results:
        if r.chunk_id not in result_lookup:
            result_lookup[r.chunk_id] = r

    # Compute RRF scores
    rrf_scores: list[tuple[str, float]] = []
    for chunk_id in all_ids:
        rrf_score = 0.0
        if chunk_id in ann_ranks:
            rrf_score += 1.0 / (rrf_k + ann_ranks[chunk_id])
        if chunk_id in bm25_ranks:
            rrf_score += 1.0 / (rrf_k + bm25_ranks[chunk_id])
        rrf_scores.append((chunk_id, rrf_score))

    # Sort by RRF score descending, take top_k
    rrf_scores.sort(key=lambda x: x[1], reverse=True)

    # Normalize RRF scores to [0, 1] range.
    # Theoretical max: 2/(k+1) when a doc ranks #1 in both lists.
    max_rrf = 2.0 / (rrf_k + 1)

    return [
        QueryResult(
            chunk_id=chunk_id,
            raw_text=result_lookup[chunk_id].raw_text,
            score=min(rrf_score / max_rrf, 1.0) if max_rrf > 0 else 0.0,
            metadata=result_lookup[chunk_id].metadata,
        )
        for chunk_id, rrf_score in rrf_scores[:top_k]
    ]
