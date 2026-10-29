"""Quality check tests — confirm each check fires on bad input and passes on clean input."""

import pandas as pd
import pytest

from features import quality_checks as qc

ZERO_IDS = {10, 20}


def _clean_df(n=5):
    return pd.DataFrame({
        "customer_id": list(range(1, n + 1)),
        "days_since_last_txn": [10.0, 730.0, 5.0, 30.0, 100.0],
        "spend_30d": [50.0, 0.0, 200.0, 0.0, 10.0],
        "txn_count_90d": [3, 0, 8, 0, 1],
        "return_rate_90d": [0.1, 0.0, 0.2, 0.0, 0.0],
        "spend_velocity": [1.2, 0.0, 0.8, 0.0, 1.0],
        "engagement_score": [2.5, 0.0, 3.0, 0.0, 1.0],
        "as_of_date": ["2026-08-01"] * 5,
    })


# --- null checks ---

def test_null_check_passes_on_clean():
    assert qc.check_no_unexpected_nulls(_clean_df()) == []


def test_null_check_fires_on_null():
    df = _clean_df()
    df.loc[0, "spend_30d"] = None
    failures = qc.check_no_unexpected_nulls(df)
    assert any("spend_30d" in f for f in failures)


# --- zero-activity defaults ---

def test_zero_activity_passes_on_correct_defaults():
    df = _clean_df()
    df.loc[df["customer_id"] == 1, "customer_id"] = 10
    df.loc[df["customer_id"] == 10, "days_since_last_txn"] = 730.0
    df.loc[df["customer_id"] == 10, ["spend_30d", "return_rate_90d", "spend_velocity", "engagement_score"]] = 0.0
    df.loc[df["customer_id"] == 10, "txn_count_90d"] = 0
    failures = qc.check_zero_activity_defaults(df, {10})
    assert failures == []


def test_zero_activity_fires_when_nan_instead_of_default():
    df = _clean_df()
    df.loc[df["customer_id"] == 1, "customer_id"] = 10
    df.loc[df["customer_id"] == 10, "days_since_last_txn"] = float("nan")
    failures = qc.check_zero_activity_defaults(df, {10})
    assert any("days_since_last_txn" in f for f in failures)


# --- monetary bounds ---

def test_monetary_bounds_passes_on_clean():
    assert qc.check_monetary_bounds(_clean_df()) == []


def test_monetary_bounds_fires_on_negative():
    df = _clean_df()
    df.loc[0, "spend_30d"] = -5.0
    failures = qc.check_monetary_bounds(df)
    assert any("negative" in f for f in failures)


def test_monetary_bounds_fires_on_too_high():
    df = _clean_df()
    df.loc[0, "spend_30d"] = 15000.0
    failures = qc.check_monetary_bounds(df)
    assert any("10000" in f for f in failures)


# --- rate bounds ---

def test_rate_bounds_passes_on_clean():
    assert qc.check_rate_bounds(_clean_df()) == []


def test_rate_bounds_fires_on_out_of_range():
    df = _clean_df()
    df.loc[0, "return_rate_90d"] = 1.5
    failures = qc.check_rate_bounds(df)
    assert any("return_rate_90d" in f for f in failures)


# --- row count ---

def test_row_count_passes():
    assert qc.check_row_count(_clean_df(), 5) == []


def test_row_count_fires_on_mismatch():
    failures = qc.check_row_count(_clean_df(), 10)
    assert any("row count" in f for f in failures)


# --- run_all integration ---

def test_run_all_passes_on_clean():
    qc.run_all(_clean_df(), expected_row_count=5)  # must not raise


def test_run_all_raises_on_failure():
    df = _clean_df()
    df.loc[0, "spend_30d"] = -1.0
    with pytest.raises(ValueError, match="Data-quality checks failed"):
        qc.run_all(df, expected_row_count=5)
