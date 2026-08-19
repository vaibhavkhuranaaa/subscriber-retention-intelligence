# Decision 0004: Govern cutoff-safe subscription semantics

## Decision

Use dbt Core with DuckDB to read detailed Parquet facts as external views and materialize only label-cutoff features, subscriber snapshots, decision marts, definitions, and aggregate-only public extracts. Limit execution to one thread and 4 GiB memory. Use 30-day and 90-day engagement windows, preserve February and March outcomes separately, and reconcile headline metrics through an independent fact query.

## Why

The source has 410.5 million listening rows and only 38 GiB free disk at milestone start. Copying detailed facts into a second database would breach the 30 GiB reserve and add no analytical value. Cutoff-level materialization supports later modeling and interactive products while keeping future activity out of features.

## Alternatives rejected

- Copy all detailed facts into DuckDB tables: duplicates 8.94 GiB of trusted Parquet.
- Build semantics in application code: would create a second metric definition outside dbt.
- Use Docker for dbt: unnecessary compute and memory overhead on the local Mac.
- Publish private snapshots then hide columns in the UI: UI hiding is not a privacy boundary.
- Treat label windows as one target period: loses temporal identity and permits leakage.

## Not done

No model training, intervention scenario, API, interface, deployment, Fabric run, Power BI publication, Git mutation, or public exposure is part of this decision.

## Changed

Subscription state, cutoff features, observed renewal and churn, gross receipts, cancellations, engagement, cohorts, definitions, exposures, and public aggregate contracts now share one tested semantic layer. Independent controls determine whether headline marts may feed later milestones.
