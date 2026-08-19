# Decision 0001: Separate subscriber retention product

## Decision

Build Subscriber Retention Intelligence as an independent consumer subscription product. Keep fintech engagement work in its own repository and remove the equal-workspace suite narrative. Store private delivery records in a sibling ops folder outside public Git history. The permanent interface is React; Power BI is browser-authored during the temporary Fabric evidence run.

## Why

The subscription source supports observed churn labels, detailed payment history, renewal reconstruction, cohorts, and daily engagement. The fintech source has a different user, outcome, time model, and public boundary. Separating them produces two honest end-to-end products.

## Alternatives rejected

- Equal workspaces in one suite: no shared operational user or conformed business outcome.
- Enterprise SaaS positioning: source has consumers, not accounts, contracts, seats, or expansion.
- Synthetic B2B overlay: unnecessary for this product and would blur empirical evidence.
- Aggregate-only public demo: hides the analytical and engineering depth.
- Permanent Power BI workspace: unnecessary for the public product and dependent on service licensing.
- Private sibling delivery folder: rejected by the owner in favor of one ignored local folder without duplicated project storage.

## Not done

No deployment, commit, push, repository rename, Fabric run, Power BI publication, or portfolio publication is authorized by this decision.

## Changed

Product identity, source boundary, semantics, local delivery layout, milestones, deployment plan, and evidence now cover subscription retention only.
