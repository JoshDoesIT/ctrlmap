"""Content-addressable LLM response cache.

Stores LLM responses keyed by SHA-256(model + prompt) in a SQLite
database for fast retrieval during iterative development cycles.

Usage::

    cache = LLMCache(cache_dir=Path(".ctrlmap_cache"))
    cached = cache.get(model="llama3", prompt="...")
    if cached is None:
        response = llm_call(...)
        cache.put(model="llama3", prompt="...", response=response)
    cache.flush()  # commit buffered writes
"""

from __future__ import annotations

import contextlib
import hashlib
import sqlite3
from pathlib import Path


class LLMCache:
    """SQLite-backed LLM response cache with batched commits.

    Buffers ``put()`` operations and commits them in a single
    transaction when ``flush()`` is called — or when the buffer
    reaches ``_FLUSH_INTERVAL`` entries.  This avoids per-insert
    ``fsync`` overhead during high-throughput LLM pipelines.

    Args:
        cache_dir: Directory for the SQLite database file.
    """

    _FLUSH_INTERVAL = 16

    def __init__(self, cache_dir: Path) -> None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        self._db_path = cache_dir / "llm_cache.db"
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, response TEXT NOT NULL)"
        )
        self._conn.commit()
        self._hits = 0
        self._misses = 0
        self._pending = 0

    def __del__(self) -> None:
        """Flush pending writes on instance destruction."""
        with contextlib.suppress(Exception):
            self.flush()

    @staticmethod
    def _make_key(model: str, prompt: str) -> str:
        """Generate a SHA-256 cache key from model + prompt.

        Args:
            model: The LLM model name.
            prompt: The full prompt text.

        Returns:
            A hex-encoded SHA-256 digest.
        """
        return hashlib.sha256(f"{model}::{prompt}".encode()).hexdigest()

    def get(self, *, model: str, prompt: str) -> str | None:
        """Look up a cached response.

        Flushes pending writes first so that recently cached
        responses are visible.

        Args:
            model: The LLM model name.
            prompt: The full prompt text.

        Returns:
            The cached response string, or ``None`` on a miss.
        """
        if self._pending:
            self.flush()
        key = self._make_key(model, prompt)
        row = self._conn.execute("SELECT response FROM cache WHERE key = ?", (key,)).fetchone()
        if row is not None:
            self._hits += 1
            return str(row[0])
        self._misses += 1
        return None

    def put(self, *, model: str, prompt: str, response: str) -> None:
        """Buffer a response for later commit.

        Args:
            model: The LLM model name.
            prompt: The full prompt text.
            response: The LLM response to cache.
        """
        key = self._make_key(model, prompt)
        self._conn.execute(
            "INSERT OR REPLACE INTO cache (key, response) VALUES (?, ?)",
            (key, response),
        )
        self._pending += 1
        if self._pending >= self._FLUSH_INTERVAL:
            self.flush()

    def flush(self) -> None:
        """Commit all buffered writes to disk."""
        if self._pending:
            self._conn.commit()
            self._pending = 0

    def clear(self) -> None:
        """Remove all cached entries."""
        self._conn.execute("DELETE FROM cache")
        self._conn.commit()
        self._hits = 0
        self._misses = 0
        self._pending = 0

    def stats(self) -> dict[str, int]:
        """Return cache hit/miss statistics.

        Returns:
            A dict with ``hits`` and ``misses`` counts.
        """
        return {"hits": self._hits, "misses": self._misses}
