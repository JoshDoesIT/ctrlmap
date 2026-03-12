"""Batch meta-classification accuracy evaluation.

Validates that ``classify_controls_batch_async()`` (the production code
path) produces the same accuracy as individual ``classify_control_type()``
calls.  This is critical because the enrichment pipeline now sends all
controls in a single batch LLM call.

Reuses ``meta_classification_eval_set.json`` ground truth for direct
comparison with the individual-call meta-classification test.

Metric: Binary accuracy.
Threshold: >= 0.90 (same as individual meta-classification test).
"""

from __future__ import annotations

import asyncio

import pytest

from ctrlmap.llm.client import OllamaClient

from .conftest import compute_binary_metrics, load_eval_fixture

META_FIXTURE = "meta_classification_eval_set.json"
ACCURACY_THRESHOLD = 0.90


@pytest.mark.eval
class TestBatchMetaClassificationAccuracy:
    """Batch meta-classification accuracy against ground truth."""

    def test_batch_meta_accuracy_exceeds_threshold(self) -> None:
        """Batch-classified meta vs. substantive accuracy must be >= 0.90.

        Sends ALL controls from the eval set through
        ``classify_controls_batch_async()`` in a single batch call
        (exactly as the pipeline does), and compares each result
        against the expert label.
        """
        dataset = load_eval_fixture(META_FIXTURE)
        client = OllamaClient()

        control_texts = [entry["control_text"] for entry in dataset]
        expected_labels = [entry["expected_is_meta"] for entry in dataset]

        # Send all controls in one batch (the real pipeline code path)
        predictions = asyncio.run(
            client.classify_controls_batch_async(
                control_texts=control_texts,
            )
        )

        assert len(predictions) == len(expected_labels), (
            f"Batch returned {len(predictions)} results but expected {len(expected_labels)}"
        )

        for entry, predicted, expected in zip(dataset, predictions, expected_labels, strict=True):
            status = "OK" if predicted == expected else "MISS"
            print(
                f"  [{status}] {entry['id']} ({entry['control_id']}): "
                f"predicted={predicted}, expected={expected}"
            )
            if status == "MISS":
                print(f"    Rationale: {entry.get('rationale', 'N/A')}")

        metrics = compute_binary_metrics(predictions, expected_labels)

        print("\nBatch Meta-Classification Results:")
        print(f"  Accuracy:   {metrics['accuracy']:.4f}")
        print(f"  Precision:  {metrics['precision']:.4f}")
        print(f"  Recall:     {metrics['recall']:.4f}")
        print(f"  F1:         {metrics['f1']:.4f}")
        print(f"  Threshold:  {ACCURACY_THRESHOLD}")

        assert metrics["accuracy"] >= ACCURACY_THRESHOLD, (
            f"Batch meta-classification accuracy = {metrics['accuracy']:.4f} "
            f"is below threshold {ACCURACY_THRESHOLD}."
        )
