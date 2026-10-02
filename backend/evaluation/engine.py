"""Orchestration for the official precision/recall evaluation.

The engine's contract is deliberately blunt: without validated official ground
truth it returns a NOT_AVAILABLE payload and **no metric values at all**. It
will not fall back to a proxy label set, and it will not treat its own detector
output as ground truth.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from backend.evaluation import metrics as M
from backend.evaluation.ground_truth import (
    EXPECTED_MULE_ACCOUNTS,
    EXPECTED_REGULAR_ACCOUNTS,
    GROUND_TRUTH_PATH,
    STATUS_OK,
    GroundTruth,
    load_ground_truth,
)
from backend.evaluation.predictions import (
    DEFAULT_RISK_THRESHOLD,
    DETECTOR_SIGNALS,
    SIGNAL_LABELS,
    PredictionSet,
    get_predictions,
    signal_attribution,
)

DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "storage", "tracex.duckdb"
)

# Thresholds offered for comparison once real labels exist. These are the
# discrete risk-index values the existing detectors can actually produce
# (0, 25, 50, 75, 100), not a search grid fitted to anything.
DEFAULT_SWEEP = [25, 50, 75, 100]

TOP_FP_LIMIT = 25


@dataclass
class EvaluationResult:
    status: str
    ground_truth: GroundTruth
    predictions: Optional[PredictionSet] = None
    combined: Optional[M.MetricSet] = None
    per_detector: Dict[str, Optional[M.MetricSet]] = field(default_factory=dict)
    false_positive_analysis: Dict = field(default_factory=dict)
    threshold_table: List[Dict] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    @property
    def has_metrics(self) -> bool:
        return self.combined is not None

    def as_dict(self) -> Dict:
        payload: Dict = {
            "status": self.status,
            "ground_truth": self.ground_truth.as_dict(),
            "notes": self.notes,
        }

        if not self.has_metrics:
            # No ground truth means no metric keys at all, rather than zeros that
            # could be misread as a perfect or a failed detector.
            payload["metrics_available"] = False
            payload["message"] = (
                "OFFICIAL GROUND TRUTH NOT AVAILABLE. Precision, recall, F1 and "
                "false-positive rate are not reported because no official labels "
                "exist in this repository."
            )
            return payload

        combined = self.combined.as_dict()
        gt = self.ground_truth
        payload.update(
            {
                "metrics_available": True,
                "ground_truth_accounts": gt.row_count,
                "mule_accounts": gt.mule_accounts,
                "regular_accounts": gt.regular_accounts,
                "expected_mule_accounts": EXPECTED_MULE_ACCOUNTS,
                "expected_regular_accounts": EXPECTED_REGULAR_ACCOUNTS,
                "population_validated": (
                    gt.mule_accounts == EXPECTED_MULE_ACCOUNTS
                    and gt.regular_accounts == EXPECTED_REGULAR_ACCOUNTS
                ),
                "predicted_mules": self.predictions.flagged_count()
                if self.predictions
                else combined["predicted_positives"],
                "risk_threshold": self.predictions.threshold if self.predictions else None,
                "prediction_source": self.predictions.source if self.predictions else None,
                "true_positives": combined["true_positives"],
                "false_positives": combined["false_positives"],
                "true_negatives": combined["true_negatives"],
                "false_negatives": combined["false_negatives"],
                "precision": combined["precision"],
                "recall": combined["recall"],
                "f1": combined["f1"],
                "false_positive_rate": combined["false_positive_rate"],
                "false_negative_rate": combined["false_negative_rate"],
                "true_positive_rate": combined["true_positive_rate"],
                "accuracy": combined["accuracy"],
                "evaluated_accounts": combined["evaluated_accounts"],
                "per_detector": {
                    name: (metric.as_dict() if metric else None)
                    for name, metric in self.per_detector.items()
                },
                "false_positive_analysis": self.false_positive_analysis,
                "threshold_comparison": self.threshold_table,
            }
        )
        return payload


def evaluate_predictions(
    ground_truth: GroundTruth, predictions: PredictionSet
) -> EvaluationResult:
    """Score a prediction set against an already-validated label set."""
    if not ground_truth.is_usable:
        return EvaluationResult(status=ground_truth.status, ground_truth=ground_truth)

    labels = ground_truth.labels
    buckets = M.split_errors(labels, predictions.combined)
    fp_accounts = buckets["false_positives"]

    combined = M.evaluate(labels, predictions.combined)

    per_detector: Dict[str, Optional[M.MetricSet]] = {}
    for key in DETECTOR_SIGNALS:
        per_detector[key] = M.evaluate(labels, predictions.per_detector.get(key, {}))

    fp_analysis = _false_positive_analysis(
        ground_truth, predictions, fp_accounts, per_detector
    )
    threshold_table = _threshold_table(labels, predictions, predictions.threshold)

    return EvaluationResult(
        status=STATUS_OK,
        ground_truth=ground_truth,
        predictions=predictions,
        combined=combined,
        per_detector=per_detector,
        false_positive_analysis=fp_analysis,
        threshold_table=threshold_table,
        notes=[
            f"Scores the configured Risk Engine decision at mule_risk_index >= "
            f"{predictions.threshold}.",
            "Distributor L2 is evaluated on exactly what it predicts; its "
            "false positives are reported rather than hidden.",
        ],
    )


def _false_positive_analysis(
    ground_truth: GroundTruth,
    predictions: PredictionSet,
    fp_accounts: List[str],
    per_detector: Dict[str, Optional[M.MetricSet]],
) -> Dict:
    """Detail every regular account the combined pipeline wrongly flagged."""
    regular_accounts = ground_truth.regular_accounts
    fp_count = len(fp_accounts)
    # False positive rate is measured over the labelled regular population.
    fpr = M.safe_div(fp_count, regular_accounts) if regular_accounts else None
    labelled_regular = regular_accounts

    ranked = sorted(
        fp_accounts,
        key=lambda account_id: predictions.risk_scores.get(account_id, 0),
        reverse=True,
    )
    top = ranked[:TOP_FP_LIMIT]
    attribution = signal_attribution(predictions, top)

    signal_counts: Dict[str, int] = {}
    for account_id in fp_accounts:
        for signal_type in predictions.signals.get(account_id, []):
            signal_counts[signal_type] = signal_counts.get(signal_type, 0) + 1

    sole_signal_counts: Dict[str, int] = {}
    for account_id in fp_accounts:
        account_signals = predictions.signals.get(account_id, [])
        if len(account_signals) == 1:
            sole_signal_counts[account_signals[0]] = (
                sole_signal_counts.get(account_signals[0], 0) + 1
            )

    return {
        "total_regular_accounts": regular_accounts,
        "regular_accounts_evaluated": labelled_regular,
        "regular_accounts_incorrectly_flagged": fp_count,
        "regular_accounts_correctly_cleared": labelled_regular - fp_count,
        "false_positive_count": fp_count,
        "false_positive_rate": fpr,
        "top_false_positives": [
            {
                "account_id": account_id,
                "risk_index": predictions.risk_scores.get(account_id, 0),
                "responsible_detectors": attribution.get(account_id, []),
            }
            for account_id in top
        ],
        "false_positives_by_signal": [
            {
                "signal": signal_type,
                "detector": SIGNAL_LABELS.get(signal_type, signal_type),
                "false_positives": count,
            }
            for signal_type, count in sorted(
                signal_counts.items(), key=lambda kv: kv[1], reverse=True
            )
        ],
        "false_positives_by_sole_signal": [
            {
                "signal": signal_type,
                "detector": SIGNAL_LABELS.get(signal_type, signal_type),
                "false_positives": count,
            }
            for signal_type, count in sorted(
                sole_signal_counts.items(), key=lambda kv: kv[1], reverse=True
            )
        ],
        "detector_false_positive_counts": {
            name: (
                metric.as_dict()["false_positives"] if metric else None
            )
            for name, metric in per_detector.items()
        },
    }


def _threshold_table(
    labels: Dict[str, int], predictions: PredictionSet, active: int
) -> List[Dict]:
    """Compare discrete risk thresholds, all scored on the same real labels."""
    rows: List[Dict] = []
    for threshold in sorted(set(DEFAULT_SWEEP) | {active}):
        tuned = {account_id: 1 for account_id, score in predictions.risk_scores.items() if score >= threshold}
        metric = M.evaluate(labels, tuned)
        rows.append(
            {
                "threshold": threshold,
                "active": threshold == active,
                **metric.as_dict(),
            }
        )
    return rows


def run_evaluation(
    db_path: Optional[str] = None,
    ground_truth_path: Optional[str] = None,
    threshold: int = DEFAULT_RISK_THRESHOLD,
    risk_engine=None,
    known_accounts: Optional[set] = None,
    use_cache: bool = True,
    refresh: bool = False,
    allow_population_mismatch: bool = False,
) -> EvaluationResult:
    """Full evaluation: validate labels, predict, score, analyse.

    When labels are missing or invalid the detector pipeline is not even run,
    because a metric without labels has nothing to report.
    """
    db = os.path.abspath(db_path or DEFAULT_DB_PATH)
    gt = load_ground_truth(
        path=ground_truth_path or GROUND_TRUTH_PATH,
        known_accounts=known_accounts,
        allow_population_mismatch=allow_population_mismatch,
    )

    if not gt.is_usable:
        return EvaluationResult(
            status=gt.status,
            ground_truth=gt,
            notes=[
                "Detector pipeline was not scored: no validated labels exist.",
            ],
        )

    predictions = get_predictions(
        db,
        threshold=threshold,
        risk_engine=risk_engine,
        use_cache=use_cache,
        refresh=refresh,
    )
    return evaluate_predictions(gt, predictions)
