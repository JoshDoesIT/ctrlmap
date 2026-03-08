# LLM

Ollama client, prompt management, and structured output parsing. Handles all local LLM inference for compliance rationale generation and control classification.

## Key Exports

| Symbol | Description |
|--------|-------------|
| `OllamaClient` | Client for local Ollama LLM inference (connection handling, prompt formatting) |
| `OllamaConnectionError` | Raised when Ollama is unreachable |
| `generate_rationale(control_text, chunk_text, model)` | Generate a structured `MappingRationale` for a control–chunk pair |
| `generate_gap_rationale(control_text, model, client)` | Generate a rationale for unmapped (non-compliant) controls |
| `select_best_rationale(rationales)` | Pick the highest-confidence rationale from per-chunk evaluations |
| `load_prompt(name)` | Load a prompt template from the `prompts/` directory |

## Prompt Templates

All LLM prompts live in `src/ctrlmap/llm/prompts/` as plain `.txt` files:

| Template | Purpose |
|----------|---------|
| `compliance_rationale.txt` | Generate structured compliance rationale for a control–chunk pair |
| `gap_rationale.txt` | Explain why an unmapped control is non-compliant |
| `meta_classification.txt` | Classify whether a control is a meta-requirement |
| `relevance_check.txt` | Verify if a chunk directly addresses a control |
| `control_extraction.txt` | Extract controls from raw PDF text |

## Modules

- **`client.py`** — `OllamaClient` with connection handling and prompt formatting
- **`structured_output.py`** — LLM response → `MappingRationale | InsufficientEvidence`
- **`_json_utils.py`** — Shared JSON extraction utilities for LLM responses
- **`prompts/__init__.py`** — Process-level prompt template caching via `load_prompt()`

## Full API Reference

::: ctrlmap.llm
