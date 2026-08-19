# Decision 0012: replace the dashboard with an analysis blotter

## Status

Accepted on 2026-08-17.

## Decision

Replace the public overview's editorial verdict and KPI-card sequence with an exception-first operating blotter. Lead with comparable metric rows, then let the analyst inspect reconciliation, definition, limitation, cohort breaks, and segment rate differences in place.

Deploy all privacy-safe governed cohort and segment aggregates. Keep raw archives, direct identifiers, private journeys, model artifacts, and scenario curves outside the public static release.

## Why

The prior screen presented conclusions before evidence and resembled a generic portfolio dashboard. Retention review is an operating task: users need denominators, deltas, comparison windows, and drillable diagnostic tables before narrative.

## Alternatives rejected

- A statistical-control board would imply control limits that two observed label windows cannot support.
- A cohort-only worksheet would hide material movements outside registration cohorts.
- A visual polish pass would preserve the same hero-and-card information architecture.

## Not done

The redesign does not claim segment causality or additive contribution to churn change. It does not expose raw subscribers or make a third time period, seasonality, causal uplift, or revenue claim.

## Changed

Overview becomes a selectable movement table with a synchronized inspector. Matching cohort and segment rows gain explicit two-window comparisons. The public snapshot expands from 48 to every privacy-safe cohort row. The global shell adopts compact analytical software density.
