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
