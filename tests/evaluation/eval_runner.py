#!/usr/bin/env python3
"""Prompt regression harness for ctrlmap eval suites.

Runs all eval suites (relevance, compliance, meta-classification,
retrieval precision, and end-to-end scenario) and produces a summary
table with per-suite scores.

Usage::

    uv run python tests/evaluation/eval_runner.py
    uv run python tests/evaluation/eval_runner.py --suite relevance
    uv run python tests/evaluation/eval_runner.py --suite relevance --suite meta

This is the P4 "prompt regression harness" — change a prompt in
``client.py``, run this script, and see if scores improve or regress.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time

SUITES: dict[str, dict[str, str]] = {
    "retrieval": {
        "name": "Retrieval Precision (Recall@5)",
        "test": "tests/evaluation/test_retrieval_precision.py",
        "marker": "eval",
    },
    "relevance": {
        "name": "Relevance Verification (F1)",
        "test": "tests/evaluation/test_relevance_accuracy.py",
        "marker": "eval",
    },
    "compliance": {
        "name": "Compliance Classification (Accuracy)",
        "test": "tests/evaluation/test_compliance_accuracy.py",
        "marker": "eval",
    },
    "meta": {
        "name": "Meta-Classification (Accuracy)",
        "test": "tests/evaluation/test_meta_classification.py",
        "marker": "eval",
    },
    "e2e": {
        "name": "End-to-End Scenario",
        "test": "tests/evaluation/test_end_to_end_scenario.py",
        "marker": "eval",
    },
}


def run_suite(suite_key: str) -> dict[str, str | float]:
    """Run a single eval suite and capture the result.

    Args:
        suite_key: Key from SUITES dict.

    Returns:
        Dict with suite name, status (PASS/FAIL), and duration.
    """
    suite = SUITES[suite_key]
    print(f"\n{'=' * 60}")
    print(f"  Running: {suite['name']}")
    print(f"{'=' * 60}")

    t0 = time.monotonic()
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            suite["test"],
            "-m",
            suite["marker"],
            "-v",
            "-s",
            "--tb=short",
        ],
        capture_output=False,
    )
    elapsed = time.monotonic() - t0

    return {
        "name": suite["name"],
        "status": "PASS" if result.returncode == 0 else "FAIL",
        "duration": round(elapsed, 1),
        "exit_code": result.returncode,
    }


def print_summary(results: list[dict[str, str | float]]) -> None:
    """Print a formatted summary table of all results."""
    print(f"\n{'=' * 60}")
    print("  EVAL SUITE SUMMARY")
    print(f"{'=' * 60}")
    print(f"  {'Suite':<40} {'Status':<8} {'Time':>6}")
    print(f"  {'-' * 40} {'-' * 8} {'-' * 6}")

    all_passed = True
    for r in results:
        status_icon = "✅" if r["status"] == "PASS" else "❌"
        print(f"  {r['name']:<40} {status_icon} {r['status']:<5} {r['duration']:>5.1f}s")
        if r["status"] != "PASS":
            all_passed = False

    print(f"  {'-' * 56}")
    overall = "ALL PASSED ✅" if all_passed else "SOME FAILED ❌"
    print(f"  {overall}")
    print()


def main() -> None:
    """Run eval suites and produce summary."""
    parser = argparse.ArgumentParser(description="ctrlmap prompt regression harness")
    parser.add_argument(
        "--suite",
        action="append",
        dest="suites",
        choices=list(SUITES.keys()),
        help="Run specific suite(s). Defaults to all.",
    )
    args = parser.parse_args()

    suite_keys = args.suites if args.suites else list(SUITES.keys())

    print("ctrlmap Eval Runner — Prompt Regression Harness")
    print(f"Running {len(suite_keys)} suite(s): {', '.join(suite_keys)}")

    results = []
    for key in suite_keys:
        results.append(run_suite(key))

    print_summary(results)

    # Exit with 1 if any suite failed
    if any(r["status"] != "PASS" for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
