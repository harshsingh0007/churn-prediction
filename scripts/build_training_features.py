"""Build training features as of a given date and register all versions in the feature store."""

import sqlite3
import sys

import pandas as pd

sys.path.insert(0, ".")

from features.build import build_features
from features.quality_checks import run_all
from feature_store import store
from feature_store.store import version_exists_with_parameters

AS_OF = "2026-08-01"


def _zero_txn_ids() -> set[int]:
    cust = pd.read_csv("data/customers.csv")
    con = sqlite3.connect("data/transactions.db")
    has_txn = set(pd.read_sql("SELECT DISTINCT customer_id FROM transactions", con)["customer_id"])
    con.close()
    return set(cust[~cust["customer_id"].isin(has_txn)]["customer_id"])


def main() -> None:
    print(f"Building training features as_of={AS_OF} ...")

    # --- v1 features (spec defaults) ---
    feat_v1 = build_features(AS_OF, spend_velocity_short_window=30, engagement_electronics_weight=1.5)
    zero_ids = _zero_txn_ids()
    run_all(feat_v1, expected_row_count=1500, zero_txn_customer_ids=zero_ids)
    print(f"  Quality checks passed. {len(feat_v1)} rows.")

    def _register_if_new(fname, values_df, desc, src, transform, rationale, params):
        if version_exists_with_parameters(fname, params):
            print(f"  Skipped {fname} params={params} (already registered)")
            return
        v = store.register_version(
            feature_name=fname,
            values_df=values_df,
            description=desc,
            source_columns=src,
            transform_summary=transform,
            business_rationale=rationale,
            parameters=params,
        )
        print(f"  Registered {fname} v{v}")

    # Register every non-versioned feature at v1
    for fname, desc, src, transform in [
        (
            "days_since_last_txn",
            "Days since the customer's last transaction as of the as-of date.",
            "data/transactions.db:transactions.txn_timestamp",
            "max(txn_timestamp) per customer filtered to <= as_of; default 730.0 for zero-txn customers.",
        ),
        (
            "spend_30d",
            "Total spend in the 30 days ending at the as-of date.",
            "data/transactions.db:transactions.amount,txn_timestamp",
            "sum(amount) where txn_timestamp in (as_of-30d, as_of]; default 0.0.",
        ),
        (
            "txn_count_90d",
            "Transaction count in the 90 days ending at the as-of date.",
            "data/transactions.db:transactions.txn_timestamp",
            "count(*) where txn_timestamp in (as_of-90d, as_of]; default 0.",
        ),
        (
            "return_rate_90d",
            "Fraction of transactions returned in the 90-day window.",
            "data/transactions.db:transactions.is_returned,txn_timestamp",
            "sum(is_returned)/count(*) in 90d window; default 0.0 when count=0.",
        ),
    ]:
        snapshot = feat_v1[["customer_id", fname, "as_of_date"]].copy()
        _register_if_new(fname, snapshot, desc, src, transform, "Initial version per feature_spec.md.", {})

    # --- spend_velocity v1 (short_window_days=30) ---
    snap_sv1 = feat_v1[["customer_id", "spend_velocity", "as_of_date"]].copy()
    _register_if_new(
        "spend_velocity", snap_sv1,
        "Ratio of short-window spend rate to 90-day baseline spend rate. short_window_days=30.",
        "data/transactions.db:transactions.amount,txn_timestamp",
        "spend_30d / (spend_90d / (90/30)); 0.0 when spend_90d=0.",
        "v1: 30-day short window, baseline version of velocity feature.",
        {"short_window_days": 30},
    )

    # --- spend_velocity v2 (short_window_days=14) ---
    feat_sv2 = build_features(AS_OF, spend_velocity_short_window=14, engagement_electronics_weight=1.5)
    snap_sv2 = feat_sv2[["customer_id", "spend_velocity", "as_of_date"]].copy()
    _register_if_new(
        "spend_velocity", snap_sv2,
        "Ratio of short-window spend rate to 90-day baseline spend rate. short_window_days=14.",
        "data/transactions.db:transactions.amount,txn_timestamp",
        "spend_14d / (spend_90d / (90/14)); 0.0 when spend_90d=0.",
        "v2: shortened to 14-day window after v1 (30d) lagged in detecting sudden spending halts for frequent buyers two weeks prior to churn events.",
        {"short_window_days": 14},
    )

    # --- engagement_score v1 (electronics_weight=1.5) ---
    snap_es1 = feat_v1[["customer_id", "engagement_score", "as_of_date"]].copy()
    _register_if_new(
        "engagement_score", snap_es1,
        "Weighted category activity score in 60d window. electronics_weight=1.5.",
        "data/transactions.db:transactions.category,txn_timestamp",
        "sum(category_weight) in 60d window; electronics=1.5, apparel=1.2, home=1.0, other=0.8.",
        "v1: initial electronics multiplier of 1.5 based on prior domain knowledge.",
        {"electronics_weight": 1.5},
    )

    # --- engagement_score v2 (electronics_weight=2.0) ---
    feat_es2 = build_features(AS_OF, spend_velocity_short_window=30, engagement_electronics_weight=2.0)
    snap_es2 = feat_es2[["customer_id", "engagement_score", "as_of_date"]].copy()
    _register_if_new(
        "engagement_score", snap_es2,
        "Weighted category activity score in 60d window. electronics_weight=2.0.",
        "data/transactions.db:transactions.category,txn_timestamp",
        "sum(category_weight) in 60d window; electronics=2.0, apparel=1.2, home=1.0, other=0.8.",
        "v2: bumped electronics multiplier from 1.5 to 2.0 after feature attribution on historical validation splits showed electronics purchases carry twice the retention signal of general categories, improving separation on high-value cohorts.",
        {"electronics_weight": 2.0},
    )

    print("Done. Feature store populated.")


if __name__ == "__main__":
    main()
