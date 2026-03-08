# Architecture

ctrlmap operates as a **four-stage pipeline** that maps organizational policies to security framework controls using local AI inference.

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌─────────────┐
│  Parse   │────▶│  Index   │────▶│   Map    │────▶│  Harmonize  │
│          │     │          │     │          │     │             │
│ PDF→JSONL│     │ Embed→DB │     │ RAG+LLM  │     │  Cluster    │
└──────────┘     └──────────┘     └──────────┘     └─────────────┘
```

## Stages

### 1. Parse (`ctrlmap.parse`)

Extracts text from PDF documents, preserving layout structure.

- **`extractor.py`** — PyMuPDF-based text extraction with bounding-box data (`TextBlock`)
- **`heuristics.py`** — Layout detection (single-column, dual-column, table) and element classification (header, footer, body)
- **`chunker.py`** — Hybrid structural + semantic chunking with boilerplate detection and sentence healing
- **`llm_chunker.py`** — Alternative LLM-based control extraction via Ollama
- **`parse_command.py`** — CLI wiring

**Output:** `.jsonl` of `ParsedChunk` objects.

### 2. Index (`ctrlmap.index`)

Embeds text and stores vectors locally.

- **`embedder.py`** — Sentence-Transformers embedding (`all-MiniLM-L6-v2`)
- **`vector_store.py`** — ChromaDB `PersistentClient` wrapper
- **`query.py`** — Vector similarity search with embedding
- **`index_command.py`** — CLI wiring

**Output:** Populated ChromaDB database.

### 3. Map (`ctrlmap.map`)

Matches controls to supporting evidence via RAG, then enriches with LLM analysis.

- **`mapper.py`** — Core mapping: query expansion → vector search → min-score filtering
- **`enrichment.py`** — Orchestrates the 5-step LLM pipeline: relevance filter → rationale → meta-classify → gap → resolve. Entry point: `enrich_with_rationale()`
- **`meta_requirements.py`** — Governance/documentation meta-requirement classification
- **`map_command.py`** — CLI wiring + format dispatch via `_FORMAT_REGISTRY`
- **`expansion_map.json`** — Domain synonym data for query expansion

**Output:** `MappedResult` objects with rationales.

### 4. Harmonize (`ctrlmap.map.cluster`)

Deduplicates overlapping controls across frameworks.

- **`cluster.py`** — Single-linkage clustering via cosine similarity + Union-Find

**Output:** `CommonControl` objects with source references.

## Supporting Modules

| Module | Responsibility |
|--------|----------------|
| `ctrlmap.models.schemas` | Pydantic V2 data models (`ParsedChunk`, `SecurityControl`, `MappedResult`, etc.) |
| `ctrlmap.models.oscal` | OSCAL JSON catalog parser |
| `ctrlmap.llm.client` | Ollama client (connection handling, prompt formatting) |
| `ctrlmap.llm.structured_output` | LLM response → `MappingRationale \| InsufficientEvidence` |
| `ctrlmap.llm._json_utils` | Shared JSON extraction utilities for LLM responses |
| `ctrlmap.llm.prompts/` | Externalized prompt templates (`.txt` files) |
| `ctrlmap.export.*` | Output formatters (CSV, Markdown, OSCAL, HTML) |
| `ctrlmap.eval_command` | CLI subcommand for the RAG evaluation harness |
| `ctrlmap.eval_ragas` | RAGAS integration for retrieval quality metrics |
| `ctrlmap._defaults` | Centralized default constants (model names) |
| `ctrlmap._console` | Shared Rich console instances |

## Data Flow

```mermaid
graph LR
    A[PDF Documents] -->|parse| B[JSONL Chunks]
    D[OSCAL Framework] -->|index| C
    B -->|index| C[ChromaDB]
    C -->|map| E[MappedResults]
    E -->|LLM enrich| F[Rationales]
    F -->|harmonize| G[CommonControls]
    F -->|export| H[CSV / MD / OSCAL / HTML]
```

## Design Principles

- **Local-first:** All processing (LLM, embeddings, vector store) runs locally. No data leaves the machine.
- **Pipeline architecture:** Clear stage boundaries with serializable intermediate outputs (JSONL, ChromaDB).
- **Pydantic V2 strict mode:** `extra='forbid'` and `strict=True` on all core data models for data integrity.
- **Test-driven:** Red-Green-Refactor on every feature. Unit, integration, and LLM evaluation test suites.
