# Governed semantic model

dbt reads validated private Parquet facts as views and materializes only cutoff-level features, snapshots, marts, and public aggregates. The full transaction and listening grains remain in Parquet and are not copied into the DuckDB warehouse.

## Cutoffs and outcomes

February labels use a 2017-01-31 history cutoff. March labels use a 2017-02-28 history cutoff. Transactions and listening activity after each cutoff are excluded from features. Observed renewal is the complement of the challenge-compatible churn label inside each declared renewal-observation window; it is not a causal intervention result.

Same-day transactions follow the locked sequence: plan signature descending, renewal expirations ascending, cancellation expirations descending, then subscription before cancellation. The last sequenced event through a cutoff supplies reconstructed active state and effective expiration.

## Metrics

- Active subscribers have reconstructed effective expiration on or after the history cutoff.
- Gross receipts sum actual amount paid in source currency. They are not recognized revenue.
- Observed renewal and churn use separate February and March label windows.
- Cancellation rate is cancellation events divided by subscription events through the cutoff.
- Engagement features use 30-day and 90-day pre-cutoff windows.
- Corrected negative listening durations remain counted through `negative_duration_rows_90d` and are never treated as ordinary observed zeroes.

## Public boundary

Public dashboard tables contain no subscriber token, city, age, gender, or registration-method field. Cohort and segment rows require at least 100 eligible subscribers, and dashboard extracts remain aggregate-only. The separate `public-m12` Parquet release publishes detailed facts only after release-specific re-keying and member-field generalization; private source tokens and the publication salt remain private.

## Run

```sh
.venv/bin/python scripts/build_semantics.py
.venv/bin/python scripts/reconcile_semantics.py \
  --warehouse "$RETENTION_PRIVATE_DIR/warehouse/retention.duckdb" \
  --facts "$RETENTION_PRIVATE_DIR/facts"
```

The committed profile caps dbt at one thread and DuckDB at 4 GiB memory. No Docker runtime is needed.
