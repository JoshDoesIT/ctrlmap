"""Tests for the LLM response cache.

TDD RED phase: Content-addressable LLM response caching for
the performance optimization feature.
"""

from __future__ import annotations

from pathlib import Path


class TestLLMCache:
    """LLM response cache uses SHA-256 of (model + prompt) as key."""

    def test_cache_miss_returns_none(self, tmp_path: Path) -> None:
        """Cache returns None for unseen prompts."""
        from ctrlmap.llm.cache import LLMCache

        cache = LLMCache(cache_dir=tmp_path)
        result = cache.get(model="llama3", prompt="never seen before")
        assert result is None

    def test_cache_hit_returns_stored_response(self, tmp_path: Path) -> None:
        """Cache returns previously stored responses."""
        from ctrlmap.llm.cache import LLMCache

        cache = LLMCache(cache_dir=tmp_path)
        cache.put(model="llama3", prompt="test prompt", response="test response")
        result = cache.get(model="llama3", prompt="test prompt")
        assert result == "test response"

    def test_cache_key_includes_model(self, tmp_path: Path) -> None:
        """Different models produce different cache keys for the same prompt."""
        from ctrlmap.llm.cache import LLMCache

        cache = LLMCache(cache_dir=tmp_path)
        cache.put(model="llama3", prompt="same prompt", response="llama3 response")
        cache.put(model="qwen2.5:14b", prompt="same prompt", response="qwen response")

        assert cache.get(model="llama3", prompt="same prompt") == "llama3 response"
        assert cache.get(model="qwen2.5:14b", prompt="same prompt") == "qwen response"

    def test_cache_persists_across_instances(self, tmp_path: Path) -> None:
        """Cache data survives creating a new instance with the same path."""
        from ctrlmap.llm.cache import LLMCache

        cache1 = LLMCache(cache_dir=tmp_path)
        cache1.put(model="llama3", prompt="persistent", response="persisted value")

        cache2 = LLMCache(cache_dir=tmp_path)
        assert cache2.get(model="llama3", prompt="persistent") == "persisted value"

    def test_cache_clear_removes_all_entries(self, tmp_path: Path) -> None:
        """clear() removes all cached entries."""
        from ctrlmap.llm.cache import LLMCache

        cache = LLMCache(cache_dir=tmp_path)
        cache.put(model="llama3", prompt="prompt1", response="r1")
        cache.put(model="llama3", prompt="prompt2", response="r2")
        cache.clear()

        assert cache.get(model="llama3", prompt="prompt1") is None
        assert cache.get(model="llama3", prompt="prompt2") is None

    def test_cache_stats_returns_hit_miss_counts(self, tmp_path: Path) -> None:
        """stats() reports cache hit and miss counts."""
        from ctrlmap.llm.cache import LLMCache

        cache = LLMCache(cache_dir=tmp_path)
        cache.put(model="llama3", prompt="known", response="value")
        cache.get(model="llama3", prompt="known")  # hit
        cache.get(model="llama3", prompt="unknown")  # miss

        stats = cache.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
