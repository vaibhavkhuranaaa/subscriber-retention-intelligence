# Bounded intervention scenario planner

M7 lets a lifecycle operator test capacity, calibrated risk threshold, contact cost, offer cost, assumed retention lift, and lift sensitivity. Every result is simulated. The planner does not estimate intervention effect or recommend a treatment.

## Population and selection

The eligible population is the 881,701 repeat subscribers accepted by M6. March-new subscribers remain excluded because their held-out calibration error is 0.106. Candidates must meet the entered minimum score and are ordered by calibrated historical churn risk with a deterministic private tie break. Capacity and threshold are both binding.

The private aggregate curve contains one cumulative point per 100 contacts plus the final eligible point. It contains no subscriber token or row-level score. Interactive requests do not run model inference or query detailed facts.

## Formulas

For selected set `S`, predicted churn probability `p`, latest nonnegative payment proxy `v`, assumed lift `L`, contact cost `c`, and offer cost `o`:

```text
modeled churn exposure = sum(p for S)
simulated retained subscribers = L * sum(p for S)
simulated retained gross-receipt proxy = L * sum(p * v for S)
total spend = count(S) * (c + o)
simulated net gross-receipt proxy = simulated retained gross-receipt proxy - total spend
break-even assumed lift = total spend / sum(p * v for S)
```

Offer cost applies to every selected contact because acceptance and redemption are not observed. Low and high outcomes use the entered lift plus or minus the sensitivity amount, clipped to zero and one. They use the same selected set and spend. They are not confidence or prediction intervals.

## Controls

- Capacity ranges from zero to the eligible repeat-subscriber population. Positive capacity is at least 100.
- Threshold and lift range from zero to one.
- Lift sensitivity ranges from zero to 0.5.
- Each cost ranges from zero to 10,000 source-currency units per contact.
- Zero capacity, zero lift, threshold one, full capacity, high cost, uncertainty order, and repeat-only scope reconcile independently.
- Maximum measured formula reconciliation error is zero against a `0.000001` gate.

## Run

```sh
.venv/bin/python scripts/build_scenario_curve.py
.venv/bin/python scripts/verify_scenario.py
cd web
npm run build
npx playwright test
```

The curve build uses one DuckDB thread, a 4 GiB cap, one model thread, and no Docker. The latest run completed in 8.368 seconds. Scenario API P95 was 2.619 ms across 25 measured requests.

## Limitations

No randomized intervention, causal uplift, contact delivery, offer acceptance, incremental margin, standardized future billing horizon, recognized revenue, or lifetime value exists in the source. Historical risk association and scenario arithmetic do not establish that outreach will work.
