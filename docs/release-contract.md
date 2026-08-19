# Release contract

## Candidate boundary

The release candidate contains source code, aggregate evaluation results, governed contracts, and sanitized product visuals. Private source archives, detailed facts, model artifacts, delivery state, approvals, cost receipts, and generated graphs stay in the sibling ops folder.

Public API mode registers aggregate routes only. Source attribution is structured JSON data. React owns presentation. API payloads must not contain HTML or executable script.

Static delivery generates the approved aggregate snapshot and overview exports from public API mode immediately before the frontend build. Generated JSON and CSV stay ignored and are never committed. Journeys, subscriber routes, and scenario data are absent from the public artifact.

## Required checks

- Python tests cover ingestion contracts, semantic rules, churn gates, scenario arithmetic, public and private API modes, recovery, privacy, and release policy.
- dbt parsing verifies source-controlled semantics without requiring private data in CI.
- Power BI contract checks validate dimensions, facts, grains, one-way relationships, privacy, DAX guards, and fixed contexts.
- Browser tests cover 1440 px and 390 px layouts, keyboard focus, loading, empty, error, public mode, serious and critical accessibility findings, console errors, and horizontal overflow.
- Web type checking and production build must pass.
- Permanent deployment must keep recurring infrastructure cost at zero and add a provider request ceiling before public exposure.

## Approval boundary

Repository code and documentation use the MIT License. The source dataset remains governed by its provider terms and is not redistributed or relicensed. Staging, commits, pushes, history curation, repository rename, default-branch change, description, homepage, topics, deployment, and public exposure require owner approval. Power BI execution and Fabric resources require separate approval. Local contract verification does not claim that either engine ran.
