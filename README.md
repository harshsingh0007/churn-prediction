# Churn Feature Pipeline

Feature engineering pipeline for e-commerce customer churn prediction.
Ingests from three heterogeneous sources, builds a versioned local feature store,
and enforces train/score parity through a single shared code path.

## Environment setup

```bash
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Requires Python 3.10+. All dependencies are pinned in `requirements.txt`.

## Run the three scripts

All scripts must be run as modules (the `-m` form) from the repo root so that
`features/` and `feature_store/` resolve as imports.

### 1. Build training features and populate the feature store

```bash
python -m scripts.build_training_features
```

Builds features for all 1500 customers as of 2026-08-01, runs data-quality checks,
and registers every feature version into `feature_store/registry.db` with parquet
snapshots under `feature_store/values/`. Re-running is safe — already-registered
versions are skipped.

### 2. Score one or more customers

```bash
python -m scripts.score_customer 2026-08-01 2
python -m scripts.score_customer 2026-08-01 2 50 200
```

Uses the same `build_features(as_of, customer_ids=...)` code path as training.
Feature values for the same customer and as-of date will be identical to the
training snapshot.

### 3. Compare feature versions

```bash
python -m scripts.compare_feature_versions
```

Loads all registered versions of `spend_velocity` and `engagement_score` from the
feature store and writes `VERSION_COMPARISON.md` with per-feature distribution
statistics and an interpretation of the version-to-version change.

## Run the test suite

```bash
python -m pytest tests/ -v
```

40 tests across four files:

| File | What it tests |
|---|---|
| `tests/test_transforms.py` | Each feature function in isolation: normal, zero-activity, boundary cases |
| `tests/test_parity.py` | Training and scoring paths produce identical values for the same customer/as-of date |
| `tests/test_quality_checks.py` | Each quality check fires on bad input and does not false-positive on clean input |
| `tests/test_feature_store.py` | Version registration, independent retrieval, is_latest correctness, no-overwrite guard |

## Repo layout

```
features/           ingest.py, transforms.py, schema.py, quality_checks.py, build.py
feature_store/      store.py, registry.db, values/*.parquet
scripts/            build_training_features.py, score_customer.py, compare_feature_versions.py
tests/              test_transforms.py, test_parity.py, test_quality_checks.py, test_feature_store.py
data/               customers.csv, transactions.db, transactions_monthly_agg.parquet (do not edit)
```

Key docs: `feature_spec.md`, `data_dictionary.md`, `FEATURE_LINEAGE.md`,
`VERSION_COMPARISON.md`, `PARITY_CHECK.md`, `ARTIFACT_NOTES.md`, `review_log.md`.
