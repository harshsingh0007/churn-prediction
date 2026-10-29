"""Train/score parity test — the same customer must produce identical features on both paths."""

import pytest
from features.build import build_features

AS_OF = "2026-08-01"
TEST_CUSTOMER_IDS = [2, 50, 200]  # mix of active and potentially low-activity customers


def test_training_scoring_parity():
    """Training path (all customers) and scoring path (subset) must be identical."""
    training = build_features(AS_OF, customer_ids=None)
    scoring = build_features(AS_OF, customer_ids=TEST_CUSTOMER_IDS)

    training_subset = (
        training[training["customer_id"].isin(TEST_CUSTOMER_IDS)]
        .sort_values("customer_id")
        .reset_index(drop=True)
    )
    scoring_sorted = scoring.sort_values("customer_id").reset_index(drop=True)

    feature_cols = [c for c in training_subset.columns if c not in ("customer_id", "as_of_date")]
    for col in feature_cols:
        assert (training_subset[col].values == scoring_sorted[col].values).all(), (
            f"Parity failure on column '{col}': training and scoring paths disagree"
        )


def test_scoring_single_customer():
    """Score a single customer and confirm output has exactly one row."""
    result = build_features(AS_OF, customer_ids=[2])
    assert len(result) == 1
    assert result.iloc[0]["customer_id"] == 2


def test_as_of_date_in_output():
    """as_of_date must appear in the output and match the parameter."""
    result = build_features(AS_OF, customer_ids=[2])
    assert result.iloc[0]["as_of_date"] == AS_OF
