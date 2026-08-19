# Decision 0006: Scope calibrated challenger to repeat subscribers

## Decision

Select the calibrated histogram gradient-boosting challenger for repeat subscribers only. Keep March-new subscribers outside probability-driven action because their held-out calibration error is 0.106, above the 0.030 gate. Use a fixed February token-hash fit cohort, a disjoint February calibration cohort, and the untouched March label window for final testing. Age, gender, city, identifiers, outcomes, and post-cutoff activity never enter scoring.

## Why

The challenger improves full-population log loss over calibrated logistic regression by 5.09 percent and repeat-subscriber log loss by 5.57 percent. Repeat-subscriber expected calibration error is 0.017 and top-decile lift is 4.95. These pass the declared gates with paired fixed-seed intervals. March-new subscribers have 39.84 percent churn and form 54.69 percent of the global top decile, but both models materially understate their risk. Shipping those probabilities would turn population shift into false precision.

Only February and March observed label windows exist. A true three-period train, validation, and test design is impossible. February calibration is disjoint but cross-sectional, not a third temporal cutoff. The scope restriction preserves an honest model decision without inventing data or weakening the calibration gate.

## Alternatives rejected

- Ship the challenger for every March subscriber: fails the new-subscriber calibration gate.
- Retain logistic regression everywhere: simpler, but loses a statistically supported 5.57 percent repeat-subscriber log-loss improvement and modest lift gain.
- Treat a second February hash cohort as a later time period: false temporal claim.
- Tune multiple challengers against March: contaminates the final future-window test.
- Add a large boosting framework or distributed training: unnecessary for the bounded feature matrix and local compute budget.
- Use protected demographics as model features: prohibited by the product contract.

## Not done

No threshold selection, intervention economics, causal lift, application score integration, deployment, Fabric run, Power BI publication, Git mutation, or public row-level artifact is part of this decision.

## Changed

M6 adds a reproducible single-thread evaluation, strict feature allow-list, calibrated logistic baseline, one shallow histogram challenger, paired bootstrap intervals, exact tie-safe top-decile lift, private subgroup diagnostics, a scoped model artifact, automated leakage and artifact tests, and stakeholder evidence.
