"""Core mapping algorithm: control → vector DB → ranked chunks.

Iterates through SecurityControl objects, queries the vector database
for top-K matching policy chunks, and returns MappedResult objects
ranked by cosine similarity.

Ref: GitHub Issue #16.
"""

from __future__ import annotations

from ctrlmap.index.embedder import Embedder
from ctrlmap.index.query import query
from ctrlmap.index.vector_store import VectorStore
from ctrlmap.models.schemas import MappedResult, ParsedChunk, SecurityControl


def map_controls(
    *,
    controls: list[SecurityControl],
    store: VectorStore,
    collection_name: str,
    top_k: int = 5,
    embedder: Embedder | None = None,
) -> list[MappedResult]:
    """Map security controls to supporting policy chunks via vector similarity.

    For each control, queries the vector DB for the top-K most similar
    policy chunks and returns a ``MappedResult`` with the ranked matches.

    Args:
        controls: List of SecurityControl objects to map.
        store: The VectorStore instance containing indexed policy chunks.
        collection_name: Name of the ChromaDB collection to search.
        top_k: Maximum number of supporting chunks per control (default: 5).
        embedder: Optional Embedder instance. Creates a default one if None.

    Returns:
        A list of ``MappedResult`` objects, one per input control.
    """
    if embedder is None:
        embedder = Embedder()

    results: list[MappedResult] = []

    for control in controls:
        query_text = f"{control.control_id}: {control.title}. {control.description}"

        query_results = query(
            store=store,
            collection_name=collection_name,
            query_text=query_text,
            top_k=top_k,
            embedder=embedder,
        )

        supporting_chunks: list[ParsedChunk] = []
        for qr in query_results:
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
