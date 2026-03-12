"""Batch evaluation accuracy evaluation.

Validates that the batch evaluation pipeline (``evaluate_chunks_batch_async``)
produces the same accuracy as individual ``generate_rationale()`` calls.  This
is critical because the production pipeline uses the batch code path, not
the individual one.

Reuses the same ``compliance_eval_set.json`` ground truth so we can directly
compare accuracy against the individual-call compliance test.

Metrics: compliance_level exact-match accuracy, is_compliant directional
accuracy.
Threshold: >= 0.80 on both (same as individual compliance test).
"""

from __future__ import annotations

import asyncio

import pytest

from ctrlmap.llm.client import OllamaClient
from ctrlmap.models.schemas import MappingRationale

from .conftest import compute_binary_metrics, compute_multiclass_accuracy, load_eval_fixture

COMPLIANCE_FIXTURE = "compliance_eval_set.json"
ACCURACY_THRESHOLD = 0.80


async def _run_batch_eval(dataset: list[dict]) -> list[dict]:
    """Run batch evaluation for all entries using a single event loop.

    Creates one OllamaClient and processes all entries sequentially
    within a single async context to avoid event-loop-closed errors.

    Args:
        dataset: The compliance eval fixture entries.

    Returns:
        List of dicts with predicted level. and compliance for each entry.
    """
    client = OllamaClient()
    results = []

    for entry in dataset:
        batch_results, _sub_reqs = await client.evaluate_chunks_batch_async(
            control_text=entry["control_text"],
            chunk_texts=[entry["chunk_text"]],
            requirement_family=entry.get("requirement_family", ""),
        )

        result = batch_results[0]
        if isinstance(result, MappingRationale):
            pred_level = result.compliance_level.value
            pred_compliant = result.is_compliant
        else:
            pred_level = "non_compliant"
            pred_compliant = False

        results.append(
            {
                "id": entry["id"],
                "pred_level": pred_level,
                "pred_compliant": pred_compliant,
                "expected_level": entry["expected_compliance_level"],
                "expected_compliant": entry["expected_is_compliant"],
                "rationale": entry.get("rationale", "N/A"),
            }
        )

    return results


@pytest.mark.eval
class TestBatchEvaluationAccuracy:
    """Batch evaluation pipeline accuracy against compliance ground truth."""

    def test_batch_eval_accuracy_exceeds_threshold(self) -> None:
        """Batch-evaluated compliance levels must match ground truth >= 0.80.

        Groups the compliance fixture entries by control, sends each
        group through ``evaluate_chunks_batch_async()`` (the actual
        pipeline code path), and compares results against expert labels.
        """
        dataset = load_eval_fixture(COMPLIANCE_FIXTURE)

        # Run all evaluations in a single event loop
        eval_results = asyncio.run(_run_batch_eval(dataset))

        level_predictions: list[str] = []
        level_labels: list[str] = []
        compliant_predictions: list[bool] = []
        compliant_labels: list[bool] = []

        for r in eval_results:
            level_predictions.append(r["pred_level"])
            level_labels.append(r["expected_level"])
            compliant_predictions.append(r["pred_compliant"])
            compliant_labels.append(r["expected_compliant"])

            status = "OK" if r["pred_level"] == r["expected_level"] else "MISS"
            print(
                f"  [{status}] {r['id']}: "
                f"predicted={r['pred_level']}, expected={r['expected_level']}"
            )
            if status == "MISS":
                print(f"    Rationale: {r['rationale']}")

        level_accuracy = compute_multiclass_accuracy(level_predictions, level_labels)
        compliant_metrics = compute_binary_metrics(compliant_predictions, compliant_labels)

        print("\nBatch Evaluation Results:")
        print(f"  Level accuracy:     {level_accuracy:.4f}")
        print(f"  Compliant accuracy: {compliant_metrics['accuracy']:.4f}")
        print(f"  Compliant F1:       {compliant_metrics['f1']:.4f}")
        print(f"  Threshold:          {ACCURACY_THRESHOLD}")

        assert level_accuracy >= ACCURACY_THRESHOLD, (
            f"Batch eval level accuracy = {level_accuracy:.4f} "
            f"is below threshold {ACCURACY_THRESHOLD}."
        )
        assert compliant_metrics["accuracy"] >= ACCURACY_THRESHOLD, (
            f"Batch eval is_compliant accuracy = {compliant_metrics['accuracy']:.4f} "
            f"is below threshold {ACCURACY_THRESHOLD}."
        )
