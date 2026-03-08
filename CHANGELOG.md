# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Version read from installed package metadata at runtime (`importlib.metadata`).
- `LayoutType` and `ElementRole` enums now use `StrEnum` for consistency.
- Debug output in LLM chunker now uses centralized `err_console` instead of bare `print`.
- Late imports in `heuristics.py` moved to file-level.
- Deduplicated `_extract_json` across LLM modules into shared `_json_utils`.
- Extracted `_call_llm` helper in `OllamaClient` to reduce boilerplate.
- `llm_chunker.py` now routes LLM calls through `OllamaClient`.
- Replaced `type: ignore` comments in `meta_requirements.py` with type guards.
- Extracted inline CSS/JS from HTML formatter into template files.

### Added

- `CHANGELOG.md` following Keep a Changelog format.
- `ctrlmap.llm._json_utils` module for shared JSON extraction utilities.
- `enrichment.py` pipeline module extracted from `map_command.py`.
- `SecurityControl.as_prompt_text()` method for LLM prompt formatting.
- `_FORMAT_REGISTRY` format dispatch registry replacing hardcoded branching.
- `_defaults.py` for centralized model name constants.
- `_console.py` for shared Rich console instances with `__all__` exports.
- `expansion_map.json` externalized domain synonym data.

## [0.1.0] - 2026-03-08

### Added

- Core CLI with `parse`, `index`, `map`, `harmonize`, and `eval` commands.
- PyMuPDF-based PDF extraction with layout-aware chunking.
- ChromaDB vector store for embedding persistence and search.
- Ollama integration for local LLM inference.
- Export formatters: CSV, Markdown, OSCAL JSON, interactive HTML.
- Meta-requirement detection and sibling compliance aggregation.
- Control harmonization via vector-based clustering.
- RAG pipeline evaluation harness with precision/recall metrics.
