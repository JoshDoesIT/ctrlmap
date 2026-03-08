"""Map subcommand for the ctrlmap CLI.

Maps security controls from an OSCAL framework to supporting policy
chunks in the vector database, optionally generating LLM rationales.

Usage::

    ctrlmap map --db-path <path> --framework <path> \\
        [--output-format json|csv|markdown|oscal|html] [--output <path>] \\
        [--llm-model <string>] [--rationale] [--top-k <int>]

Ref: GitHub Issue #20.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, NamedTuple

import typer

from ctrlmap._console import console
from ctrlmap._defaults import DEFAULT_LLM_MODEL
from ctrlmap.export.csv_formatter import export_csv, format_csv
from ctrlmap.export.html_formatter import export_html, format_html
from ctrlmap.export.markdown_formatter import export_markdown, format_markdown
from ctrlmap.export.oscal_formatter import export_oscal, format_oscal
from ctrlmap.index.vector_store import VectorStore
from ctrlmap.map.enrichment import enrich_with_rationale
from ctrlmap.map.mapper import map_controls
from ctrlmap.models.oscal import parse_oscal_catalog
from ctrlmap.models.schemas import MappedResult, ParsedChunk

# ---------------------------------------------------------------------------
# Format dispatch registry
# ---------------------------------------------------------------------------


class _FormatterEntry(NamedTuple):
    """Registry entry for an output format."""

    format_fn: Callable[..., Any]
    """Callable that produces a string (or dict for OSCAL)."""
    export_fn: Callable[..., None]
    """Callable that writes results to disk."""
    needs_all_chunks: bool = False
    """Whether the formatter requires all indexed chunks (e.g. HTML)."""
    format_returns_dict: bool = False
    """Whether format_fn returns a dict requiring JSON serialization (e.g. OSCAL)."""


_FORMAT_REGISTRY: dict[str, _FormatterEntry] = {
    "csv": _FormatterEntry(format_csv, export_csv),
    "markdown": _FormatterEntry(format_markdown, export_markdown),
    "oscal": _FormatterEntry(format_oscal, export_oscal, format_returns_dict=True),
    "html": _FormatterEntry(format_html, export_html, needs_all_chunks=True),
}


def map_controls_cmd(
    db_path: Path = typer.Option(
        Path("./ctrlmap_db"),
        "--db-path",
        help="ChromaDB persistence directory.",
        resolve_path=True,
    ),
    framework_path: Path = typer.Option(
        ...,
        "--framework",
        help="Path to an OSCAL JSON framework file.",
        exists=True,
        readable=True,
        resolve_path=True,
    ),
    output_format: str = typer.Option(
        "json",
        "--output-format",
        help="Output format: json, csv, markdown, oscal, or html.",
    ),
    output_path: Path | None = typer.Option(
        None,
        "--output",
        help="Output file path. Prints to stdout if not specified.",
    ),
    llm_model: str = typer.Option(
        DEFAULT_LLM_MODEL,
        "--llm-model",
        help="Ollama model name for rationale generation.",
    ),
    rationale: bool = typer.Option(
        False,
        "--rationale",
        help="Invoke LLM for compliance rationale generation.",
    ),
    top_k: int = typer.Option(
        10,
        "--top-k",
        help="Maximum supporting chunks per control.",
    ),
    concurrency: int = typer.Option(
        4,
        "--concurrency",
        help="Maximum concurrent LLM requests (higher = faster, more RAM).",
    ),
    cache: bool = typer.Option(
        False,
        "--cache/--no-cache",
        help="Enable LLM response cache for faster re-runs.",
    ),
) -> None:
    """Map policies to security controls via vector similarity."""
    console.print("[bold blue]Map:[/] Loading framework controls...")
    controls = parse_oscal_catalog(framework_path)

    console.print(f"[dim]Mapping {len(controls)} controls (top-k={top_k})...[/]")
    store = VectorStore(db_path=db_path)

    results = map_controls(
        controls=controls,
        store=store,
        collection_name="chunks",
        top_k=top_k,
    )

    if rationale:
        results = enrich_with_rationale(
            results,
            llm_model=llm_model,
            concurrency=concurrency,
            cache_enabled=cache,
        )

    # Load ALL chunks for the Policy Coverage tab
    all_chunks = store.get_all_chunks("chunks")

    # Output results
    _emit_results(results, output_format, output_path, all_chunks=all_chunks)
    console.print(f"[bold green]Done:[/] Mapped {len(results)} controls.")


# ---------------------------------------------------------------------------
# Output routing
# ---------------------------------------------------------------------------


def _emit_results(
    results: list[MappedResult],
    output_format: str,
    output_path: Path | None = None,
    all_chunks: list[ParsedChunk] | None = None,
) -> None:
    """Route results to the appropriate formatter and output destination.

    Supports comma-separated ``output_format`` values (e.g.
    ``"markdown,json,html"``) paired with comma-separated paths in
    ``output_path``.  This allows a single LLM run to produce all
    report formats at once, eliminating inter-run inconsistencies.

    Args:
        results: The mapping results to export.
        output_format: One or more comma-separated format names.
        output_path: One or more comma-separated file paths (or ``None``
            for stdout when using a single format).
        all_chunks: All indexed chunks for the Policy Coverage tab (HTML).
    """
    formats = [f.strip() for f in output_format.split(",")]

    if len(formats) == 1:
        # Single format — backward-compatible behavior
        if output_path:
            _write_to_file(results, formats[0], output_path, all_chunks=all_chunks)
        else:
            _write_to_stdout(results, formats[0], all_chunks=all_chunks)
        return

    # Multi-format: output_path is required and must have matching count
    if output_path is None:
        msg = "Multi-format output requires --output with comma-separated paths"
        raise ValueError(msg)

    paths = [Path(p.strip()) for p in str(output_path).split(",")]
    if len(formats) != len(paths):
        msg = f"Multi-format/path count mismatch: {len(formats)} format(s) but {len(paths)} path(s)"
        raise ValueError(msg)

    for fmt, path in zip(formats, paths, strict=True):
        _write_to_file(results, fmt, path, all_chunks=all_chunks)


def _write_to_file(
    results: list[MappedResult],
    output_format: str,
    path: Path,
    all_chunks: list[ParsedChunk] | None = None,
) -> None:
    """Write results to a file using the appropriate formatter."""
    entry = _FORMAT_REGISTRY.get(output_format)
    if entry is not None:
        if entry.needs_all_chunks:
            entry.export_fn(results, path, all_chunks=all_chunks)
        else:
            entry.export_fn(results, path)
    else:
        path.write_text(
            json.dumps([r.model_dump() for r in results], indent=2),
            encoding="utf-8",
        )


def _write_to_stdout(
    results: list[MappedResult],
    output_format: str,
    all_chunks: list[ParsedChunk] | None = None,
) -> None:
    """Write results to stdout using the appropriate formatter."""
    entry = _FORMAT_REGISTRY.get(output_format)
    if entry is not None:
        if entry.needs_all_chunks:
            typer.echo(entry.format_fn(results, all_chunks=all_chunks))
        elif entry.format_returns_dict:
            typer.echo(json.dumps(entry.format_fn(results), indent=2))
        else:
            typer.echo(entry.format_fn(results))
    else:
        typer.echo(json.dumps([r.model_dump() for r in results], indent=2))
