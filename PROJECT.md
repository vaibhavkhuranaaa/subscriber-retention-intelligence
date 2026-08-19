# Subscriber Retention Intelligence

## Product contract

Build an end-to-end consumer subscription-retention product using longitudinal membership, subscription transaction, daily listening, and observed churn-label data.

## Decision

A subscription lifecycle leader reviews renewal economics, cohort behavior, engagement change, calibrated churn risk, and finite outreach capacity to choose which subscribers receive attention and why.

## Success

- Full detailed transaction and subscriber-day grains remain available privately.
- Renewal, churn, cancellation, cohort, engagement, and payment metrics reconcile to source controls.
- A time-safe challenger beats a named baseline or is dropped.
- Scenario planning distinguishes observed facts, modeled probabilities, and assumed intervention lift.
- Public product uses the owner-approved source under its attribution and privacy contract.
- Local web and full-volume pipeline evidence demonstrate system depth without requiring paid provider execution.

## Boundaries

This is a consumer digital-subscription product, not enterprise SaaS. Payment amounts are gross receipts, not recognized revenue. The source has no account hierarchy, contracts, seats, support cases, intervention outcomes, or causal treatment effects.

## Status

The public analytical product is deployed at https://subscriber-retention-intelligence.pages.dev/. Dashboard endpoints remain aggregate-only and have no Pages Functions or request-time private-data access. The complete re-keyed, generalized row-level Parquet release is published through its governed data catalog at https://huggingface.co/datasets/vaibhavkhurana/subscriber-retention-intelligence. The paid scaled-evidence milestone is closed under the zero-additional-cost constraint. Actual Fabric and Power BI engine execution remain explicitly unverified.
