# Calibrated churn model

M6 compares a regularized logistic baseline with one predeclared shallow histogram gradient-boosting challenger. Both use the governed cutoff snapshot. No raw archive, post-cutoff event, demographic, identifier, or observed outcome enters the feature matrix.

## Evaluation contract

- Fit: 198,861 fixed token-hash rows from the February label window.
- Calibration: 98,740 disjoint February rows. This is cross-sectional, not a later cutoff.
- Final test: all 970,960 March rows, untouched until both models and sigmoid calibrators were fixed.
- Bootstrap: 100 paired fixed-seed replicates over a 250,000-row stratified test sample.
- Compute: one DuckDB thread, 4 GiB memory cap, one model thread, no Docker.

Seven February hash buckets remain unused to reduce local heat and memory. The fit cohort is still large enough to support the fixed model comparison. Another observed label window is required before calibration can be temporally separated from fitting.

## Features

Subscription counts, gross receipts, cancellations, transaction recency, effective-expiration horizon, current plan and payment state, listening counts and recency, registration tenure, and explicit missingness flags are cutoff-safe inputs. Skewed counts and amounts use `log1p` transforms.

The deny-list includes subscriber token, label, observed renewal, label window, observation dates, raw event dates, age, gender, city, and repeat/new diagnostic status. Token hashes assign deterministic cohorts and break ranking ties only. Age and gender appear only in private aggregate diagnostics.

## Results

On the untouched March window:

- Logistic log loss: 0.2157.
- Challenger log loss: 0.2047.
- Full-population relative improvement: 5.09 percent, with 95 percent interval 4.59 to 5.32 percent.
- Challenger expected calibration error: 0.0240.
- Challenger top-decile lift: 6.02.

For the selected repeat-subscriber scope:

- Relative log-loss improvement: 5.57 percent, with 95 percent interval 5.40 to 5.83 percent.
- Expected calibration error: 0.0166.
- Top-decile lift: 4.95, with 95 percent interval 4.86 to 5.03.

March-new subscribers are excluded. Their churn rate is 39.84 percent and challenger calibration error is 0.106. They represent 9.19 percent of the test population but 54.69 percent of the unrestricted top decile. A representative later window is required before probability use for that group.

## Run

```sh
.venv/bin/python scripts/evaluate_churn_models.py
.venv/bin/python scripts/render_model_evidence.py
```

The private selected artifact is written under `$RETENTION_PRIVATE_DIR/models/`. Technical evidence contains aggregate metrics only. Historical association does not measure intervention effect.
