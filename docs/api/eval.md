# Eval

RAG pipeline evaluation harness. Measures retrieval quality against expert-labeled golden datasets.

## CLI Usage

```bash
ctrlmap eval --db-path <path> --golden-dataset <path> \
    [--metric precision|recall|ragas] [--threshold <float>] [--top-k <int>]
```

## Supported Metrics

| Metric | Description |
|--------|-------------|
| `precision` | Fraction of retrieved chunks that are in the expected set (default) |
| `recall` | Fraction of expected chunks that were retrieved |
| `ragas` | RAGAS faithfulness and relevance evaluation (requires `ragas` package) |

## Golden Dataset Format

```json
{
  "queries": [
    {
      "query": "access control enforcement for logical access",
      "expected_ids": ["chunk-ac-03-001", "chunk-ac-03-002"]
    }
  ]
}
```

## Key Functions

| Function | Description |
|----------|-------------|
| `eval_cmd(...)` | Main CLI entry point (Typer command) |
| `_compute_metric(metric, expected, retrieved)` | Compute precision or recall |
| `_run_ragas_eval(dataset, store, ...)` | Delegate to RAGAS evaluation |

## Full API Reference

::: ctrlmap.eval_command
