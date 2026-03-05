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
from pathlib import Path

import typer
from rich.console import Console

from ctrlmap.export.csv_formatter import export_csv, format_csv
from ctrlmap.export.html_formatter import export_html, format_html
from ctrlmap.export.markdown_formatter import export_markdown, format_markdown
from ctrlmap.export.oscal_formatter import export_oscal, format_oscal
from ctrlmap.index.vector_store import VectorStore
from ctrlmap.llm.structured_output import generate_rationale
from ctrlmap.map.mapper import map_controls
from ctrlmap.models.oscal import parse_oscal_catalog
from ctrlmap.models.schemas import ParsedChunk

console = Console()


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
        "llama3",
        "--llm-model",
        help="Ollama model name for rationale generation.",
    ),
    rationale: bool = typer.Option(
        False,
        "--rationale",
        help="Invoke LLM for compliance rationale generation.",
    ),
    top_k: int = typer.Option(
        5,
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

    # Optionally enrich with LLM rationales
    if rationale:
        from ctrlmap.llm.client import OllamaClient

        llm_client = OllamaClient(model=llm_model)

        # Step 1: LLM relevance verification — filter out chunks that
        # only share keywords with the control but don't directly address it
        console.print("[bold blue]LLM:[/] Verifying evidence relevance...")
        for result in results:
            if not result.supporting_chunks:
                continue
            ctrl = result.control
            control_text = f"{ctrl.control_id}: {ctrl.title}. {ctrl.description}"
            verified: list[ParsedChunk] = []
            for chunk in result.supporting_chunks:
                is_relevant = llm_client.verify_chunk_relevance(
                    control_text=control_text,
                    chunk_text=chunk.raw_text,
                )
                if is_relevant:
                    verified.append(chunk)
                else:
                    console.print(
                        f"[yellow]  {ctrl.control_id}: dropped "
                        f'irrelevant chunk "{chunk.raw_text[:50]}…"[/]'
                    )
            result.supporting_chunks = verified

        # Step 2: Generate rationales for controls with verified evidence
        console.print("[bold blue]LLM:[/] Generating rationales...")
        for result in results:
            if result.supporting_chunks:
                chunk_texts = " ".join(c.raw_text for c in result.supporting_chunks)
                ctrl = result.control
                control_text = f"{ctrl.control_id}: {ctrl.title}. {ctrl.description}"
                result.rationale = generate_rationale(
                    control_text=control_text,
                    chunk_text=chunk_texts,
                    model=llm_model,
                )

    # Load ALL chunks for the Policy Coverage tab
    all_chunks = store.get_all_chunks("chunks")

    # Output results
    _emit_results(results, output_format, output_path, all_chunks=all_chunks)
    console.print(f"[bold green]Done:[/] Mapped {len(results)} controls.")


def _emit_results(
    results: list,  # type: ignore[type-arg]
    output_format: str,
    output_path: Path | None,
    all_chunks: list | None = None,  # type: ignore[type-arg]
) -> None:
    """Route results to the appropriate formatter and output destination."""
    if output_path:
        _write_to_file(results, output_format, output_path, all_chunks=all_chunks)
    else:
        _write_to_stdout(results, output_format, all_chunks=all_chunks)


def _write_to_file(
    results: list,  # type: ignore[type-arg]
    output_format: str,
    path: Path,
    all_chunks: list | None = None,  # type: ignore[type-arg]
) -> None:
    """Write results to a file using the appropriate formatter."""
    if output_format == "csv":
        export_csv(results, path)
    elif output_format == "markdown":
        export_markdown(results, path)
    elif output_format == "oscal":
        export_oscal(results, path)
    elif output_format == "html":
        export_html(results, path, all_chunks=all_chunks)
    else:
        path.write_text(
            json.dumps([r.model_dump() for r in results], indent=2),
            encoding="utf-8",
        )


def _write_to_stdout(
    results: list,  # type: ignore[type-arg]
    output_format: str,
    all_chunks: list | None = None,  # type: ignore[type-arg]
) -> None:
    """Write results to stdout using the appropriate formatter."""
    if output_format == "csv":
        typer.echo(format_csv(results))
    elif output_format == "markdown":
        typer.echo(format_markdown(results))
    elif output_format == "oscal":
        oscal_dict = format_oscal(results)
        typer.echo(json.dumps(oscal_dict, indent=2))
    elif output_format == "html":
        typer.echo(format_html(results, all_chunks=all_chunks))
    else:
        typer.echo(json.dumps([r.model_dump() for r in results], indent=2))
