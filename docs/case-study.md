# Subscriber Retention Intelligence case study

## Decision supported

A subscription lifecycle analyst needs to separate material changes in renewal behavior from ordinary volume movement, identify which repeat subscribers carry the most historical churn risk, and test whether a finite contact program could be economically plausible under declared assumptions.

The product answers that sequence without presenting modeled association as treatment response. It opens on exception-led descriptive analysis, keeps metric definitions beside the evidence, and limits the intervention planner to repeat subscribers whose probabilities passed the evaluation contract.

## Data and scale

The analytical source contains membership, subscription transactions, daily listening activity, and two observed churn-label windows. The pipeline accepts and reconciles 442,211,685 rows. A public release preserves all accepted analytical rows in 32 Zstandard-compressed Parquet files totaling 7,522,254,856 bytes.

Public subscriber and event keys are release-specific and collision checked. Exact source identifiers, private tokens, exact age, exact registration date, model artifacts, and the publication salt are excluded. The full release is available from the [Hugging Face dataset](https://huggingface.co/datasets/vaibhavkhurana/subscriber-retention-intelligence).

## Analytical system

1. Compressed archives stream through schema, row, overlap, and checksum controls into typed Parquet.
2. DuckDB and dbt reconstruct subscription state, cutoff snapshots, listening features, cohorts, segments, and governed metric marts.
3. A calibrated histogram gradient boosting challenger is evaluated against a logistic baseline with March held untouched until final evaluation.
4. A private scenario curve turns calibrated historical risk into capacity-bounded sensitivity arithmetic using user-entered lift and cost assumptions.
5. React serves the analyst workflow. Cloudflare Pages hosts a static public product, while Hugging Face serves the complete transformed row-level release.

See the [architecture](architecture.md), [data contract](data-contract.md), and [metric glossary](metric-glossary.md).

## Evaluation

The selected challenger is valid only for the 881,701 repeat subscribers in the March test window. It improves log loss by 5.57 percent over the baseline, has expected calibration error of 0.0166, and produces 4.95 times baseline churn concentration in the top decile. Probability use is blocked for 89,259 March-new subscribers because that group failed the calibration boundary.

The scenario engine reconciles with maximum absolute formula error of 0 and responds in 2.619 ms P95 in the recorded local benchmark. Lift is a user assumption, not a causal estimate. Latest payment is a one-payment gross-receipt proxy, not revenue, margin, lifetime value, or a forecast.

## Product choices

- The public product is a dense analysis surface, not a marketing dashboard. Movement rows, comparable cohort breaks, segment contrasts, definitions, and freshness carry the visual hierarchy.
- Public request-time compute is zero. The deployed site is static and has no Pages Functions, database connection, or private API path.
- The detailed dataset is separate from the interface. This keeps the dashboard fast while making every accepted transformed row available for independent analysis.
- Fabric and actual Power BI engine execution remain unverified. The provider milestone was closed rather than run because the final delivery constraint is zero additional cost.

## What this proves

- Full-volume analytical engineering over 442.2 million accepted rows.
- Cutoff-safe metric and feature contracts that reject post-cutoff activity.
- Honest model scoping that excludes a population where probability use is not supported.
- Explicit separation of observed, modeled, and simulated quantities.
- A permanent public product and complete row-level data release with zero recurring project cost.

## What it does not prove

- Causal retention lift or offer response.
- Enterprise SaaS revenue, account, seat, contract, or customer-success behavior.
- Recognized revenue, margin, lifetime value, or future receipts.
- Fabric runtime, Direct Lake behavior, or Power BI engine reconciliation.

## Links

- [Live analytical product](https://subscriber-retention-intelligence.pages.dev/)
- [Complete row-level dataset](https://huggingface.co/datasets/vaibhavkhurana/subscriber-retention-intelligence)
- [Source repository](https://github.com/vaibhavkhuranaaa/subscriber-retention-intelligence)
- [Release contract](../release/manifest.json)
