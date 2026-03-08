"""Eval subcommand for the ctrlmap CLI.

Evaluates the RAG pipeline's retrieval quality against a golden dataset
of known query-to-expected-result pairs.

Usage::

    ctrlmap eval --db-path <path> --golden-dataset <path> \\
        [--metric precision|recall|ragas] [--threshold <float>] [--top-k <int>]

Ref: GitHub Issue #23.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from ctrlmap.index.embedder import Embedder
from ctrlmap.index.query import query
from ctrlmap.index.vector_store import VectorStore

console = Console()


def eval_cmd(
    db_path: Path = typer.Option(  # noqa: B008
        ...,
        "--db-path",
        help="ChromaDB persistence directory.",
        resolve_path=True,
    ),
    golden_dataset: Path = typer.Option(  # noqa: B008
        ...,
        "--golden-dataset",
        help="Path to a JSON golden dataset file.",
        exists=True,
        readable=True,
        resolve_path=True,
    ),
    metric: str = typer.Option(
        "precision",
        "--metric",
        help="Evaluation metric: precision, recall, or ragas.",
    ),
    threshold: float = typer.Option(
        0.0,
        "--threshold",
        help="Minimum score threshold. Exit code 1 if score is below.",
    ),
    top_k: int = typer.Option(
        3,
        "--top-k",
        help="Number of top results to consider for evaluation.",
    ),
    limit: int = typer.Option(
        0,
        "--limit",
        help="Limit evaluation to the first N queries (0 = all). "
        "Useful for fast iteration on prompt changes.",
    ),
) -> None:
    """Evaluate RAG pipeline retrieval quality against a golden dataset."""
    console.print("[bold blue]Eval:[/] Loading golden dataset...")
    dataset = _load_golden_dataset(golden_dataset)

    if limit > 0:
        dataset = dataset[:limit]
        console.print(f"[yellow]Limited to first {limit} queries.[/]")

    console.print(f"[dim]Evaluating {len(dataset)} queries (metric={metric}, top-k={top_k})...[/]")
    store = VectorStore(db_path=db_path)
    embedder = Embedder()

    if metric == "ragas":
        _run_ragas_eval(dataset, store, embedder, top_k, threshold)
        return

    scores: list[float] = []

    for entry in dataset:
        query_text = entry["query"]
        expected_ids = set(entry["expected_ids"])

        results = query(
            store=store,
            collection_name="chunks",
            query_text=query_text,
            top_k=top_k,
            embedder=embedder,
        )

        retrieved_ids = {r.chunk_id for r in results}
        score = _compute_metric(metric, expected_ids, retrieved_ids)
        scores.append(score)

    avg_score = sum(scores) / len(scores) if scores else 0.0

    # Display results
    _display_results(metric, scores, avg_score, threshold)

    # Exit code based on threshold
    if threshold > 0.0 and avg_score < threshold:
        raise typer.Exit(code=1)


def _load_golden_dataset(path: Path) -> list[dict[str, Any]]:
    """Load and validate a golden dataset JSON file.

    Args:
        path: Path to the golden dataset file.

    Returns:
        A list of query-expected pairs.

    Raises:
        typer.BadParameter: If the file format is invalid.
    """
    with path.open() as f:
        data = json.load(f)

    queries = data.get("queries", [])
    if not queries:
        msg = "Golden dataset must contain a non-empty 'queries' array."
        raise typer.BadParameter(msg)

    return queries  # type: ignore[no-any-return]


def _compute_metric(
    metric: str,
    expected_ids: set[str],
    retrieved_ids: set[str],
) -> float:
    """Compute a retrieval metric.

    Args:
        metric: The metric name (precision or recall).
        expected_ids: Set of expected chunk IDs.
        retrieved_ids: Set of actually retrieved chunk IDs.

    Returns:
        The computed metric score between 0.0 and 1.0.
    """
    if not retrieved_ids:
        return 0.0

    hits = expected_ids & retrieved_ids

    if metric == "recall":
        return len(hits) / len(expected_ids) if expected_ids else 0.0
    # Default: precision
    return len(hits) / len(retrieved_ids) if retrieved_ids else 0.0


def _display_results(
    metric: str,
    scores: list[float],
    avg_score: float,
    threshold: float,
) -> None:
    """Display evaluation results in a Rich table."""
    table = Table(title="Evaluation Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Score", style="green")
    table.add_column("Threshold", style="yellow")
    table.add_column("Status", style="bold")

    status = "PASS" if avg_score >= threshold else "FAIL"
    status_style = "[green]PASS[/]" if status == "PASS" else "[red]FAIL[/]"

    table.add_row(
        metric.capitalize(),
        f"{avg_score:.4f}",
        f"{threshold:.4f}",
        status_style,
    )

    console.print(table)
    console.print(f"\n[dim]{metric.capitalize()}: {avg_score:.4f} ({len(scores)} queries)[/]")


def _run_ragas_eval(
    dataset: list[dict[str, Any]],
    store: VectorStore,
    embedder: Embedder,
    top_k: int,
    threshold: float,
) -> None:
    """Run RAGAS faithfulness and relevance evaluation.

    Requires the ``ragas`` package and a running Ollama instance.
    Delegates to Stories #24 and #25 for the full implementation.
    """
    try:
        from ctrlmap.eval_ragas import run_ragas_evaluation

        run_ragas_evaluation(
            dataset=dataset,
            store=store,
            embedder=embedder,
            top_k=top_k,
            threshold=threshold,
        )
    except ImportError as err:
        console.print(
            "[bold yellow]Warning:[/] RAGAS evaluation requires the `ragas` package "
            "and a running Ollama instance.\n"
            "Install with: [cyan]uv add ragas[/]\n"
            "See Stories #24 and #25 for full implementation."
        )
        raise typer.Exit(code=1) from err
