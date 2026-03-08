"""P0: Relevance verification accuracy evaluation.

Evaluates the LLM's ability to correctly determine whether a policy
chunk directly addresses a security control, using expert-labeled
ground truth.

Metrics: Precision, Recall, F1, Accuracy.
Threshold: F1 >= 0.85.

Ref: analysis_results.md — P0 recommendation.
"""

from __future__ import annotations

import pytest

from ctrlmap.llm.client import OllamaClient

from .conftest import compute_binary_metrics, load_eval_fixture

RELEVANCE_FIXTURE = "relevance_eval_set.json"
F1_THRESHOLD = 0.85


@pytest.mark.eval
class TestRelevanceAccuracy:
    """P0: LLM relevance verification accuracy against ground truth."""

    def test_relevance_f1_exceeds_threshold(self) -> None:
        """F1 score for relevance classification must be >= 0.85.

        For each entry in the relevance eval set, calls
        verify_chunk_relevance() and compares against the expert label.
        Reports per-entry results for debugging misses, then asserts
        the aggregate F1 meets the threshold.
        """
        dataset = load_eval_fixture(RELEVANCE_FIXTURE)
        client = OllamaClient()

        predictions: list[bool] = []
        labels: list[bool] = []

        for entry in dataset:
            predicted = client.verify_chunk_relevance(
                control_text=entry["control_text"],
                chunk_text=entry["chunk_text"],
                requirement_family=entry.get("requirement_family", ""),
            )
            expected = entry["expected_relevant"]

            predictions.append(predicted)
            labels.append(expected)

            status = "OK" if predicted == expected else "MISS"
            print(f"  [{status}] {entry['id']}: predicted={predicted}, expected={expected}")
            if predicted != expected:
                print(f"    Rationale: {entry.get('rationale', 'N/A')}")

        metrics = compute_binary_metrics(predictions, labels)

        print("\nRelevance Eval Results:")
        print(f"  Precision: {metrics['precision']:.4f}")
        print(f"  Recall:    {metrics['recall']:.4f}")
        print(f"  F1:        {metrics['f1']:.4f}")
        print(f"  Accuracy:  {metrics['accuracy']:.4f}")
        print(f"  Threshold: {F1_THRESHOLD}")

        assert metrics["f1"] >= F1_THRESHOLD, (
            f"Relevance F1 = {metrics['f1']:.4f} is below threshold {F1_THRESHOLD}. "
            f"Precision={metrics['precision']:.4f}, Recall={metrics['recall']:.4f}."
        )
