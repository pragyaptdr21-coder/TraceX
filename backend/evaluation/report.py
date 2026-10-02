"""Text report rendering for the precision/recall evaluation.

The report states plainly what could not be measured. Absence of labels is
reported as ``NOT AVAILABLE``, never as a zero or a percentage.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import List, Optional

from backend.evaluation.engine import EvaluationResult
from backend.evaluation.ground_truth import (
    EXPECTED_MULE_ACCOUNTS,
    EXPECTED_REGULAR_ACCOUNTS,
)
from backend.evaluation.metrics import format_rate
from backend.evaluation.predictions import SIGNAL_LABELS

REPORT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "reports",
    "TraceX_Precision_Recall_Evaluation_Report.txt",
)

RULE = "=" * 78
THIN = "-" * 78

NOT_AVAILABLE_REASON = (
    "The official 1,500 injected mule account IDs are not present in the "
    "current repository."
)


def _rate_or_na(value: Optional[float]) -> str:
    if value is None:
        return "NOT AVAILABLE"
    return f"{value * 100:.2f}%"


def render_report(result: EvaluationResult) -> str:
    lines: List[str] = []
    add = lines.append

    add(RULE)
    add("TRACEX - PRECISION / RECALL DETECTION EVALUATION REPORT")
    add(RULE)
    add(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    add(f"Status: {result.status}")
    add("")

    gt = result.ground_truth
    add("GROUND TRUTH")
    add(THIN)
    add(f"  Source file            : {gt.path or 'n/a'}")
    add(f"  Ground truth accounts  : {gt.row_count}")
    add(f"  Mule accounts labelled : {gt.mule_accounts} (required {EXPECTED_MULE_ACCOUNTS})")
    add(f"  Regular accounts       : {gt.regular_accounts} (required {EXPECTED_REGULAR_ACCOUNTS})")
    if gt.issues:
        add("  Validation issues:")
        for issue in gt.issues:
            sample = ""
            if issue.samples:
                sample = " e.g. " + ", ".join(issue.samples[:5])
            add(f"    - [{issue.code}] {issue.message}{sample}")
    add("")

    if not result.has_metrics:
        add("MEASURED METRICS")
        add(THIN)
        add("  PRECISION : NOT AVAILABLE")
        add("  RECALL    : NOT AVAILABLE")
        add("  F1        : NOT AVAILABLE")
        add("  FALSE POSITIVE RATE : NOT AVAILABLE")
        add("")
        add("REASON")
        add(THIN)
        add(f"  {NOT_AVAILABLE_REASON}")
        add("")
        add("  TraceX does not substitute a proxy label set. Detector output is")
        add("  never treated as ground truth, and no precision or recall figure")
        add("  is produced until official labels are supplied in")
        add("  evaluation/ground_truth.csv.")
        add("")
        add("  The evaluation engine is implemented and validated. It is ready to")
        add("  run unchanged once the official labels arrive.")
        add("")
        add(RULE)
        add("END OF REPORT - NO METRICS CALCULATED")
        add(RULE)
        return "\n".join(lines)

    payload = result.as_dict()
    combined = result.combined

    add("MEASURED METRICS - COMBINED RISK ENGINE")
    add(THIN)
    add(f"  Risk threshold         : mule_risk_index >= {result.predictions.threshold}")
    add(f"  Prediction source      : {result.predictions.source}")
    add(f"  Accounts evaluated     : {combined.confusion.total}")
    add(f"  True positives  (TP)   : {combined.confusion.true_positives}")
    add(f"  False positives (FP)   : {combined.confusion.false_positives}")
    add(f"  True negatives  (TN)   : {combined.confusion.true_negatives}")
    add(f"  False negatives (FN)   : {combined.confusion.false_negatives}")
    add("")
    add(f"  PRECISION              : {_rate_or_na(combined.precision)}   (raw {format_rate(combined.precision)})")
    add(f"  RECALL                 : {_rate_or_na(combined.recall)}   (raw {format_rate(combined.recall)})")
    add(f"  F1                     : {_rate_or_na(combined.f1)}   (raw {format_rate(combined.f1)})")
    add(f"  FALSE POSITIVE RATE    : {_rate_or_na(combined.false_positive_rate)}   (raw {format_rate(combined.false_positive_rate)})")
    add(f"  FALSE NEGATIVE RATE    : {_rate_or_na(combined.false_negative_rate)}   (raw {format_rate(combined.false_negative_rate)})")
    add("")

    fpa = result.false_positive_analysis
    add("FALSE POSITIVE ANALYSIS (regular accounts)")
    add(THIN)
    add(f"  Total regular accounts            : {fpa['total_regular_accounts']}")
    add(f"  Regular accounts wrongly flagged  : {fpa['false_positive_count']}")
    add(f"  Regular accounts correctly cleared: {fpa['regular_accounts_correctly_cleared']}")
    add(f"  False positive rate               : {_rate_or_na(fpa['false_positive_rate'])}")
    add("")
    if fpa["false_positives_by_signal"]:
        add("  False positives attributed to each detector signal:")
        for row in fpa["false_positives_by_signal"]:
            add(f"    {row['detector']:<16} {row['signal']:<32} {row['false_positives']}")
    else:
        add("  No false positives to attribute.")
    add("")
    if fpa["top_false_positives"]:
        add("  Top false-positive accounts:")
        add(f"    {'ACCOUNT':<18}{'RISK':>6}  RESPONSIBLE DETECTORS")
        for row in fpa["top_false_positives"]:
            detectors = ", ".join(
                SIGNAL_LABELS.get(s["signal"], s["signal"])
                for s in row["responsible_detectors"]
            ) or "none recorded"
            add(f"    {row['account_id']:<18}{row['risk_index']:>6}  {detectors}")
    add("")

    add("PER-DETECTOR RESULTS")
    add(THIN)
    add(
        f"  {'DETECTOR':<16}{'TP':>6}{'FP':>6}{'TN':>7}{'FN':>6}"
        f"{'PRECISION':>12}{'RECALL':>11}{'F1':>10}{'FPR':>11}"
    )
    for name, metric in result.per_detector.items():
        if metric is None:
            add(f"  {name:<16}  NOT COMPUTED")
            continue
        cm = metric.confusion
        add(
            f"  {name:<16}{cm.true_positives:>6}{cm.false_positives:>6}"
            f"{cm.true_negatives:>7}{cm.false_negatives:>6}"
            f"{format_rate(metric.precision):>12}{format_rate(metric.recall):>11}"
            f"{format_rate(metric.f1):>10}{format_rate(metric.false_positive_rate):>11}"
        )
    add("")
    add("  These are objective measurements of each detector as configured.")
    add("  No detector is ranked or characterised here.")
    add("")

    if result.threshold_table:
        add("THRESHOLD COMPARISON (scored on official labels)")
        add(THIN)
        add(
            f"  {'THRESHOLD':>10}{'TP':>7}{'FP':>7}{'TN':>8}{'FN':>7}"
            f"{'PRECISION':>12}{'RECALL':>11}{'F1':>10}"
        )
        for row in result.threshold_table:
            marker = " (active)" if row.get("active") else ""
            add(
                f"  {str(row['threshold']) + marker:>10}{row['true_positives']:>7}"
                f"{row['false_positives']:>7}{row['true_negatives']:>8}"
                f"{row['false_negatives']:>7}{format_rate(row['precision']):>12}"
                f"{format_rate(row['recall']):>11}{format_rate(row['f1']):>10}"
            )
        add("")

    add("NOTES")
    add(THIN)
    for note in result.notes:
        add(f"  - {note}")
    add("")
    add(RULE)
    add("END OF REPORT")
    add(RULE)
    return "\n".join(lines)


def write_report(result: EvaluationResult, path: Optional[str] = None) -> str:
    target = os.path.abspath(path or REPORT_PATH)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as handle:
        handle.write(render_report(result))
        handle.write("\n")
    return target
