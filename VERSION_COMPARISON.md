# VERSION_COMPARISON.md

Per-feature version comparison for the spec-defined versioning exercise.

## spend_velocity

Versions registered: [1, 2]

### v1
Parameters: {"short_window_days": 30}
- mean=0.8944, std=1.1326, min=0.0000, p25=0.0000, p50=0.1811, p75=1.7449, max=3.0000
- non-zero customers: 767 / 1500

### v2
Parameters: {"short_window_days": 14}
- mean=0.8597, std=1.7447, min=0.0000, p25=0.0000, p50=0.0000, p75=0.7246, max=6.4286
- non-zero customers: 431 / 1500

### v1 → v2 comparison
- Customers whose value changed: 767 / 1500
- Mean absolute change: 0.8214
- Mean signed change: -0.0347
- Customers with value increase: 356
- Customers with value decrease: 411
- Customers unchanged: 733
- Customers shifting >10 percentile points in rank: 1328

**Interpretation:**
Moving from a 30-day to a 14-day short window amplifies velocity signals for customers with very recent spend changes but suppresses them for customers whose spend pattern is stable month-over-month. The mean signed change indicates whether the shorter window systematically raises or lowers velocity scores. A model consuming this feature would notice the change if the rank-shift count is substantial — customers near a decision boundary would re-rank.

## engagement_score

Versions registered: [1, 2]

### v1
Parameters: {"electronics_weight": 1.5}
- mean=1.5765, std=1.4938, min=0.0000, p25=0.0000, p50=1.5000, p75=2.3000, max=11.3000
- non-zero customers: 1120 / 1500

### v2
Parameters: {"electronics_weight": 2.0}
- mean=1.6992, std=1.6520, min=0.0000, p25=0.0000, p50=1.6000, p75=2.4000, max=11.8000
- non-zero customers: 1120 / 1500

### v1 → v2 comparison
- Customers whose value changed: 320 / 1500
- Mean absolute change: 0.1227
- Mean signed change: 0.1227
- Customers with value increase: 320
- Customers with value decrease: 0
- Customers unchanged: 1180
- Customers shifting >10 percentile points in rank: 89

**Interpretation:**
Raising the electronics multiplier from 1.5 to 2.0 increases scores for customers who bought electronics in the 60-day window and leaves all other customers unchanged. The magnitude of change per affected customer equals (2.0 - 1.5) × number of electronics transactions in the window. A model would notice this only for the subset of customers with recent electronics purchases; the rank shift among that cohort could be significant.
