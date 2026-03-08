#!/usr/bin/env python3
"""Model comparison script for eval suites.

Runs relevance, compliance, and meta-classification evaluations across
multiple Ollama models and produces a comparison table.

Usage:
    # Compare default models:
    uv run python tests/evaluation/model_compare.py

    # Specify models:
    uv run python tests/evaluation/model_compare.py llama3 qwen2.5:14b gemma2:27b

    # Run a single suite:
    uv run python tests/evaluation/model_compare.py --suite relevance llama3 qwen2.5:14b
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

# Ensure src is on the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from ctrlmap.llm.client import OllamaClient
from ctrlmap.llm.structured_output import generate_rationale
from ctrlmap.models.schemas import MappingRationale

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


# ---------------------------------------------------------------------------
# Metric helpers (standalone from conftest to avoid pytest import issues)
# ---------------------------------------------------------------------------
def _binary_metrics(preds: list[bool], labels: list[bool]) -> dict[str, float]:
    tp = sum(p and lbl for p, lbl in zip(preds, labels, strict=True))
    fp = sum(p and not lbl for p, lbl in zip(preds, labels, strict=True))
    fn = sum(not p and lbl for p, lbl in zip(preds, labels, strict=True))
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    correct = sum(p == lbl for p, lbl in zip(preds, labels, strict=True))
    accuracy = correct / len(preds) if preds else 0.0
    return {"precision": precision, "recall": recall, "f1": f1, "accuracy": accuracy}


def _multiclass_accuracy(preds: list[str], labels: list[str]) -> float:
    if not preds:
        return 0.0
    return sum(p == lbl for p, lbl in zip(preds, labels, strict=True)) / len(preds)


# ---------------------------------------------------------------------------
# Suite runners — each returns a dict of metric_name → float
# ---------------------------------------------------------------------------
def run_relevance(model: str) -> dict[str, float]:
    """Run relevance eval and return metrics."""
    with (FIXTURES_DIR / "relevance_eval_set.json").open() as f:
        dataset = json.load(f)

    client = OllamaClient(model=model)
    preds: list[bool] = []
    labels: list[bool] = []

    for entry in dataset:
        predicted = client.verify_chunk_relevance(
            control_text=entry["control_text"],
            chunk_text=entry["chunk_text"],
            requirement_family=entry.get("requirement_family", ""),
        )
        preds.append(predicted)
        labels.append(entry["expected_relevant"])

    metrics = _binary_metrics(preds, labels)
    return {
        "precision": metrics["precision"],
        "recall": metrics["recall"],
        "f1": metrics["f1"],
    }


def run_compliance(model: str) -> dict[str, float]:
    """Run compliance eval and return metrics."""
    with (FIXTURES_DIR / "compliance_eval_set.json").open() as f:
        dataset = json.load(f)

    level_preds: list[str] = []
    level_labels: list[str] = []
    compliant_preds: list[bool] = []
    compliant_labels: list[bool] = []

    for entry in dataset:
        result = generate_rationale(
            control_text=entry["control_text"],
            chunk_text=entry["chunk_text"],
            model=model,
        )

        if isinstance(result, MappingRationale):
            level_preds.append(result.compliance_level.value)
            compliant_preds.append(result.is_compliant)
        else:
            level_preds.append("non_compliant")
            compliant_preds.append(False)

        level_labels.append(entry["expected_compliance_level"])
        compliant_labels.append(entry["expected_is_compliant"])

    level_acc = _multiclass_accuracy(level_preds, level_labels)
    compliant_metrics = _binary_metrics(compliant_preds, compliant_labels)
    return {
        "level_accuracy": level_acc,
        "is_compliant_accuracy": compliant_metrics["accuracy"],
        "is_compliant_f1": compliant_metrics["f1"],
    }


def run_meta(model: str) -> dict[str, float]:
    """Run meta-classification eval and return metrics."""
    with (FIXTURES_DIR / "meta_classification_eval_set.json").open() as f:
        dataset = json.load(f)

    client = OllamaClient(model=model)
    preds: list[bool] = []
    labels: list[bool] = []

    for entry in dataset:
        predicted = client.classify_control_type(control_text=entry["control_text"])
        preds.append(predicted)
        labels.append(entry["expected_is_meta"])

    metrics = _binary_metrics(preds, labels)
    return {
        "accuracy": metrics["accuracy"],
        "f1": metrics["f1"],
    }


SUITES: dict[str, Any] = {
    "relevance": run_relevance,
    "compliance": run_compliance,
    "meta": run_meta,
}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Compare Ollama models on eval suites")
    parser.add_argument(
        "models",
        nargs="*",
        default=["llama3"],
        help="Model names to compare (e.g. llama3 qwen2.5:14b)",
    )
    parser.add_argument(
        "--suite", choices=list(SUITES.keys()), help="Run a single suite instead of all"
    )
    parser.add_argument(
        "--json", action="store_true", help="Output raw JSON results instead of table"
    )
    args = parser.parse_args()

    suites_to_run = {args.suite: SUITES[args.suite]} if args.suite else SUITES
    all_results: dict[str, dict[str, dict[str, float]]] = {}

    for model in args.models:
        print(f"\n{'=' * 60}")
        print(f"  MODEL: {model}")
        print(f"{'=' * 60}")
        all_results[model] = {}

        for suite_name, runner in suites_to_run.items():
            print(f"\n  Running {suite_name}...", end=" ", flush=True)
            start = time.time()
            try:
                metrics = runner(model)
                elapsed = time.time() - start
                metrics["time_s"] = round(elapsed, 1)
                all_results[model][suite_name] = metrics
                print(f"done ({elapsed:.1f}s)")
                for k, v in metrics.items():
                    if k != "time_s":
                        print(f"    {k}: {v:.4f}")
            except Exception as e:
                elapsed = time.time() - start
                print(f"FAILED ({elapsed:.1f}s): {e}")
                all_results[model][suite_name] = {"error": str(e)}  # type: ignore[dict-item]

    # Output raw JSON if requested
    if args.json:
        print("\n" + json.dumps(all_results, indent=2))
        return

    # Print comparison table
    print(f"\n\n{'=' * 80}")
    print("  MODEL COMPARISON RESULTS")
    print(f"{'=' * 80}\n")

    # Collect all metric names
    all_metrics: list[tuple[str, str]] = []
    for suite_name in suites_to_run:
        for model in args.models:
            if suite_name in all_results.get(model, {}):
                for k in all_results[model][suite_name]:
                    pair = (suite_name, k)
                    if pair not in all_metrics:
                        all_metrics.append(pair)

    # Header
    model_width = max(len(m) for m in args.models)
    header = f"  {'Metric':<35}" + "".join(f"  {m:>{max(model_width, 8)}}" for m in args.models)
    print(header)
    print("  " + "-" * (len(header) - 2))

    # Rows
    current_suite = ""
    for suite_name, metric_name in all_metrics:
        if suite_name != current_suite:
            if current_suite:
                print()
            print(f"  [{suite_name.upper()}]")
            current_suite = suite_name

        label = f"    {metric_name}"
        row = f"  {label:<35}"
        for model in args.models:
            val = all_results.get(model, {}).get(suite_name, {}).get(metric_name)
            if val is None:
                row += f"  {'---':>{max(model_width, 8)}}"
            elif isinstance(val, float):
                row += f"  {val:>{max(model_width, 8)}.4f}"
            else:
                row += f"  {val!s:>{max(model_width, 8)}}"
        print(row)

    print()


if __name__ == "__main__":
    main()
