# Detailed fact pipeline

Compressed owner-obtained archives stream directly through strict schemas into private typed Zstandard Parquet. Source subscriber IDs become deterministic 96-bit private tokens before any fact is written. Grain-level uniqueness checks reject a token collision; birthday collision risk at observed subscriber scale is approximately 3e-16. No expanded CSV is retained.

## Facts

- `dim_member`: one subscriber token with private profile attributes and typed registration date.
- `fact_churn_label`: one subscriber token and label window with observed churn flag. February and March remain separate.
- `fact_subscription_transaction`: one deterministic event key with typed dates, gross receipt fields, renewal flag, and cancellation flag.
- `fact_listening_day`: one subscriber token and activity date with detailed listening counts and seconds, partitioned by source version and month.

Source v1 contains 61,493 negative duration anomalies while all six listening count fields remain nonnegative. Facts retain every row, set those invalid durations to zero, and carry `total_secs_was_negative` so downstream quality reporting remains explicit.

## Replay and promotion

Archive bytes, members, headers, schemas, row counts, allowed domains, duplicate keys, control totals, storage, and free disk validate before promotion. A matching source and contract fingerprint returns a verified no-op. A full rebuild writes a same-filesystem staging directory and replaces the prior validated run only after every control passes. Failed promotion restores the prior run.

## Duplicate rules

- Member and label duplicate keys fail because they make dimensions or observed outcomes ambiguous.
- Byte-identical transaction events collapse across and within source versions. Nonidentical events remain, including events on overlapping dates. Source has no transaction ID, so identical legitimate events cannot be distinguished.
- Listening subscriber-date duplicates fail. Current source versions have disjoint measured activity-date ranges.

## Resource limits

Listening facts partition by activity month so exact duplicate and measure controls stay bounded. Build stops before free disk falls below 30 GiB. Measured facts plus a 20 percent downstream allowance must remain at or below 11 GiB.
