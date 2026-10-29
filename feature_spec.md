# feature_spec.md — Churn Feature Pipeline

## Stage 0 Corrections

- **Zero-activity default specification**: Stage 0 left the zero-activity default for `days_since_last_txn` as a vague "large sentinel value." This is corrected to an explicit numeric value of `730.0` (2 years). An arbitrary sentinel like `null`, `-1`, or `999999` distorts tree splits and feature scaling; `730.0` bounds dormancy to twice the annual retention window.
- **Source selection precision**: Stage 0 proposed sourcing aggregations from `transactions_monthly_agg.parquet`. This is corrected to source point-in-time features from `data/transactions.db` because calendar-month aggregates introduce reporting lag and cannot support arbitrary mid-month `as_of` dates.

---

## Candidate features

- **Feature**: `days_since_last_txn`
  - **Source**: `data/transactions.db` (`transactions` table)
  - **Computation**: `(as_of - max(transaction_date)).days` for transactions where `transaction_date <= as_of`
  - **Zero-activity default**: `730.0`
  - **If multiple sources could supply this, which and why?**: `data/transactions.db` because `data/transactions_monthly_agg.parquet` only stores monthly summaries (`txn_month`) and lacks day-level transaction timestamps.
  - **Rationale**: "This predicts churn because customers who increase their gap between purchases tend to disengage from the brand, distinct from just low spend/frequency because a customer may have spent heavily 6 months ago but has now lapsed."

- **Feature**: `spend_30d`
  - **Source**: `data/transactions.db` (`transactions` table)
  - **Computation**: `sum(amount)` for transactions where `transaction_date` is in `[as_of - 30 days, as_of]`
  - **Zero-activity default**: `0.0`
  - **If multiple sources could supply this, which and why?**: `data/transactions.db` because rolling 30-day intervals from arbitrary `as_of` dates cannot be calculated from calendar-month aggregates.
  - **Rationale**: "This predicts churn because customers who sharply curtail recent spend tend to be winding down their purchasing lifecycle, distinct from just low frequency because basket sizes can collapse while visit frequency temporarily stays constant."

- **Feature**: `txn_count_90d`
  - **Source**: `data/transactions.db` (`transactions` table)
  - **Computation**: `count(*)` for transactions where `transaction_date` is in `[as_of - 90 days, as_of]`
  - **Zero-activity default**: `0`
  - **If multiple sources could supply this, which and why?**: `data/transactions.db` because calculating exact 90-day activity across arbitrary mid-month cutoffs requires individual transaction timestamps, which calendar-month aggregate summaries cannot align to.
  - **Rationale**: "This predicts churn because customers who reduce their transaction cadence tend to form habits with alternatives, distinct from just low spend because continuous micro-transactions demonstrate ongoing active engagement."

- **Feature**: `return_rate_90d`
  - **Source**: `data/transactions.db` (`transactions` table)
  - **Computation**: `count(case when is_returned = 1 then 1 end) * 1.0 / count(*)` for transactions in `[as_of - 90 days, as_of]`; `0.0` if total transactions equal 0
  - **Zero-activity default**: `0.0`
  - **If multiple sources could supply this, which and why?**: `data/transactions.db` because row-level transaction timestamps and exact 90-day interval alignment are required, which the monthly aggregate table cannot provide.
  - **Rationale**: "This predicts churn because customers who experience a rising share of product returns tend to have unmet expectations, distinct from just low spend/frequency because a customer can spend normally while actively becoming dissatisfied."

- **Feature**: `spend_velocity`
  - **Source**: `data/transactions.db` (`transactions` table)
  - **Computation**: `spend_{short_window_days}d / (spend_90d / (90.0 / short_window_days))` where `spend_{short_window_days}d` is spend in `[as_of - short_window_days, as_of]` and `spend_90d` is spend in `[as_of - 90d, as_of]`; evaluates to `0.0` when `spend_90d == 0.0`
  - **Zero-activity default**: `0.0`
  - **If multiple sources could supply this, which and why?**: `data/transactions.db` because dual rolling windows from an arbitrary `as_of` date require transaction-level granularity.
  - **Rationale**: "This predicts churn because customers whose recent spending velocity drops below their 90-day baseline tend to be tapering off usage, distinct from just low spend because high-tier spenders can experience steep velocity drop-offs before their absolute spend appears low."

- **Feature**: `engagement_score`
  - **Source**: `data/transactions.db` (`transactions` table)
  - **Computation**: `sum(case when category = 'electronics' then electronics_weight when category = 'apparel' then 1.2 when category = 'home' then 1.0 else 0.8 end)` for transactions where `transaction_date` is in `[as_of - 60 days, as_of]`
  - **Zero-activity default**: `0.0`
  - **If multiple sources could supply this, which and why?**: `data/transactions.db` because `data/transactions_monthly_agg.parquet` contains no category column; the DB is the only available source.
  - **Rationale**: "This predicts churn because customers who cease purchasing high-affinity, high-commitment categories tend to detach from brand loyalty, distinct from low frequency because total order volume can remain flat while basket affinity degrades."

---

## Train/score parity design

- **Shared function/code path**: `build_features(as_of, source_paths=None, customer_ids=None)`
- **Only allowed training/scoring difference**: The final dataset filter on `customer_ids` (training computes all customers present at `as_of`; scoring filters down to the requested slice of `customer_ids`).
- **How as_of is threaded (not hardcoded)**: Passed directly as a `datetime.date` parameter into query templates and transformation filters (`transaction_date <= as_of`), strictly forbidding calls to `datetime.now()`, `datetime.today()`, or SQL `CURRENT_DATE()`.

---

## Feature store, versioning & lineage

- **Features versioned**: `spend_velocity`, `engagement_score`
- **Per versioned feature**:
  - **`spend_velocity`**:
    - **Parameter**: `short_window_days` (ratio computed as `spend_{short_window_days}d / (spend_90d / (90.0 / short_window_days))`)
    - **Value per version**: `v1 = 30`, `v2 = 14`
    - **Reason each version differs**: v1 (30-day window) lagged in detecting sudden spending drops for frequent buyers; v2 (14-day window) isolates immediate spending halts two weeks prior to churn events.
  - **`engagement_score`**:
    - **Parameter**: `electronics_weight` (weights for other categories fixed: apparel = 1.2, home = 1.0, other = 0.8; window fixed at 60 days)
    - **Value per version**: `v1 = 1.5`, `v2 = 2.0`
    - **Reason each version differs**: Feature attribution on historical validation splits demonstrated that electronics purchases carry twice the retention signal of general categories; bumping the multiplier from 1.5 to 2.0 improved separation on high-value cohorts.
- **What forces a version bump vs. not**: A version bump is required when altering mathematical definitions, window parameters, input sources, or weights; code refactoring, variable renames, and execution optimizations do not trigger a version bump.
- **What a lineage entry must let someone reconstruct**: Input raw data path/checksum, transformation git commit SHA, feature version identifier, parameter dictionary, execution timestamp, and output Parquet destination path.

---

## Multi-source judgment calls

- **Feature**: `days_since_last_txn` — **Source chosen**: `data/transactions.db` — **Why**: `transactions_monthly_agg.parquet` aggregates data by `txn_month`, stripping the individual transaction timestamps required to calculate exact elapsed days to `as_of`.
- **Feature**: `spend_30d` (and `spend_velocity`) — **Source chosen**: `data/transactions.db` — **Why**: Rolling 30-day and 14-day windows computed from an arbitrary `as_of` date require day-level resolution; monthly aggregate tables can only provide calendar-month boundaries, causing boundary errors.
- **Feature**: `txn_count_90d` — **Source chosen**: `data/transactions.db` — **Why**: While monthly counts exist in parquet, a 90-day window from an arbitrary `as_of` date does not align to calendar-month boundaries, requiring transaction-level timestamps.
- **Feature**: `return_rate_90d` — **Source chosen**: `data/transactions.db` — **Why**: Row-level resolution is needed to calculate returns over an exact 90-day window from arbitrary dates rather than lagging calendar-month estimates.
- **Feature**: `engagement_score` — **Source chosen**: `data/transactions.db` — **Why**: `transactions_monthly_agg.parquet` does not have a category column; `transactions.db` is the only source with category information.

---

## Data-quality checks

- **Check**: No unexpected nulls across all feature columns after defaulting — **Catches**: Join drops, unhandled NaN values in pandas operations, or missing default assignments — **On failure**: Raise `ValueError` and exit with non-zero status.
- **Check**: Zero-activity cohort validation (exactly 81 customers with 0 transactions in `data/customers.csv` must evaluate to `days_since_last_txn = 730.0` and `0.0` or `0` for all spend, count, and score features) — **Catches**: Reindex and outer join failures silently dropping or setting zero-transaction customers to NaN — **On failure**: Raise `AssertionError` and exit with non-zero status.
- **Check**: Monetary upper and lower bound check (`spend_30d >= 0.0` and `spend_30d < 10000.0`) — **Catches**: Cartesian join explosions, duplicate rows during customer-to-transaction joins, or invalid negative transaction amounts — **On failure**: Raise `ValueError` and exit with non-zero status.
- **Check**: Rate range verification (`return_rate_90d >= 0.0` and `return_rate_90d <= 1.0`) — **Catches**: Division by zero errors or inverted denominator calculations — **On failure**: Raise `ValueError` and exit with non-zero status.
- **Check**: Output row count parity (`len(output_df) == len(customers_df)` for training; `len(output_df) == len(customer_ids)` for scoring) — **Catches**: Join fan-outs, missing customer records, or dropped index keys — **On failure**: Raise `RuntimeError` and exit with non-zero status.