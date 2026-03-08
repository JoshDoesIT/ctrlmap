"""P2: Meta-requirement classification accuracy evaluation.

Evaluates the LLM's ability to correctly classify whether a control
is a meta-requirement (governance/documentation about other requirements)
or a substantive control (prescribes a specific security action).

Metric: Binary accuracy.
Threshold: >= 0.90.

Ref: analysis_results.md — P2 recommendation.
"""

from __future__ import annotations

import pytest

from ctrlmap.llm.client import OllamaClient

from .conftest import compute_binary_metrics, load_eval_fixture

META_FIXTURE = "meta_classification_eval_set.json"
ACCURACY_THRESHOLD = 0.90


@pytest.mark.eval
class TestMetaClassificationAccuracy:
    """P2: LLM meta-requirement classification accuracy against ground truth."""

    def test_meta_classification_accuracy_exceeds_threshold(self) -> None:
        """Binary accuracy for meta vs. substantive must be >= 0.90.

        For each control in the meta eval set, calls
        classify_control_type() and compares against the expert label.
        """
        dataset = load_eval_fixture(META_FIXTURE)
        client = OllamaClient()

        predictions: list[bool] = []
        labels: list[bool] = []

        for entry in dataset:
            predicted = client.classify_control_type(
                control_text=entry["control_text"],
            )
            expected = entry["expected_is_meta"]

            predictions.append(predicted)
            labels.append(expected)

            status = "OK" if predicted == expected else "MISS"
            print(
                f"  [{status}] {entry['id']} ({entry['control_id']}): "
                f"predicted={predicted}, expected={expected}"
            )
            if status == "MISS":
                print(f"    Rationale: {entry.get('rationale', 'N/A')}")

        metrics = compute_binary_metrics(predictions, labels)

        print("\nMeta-Classification Eval Results:")
        print(f"  Accuracy:   {metrics['accuracy']:.4f}")
        print(f"  Precision:  {metrics['precision']:.4f}")
        print(f"  Recall:     {metrics['recall']:.4f}")
        print(f"  F1:         {metrics['f1']:.4f}")
        print(f"  Threshold:  {ACCURACY_THRESHOLD}")

        assert metrics["accuracy"] >= ACCURACY_THRESHOLD, (
            f"Meta-classification accuracy = {metrics['accuracy']:.4f} "
            f"is below threshold {ACCURACY_THRESHOLD}."
        )
