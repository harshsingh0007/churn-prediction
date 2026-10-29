"""Output feature schema — names, dtypes, nullability, source, version metadata."""

FEATURE_SCHEMA = [
    {
        "name": "days_since_last_txn",
        "dtype": "float64",
        "nullable": False,
        "zero_activity_default": 730.0,
        "source": "data/transactions.db:transactions.txn_timestamp",
        "version": 1,
        "parameters": {},
    },
    {
        "name": "spend_30d",
        "dtype": "float64",
        "nullable": False,
        "zero_activity_default": 0.0,
        "source": "data/transactions.db:transactions.amount,txn_timestamp",
        "version": 1,
        "parameters": {},
    },
    {
        "name": "txn_count_90d",
        "dtype": "int64",
        "nullable": False,
        "zero_activity_default": 0,
        "source": "data/transactions.db:transactions.txn_timestamp",
        "version": 1,
        "parameters": {},
    },
    {
        "name": "return_rate_90d",
        "dtype": "float64",
        "nullable": False,
        "zero_activity_default": 0.0,
        "source": "data/transactions.db:transactions.is_returned,txn_timestamp",
        "version": 1,
        "parameters": {},
    },
    {
        "name": "spend_velocity",
        "dtype": "float64",
        "nullable": False,
        "zero_activity_default": 0.0,
        "source": "data/transactions.db:transactions.amount,txn_timestamp",
        "version": 1,  # v1: short_window_days=30
        "parameters": {"short_window_days": 30},
    },
    {
        "name": "engagement_score",
        "dtype": "float64",
        "nullable": False,
        "zero_activity_default": 0.0,
        "source": "data/transactions.db:transactions.category,txn_timestamp",
        "version": 1,  # v1: electronics_weight=1.5
        "parameters": {"electronics_weight": 1.5},
    },
]

FEATURE_NAMES = [f["name"] for f in FEATURE_SCHEMA]
