"""Official precision/recall evaluation for the TraceX detection engine.

This package scores the existing TraceX detectors against externally supplied
ground-truth labels. It contains no detection logic of its own and no embedded
labels: without an official ``evaluation/ground_truth.csv`` it reports
NOT_AVAILABLE rather than producing a number.
"""

from backend.evaluation.ground_truth import (
    EXPECTED_MULE_ACCOUNTS,
    EXPECTED_REGULAR_ACCOUNTS,
    GROUND_TRUTH_PATH,
    STATUS_COUNT_MISMATCH,
    STATUS_INVALID,
    STATUS_NOT_AVAILABLE,
    STATUS_OK,
    GroundTruth,
    load_ground_truth,
)
from backend.evaluation.metrics import (
    ConfusionMatrix,
    MetricSet,
    compute_metrics,
    confusion_matrix,
    evaluate,
    safe_div,
    split_errors,
)
from backend.evaluation.predictions import (
    DEFAULT_RISK_THRESHOLD,
    DETECTOR_SIGNALS,
    SIGNAL_LABELS,
    PredictionSet,
    build_predictions,
    get_predictions,
    run_detection_pipeline,
)
from backend.evaluation.engine import (
    EvaluationResult,
    evaluate_predictions,
    run_evaluation,
)

__all__ = [
    "ConfusionMatrix",
    "DEFAULT_RISK_THRESHOLD",
    "DETECTOR_SIGNALS",
    "EXPECTED_MULE_ACCOUNTS",
    "EXPECTED_REGULAR_ACCOUNTS",
    "EvaluationResult",
    "GROUND_TRUTH_PATH",
    "GroundTruth",
    "MetricSet",
    "PredictionSet",
    "SIGNAL_LABELS",
    "STATUS_COUNT_MISMATCH",
    "STATUS_INVALID",
    "STATUS_NOT_AVAILABLE",
    "STATUS_OK",
    "build_predictions",
    "compute_metrics",
    "confusion_matrix",
    "evaluate",
    "evaluate_predictions",
    "get_predictions",
    "load_ground_truth",
    "run_detection_pipeline",
    "run_evaluation",
    "safe_div",
    "split_errors",
]
