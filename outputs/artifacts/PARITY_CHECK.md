# PARITY_CHECK.md

## Parity Mutation Check Result

**Date:** 2026-10-29  
**as_of:** 2026-08-01  
**Test customers used:** [2, 50, 200]

### Method

A sabotaged copy of `features/build.py` was created with the following deliberate divergence
introduced in the scoring path only:

```python
# scoring path only
if customer_ids is not None:
    feat['spend_30d'] = feat['spend_30d'] * 1.01
```

This simulates a real parity bug: a transform applied differently depending on whether
`customer_ids` is set, which is exactly the kind of silent divergence the parity test is
designed to catch.

### Result

`test_parity.py::test_training_scoring_parity` **FAILED** on the sabotaged build with:

```
AssertionError: Parity failure on column 'spend_30d': training and scoring paths disagree
```

The training path returned `spend_30d = 136.62` for customer 2; the sabotaged scoring path
returned `137.99` (1% higher). The test caught the divergence on the first differing column.

After restoring `features/build.py`, all three parity tests passed.

### Coverage-of-intent check

Spec'd features vs. test coverage:

| Feature | test_transforms.py | test_parity.py |
|---|---|---|
| `days_since_last_txn` | ✓ (4 cases) | ✓ (via parity) |
| `spend_30d` | ✓ (3 cases) | ✓ (via parity) |
| `txn_count_90d` | ✓ (2 cases) | ✓ (via parity) |
| `return_rate_90d` | ✓ (3 cases) | ✓ (via parity) |
| `spend_velocity` | ✓ (3 cases incl. v2 window) | ✓ (via parity) |
| `engagement_score` | ✓ (3 cases incl. v2 weight) | ✓ (via parity) |

Spec'd quality checks vs. test coverage:

| Check | test_quality_checks.py |
|---|---|
| No nulls after defaulting | ✓ (fires and passes) |
| Zero-activity defaults (730.0 / 0.0 / 0) | ✓ (fires and passes) |
| Monetary bounds on spend_30d | ✓ (negative and too-high cases) |
| Rate bounds on return_rate_90d | ✓ |
| Row count parity | ✓ |

No spec'd feature or check was found untested. No additions needed.
