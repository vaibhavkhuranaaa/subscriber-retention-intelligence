# Decision 0002: Lock source, churn, privacy, and storage contracts

## Decision

Inventory all nine owner-obtained archives, select seven analytical sources, and exclude both submission templates. Keep the two label files as separate challenge windows. Union transaction and listening versions only under explicit overlap and duplicate rules. Apply the challenge-compatible 30-day renewal-gap definition and deterministic same-day transaction ordering. Stream typed sources directly into Zstandard Parquet with no durable expanded CSV.

## Why

The source versions overlap in purpose and sometimes calendar coverage. Treating them as interchangeable snapshots or blindly appending them can duplicate subscriber activity and corrupt churn labels. Machine-readable field, privacy, and storage contracts make those ambiguities fail before downstream facts and metrics are built.

## Alternatives rejected

- Expand all CSV files before profiling: requires about 31.95 GiB of redundant storage.
- Combine `train` and `train_v2`: mixes two different prediction windows.
- Use submission templates as labels: they contain placeholders, not observed outcomes.
- Publish source subscriber identifiers or detailed rows: unnecessary and outside the public output boundary.
- Claim payment amounts as recognized revenue: source supports gross receipts only.

## Not done

No detailed fact pipeline, dbt model, churn model, interface, deployment, Fabric run, Power BI publication, dataset download, or Git/GitHub mutation is part of this decision. Pilot storage is a projection; M3 must measure and reconcile the full streamed build.

## Changed

Source provenance, field schemas, row controls, version rules, duplicate keys, churn windows, privacy classes, disk reserve, storage ceiling, and direct-to-Parquet pilot are now explicit and testable.
