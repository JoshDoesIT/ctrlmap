"""Core mapping algorithm: control → vector DB → ranked chunks.

Iterates through SecurityControl objects, queries the vector database
for top-K matching policy chunks, and returns MappedResult objects
ranked by cosine similarity.

Performance:
    Builds all query texts upfront and uses ``embed_batch()`` for a
    single vectorization pass, then queries ChromaDB with pre-computed
    embeddings via ``query_by_embedding()``.

Ref: GitHub Issue #16.
"""

from __future__ import annotations

import functools
import json
from pathlib import Path
from typing import cast

from ctrlmap.index.embedder import Embedder
from ctrlmap.index.query import query_by_embedding
from ctrlmap.index.vector_store import VectorStore
from ctrlmap.models.schemas import MappedResult, ParsedChunk, SecurityControl

_EXPANSION_MAP_FILE = Path(__file__).parent / "expansion_map.json"


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


def map_controls(
    *,
    controls: list[SecurityControl],
    store: VectorStore,
    collection_name: str,
    top_k: int = 5,
    min_score: float = 0.50,
    embedder: Embedder | None = None,
) -> list[MappedResult]:
    """Map security controls to supporting policy chunks via vector similarity.

    For each control, queries the vector DB for the top-K most similar
    policy chunks and filters out results below ``min_score`` to prevent
    weak/irrelevant matches from appearing as false positives.

    Uses batch embedding for performance: all query texts are embedded
    in a single pass via ``embed_batch()``, then each pre-computed
    embedding is used for ANN search via ``query_by_embedding()``.

    Args:
        controls: List of SecurityControl objects to map.
        store: The VectorStore instance containing indexed policy chunks.
        collection_name: Name of the ChromaDB collection to search.
        top_k: Maximum number of supporting chunks per control (default: 10).
        min_score: Minimum similarity score to include a chunk (default: 0.35).
            Chunks below this threshold are dropped to avoid false matches.
        embedder: Optional Embedder instance. Creates a default one if None.

    Returns:
        A list of ``MappedResult`` objects, one per input control.
    """
    if embedder is None:
        embedder = Embedder()

    # Build all query texts upfront
    query_texts: list[str] = []
    for control in controls:
        query_text = control.as_prompt_text()
        if control.requirement_family:
            query_text = f"[{control.requirement_family}] {query_text}"
        query_text = _expand_query(query_text)
        query_texts.append(query_text)

    # Batch embed all queries in one pass
    embeddings = embedder.embed_batch(query_texts)

    results: list[MappedResult] = []

    for control, embedding in zip(controls, embeddings, strict=True):
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
