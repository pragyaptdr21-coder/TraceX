"""CLI entry point for the TraceX detection evaluation.

    python -m backend.evaluation.run_evaluation

Exits with status 0 when an evaluation was produced, and 1 when ground truth is
missing or invalid, so the command is safe to wire into CI as a gate.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from backend.evaluation.engine import DEFAULT_DB_PATH, run_evaluation
from backend.evaluation.predictions import DEFAULT_RISK_THRESHOLD
from backend.evaluation.report import REPORT_PATH, render_report, write_report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Score the TraceX detection engine against official ground truth."
    )
    parser.add_argument(
        "--ground-truth",
        default=None,
        help="Path to ground_truth.csv (defaults to evaluation/ground_truth.csv).",
    )
    parser.add_argument(
        "--db",
        default=DEFAULT_DB_PATH,
        help="Path to the TraceX DuckDB database.",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=DEFAULT_RISK_THRESHOLD,
        help=(
            "Risk Engine decision boundary to score. Defaults to the threshold "
            "TraceX already uses (mule_risk_index >= 50)."
        ),
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Ignore the prediction cache and re-run the detectors.",
    )
    parser.add_argument(
        "--allow-population-mismatch",
        action="store_true",
        help=(
            "Score even when the label counts differ from 1,500 / 23,500. The "
            "mismatch is still reported."
        ),
    )
    parser.add_argument(
        "--json", action="store_true", help="Print the full JSON payload."
    )
    parser.add_argument(
        "--report",
        nargs="?",
        const=REPORT_PATH,
        default=None,
        help="Write the text report to this path.",
    )
    args = parser.parse_args(argv)

    result = run_evaluation(
        db_path=args.db,
        ground_truth_path=args.ground_truth,
        threshold=args.threshold,
        refresh=args.refresh,
        allow_population_mismatch=args.allow_population_mismatch,
    )

    if args.json:
        print(json.dumps(result.as_dict(), indent=2, default=str))
    else:
        print(render_report(result))

    if args.report:
        written = write_report(result, args.report)
        print(f"\nReport written to: {os.path.relpath(written)}")

    return 0 if result.has_metrics else 1


if __name__ == "__main__":
    sys.exit(main())
