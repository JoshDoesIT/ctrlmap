# Export

Output formatters for compliance mapping results. Supports CSV, Markdown, OSCAL JSON, and interactive HTML reports.

## Key Exports

| Symbol | Description |
|--------|-------------|
| `format_csv(results)` / `export_csv(results, path)` | CSV output (one row per control–chunk pair) |
| `format_markdown(results)` / `export_markdown(results, path)` | Markdown report with evidence tables |
| `format_oscal(results)` / `export_oscal(results, path)` | OSCAL-aligned assessment results JSON |
| `format_html(results, all_chunks)` / `export_html(results, path, all_chunks)` | Interactive single-file HTML dashboard |
| `atomic_write(path, content)` | Shared atomic file-write utility |

## Modules

- **`csv_formatter.py`** — One row per control–chunk pair
- **`markdown_formatter.py`** — Markdown report with evidence tables
- **`oscal_formatter.py`** — OSCAL assessment results JSON
- **`html_formatter.py`** — Interactive HTML dashboard with Policy Coverage tab
- **`_io.py`** — Shared `atomic_write` utility
- **`_formatting.py`** — Shared text formatting helpers
- **`templates/`** — CSS and JS assets for the HTML report (`report.css`, `report.js`)

## Full API Reference

::: ctrlmap.export
