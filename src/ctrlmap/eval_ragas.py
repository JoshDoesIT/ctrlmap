"""RAGAS-based evaluation for the ctrlmap RAG pipeline.

Computes faithfulness and context relevance metrics using the RAGAS
framework against a golden dataset. Requires the ``ragas`` optional
dependency and a running Ollama instance.

Usage::

    ctrlmap eval --db-path <path> --golden-dataset <path> --metric ragas

Ref: GitHub Issues #24, #25.
"""

from __future__ import annotations

from typing import Any

import typer
from rich.console import Console
from rich.table import Table

console = Console()


def run_ragas_evaluation(
    *,
    dataset: list[dict[str, Any]],
    store: Any,
    embedder: Any,
    top_k: int = 3,
    threshold: float = 0.0,
) -> None:
    """Run RAGAS faithfulness and relevance evaluation.

    For each query in the golden dataset, retrieves chunks from the
    vector store and feeds (query, context, answer) triples through
    RAGAS metrics.

    Args:
        dataset: List of golden dataset query entries.
        store: VectorStore instance.
        embedder: Embedder instance.
        top_k: Number of top results for retrieval.
        threshold: Minimum score threshold. Exits with code 1 if below.

    Raises:
        typer.Exit: If the average score is below the threshold.
    """
    try:
        from ragas import evaluate  # type: ignore[import-not-found]
        from ragas.metrics import (  # type: ignore[import-not-found]
            context_precision,
            context_recall,
            faithfulness,
        )
    except ImportError as err:
        console.print(
            "[bold yellow]Warning:[/] RAGAS evaluation requires the `ragas` package.\n"
            "Install with: [cyan]uv add ragas[/]"
        )
        raise typer.Exit(code=1) from err

    from ctrlmap.index.query import query as query_store

    # Build RAGAS evaluation dataset
    questions: list[str] = []
    contexts: list[list[str]] = []
    ground_truths: list[str] = []

    for entry in dataset:
        query_text = entry["query"]
        results = query_store(
            store=store,
            collection_name="chunks",
            query_text=query_text,
            top_k=top_k,
            embedder=embedder,
        )

        retrieved_texts = [r.raw_text for r in results]
        questions.append(query_text)
        contexts.append(retrieved_texts)
        # Use the query itself as a proxy ground truth
        # (for context relevance, the ground truth is the expected answer)
        ground_truths.append(query_text)

    console.print(f"[dim]Running RAGAS evaluation on {len(questions)} queries...[/]")

    try:
        from datasets import Dataset  # type: ignore[import-not-found]

        eval_dataset = Dataset.from_dict(
            {
                "question": questions,
                "contexts": contexts,
                "ground_truth": ground_truths,
                "answer": ground_truths,  # Use query as proxy answer
            }
        )

        result = evaluate(
            eval_dataset,
            metrics=[faithfulness, context_precision, context_recall],
        )

        # Display results
        table = Table(title="RAGAS Evaluation Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Score", style="green")
        table.add_column("Threshold", style="yellow")
        table.add_column("Status", style="bold")

        scores: dict[str, float] = {}
        for metric_name, score in result.items():
            if isinstance(score, (int, float)):
                scores[metric_name] = float(score)
                status = "[green]PASS[/]" if score >= threshold else "[red]FAIL[/]"
                table.add_row(
                    metric_name,
                    f"{score:.4f}",
                    f"{threshold:.4f}",
                    status,
                )

        console.print(table)

        # Check threshold
        if threshold > 0.0:
            avg_score = sum(scores.values()) / len(scores) if scores else 0.0
            if avg_score < threshold:
                console.print(
                    f"[red]FAIL:[/] Average RAGAS score {avg_score:.4f} "
                    f"is below threshold {threshold:.4f}"
                )
                raise typer.Exit(code=1)

    except Exception as exc:
        console.print(f"[bold red]RAGAS evaluation error:[/] {exc}")
        console.print(
            "[dim]Ensure Ollama is running and the ragas package is properly installed.[/]"
        )
        raise typer.Exit(code=1) from exc
