"""ctrlmap.llm: Ollama tool-calling, prompt management, and structured output parsing.

Public API:
    OllamaClient: Client for local Ollama LLM inference.
    OllamaConnectionError: Raised when Ollama is unreachable.
    generate_rationale: Generate a structured compliance rationale.
    generate_gap_rationale: Generate a rationale for unmapped controls.
    select_best_rationale: Pick the best rationale from per-chunk evaluations.
    load_prompt: Load a prompt template from the prompts/ directory.
"""

from ctrlmap.llm.client import OllamaClient, OllamaConnectionError
from ctrlmap.llm.prompts import load_prompt
from ctrlmap.llm.structured_output import (
    generate_gap_rationale,
    generate_rationale,
    select_best_rationale,
)

__all__ = [
    "OllamaClient",
    "OllamaConnectionError",
    "generate_gap_rationale",
    "generate_rationale",
    "load_prompt",
    "select_best_rationale",
]
