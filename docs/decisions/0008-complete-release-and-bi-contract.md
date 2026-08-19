# Decision 0008: Complete release and BI contract

## Decision

Separate source attribution data from React presentation, define a browser-compatible Power BI semantic contract over aggregate marts, generate a contract-only CI fixture, and gate release with Python, dbt, browser, accessibility, privacy, recovery, cost, and responsive checks. Keep actual deployment and Power BI engine execution approval-gated.

## Why

The remote default branch serves presentation HTML and script inside an API attribution string, tests only legacy code, and does not describe the subscriber product. A clean release needs one source of metric truth, reproducible checks without private data, and an explicit boundary between local verification and provider execution.

## Alternatives rejected

- Reuse the legacy Worker response: mixes unrelated fintech presentation with API data.
- Commit private warehouse or model fixtures: violates source, privacy, and repository-purity boundaries.
- Relate subscription segments by `segment_key`: keys collide across dimensions.
- Drop null registration cohorts: silently removes eligible subscribers.
- Claim Power BI reconciliation from DAX-equivalent SQL: does not prove browser-engine execution.

## Not done

No branch, staging, commit, push, remote setting, repository rename, deployment, Fabric resource, Power BI item, license choice, or public exposure changed. Power BI engine reconciliation remains pending approved execution.

The owner selected the MIT License on 2026-08-17 after local M8 verification. The license covers repository code and documentation, not the source dataset or private derived data.

## Changed

Private data and delivery state moved to the sibling ops folder. Public source now carries structured attribution, release manifests, aggregate evaluation results, CI, responsive state checks, and the semantic contract. Null cohorts map to `unknown`; subscription relationship keys combine dimension and segment key; all relationships filter one way from dimensions to facts.
