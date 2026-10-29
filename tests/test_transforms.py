"""Unit tests for feature transform functions."""

import datetime

import pandas as pd
import pytest

from features import transforms

AS_OF = datetime.date(2026, 8, 1)


def _cust(ids):
    return pd.DataFrame({"customer_id": ids, "signup_date": [datetime.date(2024, 1, 1)] * len(ids)})


def _txn(rows):
    df = pd.DataFrame(rows, columns=["customer_id", "txn_timestamp", "category", "channel", "amount", "is_returned"])
    if not df.empty:
        df["txn_timestamp"] = pd.to_datetime(df["txn_timestamp"])
    return df


# --- days_since_last_txn ---

def test_days_since_last_txn_normal():
    cust = _cust([1])
    txn = _txn([[1, "2026-07-01 00:00:00", "home", "web", 50.0, 0]])
    result = transforms.days_since_last_txn(cust, txn, AS_OF)
    assert result.iloc[0] == 31.0


def test_days_since_last_txn_zero_activity():
    cust = _cust([99])
    txn = _txn([])
    result = transforms.days_since_last_txn(cust, txn, AS_OF)
    assert result.iloc[0] == 730.0


def test_days_since_last_txn_boundary():
    # transaction at midnight on as_of should be counted (0 days)
    cust = _cust([1])
    txn = _txn([[1, "2026-08-01 00:00:00", "home", "web", 50.0, 0]])
    result = transforms.days_since_last_txn(cust, txn, AS_OF)
    assert result.iloc[0] == 0.0


def test_days_since_last_txn_future_excluded():
    cust = _cust([1])
    txn = _txn([[1, "2026-08-02 00:00:00", "home", "web", 50.0, 0]])
    result = transforms.days_since_last_txn(cust, txn, AS_OF)
    assert result.iloc[0] == 730.0  # future transaction excluded → treated as zero-activity


# --- spend_30d ---

def test_spend_30d_normal():
    cust = _cust([1])
    txn = _txn([[1, "2026-07-20 00:00:00", "home", "web", 100.0, 0]])
    result = transforms.spend_30d(cust, txn, AS_OF)
    assert result.iloc[0] == pytest.approx(100.0)


def test_spend_30d_zero_activity():
    cust = _cust([99])
    result = transforms.spend_30d(cust, _txn([]), AS_OF)
    assert result.iloc[0] == 0.0


def test_spend_30d_boundary_excluded():
    # transaction exactly 30 days before as_of: window is (as_of-30d, as_of] so boundary is excluded
    cust = _cust([1])
    txn = _txn([[1, "2026-07-02 00:00:00", "home", "web", 50.0, 0]])
    result = transforms.spend_30d(cust, txn, AS_OF)
    assert result.iloc[0] == 0.0


# --- txn_count_90d ---

def test_txn_count_90d_normal():
    cust = _cust([1])
    txn = _txn([
        [1, "2026-06-01 00:00:00", "home", "web", 20.0, 0],
        [1, "2026-07-15 00:00:00", "home", "web", 30.0, 0],
    ])
    result = transforms.txn_count_90d(cust, txn, AS_OF)
    assert result.iloc[0] == 2


def test_txn_count_90d_zero_activity():
    cust = _cust([99])
    result = transforms.txn_count_90d(cust, _txn([]), AS_OF)
    assert result.iloc[0] == 0


# --- return_rate_90d ---

def test_return_rate_90d_normal():
    cust = _cust([1])
    txn = _txn([
        [1, "2026-07-01 00:00:00", "home", "web", 50.0, 1],
        [1, "2026-07-15 00:00:00", "home", "web", 50.0, 0],
    ])
    result = transforms.return_rate_90d(cust, txn, AS_OF)
    assert result.iloc[0] == pytest.approx(0.5)


def test_return_rate_90d_zero_activity():
    cust = _cust([99])
    result = transforms.return_rate_90d(cust, _txn([]), AS_OF)
    assert result.iloc[0] == 0.0


def test_return_rate_90d_no_returns():
    cust = _cust([1])
    txn = _txn([[1, "2026-07-01 00:00:00", "home", "web", 50.0, 0]])
    result = transforms.return_rate_90d(cust, txn, AS_OF)
    assert result.iloc[0] == 0.0


# --- spend_velocity ---

def test_spend_velocity_normal():
    cust = _cust([1])
    # 90d spend = 90, 30d spend = 30 → velocity = 30 / (90/3) = 1.0
    txns = [[1, f"2026-0{m}-15 00:00:00", "home", "web", 30.0, 0] for m in (5, 6, 7)]
    txn = _txn(txns)
    result = transforms.spend_velocity(cust, txn, AS_OF, short_window_days=30)
    assert result.iloc[0] == pytest.approx(1.0, rel=0.01)


def test_spend_velocity_zero_activity():
    cust = _cust([99])
    result = transforms.spend_velocity(cust, _txn([]), AS_OF, short_window_days=30)
    assert result.iloc[0] == 0.0


def test_spend_velocity_v2_window():
    cust = _cust([1])
    # as_of=2026-08-01; 90d window opens 2026-05-03; 14d window opens 2026-07-18
    # Place two txns inside 90d but outside 14d, one txn inside 14d
    txns = [
        [1, "2026-05-15 00:00:00", "home", "web", 30.0, 0],  # in 90d, outside 14d
        [1, "2026-06-15 00:00:00", "home", "web", 30.0, 0],  # in 90d, outside 14d
        [1, "2026-07-25 00:00:00", "home", "web", 30.0, 0],  # in both 90d and 14d
    ]
    txn = _txn(txns)
    result = transforms.spend_velocity(cust, txn, AS_OF, short_window_days=14)
    # spend_14d=30, spend_90d=90, baseline=90/(90/14)=14, vel=30/14≈2.14
    assert result.iloc[0] == pytest.approx(30.0 / 14.0, rel=0.01)


# --- engagement_score ---

def test_engagement_score_normal():
    cust = _cust([1])
    txn = _txn([[1, "2026-07-15 00:00:00", "electronics", "web", 100.0, 0]])
    result = transforms.engagement_score(cust, txn, AS_OF, electronics_weight=1.5)
    assert result.iloc[0] == pytest.approx(1.5)


def test_engagement_score_zero_activity():
    cust = _cust([99])
    result = transforms.engagement_score(cust, _txn([]), AS_OF, electronics_weight=1.5)
    assert result.iloc[0] == 0.0


def test_engagement_score_v2_weight():
    cust = _cust([1])
    txn = _txn([[1, "2026-07-15 00:00:00", "electronics", "web", 100.0, 0]])
    r1 = transforms.engagement_score(cust, txn, AS_OF, electronics_weight=1.5)
    r2 = transforms.engagement_score(cust, txn, AS_OF, electronics_weight=2.0)
    assert r2.iloc[0] == pytest.approx(2.0)
    assert r2.iloc[0] > r1.iloc[0]
