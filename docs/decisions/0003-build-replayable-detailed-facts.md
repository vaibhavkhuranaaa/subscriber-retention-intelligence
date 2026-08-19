# Decision 0003: Build replayable detailed facts

## Decision

Stream each selected archive through its locked schema into private typed Zstandard Parquet. Replace subscriber IDs with 96-bit SHA-256 prefixes before writes, partition listening by month, preserve separate label windows, collapse byte-identical transaction events, and fail on ambiguous member, label, or listening keys. Promote only a fully reconciled staged run. Matching source and contract fingerprints replay as a verified no-op after physical output checks.

## Why

The source expands to about 31.95 GiB and listening contains more than 410 million rows. Direct streaming avoids redundant CSV storage. Monthly listening partitions keep exact controls bounded. Staged validation prevents partial or drifted data from replacing trusted facts.

## Alternatives rejected

- Durable expanded CSV: exceeds safe local storage without adding analytical value.
- One global listening sort: unnecessary spill and disk pressure for already month-addressable facts.
- Silent precedence for overlapping versions: can discard valid distinct events.
- Preserve source subscriber IDs in facts: unnecessary privacy exposure.
- Keep multiple permanent full runs: violates local footprint target.
- Use longer binary tokens: failed the 11 GiB storage gate; 96-bit tokens retain negligible observed-scale collision risk and fail promotion on collision.

## Not done

No membership-state reconstruction, dbt semantics, feature engineering, churn model, interface, deployment, Fabric run, Power BI publication, or Git/GitHub mutation is part of this decision.

## Changed

Detailed member, label, transaction, and listening grains now have replay, drift, duplicate, reconciliation, privacy, disk, storage, and promotion controls. One unknown registration-method sentinel becomes null. Negative source listening durations become flagged zeros without changing listening counts or dropping rows. M4 may consume these facts without reopening raw archives.
