"""Ground-truth loading and validation.

The official 1,500 injected mule account IDs are **not** present in this
repository. This module therefore only ever reads labels that a human supplied.
It never infers a label, never derives one from an account name, and never
falls back to the detector output as a stand-in for ground truth.

Validation is deliberately strict and *blocking*: any structural problem raises
or returns a non-OK status so a metric can never be computed against a
compromised label set.
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

# Population the Problem Statement defines for the official evaluation set.
EXPECTED_MULE_ACCOUNTS = 1500
EXPECTED_REGULAR_ACCOUNTS = 23500

STATUS_OK = "OK"
STATUS_NOT_AVAILABLE = "OFFICIAL GROUND TRUTH NOT AVAILABLE"
STATUS_INVALID = "INVALID GROUND TRUTH"
STATUS_COUNT_MISMATCH = "GROUND TRUTH COUNT MISMATCH"

VALID_LABELS = {0, 1}

GROUND_TRUTH_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "evaluation", "ground_truth.csv"
)


@dataclass
class ValidationIssue:
    code: str
    message: str
    count: int = 0
    samples: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict:
        return {
            "code": self.code,
            "message": self.message,
            "count": self.count,
            "samples": self.samples[:10],
        }


@dataclass
class GroundTruth:
    """A validated label set plus the audit trail that produced it."""

    status: str
    labels: Dict[str, int] = field(default_factory=dict)
    issues: List[ValidationIssue] = field(default_factory=list)
    path: Optional[str] = None
    row_count: int = 0
    mule_accounts: int = 0
    regular_accounts: int = 0
    duplicate_accounts: List[str] = field(default_factory=list)
    invalid_labels: List[str] = field(default_factory=list)
    missing_labels: List[str] = field(default_factory=list)
    unknown_accounts: List[str] = field(default_factory=list)
    source: str = "file"

    @property
    def is_usable(self) -> bool:
        return self.status == STATUS_OK and bool(self.labels)

    def as_dict(self) -> Dict:
        return {
            "status": self.status,
            "usable": self.is_usable,
            "source": self.source,
            "path": self.path,
            "ground_truth_accounts": self.row_count,
            "mule_accounts": self.mule_accounts,
            "regular_accounts": self.regular_accounts,
            "expected_mule_accounts": EXPECTED_MULE_ACCOUNTS,
            "expected_regular_accounts": EXPECTED_REGULAR_ACCOUNTS,
            "duplicate_accounts": self.duplicate_accounts,
            "invalid_labels": self.invalid_labels,
            "missing_labels": self.missing_labels,
            "unknown_accounts": self.unknown_accounts,
            "issues": [issue.as_dict() for issue in self.issues],
        }


def not_available(reason: str, path: Optional[str] = None) -> GroundTruth:
    return GroundTruth(
        status=STATUS_NOT_AVAILABLE,
        path=path,
        issues=[ValidationIssue(code="GROUND_TRUTH_MISSING", message=reason)],
    )


def _normalise_label(raw: str):
    """Parse a label cell, tolerating surrounding whitespace and float text."""
    text = (raw or "").strip()
    if text == "":
        return None
    try:
        value = float(text)
    except (TypeError, ValueError):
        return "INVALID"
    if value == 1.0:
        return 1
    if value == 0.0:
        return 0
    return "INVALID"


def load_ground_truth(
    path: Optional[str] = None,
    known_accounts: Optional[Set[str]] = None,
    expected_mules: int = EXPECTED_MULE_ACCOUNTS,
    expected_regular: int = EXPECTED_REGULAR_ACCOUNTS,
    allow_population_mismatch: bool = False,
) -> GroundTruth:
    """Read and fully validate ``evaluation/ground_truth.csv``.

    ``known_accounts`` is the set of account ids that exist in the 2M dataset.
    When supplied, any label naming an account outside that set is reported.
    Population counts are checked against the Problem Statement defaults; a
    mismatch blocks the evaluation unless the caller explicitly opts out, and
    the opt-out is recorded in the result.
    """
    resolved = os.path.abspath(path or GROUND_TRUTH_PATH)

    if not os.path.exists(resolved):
        return not_available(
            "evaluation/ground_truth.csv is absent. The official 1,500 injected "
            "mule account IDs are not present in the current repository, so no "
            "precision or recall figure can be produced.",
            path=resolved,
        )

    with open(resolved, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = [f.strip() for f in (reader.fieldnames or [])]
        rows = list(reader)

    if not fieldnames or len(fieldnames) < 2:
        return GroundTruth(
            status=STATUS_INVALID,
            path=resolved,
            issues=[
                ValidationIssue(
                    code="MISSING_COLUMNS",
                    message=(
                        "ground_truth.csv must have at least the columns "
                        "account_id,label"
                    ),
                )
            ],
        )

    column_map = {name.strip(): name for name in reader.fieldnames}
    account_col = column_map.get("account_id")
    label_col = column_map.get("label")
    if account_col is None or label_col is None:
        return GroundTruth(
            status=STATUS_INVALID,
            path=resolved,
            issues=[
                ValidationIssue(
                    code="MISSING_COLUMNS",
                    message=(
                        f"Expected 'account_id' and 'label' columns, found: "
                        f"{', '.join(fieldnames)}"
                    ),
                )
            ],
        )

    labels: Dict[str, int] = {}
    duplicates: List[str] = []
    invalid: List[str] = []
    missing: List[str] = []
    unknown: List[str] = []
    issues: List[ValidationIssue] = []

    for index, row in enumerate(rows, start=2):
        raw_account = (row.get(account_col) or "").strip()
        if not raw_account:
            missing.append(f"<blank account_id at line {index}>")
            continue

        parsed = _normalise_label(row.get(label_col))
        if parsed is None:
            missing.append(raw_account)
            continue
        if parsed == "INVALID":
            invalid.append(raw_account)
            continue

        if raw_account in labels:
            if raw_account not in duplicates:
                duplicates.append(raw_account)
            continue

        labels[raw_account] = parsed

        if known_accounts is not None and raw_account not in known_accounts:
            unknown.append(raw_account)

    if duplicates:
        issues.append(
            ValidationIssue(
                code="DUPLICATE_ACCOUNT_IDS",
                message="The same account_id appears more than once; the last "
                "label was dropped and the first occurrence was used.",
                count=len(duplicates),
                samples=duplicates,
            )
        )
    if invalid:
        issues.append(
            ValidationIssue(
                code="INVALID_LABELS",
                message="Labels must be exactly 0 or 1.",
                count=len(invalid),
                samples=invalid,
            )
        )
    if missing:
        issues.append(
            ValidationIssue(
                code="MISSING_LABELS",
                message="Rows with a blank account_id or blank label.",
                count=len(missing),
                samples=missing,
            )
        )
    if unknown:
        issues.append(
            ValidationIssue(
                code="ACCOUNTS_NOT_IN_DATASET",
                message=(
                    "Labeled accounts that do not appear in the 2M transaction "
                    "dataset."
                ),
                count=len(unknown),
                samples=unknown,
            )
        )

    mule_accounts = sum(1 for value in labels.values() if value == 1)
    regular_accounts = sum(1 for value in labels.values() if value == 0)

    blocking = {"DUPLICATE_ACCOUNT_IDS", "INVALID_LABELS", "MISSING_LABELS"}
    has_blocking_issue = any(issue.code in blocking for issue in issues)

    result = GroundTruth(
        status=STATUS_OK,
        labels=labels,
        issues=issues,
        path=resolved,
        row_count=len(rows),
        mule_accounts=mule_accounts,
        regular_accounts=regular_accounts,
        duplicate_accounts=duplicates,
        invalid_labels=invalid,
        missing_labels=missing,
        unknown_accounts=unknown,
    )

    if not labels:
        if not rows:
            # A header-only template is the shipped state, and it means exactly
            # what an absent file means: no official labels are present.
            return not_available(
                "evaluation/ground_truth.csv contains no label rows. The official "
                "1,500 injected mule account IDs have not been supplied yet, so "
                "no precision or recall figure can be produced.",
                path=resolved,
            )
        result.status = STATUS_INVALID
        issues.append(
            ValidationIssue(
                code="NO_LABELS",
                message=(
                    "ground_truth.csv contains rows but none of them yielded a "
                    "usable account_id/label pair. It must not be populated with "
                    "invented IDs."
                ),
            )
        )
        return result

    # Structural problems are checked before the population check so that an
    # explicitly allowed population mismatch can never mask a duplicate or an
    # invalid label.
    if has_blocking_issue:
        result.status = STATUS_INVALID
        return result

    count_mismatch = (
        mule_accounts != expected_mules or regular_accounts != expected_regular
    )
    if count_mismatch:
        issues.append(
            ValidationIssue(
                code="POPULATION_COUNT_MISMATCH",
                message=(
                    f"Ground truth contains {mule_accounts} mule / "
                    f"{regular_accounts} regular accounts. The Problem Statement "
                    f"defines {expected_mules} mule / {expected_regular} regular "
                    "accounts."
                ),
                count=abs(mule_accounts - expected_mules)
                + abs(regular_accounts - expected_regular),
            )
        )
        if not allow_population_mismatch:
            result.status = STATUS_COUNT_MISMATCH
            return result

    return result


def load_ground_truth_from_rows(
    rows: List[Dict[str, object]],
    source: str = "request",
    **kwargs,
) -> GroundTruth:
    """Validate an inline label set supplied through the API.

    Shares the exact same validation rules as the file loader so an API
    submission can never bypass the population and structural checks.
    """
    labels: Dict[str, int] = {}
    duplicates: List[str] = []
    invalid: List[str] = []
    missing: List[str] = []
    known_accounts = kwargs.get("known_accounts")
    unknown: List[str] = []
    issues: List[ValidationIssue] = []

    for row in rows:
        raw_account = str(row.get("account_id") or "").strip()
        if not raw_account:
            missing.append("<blank account_id>")
            continue
        parsed = _normalise_label(str(row.get("label", "")))
        if parsed is None:
            missing.append(raw_account)
            continue
        if parsed == "INVALID":
            invalid.append(raw_account)
            continue
        if raw_account in labels:
            if raw_account not in duplicates:
                duplicates.append(raw_account)
            continue
        labels[raw_account] = parsed
        if known_accounts is not None and raw_account not in known_accounts:
            unknown.append(raw_account)

    if duplicates:
        issues.append(
            ValidationIssue(
                code="DUPLICATE_ACCOUNT_IDS",
                message="The same account_id appears more than once.",
                count=len(duplicates),
                samples=duplicates,
            )
        )
    if invalid:
        issues.append(
            ValidationIssue(
                code="INVALID_LABELS",
                message="Labels must be exactly 0 or 1.",
                count=len(invalid),
                samples=invalid,
            )
        )
    if missing:
        issues.append(
            ValidationIssue(
                code="MISSING_LABELS",
                message="Rows with a blank account_id or label.",
                count=len(missing),
                samples=missing,
            )
        )
    if unknown:
        issues.append(
            ValidationIssue(
                code="ACCOUNTS_NOT_IN_DATASET",
                message="Labeled accounts absent from the 2M dataset.",
                count=len(unknown),
                samples=unknown,
            )
        )

    mule_accounts = sum(1 for v in labels.values() if v == 1)
    regular_accounts = sum(1 for v in labels.values() if v == 0)

    result = GroundTruth(
        status=STATUS_OK,
        labels=labels,
        issues=issues,
        row_count=len(rows),
        mule_accounts=mule_accounts,
        regular_accounts=regular_accounts,
        duplicate_accounts=duplicates,
        invalid_labels=invalid,
        missing_labels=missing,
        unknown_accounts=unknown,
        source=source,
    )

    if not labels:
        result.status = STATUS_INVALID
        issues.append(
            ValidationIssue(
                code="NO_LABELS", message="No usable labels were supplied."
            )
        )
        return result

    blocking = {"DUPLICATE_ACCOUNT_IDS", "INVALID_LABELS", "MISSING_LABELS"}
    if any(issue.code in blocking for issue in issues):
        result.status = STATUS_INVALID
        return result

    expected_mules = kwargs.get("expected_mules", EXPECTED_MULE_ACCOUNTS)
    expected_regular = kwargs.get("expected_regular", EXPECTED_REGULAR_ACCOUNTS)
    if (
        mule_accounts != expected_mules
        or regular_accounts != expected_regular
    ) and not kwargs.get("allow_population_mismatch", False):
        issues.append(
            ValidationIssue(
                code="POPULATION_COUNT_MISMATCH",
                message=(
                    f"Received {mule_accounts} mule / {regular_accounts} regular "
                    f"accounts; expected {expected_mules} / {expected_regular}."
                ),
            )
        )
        result.status = STATUS_COUNT_MISMATCH
        return result

    return result
