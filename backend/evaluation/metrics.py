"""Confusion-matrix and rate arithmetic for the TraceX detection evaluation.

Every function here is pure: it takes already-materialised labels and
predictions and returns counts. Nothing in this module knows how predictions
are produced, and nothing in it ever substitutes a default value for a metric
that cannot be computed. An undefined rate is ``None``, never ``0`` and never
``1.0``, so a caller can never mistake "no denominator" for a real result.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, Iterable, Mapping, Optional, Sequence

# A label/prediction domain. 1 means "mule / suspicious".
POSITIVE = 1
NEGATIVE = 0


def safe_div(numerator: float, denominator: float) -> Optional[float]:
    """Divide, returning ``None`` when the denominator is zero.

    ``None`` is the only correct answer for a 0/0 rate. Returning 0.0 would be a
    fabricated metric and returning 1.0 would be worse.
    """
    if denominator == 0:
        return None
    return numerator / denominator


@dataclass(frozen=True)
class ConfusionMatrix:
    true_positives: int = 0
    false_positives: int = 0
    true_negatives: int = 0
    false_negatives: int = 0

    @property
    def total(self) -> int:
        return (
            self.true_positives
            + self.false_positives
            + self.true_negatives
            + self.false_negatives
        )

    def as_dict(self) -> Dict[str, int]:
        return asdict(self)


@dataclass(frozen=True)
class MetricSet:
    """Full metric bundle for one prediction vector.

    ``None`` in any rate field means the rate is mathematically undefined for
    this confusion matrix (for example recall with no actual positives).
    """

    confusion: ConfusionMatrix
    precision: Optional[float]
    recall: Optional[float]
    f1: Optional[float]
    false_positive_rate: Optional[float]
    false_negative_rate: Optional[float]
    true_positive_rate: Optional[float]
    accuracy: Optional[float]
    predicted_positives: int
    actual_positives: int

    def as_dict(self) -> Dict:
        return {
            "true_positives": self.confusion.true_positives,
            "false_positives": self.confusion.false_positives,
            "true_negatives": self.confusion.true_negatives,
            "false_negatives": self.confusion.false_negatives,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
            "false_positive_rate": self.false_positive_rate,
            "false_negative_rate": self.false_negative_rate,
            "true_positive_rate": self.true_positive_rate,
            "accuracy": self.accuracy,
            "predicted_positives": self.predicted_positives,
            "actual_positives": self.actual_positives,
            "evaluated_accounts": self.confusion.total,
        }


def confusion_matrix(
    labels: Mapping[str, int], predictions: Mapping[str, int]
) -> ConfusionMatrix:
    """Build a confusion matrix over the accounts present in ``labels``.

    An account present in ``labels`` but missing from ``predictions`` is counted
    as a negative prediction, not skipped. Silence from the detector means "not
    flagged", and treating it as "no data" would quietly inflate recall.
    """
    tp = fp = tn = fn = 0
    for account_id, label in labels.items():
        prediction = predictions.get(account_id, NEGATIVE)
        if label == POSITIVE and prediction == POSITIVE:
            tp += 1
        elif label == POSITIVE and prediction != POSITIVE:
            fn += 1
        elif label != POSITIVE and prediction == POSITIVE:
            fp += 1
        else:
            tn += 1
    return ConfusionMatrix(tp, fp, tn, fn)


def precision_from(cm: ConfusionMatrix) -> Optional[float]:
    return safe_div(cm.true_positives, cm.true_positives + cm.false_positives)


def recall_from(cm: ConfusionMatrix) -> Optional[float]:
    return safe_div(cm.true_positives, cm.true_positives + cm.false_negatives)


def f1_from(precision: Optional[float], recall: Optional[float]) -> Optional[float]:
    if precision is None or recall is None:
        return None
    return safe_div(2 * precision * recall, precision + recall)


def false_positive_rate_from(cm: ConfusionMatrix) -> Optional[float]:
    """FP / (FP + TN): the share of genuine regular accounts wrongly flagged."""
    return safe_div(cm.false_positives, cm.false_positives + cm.true_negatives)


def false_negative_rate_from(cm: ConfusionMatrix) -> Optional[float]:
    """FN / (FN + TP): the share of genuine mules missed."""
    return safe_div(cm.false_negatives, cm.false_negatives + cm.true_positives)


def compute_metrics(cm: ConfusionMatrix) -> MetricSet:
    """Derive the full metric bundle from a confusion matrix."""
    precision = precision_from(cm)
    recall = recall_from(cm)
    return MetricSet(
        confusion=cm,
        precision=precision,
        recall=recall,
        f1=f1_from(precision, recall),
        false_positive_rate=false_positive_rate_from(cm),
        false_negative_rate=false_negative_rate_from(cm),
        true_positive_rate=recall,
        accuracy=safe_div(cm.true_positives + cm.true_negatives, cm.total),
        predicted_positives=cm.true_positives + cm.false_positives,
        actual_positives=cm.true_positives + cm.false_negatives,
    )


def evaluate(
    labels: Mapping[str, int], predictions: Mapping[str, int]
) -> MetricSet:
    """Convenience wrapper: confusion matrix plus derived rates."""
    return compute_metrics(confusion_matrix(labels, predictions))


def split_errors(
    labels: Mapping[str, int], predictions: Mapping[str, int]
) -> Dict[str, Sequence[str]]:
    """Partition the evaluated accounts into TP/FP/TN/FN buckets by account id.

    Used by the false-positive analysis, which needs the offending account ids
    rather than just their count.
    """
    buckets: Dict[str, list] = {
        "true_positives": [],
        "false_positives": [],
        "true_negatives": [],
        "false_negatives": [],
    }
    for account_id, label in labels.items():
        prediction = predictions.get(account_id, NEGATIVE)
        if label == POSITIVE and prediction == POSITIVE:
            buckets["true_positives"].append(account_id)
        elif label == POSITIVE and prediction != POSITIVE:
            buckets["false_negatives"].append(account_id)
        elif label != POSITIVE and prediction == POSITIVE:
            buckets["false_positives"].append(account_id)
        else:
            buckets["true_negatives"].append(account_id)
    return buckets


def format_rate(value: Optional[float], digits: int = 4) -> str:
    """Render a rate for the text report, preserving "undefined" as text."""
    if value is None:
        return "NOT COMPUTABLE"
    return f"{value:.{digits}f}"


def iter_positive_accounts(labels: Iterable[tuple]) -> list:
    return [account_id for account_id, label in labels if label == POSITIVE]
