<p align="center">
  <img src="assets/logo.png" alt="ctrlmap logo" width="200" />
</p>

<p align="center">
  <a href="https://github.com/JoshDoesIT/ctrlmap/actions/workflows/ci.yml"><img src="https://github.com/JoshDoesIT/ctrlmap/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue?logo=python&logoColor=white" alt="Python" /></a>
  <a href="https://github.com/JoshDoesIT/ctrlmap/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="License: MIT" /></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff" /></a>
  <a href="https://github.com/JoshDoesIT/ctrlmap"><img src="https://img.shields.io/badge/privacy-100%25_local-blueviolet?logo=shield" alt="Privacy: 100% Local" /></a>
</p>

<p align="center">
  GRC automation CLI utility that maps internal policies to security frameworks (e.g., NIST 800-53, PCI DSS, SOC 2, ISO 27001) using local AI. Zero data leaves your machine.
</p>

## Overview

`ctrlmap` is an open-source, fully local CLI tool designed for automated GRC (Governance, Risk, and Compliance) mapping. It leverages:

- **Local document parsing:** layout-aware PDF extraction via PyMuPDF
- **Embedded vector databases:** ChromaDB for semantic similarity search
- **Local LLM execution:** Ollama integration for rationale generation

### Core Capability: Control Harmonization

Ingest multiple overlapping policy and standard documents, deduplicate their requirements, and generate a unified common control set mapped back to the original source texts. "Test once, comply many."

## Installation

```bash
# Recommended: install in an isolated environment
pipx install ctrlmap
# or
uv tool install ctrlmap
```

## Quick Start (Development)

```bash
# One-command setup: installs Python deps, Ollama, and llama3 model
make setup

# Run all tests
make test

# Run evaluation tests (requires Ollama)
make test-eval
```

See `make help` for all available targets.

## CLI Commands

| Command | Purpose |
|---------|---------|
| `ctrlmap parse` | Extract and chunk PDF documents |
| `ctrlmap index` | Embed chunks into the local vector database |
| `ctrlmap map` | Map policies to security control frameworks |
| `ctrlmap harmonize` | Deduplicate controls across multiple frameworks |
| `ctrlmap eval` | Evaluate RAG pipeline retrieval quality |

The `map` command supports multiple output formats via `--output-format` (json, csv, markdown, oscal) and an `--output` flag for writing directly to a file.

## Architecture

```
ctrlmap/
├── pyproject.toml
├── Makefile              # Developer workflow targets
├── scripts/setup.sh      # One-command environment setup
├── src/
│   └── ctrlmap/
│       ├── cli.py           # Typer command routing
│       ├── eval_command.py  # RAG evaluation harness
│       ├── parse/           # PyMuPDF ingestion & semantic chunking
│       ├── index/           # Sentence-transformers & ChromaDB
│       ├── map/             # RAG retrieval, similarity scoring, harmonization
│       ├── llm/             # Ollama tool-calling & structured outputs
│       ├── export/          # CSV, Markdown, OSCAL JSON formatters
│       └── models/          # Pydantic schemas & OSCAL serialization
└── tests/
    ├── unit/
    ├── integration/
    └── evaluation/          # Non-deterministic RAG quality tests
```

## Privacy Mandate

Zero bytes of sensitive telemetry or policy data ever leave the host machine. All processing (document parsing, embedding, vector search, and LLM inference) runs entirely locally.

## Development

This project follows **Spec-Driven Development (SDD)** and **Test-Driven Development (TDD)**. Every feature is implemented using the Red-Green-Refactor cycle.

```bash
make setup          # Install everything (deps, Ollama, llama3)
make test           # Unit + integration tests
make test-eval      # Evaluation tests (requires Ollama)
make lint           # Ruff linter
make format         # Ruff formatter
make build          # Build wheel and sdist
make install        # Install via uv tool (isolated env)
```

## License

MIT
