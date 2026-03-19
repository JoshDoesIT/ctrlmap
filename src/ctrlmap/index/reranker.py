"""Cross-encoder reranker for improving retrieval precision.

After hybrid search retrieves candidates, the reranker re-scores each
candidate using a cross-encoder model that sees both the query and
candidate text jointly.  This dramatically improves precision compared
to embedding-only similarity.

The cross-encoder model is loaded once and cached for the process
lifetime (same pattern as ``Embedder``).

.. versionadded:: 0.10.0
"""

from __future__ import annotations

import functools

from sentence_transformers import CrossEncoder

from ctrlmap.index.query import QueryResult

# Default cross-encoder model — fast and effective for passage reranking
_DEFAULT_RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-12-v2"


@functools.cache
def _load_reranker(model_name: str) -> CrossEncoder:
    """Load a CrossEncoder model (cached per model name).

    First call loads the model; subsequent calls return the cached
    instance immediately.
    """
    return CrossEncoder(model_name)  # type: ignore[no-any-return]


class Reranker:
    """Cross-encoder reranker for passage relevance scoring.

    Args:
        model_name: The cross-encoder model to load.  Defaults to
            ``cross-encoder/ms-marco-MiniLM-L-12-v2``.

    The underlying model is cached per ``model_name`` and shared across
    all ``Reranker`` instances in the same process.
    """

    def __init__(self, model_name: str = _DEFAULT_RERANKER_MODEL) -> None:
        self._model = _load_reranker(model_name)

    def rerank(
        self,
        query: str,
        candidates: list[QueryResult],
        top_k: int = 5,
    ) -> list[QueryResult]:
        """Re-score and re-sort candidates by cross-encoder relevance.

        Args:
            query: The original query text.
            candidates: List of candidate results from retrieval.
            top_k: Maximum number of results to return.

        Returns:
            A list of ``QueryResult`` objects re-sorted by cross-encoder
            score (highest first), limited to *top_k*.
        """
        if not candidates:
            return []

        # Build (query, candidate) pairs for the cross-encoder
        pairs = [(query, c.raw_text) for c in candidates]
        scores = self._model.predict(pairs)

        # Pair each candidate with its cross-encoder score
        scored = sorted(
            zip(candidates, scores, strict=True),
            key=lambda x: float(x[1]),
            reverse=True,
        )

        return [
            QueryResult(
                chunk_id=candidate.chunk_id,
                raw_text=candidate.raw_text,
                score=float(score),
                metadata=candidate.metadata,
            )
            for candidate, score in scored[:top_k]
        ]
