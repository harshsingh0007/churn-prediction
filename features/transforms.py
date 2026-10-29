"""Pure feature functions — no I/O. Each takes pre-loaded DataFrames and as_of."""

import datetime

import pandas as pd


def days_since_last_txn(
    customers: pd.DataFrame,
    transactions: pd.DataFrame,
    as_of: datetime.date,
) -> pd.Series:
    """Days between as_of and the customer's most recent transaction. Default 730.0."""
    cutoff = pd.Timestamp(as_of)
    past = transactions[transactions["txn_timestamp"] <= cutoff]
    last = past.groupby("customer_id")["txn_timestamp"].max()
    result = customers.set_index("customer_id").index.to_series().map(
        lambda cid: (cutoff - last[cid]).days if cid in last.index else 730.0
    )
    result.index = customers["customer_id"]
    result.name = "days_since_last_txn"
    return result.astype(float)


def spend_30d(
    customers: pd.DataFrame,
    transactions: pd.DataFrame,
    as_of: datetime.date,
) -> pd.Series:
    """Total spend in the 30 days up to and including as_of. Default 0.0."""
    cutoff = pd.Timestamp(as_of)
    window_start = cutoff - pd.Timedelta(days=30)
    mask = (transactions["txn_timestamp"] > window_start) & (transactions["txn_timestamp"] <= cutoff)
    agg = transactions[mask].groupby("customer_id")["amount"].sum()
    result = customers["customer_id"].map(agg).fillna(0.0)
    result.index = customers["customer_id"]
    result.name = "spend_30d"
    return result.astype(float)


def txn_count_90d(
    customers: pd.DataFrame,
    transactions: pd.DataFrame,
    as_of: datetime.date,
) -> pd.Series:
    """Transaction count in the 90 days up to and including as_of. Default 0."""
    cutoff = pd.Timestamp(as_of)
    window_start = cutoff - pd.Timedelta(days=90)
    mask = (transactions["txn_timestamp"] > window_start) & (transactions["txn_timestamp"] <= cutoff)
    agg = transactions[mask].groupby("customer_id").size()
    result = customers["customer_id"].map(agg).fillna(0)
    result.index = customers["customer_id"]
    result.name = "txn_count_90d"
    return result.astype(int)


def return_rate_90d(
    customers: pd.DataFrame,
    transactions: pd.DataFrame,
    as_of: datetime.date,
) -> pd.Series:
    """Return rate (returned / total) in 90 days before as_of. Default 0.0."""
    cutoff = pd.Timestamp(as_of)
    window_start = cutoff - pd.Timedelta(days=90)
    mask = (transactions["txn_timestamp"] > window_start) & (transactions["txn_timestamp"] <= cutoff)
    w = transactions[mask]
    total = w.groupby("customer_id").size()
    returned = w[w["is_returned"] == 1].groupby("customer_id").size()
    rate = (returned / total).fillna(0.0)
    result = customers["customer_id"].map(rate).fillna(0.0)
    result.index = customers["customer_id"]
    result.name = "return_rate_90d"
    return result.astype(float)


def spend_velocity(
    customers: pd.DataFrame,
    transactions: pd.DataFrame,
    as_of: datetime.date,
    short_window_days: int = 30,
) -> pd.Series:
    """Ratio of recent spend rate to 90-day baseline spend rate.

    spend_{short_window}d / (spend_90d / (90 / short_window_days))
    Default 0.0 when spend_90d == 0.
    """
    cutoff = pd.Timestamp(as_of)
    w90_start = cutoff - pd.Timedelta(days=90)
    w_short_start = cutoff - pd.Timedelta(days=short_window_days)

    past90 = transactions[
        (transactions["txn_timestamp"] > w90_start) & (transactions["txn_timestamp"] <= cutoff)
    ]
    past_short = transactions[
        (transactions["txn_timestamp"] > w_short_start) & (transactions["txn_timestamp"] <= cutoff)
    ]

    spend_90 = past90.groupby("customer_id")["amount"].sum()
    spend_short = past_short.groupby("customer_id")["amount"].sum()

    cids = customers["customer_id"]
    s90 = cids.map(spend_90).fillna(0.0)
    ss = cids.map(spend_short).fillna(0.0)

    baseline = s90 / (90.0 / short_window_days)
    # ponytail: divide-by-zero guard; velocity=0 when customer has no 90d spend
    vel = ss.where(baseline == 0.0, ss / baseline.replace(0.0, float("nan"))).fillna(0.0)
    vel.index = customers["customer_id"]
    vel.name = "spend_velocity"
    return vel.astype(float)


def engagement_score(
    customers: pd.DataFrame,
    transactions: pd.DataFrame,
    as_of: datetime.date,
    electronics_weight: float = 1.5,
) -> pd.Series:
    """Weighted category activity score in the 60 days before as_of.

    Weights: electronics=electronics_weight, apparel=1.2, home=1.0, other=0.8.
    Default 0.0.
    """
    cutoff = pd.Timestamp(as_of)
    window_start = cutoff - pd.Timedelta(days=60)
    mask = (transactions["txn_timestamp"] > window_start) & (transactions["txn_timestamp"] <= cutoff)
    w = transactions[mask].copy()

    weight_map = {
        "electronics": electronics_weight,
        "apparel": 1.2,
        "home": 1.0,
    }
    w["weight"] = w["category"].map(weight_map).fillna(0.8)
    agg = w.groupby("customer_id")["weight"].sum()

    result = customers["customer_id"].map(agg).fillna(0.0)
    result.index = customers["customer_id"]
    result.name = "engagement_score"
    return result.astype(float)
