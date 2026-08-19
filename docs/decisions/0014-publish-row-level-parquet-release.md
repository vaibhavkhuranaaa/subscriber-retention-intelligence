# Decision 0014: publish a re-keyed row-level Parquet release

## Status

Accepted on 2026-08-18.

## Decision

Publish all 442,211,685 accepted analytical rows as 32 Zstandard-compressed Parquet files in the public Hugging Face dataset `vaibhavkhurana/subscriber-retention-intelligence`. Generate release-specific 64-bit subscriber and event pseudonyms before upload and reject the release if either domain contains a collision. Preserve detailed listening, transaction, and churn-label rows. Preserve one member row per subscriber while replacing exact age with a 10-year band and exact registration date with registration month. Exclude source identifiers and private tokens.

Keep the analytical dashboard on Cloudflare Pages. Its Data Catalog links to the dataset, manifest, and table-specific Viewer configurations. Hugging Face provides file delivery and dataset browsing; Pages continues serving the product and governed aggregates.

## Why

The owner explicitly requested full-data publication with no recurring storage cost. The verified package is 7,522,254,856 bytes, within Hugging Face public dataset guidance. Collision-checked 64-bit pseudonyms preserve stable cross-table joins for this release while reducing the package by 33 percent versus the 128-bit draft. Parquet preserves analytical types and partition pruning without adding a database, container, or request-time scan.

## Alternatives rejected

- Cloudflare R2 would fit inside its current free storage allowance after compaction, but would still need production object-delivery configuration and would not add a Dataset Viewer.
- Raw source archives would expose source identifiers and require every user to repeat ingestion.
- The existing private token is deterministic from the source identifier and can be mapped by anyone holding the competition files.
- A live query service would add compute cost, abuse exposure, and operational failure modes without increasing data completeness.
- Aggregate-only publication does not meet the approved scope.

## Not done

No source identifier, exact reported age, exact member registration date, private model artifact, scenario curve, or private warehouse is published. The data remains historical and does not become causal, current, or enterprise subscription evidence.

## Changed

Publication expands from governed aggregates to the complete accepted row-level corpus. Hugging Face becomes the detailed-data plane; Pages remains the product plane.
