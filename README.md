# ctrlmap

Privacy-preserving GRC automation CLI. Map internal policies to security frameworks (NIST 800-53, SOC 2, ISO 27001) using local LLMs — **zero data leaves your machine**.

## Overview

`ctrlmap` is an open-source, fully local CLI tool designed for automated GRC (Governance, Risk, and Compliance) mapping. It leverages:

- **Local document parsing** — layout-aware PDF extraction via PyMuPDF
- **Embedded vector databases** — ChromaDB for semantic similarity search
- **Local LLM execution** — Ollama integration for rationale generation

### Core Capability: Control Harmonization

Ingest multiple overlapping policy and standard documents, deduplicate their requirements, and generate a unified common control set mapped back to the original source texts. "Test once, comply many."

## Installation

```bash
# Recommended: install in an isolated environment
pipx install ctrlmap

# Development
uv sync
uv run ctrlmap --help
```

## CLI Commands

| Command | Purpose |
|---------|---------|
| `ctrlmap parse` | Extract and chunk PDF documents |
| `ctrlmap index` | Embed chunks into the local vector database |
| `ctrlmap map` | Map policies to security control frameworks |
| `ctrlmap harmonize` | Deduplicate controls across multiple frameworks |
| `ctrlmap eval` | Evaluate RAG pipeline retrieval precision |

## Architecture

```
ctrlmap/
├── pyproject.toml
├── src/
│   └── ctrlmap/
│       ├── cli.py       # Typer command routing
│       ├── parse/       # PyMuPDF ingestion & semantic chunking
│       ├── index/       # Sentence-transformers & ChromaDB
│       ├── map/         # RAG retrieval, similarity scoring, harmonization
│       ├── llm/         # Ollama tool-calling & structured outputs
│       └── models/      # Pydantic schemas & OSCAL serialization
└── tests/
    ├── unit/
    └── integration/
```

## Privacy Mandate

Zero bytes of sensitive telemetry or policy data ever leave the host machine. All processing — document parsing, embedding, vector search, and LLM inference — runs entirely locally.

## Development

This project follows **Spec-Driven Development (SDD)** and **Test-Driven Development (TDD)**. Every feature is implemented using the Red-Green-Refactor cycle.

```bash
# Run tests
uv run pytest

# Lint and format
uv run ruff check .
uv run ruff format .

# Type check
uv run mypy src/
```

## License

MIT
