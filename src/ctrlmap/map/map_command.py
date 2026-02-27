"""Map subcommand for the ctrlmap CLI.

Maps security controls from an OSCAL framework to supporting policy
chunks in the vector database, optionally generating LLM rationales.

Usage::

    ctrlmap map --db-path <path> --framework <path> \
        [--output-format json|csv] [--llm-model <string>] \
        [--rationale] [--top-k <int>]

Ref: GitHub Issue #20.
"""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console

from ctrlmap.index.vector_store import VectorStore
from ctrlmap.llm.structured_output import generate_rationale
from ctrlmap.map.mapper import map_controls
from ctrlmap.models.oscal import parse_oscal_catalog

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
        help="Output format: json, csv, or oscal.",
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

    # Output results
    if output_format == "json":
        output = [r.model_dump() for r in results]
        typer.echo(json.dumps(output, indent=2))
    elif output_format == "csv":
        _output_csv(results)
    else:
        typer.echo(json.dumps([r.model_dump() for r in results], indent=2))

    console.print(f"[bold green]Done:[/] Mapped {len(results)} controls.")


def _output_csv(results: list) -> None:  # type: ignore[type-arg]
    """Output mapping results as CSV to stdout."""
    import csv
    import sys

    writer = csv.writer(sys.stdout)
    writer.writerow(["control_id", "framework", "title", "chunk_id", "raw_text", "rationale"])

    for result in results:
        for chunk in result.supporting_chunks:
            rationale_text = ""
            if result.rationale:
                rationale_text = str(result.rationale.model_dump())
            writer.writerow(
                [
                    result.control.control_id,
                    result.control.framework,
                    result.control.title,
                    chunk.chunk_id,
                    chunk.raw_text,
                    rationale_text,
                ]
            )
