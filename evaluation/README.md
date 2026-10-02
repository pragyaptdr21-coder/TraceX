# Ground Truth Input

`ground_truth.csv` is the input for the official detection evaluation.

## Status in this repository

**The official 1,500 injected mule account IDs are not present in this
repository.** This file ships with only its header row. It is deliberately
unpopulated.

Do **not** invent, infer, or derive labels to fill it. A fabricated label set
produces fabricated precision, recall and F1 figures, which is worse than
reporting nothing at all.

Until real labels are supplied:

```
STATUS: OFFICIAL GROUND TRUTH NOT AVAILABLE
PRECISION: NOT AVAILABLE
RECALL: NOT AVAILABLE
F1: NOT AVAILABLE
```

## Format

```csv
account_id,label
ACCOUNT_ID_1,1
ACCOUNT_ID_2,1
ACCOUNT_ID_3,0
```

- `account_id` — must match the account identifiers used in the 2M transaction
  dataset, for example `KKBK10000000`.
- `label` — exactly `1` (injected mule) or `0` (regular). Any other value is
  rejected and blocks the evaluation.

## Required population

The Problem Statement defines the evaluation population as:

| Class    | Required count |
| -------- | -------------- |
| Mule     | 1,500          |
| Regular  | 23,500         |
| **Total**| **25,000**     |

If the supplied file does not match these counts the evaluation reports
`GROUND TRUTH COUNT MISMATCH` with the actual counts and refuses to produce
metrics. Overriding that check is possible but must be explicit — it is never
done silently.

## Validation performed

On every load the engine checks for:

- duplicate `account_id` values
- blank or missing labels
- labels that are not `0` or `1`
- accounts that do not exist in the 2M transaction dataset
- population counts against 1,500 / 23,500

## Usage

```bash
python -m backend.evaluation.run_evaluation
```

or via the API:

```
POST /api/evaluation/precision-recall
```
