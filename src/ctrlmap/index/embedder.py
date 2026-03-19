"""Sentence-Transformers embedding pipeline.

Wraps the ``sentence-transformers`` library to convert text payloads into
high-dimensional vector representations. All computation runs locally,
no external API calls.

Ref: GitHub Issue #11.
"""

from __future__ import annotations

import functools
from typing import cast

from sentence_transformers import SentenceTransformer

from ctrlmap._defaults import DEFAULT_EMBEDDING_MODEL


@functools.cache
def _load_model(model_name: str) -> SentenceTransformer:
    """Load a SentenceTransformer model (cached per model name).

    First call loads the model (~1-2s); subsequent calls return
    the cached instance immediately.
    """
    return SentenceTransformer(model_name)


class Embedder:
    """Local embedding pipeline backed by Sentence-Transformers.

    Args:
        model_name: The Sentence-Transformers model to load.
            Defaults to ``all-MiniLM-L6-v2`` (lightweight, CPU-friendly).

    The underlying model is cached per ``model_name`` and shared across
    all ``Embedder`` instances in the same process.
    """

    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL) -> None:
        self._model = _load_model(model_name)
        self._cache: dict[str, list[float]] = {}

    def embed_text(self, text: str) -> list[float]:
        """Embed a single text string into a float vector.

        Args:
            text: The input text to embed.

        Returns:
            A list of floats representing the embedding vector.
        """
        vector = self._model.encode(text, convert_to_numpy=True)
        return cast(list[float], vector.tolist())

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts in a single batch for performance.

        Args:
            texts: A list of input texts to embed.

        Returns:
            A list of float vectors, one per input text.
        """
        vectors = self._model.encode(texts, convert_to_numpy=True)
        return [v.tolist() for v in vectors]

    def contextual_embed_batch(
        self,
        texts: list[str],
        contexts: list[str],
    ) -> list[list[float]]:
        """Embed texts with contextual prefixes for richer vectors.

        Prepends each context string to its corresponding text before
        encoding.  The context typically contains document name and
        section header metadata (e.g. ``[policy.pdf | Access Control]``).

        Args:
            texts: Raw text strings to embed.
            contexts: Context prefix for each text (same length as *texts*).

        Returns:
            A list of float vectors, one per input text.
        """
        enriched = [f"{ctx} {txt}" for ctx, txt in zip(texts, contexts, strict=True)]
        vectors = self._model.encode(enriched, convert_to_numpy=True)
        return [v.tolist() for v in vectors]

    def embed_batch_cached(self, texts: list[str]) -> list[list[float]]:
        """Embed texts with in-memory caching to avoid recomputation.

        Texts already in the cache are returned directly; only unseen
        texts are sent to the model.

        Args:
            texts: A list of input texts to embed.

        Returns:
            A list of float vectors, one per input text.
        """
        uncached_indices: list[int] = []
        uncached_texts: list[str] = []
        for i, text in enumerate(texts):
            if text not in self._cache:
                uncached_indices.append(i)
                uncached_texts.append(text)

        if uncached_texts:
            vectors = self._model.encode(uncached_texts, convert_to_numpy=True)
            for idx, vec in zip(uncached_indices, vectors, strict=True):
                self._cache[texts[idx]] = vec.tolist()

        return [self._cache[text] for text in texts]

    def clear_cache(self) -> None:
        """Clear the in-memory embedding cache."""
        self._cache.clear()
