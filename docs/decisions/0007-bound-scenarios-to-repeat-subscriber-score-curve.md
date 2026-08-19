# Decision 0007: Bound scenarios to repeat-subscriber score curve

## Decision

Precompute a private aggregate score curve for the 881,701 repeat subscribers approved by M6. Select contacts by calibrated risk threshold and capacity, ordered by score with a deterministic private tie break. Simulate retained subscribers and retained gross-receipt proxy from user-entered lift, contact cost, and offer cost assumptions. Apply both costs to every selected contact. Keep March-new subscribers outside every probability-driven scenario.

## Why

Interactive scenarios must not rescore nearly one million rows or scan 442 million facts. A 1.5 MiB aggregate curve turns each request into a bounded lookup and preserves the exact M6 population gate. The source contains no intervention, contact delivery, acceptance, redemption, margin, or future-value outcome. Applying offer cost to every selected contact is deliberately conservative and avoids inventing an acceptance rate.

Assumed lift means the user-entered share of modeled churn prevented. Low and high values are sensitivity bounds, not model intervals or causal confidence bounds. The value proxy is each subscriber's latest nonnegative payment amount in source currency. It is not revenue, margin, lifetime value, or a forecast.

## Alternatives rejected

- Score at request time: unnecessary latency, memory, and heat.
- Scan detailed facts per scenario: duplicates governed work and violates the local compute contract.
- Include March-new subscribers: their M6 calibration error fails the probability-use gate.
- Charge offer cost only to simulated retained subscribers: assumes offer acceptance that the source does not observe.
- Call simulated value revenue or CLV: no recognition, margin, horizon, or lifetime-value contract exists.
- Add an optimization solver: threshold and capacity arithmetic is already exact and transparent.

## Not done

No observed treatment effect, uplift model, contactability rule, offer acceptance model, channel constraint, threshold recommendation, deployment, Fabric run, Power BI publication, Git mutation, or public row-level score is part of this decision.

## Changed

M7 adds a single-thread score-curve build, pure scenario arithmetic, a private-only API route, explicit observed/modeled/simulated labels, low/base/high lift sensitivity, break-even lift, boundary reconciliation, API performance evidence, and a responsive scenario docket.
