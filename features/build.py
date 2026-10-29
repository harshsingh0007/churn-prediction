"""Single entry point for feature building — used by both training and scoring paths."""

import datetime

import pandas as pd

from features import ingest, transforms

DEFAULT_SOURCE_PATHS = {
    "customers": "data/customers.csv",
    "transactions": "data/transactions.db",
    "monthly_agg": "data/transactions_monthly_agg.parquet",
}


def build_features(
    as_of: str | datetime.date,
    source_paths: dict | None = None,
    customer_ids: list[int] | None = None,
    spend_velocity_short_window: int = 30,
    engagement_electronics_weight: float = 1.5,
) -> pd.DataFrame:
    """Build the full feature set as of `as_of`.

    Training path: customer_ids=None → all customers.
    Scoring path: customer_ids=[...] → subset.
    The customer_ids filter is the ONLY difference between the two paths.
    """
    if isinstance(as_of, str):
        as_of = datetime.date.fromisoformat(as_of)

    paths = {**DEFAULT_SOURCE_PATHS, **(source_paths or {})}

    customers = ingest.load_customers(paths["customers"])
    transactions = ingest.load_transactions(paths["transactions"])

    if customer_ids is not None:
        customers = customers[customers["customer_id"].isin(customer_ids)].copy()

    feat = pd.DataFrame({"customer_id": customers["customer_id"].values})

    feat["days_since_last_txn"] = transforms.days_since_last_txn(customers, transactions, as_of).values
    feat["spend_30d"] = transforms.spend_30d(customers, transactions, as_of).values
    feat["txn_count_90d"] = transforms.txn_count_90d(customers, transactions, as_of).values
    feat["return_rate_90d"] = transforms.return_rate_90d(customers, transactions, as_of).values
    feat["spend_velocity"] = transforms.spend_velocity(
        customers, transactions, as_of, short_window_days=spend_velocity_short_window
    ).values
    feat["engagement_score"] = transforms.engagement_score(
        customers, transactions, as_of, electronics_weight=engagement_electronics_weight
    ).values
    feat["as_of_date"] = str(as_of)

    return feat.reset_index(drop=True)
