# Models

Pydantic V2 data models and OSCAL serialization. All core models use `ConfigDict(extra="forbid", strict=True)`.

## Key Exports

| Class | Description |
|-------|-------------|
| `ParsedChunk` | Semantic text segment with document/page metadata |
| `SecurityControl` | Standardized control from a compliance framework |
| `CommonControl` | Deduplicated control from harmonization |
| `MappedResult` | Control + supporting chunks + rationale |
| `MappingRationale` | LLM-generated compliance justification |
| `InsufficientEvidence` | Marker when context is insufficient |
| `ComplianceLevel` | Three-tier compliance enum (`fully_compliant`, `partially_compliant`, `non_compliant`) |

## Functions

| Function | Description |
|----------|-------------|
| `parse_oscal_catalog(path)` | Parse an OSCAL JSON catalog into a `list[SecurityControl]` |

## Full API Reference

::: ctrlmap.models
