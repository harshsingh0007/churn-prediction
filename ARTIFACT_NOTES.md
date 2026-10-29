# ARTIFACT_NOTES.md

Self-critique log — things reconsidered or caught during the build.

## 1. Test helper produced string timestamps, not datetimes

During `test_transforms.py` development, the `_txn()` helper created DataFrames with
`txn_timestamp` as raw strings. The transform functions compare timestamps against
`pd.Timestamp(as_of)`, which fails silently under the ArrowStringArray backend in pandas 2.x
(no error raised; the comparison returns incorrect results). Added
`pd.to_datetime()` conversion in `_txn()`. Two test cases had incorrect assertions as a
result and were corrected.

Root cause: the transform functions correctly call `ingest.load_transactions()` in production,
which parses timestamps via `pd.to_datetime`. The test helper bypassed ingest and needed to
replicate its output format.

## 2. spend_velocity boundary: is July 15 inside a 14-day window ending Aug 1?

The initial `test_spend_velocity_v2_window` placed transactions on Jul 15, Jun 15, May 15
and expected the Jul 15 transaction to land inside a 14-day window. It doesn't:
`as_of - 14d = Jul 18`, and the window is `(Jul 18, Aug 1]`. Jul 15 is excluded.
The test was corrected to place the "recent" transaction on Jul 25.

## 3. Zero-activity defaults verified against actual data

Before writing the `check_zero_activity_defaults` quality check, I confirmed that all 81
zero-transaction customers are indeed labelled `churned=1` in `customers.csv` (verified in
Step 0). The check hardcodes 81 as the expected cohort size; if the underlying data changes,
this check will catch the discrepancy rather than silently passing.

## 4. as_of threading: no hardcoded dates found

Reviewed all transform functions and `build_features` — `as_of` is passed as a parameter
at every call site. No `datetime.now()`, `datetime.today()`, or SQL `CURRENT_DATE()` calls
are present. `get_latest()` and `get_version()` in the feature store do not depend on dates.

## 5. Feature store is_latest atomicity

The `register_version` function flips `is_latest` from 1→0 for all prior versions of a
feature before inserting the new row, within the same `sqlite3.Connection` before `commit()`.
This is effectively atomic for single-process use. For concurrent writers, a proper
transaction with `BEGIN EXCLUSIVE` would be needed — not required here.
