"""Shared default constants for the ctrlmap project.

Centralizes magic strings and default values that are referenced
across multiple modules, preventing drift between CLI options,
function signatures, and prompt templates.
"""

DEFAULT_LLM_MODEL: str = "qwen2.5:14b"
"""Default Ollama model for accuracy-critical compliance evaluation."""

DEFAULT_FAST_MODEL: str = "qwen2.5:7b"
"""Smaller Ollama model for simpler LLM tasks (meta-classification,
gap rationale, control extraction). Runs ~2x faster than the 14B model."""

DEFAULT_EMBEDDING_MODEL: str = "all-mpnet-base-v2"
"""Default Sentence-Transformers model for local text vectorization.

Uses ``all-mpnet-base-v2`` (768-dim, 109M params) for higher retrieval
quality. Scores ~5-8% higher than ``all-MiniLM-L6-v2`` on MTEB semantic
search benchmarks. Slightly slower to load but embeddings are only
computed once during indexing.
"""
