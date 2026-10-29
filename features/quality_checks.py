"""Data-quality checks — runnable standalone against a features DataFrame."""

import pandas as pd


def check_no_unexpected_nulls(df: pd.DataFrame) -> list[str]:
    feature_cols = [c for c in df.columns if c not in ("customer_id", "as_of_date")]
    failures = []
    for col in feature_cols:
        n = df[col].isna().sum()
        if n > 0:
            failures.append(f"{col}: {n} unexpected nulls")
    return failures


def check_zero_activity_defaults(
    df: pd.DataFrame,
    zero_txn_customer_ids: set[int],
) -> list[str]:
    """Zero-txn customers must have days_since_last_txn=730.0 and 0/0.0 elsewhere."""
    failures = []
    sub = df[df["customer_id"].isin(zero_txn_customer_ids)]
    if sub.empty:
        return failures

    bad_days = sub[sub["days_since_last_txn"] != 730.0]
    if not bad_days.empty:
        failures.append(
            f"days_since_last_txn: {len(bad_days)} zero-txn customers not set to 730.0"
        )
    for col in ("spend_30d", "return_rate_90d", "spend_velocity", "engagement_score"):
        bad = sub[sub[col] != 0.0]
        if not bad.empty:
            failures.append(f"{col}: {len(bad)} zero-txn customers not set to 0.0")
    bad_count = sub[sub["txn_count_90d"] != 0]
    if not bad_count.empty:
        failures.append(f"txn_count_90d: {len(bad_count)} zero-txn customers not set to 0")
    return failures


def check_monetary_bounds(df: pd.DataFrame) -> list[str]:
    failures = []
    if (df["spend_30d"] < 0).any():
        failures.append(f"spend_30d: {(df['spend_30d'] < 0).sum()} negative values")
    if (df["spend_30d"] >= 10000.0).any():
        failures.append(
            f"spend_30d: {(df['spend_30d'] >= 10000.0).sum()} values >= 10000 (possible join explosion)"
        )
    return failures


def check_rate_bounds(df: pd.DataFrame) -> list[str]:
    failures = []
    out = (df["return_rate_90d"] < 0) | (df["return_rate_90d"] > 1)
    if out.any():
        failures.append(f"return_rate_90d: {out.sum()} values outside [0, 1]")
    return failures


def check_row_count(df: pd.DataFrame, expected: int) -> list[str]:
    if len(df) != expected:
        return [f"row count: expected {expected}, got {len(df)}"]
    return []


def run_all(
    df: pd.DataFrame,
    expected_row_count: int,
    zero_txn_customer_ids: set[int] | None = None,
) -> None:
    """Run all checks; raise ValueError with combined messages on any failure."""
    failures = []
    failures += check_no_unexpected_nulls(df)
    if zero_txn_customer_ids:
        failures += check_zero_activity_defaults(df, zero_txn_customer_ids)
    failures += check_monetary_bounds(df)
    failures += check_rate_bounds(df)
    failures += check_row_count(df, expected_row_count)

    if failures:
        raise ValueError("Data-quality checks failed:\n" + "\n".join(f"  - {f}" for f in failures))
