# Source contract

Nine owner-obtained source archives are inventoried. Seven analytical archives are selected: one member snapshot, two separate churn-label windows, two transaction versions, and two daily-listening versions. Two submission templates are excluded because they are not observed labels.

Every selected field declares a type, null policy, allowed domain, privacy class, and downstream owner in `contracts/sources.json`. Subscriber source IDs and row-level personal attributes remain private. Public outputs require a separate aggregate allow-list and privacy review.

## Version rules

- `members_v3` is the only member snapshot.
- `train` and `train_v2` remain separate February and March 2017 label windows.
- Transaction versions retain distinct events in overlapping dates, reject exact duplicate rows, and reject duplicate deterministic event keys.
- Listening versions reject duplicate subscriber-date keys and reconcile any overlapping dates before promotion.

## Churn rule

Candidates expire inside the label month. A candidate churns when no valid renewal is observed or the first valid renewal is at least 30 days after effective expiration. Same-day subscription events are ordered before cancellation events using the published challenge labeller contract.

## Storage rule

Archives stream directly into typed Zstandard Parquet. Expanded CSV is never retained. A full run stops if projected derived storage exceeds 11 GiB or free disk would fall below 30 GiB. M2 records the pilot projection; M3 must replace it with a measured full-build footprint.
