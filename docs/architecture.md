# Architecture

## Source boundary

- Member profile: one subscriber.
- Subscription transaction: one payment, renewal, cancellation, or expiry-bearing transaction row.
- Listening activity: one subscriber-day aggregate.
- Churn label: one subscriber in a challenge prediction window.

## Local topology

Private compressed archives stream through schema and row validation into typed Zstandard Parquet. Source subscriber identifiers become deterministic private tokens before curated models. DuckDB and dbt Core build detailed facts, subscription-state reconstruction, cutoff snapshots, features, cohorts, metric marts, and public extracts.

The private web product uses detailed governed marts. Public web uses only an approved bounded extract. Monthly and cohort marts accelerate common queries without replacing detailed transactions or daily listening.

## Scaled topology

After separate approval, the same contracts map to Fabric bronze files, Delta silver facts, gold marts, and a Direct Lake semantic model. A Power BI report is authored in the browser. Pipeline history, lineage, monitoring, capacity, screenshots, and video are captured before teardown.

## Failure and recovery

- Archive mismatch or schema drift stops before writes.
- Same-day transaction ordering follows a versioned deterministic rule.
- Duplicate and overlap controls prevent v1/v2 double counting.
- Partial Parquet writes validate before atomic promotion.
- Feature-cutoff tests reject future transactions or listening activity.
- Model failure falls back to descriptive analytics and baseline ranking.
- Provider failure shows an explicit stale or unavailable state.
