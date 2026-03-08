"""P1: Compliance classification accuracy evaluation.

Evaluates the LLM's ability to correctly classify the compliance level
of a control-chunk pairing (fully_compliant / partially_compliant /
non_compliant) against expert-labeled ground truth.

Metrics: Exact-match accuracy on compliance_level, directional accuracy
on is_compliant.
Threshold: >= 0.80 on both.

Ref: analysis_results.md — P1 recommendation.
"""

from __future__ import annotations

import pytest

from ctrlmap.llm.structured_output import generate_rationale
from ctrlmap.models.schemas import MappingRationale

from .conftest import compute_binary_metrics, compute_multiclass_accuracy, load_eval_fixture

COMPLIANCE_FIXTURE = "compliance_eval_set.json"
ACCURACY_THRESHOLD = 0.80


@pytest.mark.eval
class TestComplianceAccuracy:
    """P1: LLM compliance classification accuracy against ground truth."""

    def test_compliance_level_accuracy_exceeds_threshold(self) -> None:
        """Exact-match accuracy on compliance_level must be >= 0.80.

        For each entry in the compliance eval set, calls
        generate_rationale() and compares the resulting compliance_level
        and is_compliant against expert labels.
        """
        dataset = load_eval_fixture(COMPLIANCE_FIXTURE)

        level_predictions: list[str] = []
        level_labels: list[str] = []
        compliant_predictions: list[bool] = []
        compliant_labels: list[bool] = []

        for entry in dataset:
            result = generate_rationale(
                control_text=entry["control_text"],
                chunk_text=entry["chunk_text"],
            )

            if isinstance(result, MappingRationale):
                pred_level = result.compliance_level.value
                pred_compliant = result.is_compliant
            else:
                # InsufficientEvidence → treat as non_compliant
                pred_level = "non_compliant"
                pred_compliant = False

            level_predictions.append(pred_level)
            level_labels.append(entry["expected_compliance_level"])
            compliant_predictions.append(pred_compliant)
            compliant_labels.append(entry["expected_is_compliant"])

            status = "OK" if pred_level == entry["expected_compliance_level"] else "MISS"
            print(
                f"  [{status}] {entry['id']}: "
                f"predicted={pred_level}, expected={entry['expected_compliance_level']}"
            )
            if status == "MISS":
                print(f"    Rationale: {entry.get('rationale', 'N/A')}")

        # Compute metrics
        level_accuracy = compute_multiclass_accuracy(level_predictions, level_labels)
        compliant_metrics = compute_binary_metrics(compliant_predictions, compliant_labels)

        print("\nCompliance Eval Results:")
        print(f"  Level accuracy:     {level_accuracy:.4f}")
        print(f"  Compliant accuracy: {compliant_metrics['accuracy']:.4f}")
        print(f"  Compliant F1:       {compliant_metrics['f1']:.4f}")
        print(f"  Threshold:          {ACCURACY_THRESHOLD}")

        assert level_accuracy >= ACCURACY_THRESHOLD, (
            f"Compliance level accuracy = {level_accuracy:.4f} "
            f"is below threshold {ACCURACY_THRESHOLD}."
        )
        assert compliant_metrics["accuracy"] >= ACCURACY_THRESHOLD, (
            f"is_compliant accuracy = {compliant_metrics['accuracy']:.4f} "
            f"is below threshold {ACCURACY_THRESHOLD}."
        )
