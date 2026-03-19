"""Tests for the Sentence-Transformers embedding pipeline.

TDD RED phase for Story #11.
Ref: GitHub Issue #11.
"""

from __future__ import annotations

import numpy as np
import pytest

from ctrlmap.index.embedder import Embedder


class TestEmbedder:
    """Sentence-Transformers embedding pipeline tests."""

    @pytest.fixture()
    def embedder(self) -> Embedder:
        """Create an Embedder with the default lightweight model."""
        return Embedder()

    def test_embed_text_returns_float_vector(self, embedder: Embedder) -> None:
        """Embedding a text string returns a list of floats."""
        result = embedder.embed_text("Access control policy requires MFA.")
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(v, float) for v in result)

    def test_embed_identical_text_produces_identical_vectors(self, embedder: Embedder) -> None:
        """Identical inputs produce deterministic, identical embeddings."""
        text = "Audit logging must be enabled on all production systems."
        vec_a = embedder.embed_text(text)
        vec_b = embedder.embed_text(text)
        assert vec_a == vec_b

    def test_embed_batch_returns_correct_count(self, embedder: Embedder) -> None:
        """Batch embedding returns one vector per input text."""
        texts = [
            "Implement role-based access control.",
            "All data must be encrypted at rest.",
            "Vulnerability scans run weekly.",
        ]
        results = embedder.embed_batch(texts)
        assert len(results) == 3
        assert all(isinstance(vec, list) for vec in results)
        assert all(isinstance(v, float) for vec in results for v in vec)

    def test_similar_texts_have_high_cosine_similarity(self, embedder: Embedder) -> None:
        """Semantically similar texts produce vectors with high cosine similarity."""
        vec_a = embedder.embed_text("Implement multi-factor authentication.")
        vec_b = embedder.embed_text("Require MFA for all user logins.")
        similarity = _cosine_similarity(vec_a, vec_b)
        assert similarity > 0.5

    def test_dissimilar_texts_have_low_cosine_similarity(self, embedder: Embedder) -> None:
        """Semantically unrelated texts produce vectors with low cosine similarity."""
        vec_a = embedder.embed_text("Implement multi-factor authentication.")
        vec_b = embedder.embed_text("The recipe calls for two cups of flour.")
        similarity = _cosine_similarity(vec_a, vec_b)
        assert similarity < 0.4


class TestContextualEmbedding:
    """Contextual embedding prepends document/section metadata for richer vectors."""

    @pytest.fixture()
    def embedder(self) -> Embedder:
        return Embedder()

    def test_contextual_embed_batch_returns_correct_count(self, embedder: Embedder) -> None:
        """contextual_embed_batch returns one vector per input."""
        texts = ["Access control policy requires MFA.", "Encryption at rest."]
        contexts = ["[policy.pdf | Access Control]", "[policy.pdf | Encryption]"]
        results = embedder.contextual_embed_batch(texts, contexts)
        assert len(results) == 2
        assert all(isinstance(vec, list) for vec in results)

    def test_contextual_embed_produces_different_vector_than_raw(self, embedder: Embedder) -> None:
        """Embedding with context prefix should produce a different vector than raw text."""
        text = "All users must authenticate."
        raw_vec = embedder.embed_text(text)
        contextual_vecs = embedder.contextual_embed_batch(
            [text], ["[Access Control Policy | Authentication]"]
        )
        # Vectors should differ because the model sees different input
        assert raw_vec != contextual_vecs[0]


class TestEmbedBatchCached:
    """Cached embedding avoids recomputing for identical texts."""

    @pytest.fixture()
    def embedder(self) -> Embedder:
        return Embedder()

    def test_embed_batch_cached_returns_same_result(self, embedder: Embedder) -> None:
        """Cached results are identical to fresh results."""
        texts = ["Implement MFA.", "Encrypt data at rest."]
        first = embedder.embed_batch_cached(texts)
        second = embedder.embed_batch_cached(texts)
        assert first == second

    def test_embed_batch_cached_avoids_recompute(self, embedder: Embedder) -> None:
        """Second call to embed_batch_cached should not re-encode."""
        from unittest.mock import patch

        texts = ["Implement MFA.", "Encrypt data at rest."]
        # Prime the cache
        embedder.embed_batch_cached(texts)
        # Now patch encode — it should NOT be called
        with patch.object(embedder._model, "encode", wraps=embedder._model.encode) as mock_enc:
            embedder.embed_batch_cached(texts)
            mock_enc.assert_not_called()

    def test_clear_cache_resets_cached_embeddings(self, embedder: Embedder) -> None:
        """clear_cache() should force recomputation on next call."""
        texts = ["Implement MFA."]
        embedder.embed_batch_cached(texts)
        embedder.clear_cache()
        # After clearing, the cache should be empty
        from unittest.mock import patch

        with patch.object(embedder._model, "encode", wraps=embedder._model.encode) as mock_enc:
            embedder.embed_batch_cached(texts)
            assert mock_enc.call_count == 1


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    arr_a = np.array(a)
    arr_b = np.array(b)
    return float(np.dot(arr_a, arr_b) / (np.linalg.norm(arr_a) * np.linalg.norm(arr_b)))
