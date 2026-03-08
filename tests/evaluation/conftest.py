"""Shared fixtures and utilities for evaluation tests.

Provides metric computation helpers (precision, recall, F1, accuracy),
fixture-loading utilities, and an OllamaClient factory for eval tests.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def load_eval_fixture(name: str) -> list[dict[str, Any]]:
    """Load a JSON eval fixture by filename from the fixtures directory.

    Args:
        name: Filename of the fixture (e.g. ``relevance_eval_set.json``).

    Returns:
        The parsed JSON data (typically a list of eval entries).
    """
    path = FIXTURES_DIR / name
    with path.open() as f:
        return json.load(f)  # type: ignore[no-any-return]


def compute_binary_metrics(
    predictions: list[bool],
    labels: list[bool],
) -> dict[str, float]:
    """Compute precision, recall, F1, and accuracy for binary classification.

    Args:
        predictions: Predicted boolean values.
        labels: Ground-truth boolean values.

    Returns:
        Dict with ``precision``, ``recall``, ``f1``, and ``accuracy`` keys.
    """
    if len(predictions) != len(labels):
        msg = f"Length mismatch: {len(predictions)} predictions vs {len(labels)} labels"
        raise ValueError(msg)

    tp = sum(1 for p, lbl in zip(predictions, labels, strict=True) if p and lbl)
    fp = sum(1 for p, lbl in zip(predictions, labels, strict=True) if p and not lbl)
    fn = sum(1 for p, lbl in zip(predictions, labels, strict=True) if not p and lbl)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    accuracy = sum(1 for p, lbl in zip(predictions, labels, strict=True) if p == lbl) / len(labels)

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "accuracy": round(accuracy, 4),
    }


def compute_multiclass_accuracy(
    predictions: list[str],
    labels: list[str],
) -> float:
    """Compute exact-match accuracy for multiclass classification.

    Args:
        predictions: Predicted class labels.
        labels: Ground-truth class labels.

    Returns:
        Accuracy as a float between 0.0 and 1.0.
    """
    if not labels:
        return 0.0
    return sum(1 for p, lbl in zip(predictions, labels, strict=True) if p == lbl) / len(labels)
