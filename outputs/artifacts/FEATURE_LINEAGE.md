# FEATURE_LINEAGE.md

Generated from `features/schema.py` and `feature_store/registry.db`.
Every candidate feature, every stored version.

---

## days_since_last_txn — v1

| Field | Value |
|---|---|
| Source | `data/transactions.db` → table `transactions`, column `txn_timestamp` |
| Transform | `max(txn_timestamp)` per customer where `txn_timestamp <= as_of`; days = `(as_of - max_ts).days` |
| Zero-activity default | `730.0` (customer has no transactions) |
| Parameters | `{}` |
| Business rationale | Customers who increase their gap between purchases tend to disengage. A high-frequency spender who suddenly goes dormant is a high churn risk distinct from a persistently low-frequency customer. |
| Parquet path | `feature_store/values/days_since_last_txn__v1.parquet` |

---

## spend_30d — v1

| Field | Value |
|---|---|
| Source | `data/transactions.db` → table `transactions`, columns `amount`, `txn_timestamp` |
| Transform | `sum(amount)` where `txn_timestamp` in `(as_of - 30d, as_of]` |
| Zero-activity default | `0.0` |
| Parameters | `{}` |
| Business rationale | Customers who sharply curtail recent spend are winding down their purchasing lifecycle. Basket sizes can collapse while visit frequency stays constant, making spend a distinct signal from frequency. |
| Multi-source judgment | Row-level DB chosen over parquet: rolling 30-day intervals from arbitrary `as_of` dates cannot be calculated from calendar-month aggregates. |
| Parquet path | `feature_store/values/spend_30d__v1.parquet` |

---

## txn_count_90d — v1

| Field | Value |
|---|---|
| Source | `data/transactions.db` → table `transactions`, column `txn_timestamp` |
| Transform | `count(*)` where `txn_timestamp` in `(as_of - 90d, as_of]` |
| Zero-activity default | `0` |
| Parameters | `{}` |
| Business rationale | Customers who reduce transaction cadence form habits with alternatives. Continuous micro-transactions signal active engagement distinct from total spend. |
| Multi-source judgment | Row-level DB chosen over parquet: 90-day window from arbitrary `as_of` does not align to calendar-month boundaries. |
| Parquet path | `feature_store/values/txn_count_90d__v1.parquet` |

---

## return_rate_90d — v1

| Field | Value |
|---|---|
| Source | `data/transactions.db` → table `transactions`, columns `is_returned`, `txn_timestamp` |
| Transform | `count(is_returned=1) / count(*)` in `(as_of - 90d, as_of]`; `0.0` if no transactions |
| Zero-activity default | `0.0` |
| Parameters | `{}` |
| Business rationale | A rising share of product returns signals unmet expectations. A customer can spend normally while actively becoming dissatisfied, making return rate independently predictive of churn. |
| Multi-source judgment | Row-level DB chosen over parquet: row-level `is_returned` flag and exact 90-day window alignment required; parquet has only `return_count` per month. |
| Parquet path | `feature_store/values/return_rate_90d__v1.parquet` |

---

## spend_velocity — v1

| Field | Value |
|---|---|
| Source | `data/transactions.db` → table `transactions`, columns `amount`, `txn_timestamp` |
| Transform | `spend_30d / (spend_90d / (90.0 / 30))` — ratio of 30-day spend rate to 90-day baseline rate; `0.0` when `spend_90d = 0` |
| Zero-activity default | `0.0` |
| Parameters | `{"short_window_days": 30}` |
| Business rationale | High-tier spenders can experience steep velocity drop-offs before their absolute spend appears low. Velocity captures rate-of-change distinct from magnitude. |
| Version reason | v1: initial 30-day short window. |
| Parquet path | `feature_store/values/spend_velocity__v1.parquet` |

---

## spend_velocity — v2

| Field | Value |
|---|---|
| Source | `data/transactions.db` → table `transactions`, columns `amount`, `txn_timestamp` |
| Transform | `spend_14d / (spend_90d / (90.0 / 14))` — ratio of 14-day spend rate to 90-day baseline rate; `0.0` when `spend_90d = 0` |
| Zero-activity default | `0.0` |
| Parameters | `{"short_window_days": 14}` |
| Business rationale | v1 (30d) lagged in detecting sudden spending halts for frequent buyers. v2 shortens to 14 days to isolate immediate spending halts two weeks prior to churn events. |
| Version reason | Window shortened from 30 to 14 days after v1 was too slow to capture rapid drop-offs. |
| Parquet path | `feature_store/values/spend_velocity__v2.parquet` |

---

## engagement_score — v1

| Field | Value |
|---|---|
| Source | `data/transactions.db` → table `transactions`, columns `category`, `txn_timestamp` |
| Transform | `sum(weight)` per customer in `(as_of - 60d, as_of]` where weight: electronics=1.5, apparel=1.2, home=1.0, other=0.8 |
| Zero-activity default | `0.0` |
| Parameters | `{"electronics_weight": 1.5}` |
| Business rationale | Customers who cease purchasing high-affinity, high-commitment categories detach from brand loyalty. Total order volume can remain flat while basket affinity degrades. |
| Version reason | v1: initial electronics multiplier of 1.5 based on prior domain knowledge. |
| Parquet path | `feature_store/values/engagement_score__v1.parquet` |

---

## engagement_score — v2

| Field | Value |
|---|---|
| Source | `data/transactions.db` → table `transactions`, columns `category`, `txn_timestamp` |
| Transform | `sum(weight)` per customer in `(as_of - 60d, as_of]` where weight: electronics=2.0, apparel=1.2, home=1.0, other=0.8 |
| Zero-activity default | `0.0` |
| Parameters | `{"electronics_weight": 2.0}` |
| Business rationale | Feature attribution on historical validation splits showed electronics purchases carry twice the retention signal of general categories. Bumping from 1.5 to 2.0 improved separation on high-value cohorts. |
| Version reason | Electronics multiplier raised from 1.5 to 2.0 after validation attribution analysis. |
| Parquet path | `feature_store/values/engagement_score__v2.parquet` |
