"""Tests for the official precision/recall evaluation engine.

IMPORTANT ON FIXTURES
--------------------
Every label set in this file is a synthetic unit-test fixture. They exist only
to prove the arithmetic and the validation rules behave correctly. They are
**not** TraceX evaluation results and must never be presented as such. No test
here asserts a real-world precision or recall figure for TraceX.

The real evaluation requires the official 1,500 injected mule account IDs, which
are not in this repository. ``test_missing_ground_truth_produces_no_metrics``
locks in the behaviour that nothing is reported until those labels arrive.
"""

from __future__ import annotations

import csv
import os
import tempfile

import pytest

from backend.evaluation import metrics as M
from backend.evaluation.engine import evaluate_predictions, run_evaluation
from backend.evaluation.ground_truth import (
    EXPECTED_MULE_ACCOUNTS,
    EXPECTED_REGULAR_ACCOUNTS,
    STATUS_COUNT_MISMATCH,
    STATUS_INVALID,
    STATUS_NOT_AVAILABLE,
    STATUS_OK,
    load_ground_truth,
    load_ground_truth_from_rows,
)
from backend.evaluation.predictions import build_predictions
from backend.detection.risk_engine import RiskEngine


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------

def write_csv(rows, header=("account_id", "label"), path=None):
    """Write a ground-truth CSV. Synthetic test data only."""
    handle = tempfile.NamedTemporaryFile(
        "w", suffix=".csv", delete=False, newline=""
    )
    writer = csv.writer(handle)
    writer.writerow(list(header))
    for row in rows:
        writer.writerow(list(row))
    handle.close()
    return handle.name


def fake_risk_engine(entries):
    """Build a RiskEngine from {account_id: (risk_index, [signal types])}.

    Exercises the real RiskEngine and the real prediction adapter without
    touching the 2M dataset.
    """
    engine = RiskEngine()
    for account_id, (index, signals) in entries.items():
        engine.account_risks[account_id] = {
            "account_id": account_id,
            "mule_risk_index": index,
            "signals": [{"type": s, "contribution": 0} for s in signals],
            "evidence_summary": [],
        }
    return engine


# --------------------------------------------------------------------------
# 1. Known synthetic labels / predictions
# --------------------------------------------------------------------------

def test_known_synthetic_labels_and_predictions():
    """A hand-checkable 2x2: one of each cell.

    Fixture values, not a TraceX result.
    """
    labels = {"A": 1, "B": 1, "C": 0, "D": 0}
    predictions = {"A": 1, "B": 0, "C": 1, "D": 0}

    result = M.evaluate(labels, predictions)

    assert result.confusion.true_positives == 1   # A
    assert result.confusion.false_negatives == 1  # B
    assert result.confusion.false_positives == 1  # C
    assert result.confusion.true_negatives == 1   # D
    assert result.confusion.total == 4


# --------------------------------------------------------------------------
# 2-5. Individual confusion cell counts
# --------------------------------------------------------------------------

def test_true_positive_count():
    cm = M.confusion_matrix({"A": 1, "B": 1}, {"A": 1, "B": 0})
    assert cm.true_positives == 1
    assert cm.total == 2


def test_false_positive_count():
    cm = M.confusion_matrix({"A": 0, "B": 0}, {"A": 1, "B": 0})
    assert cm.false_positives == 1
    assert cm.true_negatives == 1


def test_true_negative_count():
    cm = M.confusion_matrix({"A": 0, "B": 0}, {"A": 0, "B": 0})
    assert cm.true_negatives == 2
    assert cm.false_positives == 0


def test_false_negative_count():
    cm = M.confusion_matrix({"A": 1, "B": 1}, {"A": 1, "B": 0})
    assert cm.false_negatives == 1
    assert cm.true_positives == 1


# --------------------------------------------------------------------------
# 6-7. Precision and recall
# --------------------------------------------------------------------------

def test_precision():
    # TP=3, FP=1 -> 3/4
    result = M.evaluate(
        {"a": 1, "b": 1, "c": 1, "d": 0},
        {"a": 1, "b": 1, "c": 1, "d": 1},
    )
    assert result.precision == pytest.approx(0.75)


def test_recall():
    # TP=3, FN=1 -> 3/4
    result = M.evaluate(
        {"a": 1, "b": 1, "c": 1, "d": 1},
        {"a": 1, "b": 1, "c": 1, "d": 0},
    )
    assert result.recall == pytest.approx(0.75)


# --------------------------------------------------------------------------
# 8. F1
# --------------------------------------------------------------------------

def test_f1_harmonic_mean_of_precision_and_recall():
    result = M.evaluate(
        {"a": 1, "b": 1, "c": 1, "d": 1},
        {"a": 1, "b": 1, "c": 0, "d": 1},
    )
    # P=3/3, R=3/4, F1=2*1*0.75/1.75
    assert result.precision == pytest.approx(1.0)
    assert result.recall == pytest.approx(0.75)
    assert result.f1 == pytest.approx(2 * 1.0 * 0.75 / 1.75)


# --------------------------------------------------------------------------
# 9. False positive rate
# --------------------------------------------------------------------------

def test_false_positive_rate():
    # FP=2 over FP+TN=10 -> 0.2
    labels = {f"m{i}": 1 for i in range(4)}
    labels.update({f"r{i}": 0 for i in range(8)})
    predictions = {f"m{i}": 1 for i in range(4)}
    predictions.update({f"r{i}": (1 if i < 2 else 0) for i in range(8)})

    result = M.evaluate(labels, predictions)

    assert result.confusion.false_positives == 2
    assert result.confusion.true_negatives == 6
    assert result.false_positive_rate == pytest.approx(2 / 8)


# --------------------------------------------------------------------------
# Zero denominators
# --------------------------------------------------------------------------

def test_zero_denominators_return_none_not_zero():
    """A 0/0 rate must be None, never 0.0 or 1.0."""
    assert M.safe_div(0, 0) is None
    assert M.safe_div(5, 0) is None

    # No actual positives -> recall undefined.
    no_positives = M.evaluate({"a": 0, "b": 0}, {"a": 0, "b": 0})
    assert no_positives.recall is None
    assert no_positives.f1 is None
    assert no_positives.false_negative_rate is None

    # No predicted positives -> precision undefined.
    no_predictions = M.evaluate({"a": 1, "b": 1}, {"a": 0, "b": 0})
    assert no_predictions.precision is None
    assert no_predictions.f1 is None
    assert no_predictions.accuracy == pytest.approx(0.0)

    assert M.format_rate(None) == "NOT COMPUTABLE"


# --------------------------------------------------------------------------
# 10. Duplicate ground-truth IDs
# --------------------------------------------------------------------------

def test_duplicate_ground_truth_ids_are_reported_and_block():
    path = write_csv([("A", 1), ("A", 0), ("B", 0)])
    try:
        gt = load_ground_truth(path=path, allow_population_mismatch=True)
    finally:
        os.remove(path)

    assert gt.status == STATUS_INVALID
    assert not gt.is_usable
    assert "A" in gt.duplicate_accounts
    assert any(i.code == "DUPLICATE_ACCOUNT_IDS" for i in gt.issues)


def test_inline_duplicate_ids_are_reported():
    gt = load_ground_truth_from_rows(
        [{"account_id": "A", "label": 1}, {"account_id": "A", "label": 0}],
        expected_mules=1,
        expected_regular=0,
    )
    assert gt.status == STATUS_INVALID
    assert "A" in gt.duplicate_accounts


# --------------------------------------------------------------------------
# 11. Invalid labels
# --------------------------------------------------------------------------

@pytest.mark.parametrize("bad", ["2", "-1", "mule", "1.5", "yes"])
def test_invalid_labels_are_rejected(bad):
    path = write_csv([("A", bad), ("B", 0)])
    try:
        gt = load_ground_truth(path=path, allow_population_mismatch=True)
    finally:
        os.remove(path)

    assert gt.status == STATUS_INVALID
    assert not gt.is_usable
    assert "A" in gt.invalid_labels


def test_blank_label_is_reported_as_missing():
    path = write_csv([("A", ""), ("B", 0)])
    try:
        gt = load_ground_truth(path=path, allow_population_mismatch=True)
    finally:
        os.remove(path)

    assert "A" in gt.missing_labels
    assert not gt.is_usable


# --------------------------------------------------------------------------
# 12. Missing ground truth
# --------------------------------------------------------------------------

def test_missing_ground_truth_reports_not_available(tmp_path):
    gt = load_ground_truth(path=str(tmp_path / "does_not_exist.csv"))
    assert gt.status == STATUS_NOT_AVAILABLE
    assert not gt.is_usable
    assert gt.labels == {}


def test_header_only_ground_truth_reports_not_available(tmp_path):
    """The shipped template must behave like an absent file, not like data."""
    path = tmp_path / "ground_truth.csv"
    path.write_text("account_id,label\n", encoding="utf-8")

    gt = load_ground_truth(path=str(path))
    assert gt.status == STATUS_NOT_AVAILABLE
    assert not gt.is_usable


def test_missing_columns_are_invalid(tmp_path):
    path = tmp_path / "ground_truth.csv"
    path.write_text("account,flag\nA,1\n", encoding="utf-8")

    gt = load_ground_truth(path=str(path))
    assert gt.status == STATUS_INVALID
    assert any(i.code == "MISSING_COLUMNS" for i in gt.issues)


def test_shipped_ground_truth_file_has_no_labels():
    """The repository's own ground_truth.csv must never contain invented IDs."""
    from backend.evaluation.ground_truth import GROUND_TRUTH_PATH

    resolved = os.path.abspath(GROUND_TRUTH_PATH)
    if not os.path.exists(resolved):
        pytest.skip("ground_truth.csv not present")

    with open(resolved, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows == [], "ground_truth.csv must not be populated with invented labels"


# --------------------------------------------------------------------------
# 13. Population counts
# --------------------------------------------------------------------------

def test_population_count_mismatch_blocks_metrics():
    path = write_csv([("A", 1), ("B", 0)])
    try:
        gt = load_ground_truth(
            path=path,
            expected_mules=EXPECTED_MULE_ACCOUNTS,
            expected_regular=EXPECTED_REGULAR_ACCOUNTS,
        )
    finally:
        os.remove(path)

    assert gt.status == STATUS_COUNT_MISMATCH
    assert not gt.is_usable
    issue = next(i for i in gt.issues if i.code == "POPULATION_COUNT_MISMATCH")
    assert "1 mule" in issue.message
    assert "1 regular" in issue.message


def test_population_mismatch_can_be_overridden_explicitly():
    path = write_csv([("A", 1), ("B", 0)])
    try:
        gt = load_ground_truth(path=path, allow_population_mismatch=True)
    finally:
        os.remove(path)

    assert gt.status == STATUS_OK
    assert gt.is_usable
    # The mismatch is still recorded even when overridden.
    assert any(i.code == "POPULATION_COUNT_MISMATCH" for i in gt.issues)


def test_full_population_counts_are_accepted():
    """1,500 mules + 23,500 regular must validate cleanly."""
    rows = [(f"MULE{i:05d}", 1) for i in range(EXPECTED_MULE_ACCOUNTS)]
    rows += [(f"REG{i:05d}", 0) for i in range(EXPECTED_REGULAR_ACCOUNTS)]
    path = write_csv(rows)
    try:
        gt = load_ground_truth(path=path)
    finally:
        os.remove(path)

    assert gt.status == STATUS_OK
    assert gt.mule_accounts == 1500
    assert gt.regular_accounts == 23500
    assert gt.row_count == 25000


# --------------------------------------------------------------------------
# 14. Accounts missing from the dataset
# --------------------------------------------------------------------------

def test_accounts_absent_from_dataset_are_reported():
    path = write_csv([("KNOWN", 1), ("NOT_IN_DATASET", 1)])
    try:
        gt = load_ground_truth(
            path=path,
            known_accounts={"KNOWN"},
            allow_population_mismatch=True,
        )
    finally:
        os.remove(path)

    assert "NOT_IN_DATASET" in gt.unknown_accounts
    assert "KNOWN" not in gt.unknown_accounts
    issue = next(i for i in gt.issues if i.code == "ACCOUNTS_NOT_IN_DATASET")
    assert issue.count == 1


# --------------------------------------------------------------------------
# 15. No fabricated metrics
# --------------------------------------------------------------------------

def test_missing_ground_truth_produces_no_metrics():
    """The central guarantee: absent labels means no metric keys at all."""
    result = run_evaluation(ground_truth_path="/nonexistent/ground_truth.csv")

    assert result.status == STATUS_NOT_AVAILABLE
    assert not result.has_metrics
    assert result.combined is None

    payload = result.as_dict()
    for forbidden in (
        "precision",
        "recall",
        "f1",
        "false_positive_rate",
        "true_positives",
        "false_positives",
        "true_negatives",
        "false_negatives",
    ):
        assert forbidden not in payload, f"{forbidden} must be absent, not zeroed"
    assert payload["metrics_available"] is False


def test_shipped_state_reports_not_available():
    """Running against the repository as shipped yields no numbers."""
    result = run_evaluation()
    assert result.status == STATUS_NOT_AVAILABLE
    assert not result.has_metrics
    assert "NOT AVAILABLE" in result.as_dict()["message"]


def test_report_states_metrics_are_not_available():
    from backend.evaluation.report import render_report

    result = run_evaluation(ground_truth_path="/nonexistent/ground_truth.csv")
    text = render_report(result)

    assert "PRECISION : NOT AVAILABLE" in text
    assert "RECALL    : NOT AVAILABLE" in text
    assert "F1        : NOT AVAILABLE" in text
    assert "NO METRICS CALCULATED" in text
    # No percentage may appear anywhere in the not-available report.
    assert "%" not in text


def test_api_response_shape_has_no_fake_values():
    """The NOT_AVAILABLE payload must never contain numeric metrics."""
    result = run_evaluation(ground_truth_path="/nonexistent/ground_truth.csv")
    payload = result.as_dict()

    assert payload["success"] if "success" in payload else True
    assert payload["status"] == STATUS_NOT_AVAILABLE
    assert "predicted_mules" not in payload


# --------------------------------------------------------------------------
# Prediction adapter + engine behaviour with fixtures
# --------------------------------------------------------------------------

def test_prediction_adapter_uses_existing_threshold():
    engine = fake_risk_engine(
        {
            "LOW": (25, ["HIGH_VELOCITY_PASS_THROUGH"]),
            "MID": (50, ["COLLECTOR_MULE_L1"]),
            "HIGH": (75, ["TERMINAL_CASH_OUT_L3"]),
        }
    )
    predictions = build_predictions(engine, threshold=50)

    assert predictions.combined["LOW"] == 0
    assert predictions.combined["MID"] == 1
    assert predictions.combined["HIGH"] == 1
    assert predictions.per_detector["collector_l1"] == {"MID": 1}
    assert predictions.per_detector["terminal_l3"] == {"HIGH": 1}
    assert predictions.per_detector["velocity"] == {"LOW": 1}


def test_engine_scores_per_detector_and_false_positives():
    """Fixture-driven check that FP analysis attributes signals correctly."""
    engine = fake_risk_engine(
        {
            "MULE1": (50, ["COLLECTOR_MULE_L1"]),
            "MULE2": (50, ["TERMINAL_CASH_OUT_L3"]),
            "REG1": (50, ["COLLECTOR_MULE_L1"]),   # false positive
            "REG2": (0, []),                        # true negative
        }
    )
    predictions = build_predictions(engine, threshold=50)

    path = write_csv(
        [("MULE1", 1), ("MULE2", 1), ("REG1", 0), ("REG2", 0)]
    )
    try:
        gt = load_ground_truth(path=path, allow_population_mismatch=True)
    finally:
        os.remove(path)

    result = evaluate_predictions(gt, predictions)
    payload = result.as_dict()

    assert payload["true_positives"] == 2
    assert payload["false_positives"] == 1
    assert payload["true_negatives"] == 1
    assert payload["false_negatives"] == 0
    assert payload["precision"] == pytest.approx(2 / 3)

    analysis = payload["false_positive_analysis"]
    assert analysis["total_regular_accounts"] == 2
    assert analysis["false_positive_count"] == 1
    assert analysis["false_positive_rate"] == pytest.approx(0.5)
    assert analysis["top_false_positives"][0]["account_id"] == "REG1"
    assert analysis["top_false_positives"][0]["responsible_detectors"][0]["detector"] == "Collector L1"

    # Per-detector must expose the collector's own false positive.
    assert payload["per_detector"]["collector_l1"]["false_positives"] == 1
    assert payload["per_detector"]["terminal_l3"]["false_positives"] == 0

    # Distributor L2 is measured, not hidden.
    assert "distributor_l2" in payload["per_detector"]


def test_threshold_table_is_scored_on_same_labels():
    engine = fake_risk_engine(
        {"A": (25, ["HIGH_VELOCITY_PASS_THROUGH"]), "B": (50, ["COLLECTOR_MULE_L1"])}
    )
    predictions = build_predictions(engine, threshold=50)

    path = write_csv([("A", 1), ("B", 1), ("C", 0)])
    try:
        gt = load_ground_truth(path=path, allow_population_mismatch=True)
    finally:
        os.remove(path)

    table = evaluate_predictions(gt, predictions).as_dict()["threshold_comparison"]
    by_threshold = {row["threshold"]: row for row in table}

    # A and B are both labelled mules; C is a regular account.
    # At 25 both A and B clear the bar -> both recalled, no false positive.
    assert by_threshold[25]["predicted_positives"] == 2
    assert by_threshold[25]["recall"] == pytest.approx(1.0)
    assert by_threshold[25]["false_positives"] == 0

    # At 50 only B clears the bar -> A becomes a miss.
    assert by_threshold[50]["predicted_positives"] == 1
    assert by_threshold[50]["recall"] == pytest.approx(0.5)
    assert by_threshold[50]["false_negatives"] == 1
    assert by_threshold[50]["active"] is True
