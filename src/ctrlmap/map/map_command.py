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
from typing import Any

import typer

from ctrlmap._console import console
from ctrlmap._defaults import DEFAULT_LLM_MODEL
from ctrlmap.export.csv_formatter import export_csv, format_csv
from ctrlmap.export.html_formatter import export_html, format_html
from ctrlmap.export.markdown_formatter import export_markdown, format_markdown
from ctrlmap.export.oscal_formatter import export_oscal, format_oscal
from ctrlmap.index.vector_store import VectorStore
from ctrlmap.llm.structured_output import (
    generate_gap_rationale,
    generate_rationale,
    select_best_rationale,
)
from ctrlmap.map.mapper import map_controls
from ctrlmap.map.meta_requirements import classify_meta_controls, resolve_meta_requirements
from ctrlmap.models.oscal import parse_oscal_catalog
from ctrlmap.models.schemas import MappedResult, MappingRationale, ParsedChunk

# ---------------------------------------------------------------------------
# Format dispatch registry
# ---------------------------------------------------------------------------

# Each entry maps a format name to (format_fn, export_fn).
# format_fn produces a string; export_fn writes to disk.
_FORMAT_REGISTRY: dict[
    str,
    tuple[
        Callable[..., Any],
        Callable[..., None],
    ],
] = {
    "csv": (format_csv, export_csv),
    "markdown": (format_markdown, export_markdown),
    "oscal": (format_oscal, export_oscal),
    "html": (format_html, export_html),
}


def map_controls_cmd(
    db_path: Path = typer.Option(  # noqa: B008
        Path("./ctrlmap_db"),
        "--db-path",
        help="ChromaDB persistence directory.",
        resolve_path=True,
    ),
    framework_path: Path = typer.Option(  # noqa: B008
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
    output_path: Path | None = typer.Option(  # noqa: B008
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
        results = _enrich_with_rationale(results, llm_model=llm_model)

    # Load ALL chunks for the Policy Coverage tab
    all_chunks = store.get_all_chunks("chunks")

    # Output results
    _emit_results(results, output_format, output_path, all_chunks=all_chunks)
    console.print(f"[bold green]Done:[/] Mapped {len(results)} controls.")


# ---------------------------------------------------------------------------
# LLM enrichment pipeline
# ---------------------------------------------------------------------------


def _enrich_with_rationale(
    results: list[MappedResult],
    *,
    llm_model: str,
) -> list[MappedResult]:
    """Enrich mapping results with LLM-generated rationales.

    Runs a five-step pipeline:
    1. Verify chunk relevance (filter false-positive retrievals).
    2. Generate per-chunk compliance rationales and select the best.
    3. Classify which controls are meta-requirements.
    4. Generate gap rationales for unmapped controls.
    5. Resolve meta-requirements via sibling aggregation.

    Args:
        results: List of MappedResult objects from vector similarity.
        llm_model: Ollama model name for inference.

    Returns:
        The enriched list of MappedResult objects.
    """
    from ctrlmap.llm.client import OllamaClient

    llm_client = OllamaClient(model=llm_model)

    # Step 1: LLM relevance verification
    console.print("[bold blue]LLM:[/] Verifying evidence relevance...")
    for result in results:
        if not result.supporting_chunks:
            continue
        ctrl = result.control
        control_text = ctrl.as_prompt_text()
        verified: list[ParsedChunk] = []
        for chunk in result.supporting_chunks:
            is_relevant = llm_client.verify_chunk_relevance(
                control_text=control_text,
                chunk_text=chunk.raw_text,
                requirement_family=ctrl.requirement_family,
            )
            if is_relevant:
                verified.append(chunk)
            else:
                console.print(
                    f"[yellow]  {ctrl.control_id}: dropped "
                    f'irrelevant chunk "{chunk.raw_text[:50]}…"[/]'
                )
        result.supporting_chunks = verified

    # Step 2: Score each chunk individually, keep the best rationale
    console.print("[bold blue]LLM:[/] Generating per-chunk rationales...")
    for result in results:
        if not result.supporting_chunks:
            continue
        control_text = result.control.as_prompt_text()
        chunk_rationales: list[MappingRationale] = []
        for chunk in result.supporting_chunks:
            rat = generate_rationale(
                control_text=control_text,
                chunk_text=chunk.raw_text,
                model=llm_model,
            )
            if isinstance(rat, MappingRationale):
                chunk_rationales.append(rat)
        best = select_best_rationale(chunk_rationales)
        if best is not None:
            result.rationale = best

    # Step 3: Classify which unresolved controls are meta-requirements
    console.print("[bold blue]LLM:[/] Classifying meta-requirements...")
    meta_ids = classify_meta_controls(results=results, client=llm_client)

    # Step 4: Generate gap rationale for unmapped controls
    console.print("[bold blue]LLM:[/] Generating gap rationales...")
    for result in results:
        if result.rationale is None and not result.supporting_chunks:
            result.rationale = generate_gap_rationale(
                control_text=result.control.as_prompt_text(),
                model=llm_model,
                client=llm_client,
            )

    # Step 5: Resolve meta-requirements via sibling aggregation
    console.print("[bold blue]LLM:[/] Resolving meta-requirements...")
    return resolve_meta_requirements(results=results, meta_control_ids=meta_ids)


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
        _, export_fn = entry
        if output_format == "html":
            export_fn(results, path, all_chunks=all_chunks)
        else:
            export_fn(results, path)
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
        format_fn, _ = entry
        if output_format == "html":
            typer.echo(format_fn(results, all_chunks=all_chunks))
        elif output_format == "oscal":
            typer.echo(json.dumps(format_fn(results), indent=2))
        else:
            typer.echo(format_fn(results))
    else:
        typer.echo(json.dumps([r.model_dump() for r in results], indent=2))
