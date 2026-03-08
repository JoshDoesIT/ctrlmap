# Map

RAG retrieval, LLM enrichment, and control harmonization. This is the third stage of the ctrlmap pipeline — it matches framework controls to supporting policy evidence and generates compliance rationales.

## Key Exports

| Symbol | Description |
|--------|-------------|
| `map_controls(controls, store, ...)` | Map security controls to supporting chunks via vector search |
| `enrich_with_rationale(results, ...)` | 5-step LLM enrichment pipeline (see below) |
| `cluster_controls(controls)` | Single-linkage clustering for control harmonization |
| `classify_meta_controls(results, client)` | Identify governance/documentation meta-requirements |
| `resolve_meta_requirements(results, meta_ids)` | Infer meta-requirement compliance from siblings |

## LLM Enrichment Pipeline

The `enrich_with_rationale()` function runs a 5-step pipeline:

1. **Relevance filter** — Verify each retrieved chunk is actually relevant to the control
2. **Rationale generation** — Generate per-chunk compliance rationales, select the best
3. **Meta-classification** — Identify which controls are meta-requirements
4. **Gap rationale** — Generate explanations for unmapped controls
5. **Resolution** — Resolve meta-requirements via sibling aggregation

## Modules

- **`mapper.py`** — Core mapping: query expansion → vector search → min-score filtering
- **`enrichment.py`** — Orchestrates the 5-step LLM pipeline above
- **`meta_requirements.py`** — Meta-requirement classification and resolution
- **`cluster.py`** — Single-linkage clustering via cosine similarity + Union-Find
- **`map_command.py`** — CLI wiring + format dispatch via `_FORMAT_REGISTRY`
- **`expansion_map.json`** — Domain synonym data for query expansion

## Full API Reference

::: ctrlmap.map
