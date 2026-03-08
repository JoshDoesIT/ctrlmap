# Parse

PyMuPDF-based PDF ingestion and semantic chunking. This is the first stage of the ctrlmap pipeline — it converts raw PDF documents into structured `ParsedChunk` objects.

## Key Exports

| Symbol | Description |
|--------|-------------|
| `chunk_document(path)` | Full pipeline: extract → detect layout → classify → chunk |
| `extract_text_blocks(path)` | Extract layout-aware text blocks with bounding-box data |
| `detect_layout(blocks)` | Detect single-column, dual-column, or table layouts |
| `classify_block(block)` | Classify a single block as header, footer, or body |
| `classify_blocks(blocks)` | Batch-classify blocks dynamically |
| `order_blocks_by_columns(blocks)` | Reorder blocks for column-aware reading order |
| `LayoutType` | Enum: `SINGLE_COLUMN`, `DUAL_COLUMN`, `TABLE` |
| `ElementRole` | Enum: `HEADER`, `FOOTER`, `BODY` |
| `TextBlock` | Dataclass for extracted text with bounding-box coordinates |

## Modules

- **`extractor.py`** — PyMuPDF text extraction with bounding-box data
- **`heuristics.py`** — Layout detection and element role classification
- **`chunker.py`** — Hybrid structural + semantic chunking with boilerplate detection
- **`llm_chunker.py`** — Alternative LLM-based control extraction via Ollama
- **`parse_command.py`** — CLI wiring for `ctrlmap parse`

## Full API Reference

::: ctrlmap.parse
