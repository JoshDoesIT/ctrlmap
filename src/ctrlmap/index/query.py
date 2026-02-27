"""ANN query mechanism with metadata filtering.

Performs approximate nearest neighbor similarity searches against
ChromaDB collections with optional metadata filtering to prevent
cross-contamination during multi-document assessments.

Ref: GitHub Issue #14.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ctrlmap.index.embedder import Embedder
from ctrlmap.index.vector_store import VectorStore


@dataclass
class QueryResult:
    """A single ANN query result with similarity score and metadata.

    Attributes:
        chunk_id: The unique identifier of the matched chunk.
        raw_text: The original text content of the chunk.
        score: Cosine similarity score (higher = more similar).
        metadata: Dictionary of metadata fields (document_name, page_number, etc.).
    """

    chunk_id: str
    raw_text: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


def query(
    *,
    store: VectorStore,
    collection_name: str,
    query_text: str,
    top_k: int = 5,
    filters: dict[str, str] | None = None,
    embedder: Embedder | None = None,
) -> list[QueryResult]:
    """Perform an ANN similarity search with optional metadata filtering.

    Args:
        store: The VectorStore instance to query.
        collection_name: Name of the ChromaDB collection to search.
        query_text: The text to find similar chunks for.
        top_k: Maximum number of results to return (default: 5).
        filters: Optional metadata filters (AND logic). Keys can be
            ``document_name`` or ``section_header``.
        embedder: Optional Embedder instance. Creates a default one if None.

    Returns:
        A list of ``QueryResult`` objects sorted by similarity (descending).
        Returns an empty list if no matches are found.
    """
    if embedder is None:
        embedder = Embedder()

    query_embedding = embedder.embed_text(query_text)
    collection = store.get_or_create_collection(collection_name)

    # Build ChromaDB where clause from filters
    where: dict[str, Any] | None = None
    if filters:
        conditions: list[dict[str, Any]] = [{k: {"$eq": v}} for k, v in filters.items()]
        where = conditions[0] if len(conditions) == 1 else {"$and": conditions}

    results = collection.query(
        query_embeddings=[query_embedding],  # type: ignore[arg-type]
        n_results=top_k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    # ChromaDB returns distances (lower = more similar for L2, higher for cosine).
    # ChromaDB uses squared L2 distance by default; we convert to a similarity score.
    query_results: list[QueryResult] = []

    ids = (results.get("ids") or [[]])[0]
    documents = (results.get("documents") or [[]])[0]
    metadatas = (results.get("metadatas") or [[]])[0]
    distances = (results.get("distances") or [[]])[0]

    for i, chunk_id in enumerate(ids):
        # Convert L2 distance to a pseudo-similarity score (1 / (1 + distance))
        distance = distances[i] if distances else 0.0
        score = 1.0 / (1.0 + distance)

        query_results.append(
            QueryResult(
                chunk_id=chunk_id,
                raw_text=documents[i] if documents else "",
                score=score,
                metadata=dict(metadatas[i]) if metadatas else {},
            )
        )

    return query_results
