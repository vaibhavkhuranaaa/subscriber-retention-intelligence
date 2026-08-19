# Decision 0013: enforce cutoff-safe cohort publication

## Status

Accepted on 2026-08-18.

## Decision

Exclude registration cohorts later than each label window's history cutoff from the governed mart, API cohort responses, aggregate export, and public release. Keep the same boundary in automated API and browser checks.

## Why

A registration cohort after the history cutoff cannot be known in that analytical window. Publishing it would mix future information into a historical comparison and weaken the product's cutoff-safety claim.

## Alternatives rejected

- Hide future cohorts only in the interface. The API and export would still expose invalid rows.
- Filter only during static publication. Private and public cohort paths would then disagree.
- Keep the rows with a warning. Disclosure does not make post-cutoff data valid evidence.

## Not done

This change does not create another observed period, estimate causal effects, or alter subscriber eligibility, renewal, churn, or gross-receipt definitions.

## Changed

The cohort mart applies the history-cutoff boundary upstream. API queries repeat the guard at the delivery boundary. Tests prove February stops at January 2017 and March stops at February 2017. Release evidence and screenshots now reflect the corrected population.
