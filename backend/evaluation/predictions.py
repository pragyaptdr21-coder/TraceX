"""Prediction adapter over the existing TraceX detection pipeline.

This module does **not** introduce a detection algorithm. It runs the same
detectors the API already runs (velocity, collector L1, distributor L2,
terminal L3, cycle), feeds them into the existing :class:`RiskEngine`, and then
projects that output down to the account-level binary decision the evaluation
needs::

    account_id -> predicted_mule in {0, 1}

The classification threshold is *not* invented here. It defaults to the
threshold TraceX already uses to declare a high-risk account
(``mule_risk_index >= 50`` in ``run_detection.run_all``), and is exposed as a
parameter only so the threshold table can sweep it over real ground truth.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from backend.detection.collector_detector import CollectorDetector
from backend.detection.cycle_detector import CycleDetector
from backend.detection.distributor_detector import DistributorDetector
from backend.detection.risk_engine import RiskEngine
from backend.detection.terminal_detector import TerminalDetector
from backend.detection.velocity_detector import VelocityDetector

# Reused from run_detection.run_all: an account is high risk at or above 50.
# This is TraceX's own existing decision boundary, not a new one.
DEFAULT_RISK_THRESHOLD = 50

# Evaluation key -> the detection_type the existing detectors emit.
DETECTOR_SIGNALS: Dict[str, str] = {
    "velocity": "HIGH_VELOCITY_PASS_THROUGH",
    "collector_l1": "COLLECTOR_MULE_L1",
    "distributor_l2": "DISTRIBUTOR_MULE_L2",
    "terminal_l3": "TERMINAL_CASH_OUT_L3",
    "cycle": "CYCLICAL_SMURFING",
}

SIGNAL_LABELS: Dict[str, str] = {
    "HIGH_VELOCITY_PASS_THROUGH": "Velocity",
    "COLLECTOR_MULE_L1": "Collector L1",
    "DISTRIBUTOR_MULE_L2": "Distributor L2",
    "TERMINAL_CASH_OUT_L3": "Terminal L3",
    "CYCLICAL_SMURFING": "Cycle",
}

PREDICTION_CACHE = os.path.join(
    os.path.dirname(__file__), "..", "..", "storage", "evaluation_predictions.json"
)


@dataclass
class PredictionSet:
    """One binary prediction per account, plus the evidence behind it."""

    threshold: int
    combined: Dict[str, int] = field(default_factory=dict)
    per_detector: Dict[str, Dict[str, int]] = field(default_factory=dict)
    risk_scores: Dict[str, int] = field(default_factory=dict)
    signals: Dict[str, List[str]] = field(default_factory=dict)
    source: str = "live"
    detector_counts: Dict[str, int] = field(default_factory=dict)

    def flagged_count(self) -> int:
        return sum(1 for value in self.combined.values() if value == 1)

    def as_dict(self) -> Dict:
        return {
            "threshold": self.threshold,
            "source": self.source,
            "predicted_mules": self.flagged_count(),
            "detector_counts": self.detector_counts,
        }


def build_predictions(
    risk_engine: RiskEngine,
    threshold: int = DEFAULT_RISK_THRESHOLD,
    source: str = "live",
) -> PredictionSet:
    """Project an existing RiskEngine result into evaluation-ready predictions.

    Accounts the pipeline never flagged are absent from ``combined``; the
    confusion matrix treats that absence as a negative prediction, which is the
    correct reading of "no detector fired".
    """
    risk_scores: Dict[str, int] = {}
    signals: Dict[str, List[str]] = {}
    for risk in risk_engine.get_all_risks():
        risk_scores[risk["account_id"]] = int(risk.get("mule_risk_index", 0))
        signals[risk["account_id"]] = [s["type"] for s in risk.get("signals", [])]

    return _assemble(risk_scores, signals, threshold, source)


def _assemble(
    risk_scores: Dict[str, int],
    signals: Dict[str, List[str]],
    threshold: int,
    source: str,
) -> PredictionSet:
    combined: Dict[str, int] = {}
    per_detector: Dict[str, Dict[str, int]] = {key: {} for key in DETECTOR_SIGNALS}

    for account_id, index in risk_scores.items():
        combined[account_id] = 1 if index >= threshold else 0
        account_signals = signals.get(account_id, [])
        for key, signal_type in DETECTOR_SIGNALS.items():
            if signal_type in account_signals:
                per_detector[key][account_id] = 1

    return PredictionSet(
        threshold=threshold,
        combined=combined,
        per_detector=per_detector,
        risk_scores=dict(risk_scores),
        signals=dict(signals),
        source=source,
        detector_counts={key: len(value) for key, value in per_detector.items()},
    )


def run_detection_pipeline(db_path: str) -> RiskEngine:
    """Execute the unmodified TraceX detectors and return the populated engine.

    The detector order and configuration match ``backend.api.lifespan`` so an
    evaluation scores exactly what the live product scores.
    """
    risk_engine = RiskEngine()

    risk_engine.add_detections(VelocityDetector(db_path).detect())
    risk_engine.add_detections(CollectorDetector(db_path, min_unique_senders=5).detect())
    risk_engine.add_detections(DistributorDetector(db_path).detect())
    risk_engine.add_detections(CycleDetector(db_path).detect())
    risk_engine.add_detections(TerminalDetector(db_path).detect())

    return risk_engine


def _cache_path() -> str:
    return os.path.abspath(PREDICTION_CACHE)


def save_cache(predictions: PredictionSet, db_path: str) -> str:
    path = _cache_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = {
        "db_path": os.path.abspath(db_path),
        "threshold": predictions.threshold,
        "risk_scores": predictions.risk_scores,
        "signals": predictions.signals,
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle)
    return path


def load_cache(db_path: str) -> Optional[PredictionSet]:
    """Return a cached prediction set, or ``None`` if it is absent or stale."""
    path = _cache_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None

    if payload.get("db_path") != os.path.abspath(db_path):
        return None

    return _assemble(
        payload.get("risk_scores", {}),
        payload.get("signals", {}),
        payload.get("threshold", DEFAULT_RISK_THRESHOLD),
        "cache",
    )


def get_predictions(
    db_path: str,
    threshold: int = DEFAULT_RISK_THRESHOLD,
    risk_engine: Optional[RiskEngine] = None,
    use_cache: bool = True,
    refresh: bool = False,
) -> PredictionSet:
    """Predictions from the live API engine, a disk cache, or a fresh run.

    ``risk_engine`` is what the running API hands in, which avoids repeating the
    ~30 second detection pass on every evaluation request.
    """
    if risk_engine is not None:
        return build_predictions(risk_engine, threshold=threshold, source="live")

    if use_cache and not refresh:
        cached = load_cache(db_path)
        if cached is not None:
            return _assemble(
                cached.risk_scores, cached.signals, threshold, "cache"
            )

    fresh = build_predictions(
        run_detection_pipeline(db_path), threshold=threshold, source="live"
    )
    save_cache(fresh, db_path)
    return _assemble(fresh.risk_scores, fresh.signals, threshold, "live")


def signal_attribution(
    predictions: PredictionSet, account_ids: List[str]
) -> Dict[str, List[Dict]]:
    """Map each account to the detector signals that produced its flag.

    This is what lets the false-positive report name *which* detector was
    responsible instead of only counting the mistakes.
    """
    attribution: Dict[str, List[Dict]] = {}
    for account_id in account_ids:
        signal_types = predictions.signals.get(account_id, [])
        attribution[account_id] = [
            {
                "signal": signal_type,
                "detector": SIGNAL_LABELS.get(signal_type, signal_type),
                "risk_index": predictions.risk_scores.get(account_id, 0),
            }
            for signal_type in signal_types
        ]
    return attribution


def threshold_sweep_scores(
    predictions: PredictionSet, thresholds: List[int]
) -> List[Dict]:
    """Risk-index distribution ready for a threshold comparison table.

    Only the raw scores are returned here; the metrics for each threshold are
    computed by the engine so a caller cannot accidentally report a threshold
    that was never scored against real labels.
    """
    rows = []
    for threshold in thresholds:
        rows.append(
            {
                "threshold": threshold,
                "predicted_positives": sum(
                    1 for score in predictions.risk_scores.values() if score >= threshold
                ),
            }
        )
    return rows
