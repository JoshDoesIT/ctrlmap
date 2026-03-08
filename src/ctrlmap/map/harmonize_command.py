"""Harmonize subcommand for the ctrlmap CLI.

Ingests multiple OSCAL framework files, clusters overlapping controls,
and outputs a deduplicated common control set.

Usage::

    ctrlmap harmonize --inputs <dir> [--similarity-threshold <float>] \
        [--llm-model <string>]

Ref: GitHub Issue #20.
"""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console

from ctrlmap.map.cluster import cluster_controls
from ctrlmap.models.oscal import parse_oscal_catalog
from ctrlmap.models.schemas import SecurityControl

console = Console(stderr=True)


def harmonize(
    inputs: Path = typer.Option(  # noqa: B008
        ...,
        "--inputs",
        help="Directory containing OSCAL JSON framework files.",
        exists=True,
        readable=True,
        resolve_path=True,
    ),
    similarity_threshold: float = typer.Option(
        0.85,
        "--similarity-threshold",
        help="Cosine similarity threshold for clustering (0.0-1.0).",
    ),
    llm_model: str = typer.Option(
        "qwen2.5:14b",
        "--llm-model",
        help="Ollama model name (reserved for future use).",
    ),
) -> None:
    """Deduplicate controls across multiple frameworks."""
    console.print("[bold blue]Harmonize:[/] Loading frameworks...")

    all_controls: list[SecurityControl] = []
    json_files = sorted(inputs.glob("*.json"))

    for fpath in json_files:
        console.print(f"  [dim]Loading {fpath.name}...[/]")
        controls = parse_oscal_catalog(fpath)
        all_controls.extend(controls)

    console.print(
        f"[dim]Clustering {len(all_controls)} controls (threshold={similarity_threshold})...[/]"
    )

    common_controls = cluster_controls(
        controls=all_controls,
        similarity_threshold=similarity_threshold,
    )

    output = [cc.model_dump() for cc in common_controls]
    typer.echo(json.dumps(output, indent=2))

    console.print(
        f"[bold green]Done:[/] {len(all_controls)} controls → "
        f"{len(common_controls)} common controls."
    )
