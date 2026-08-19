# Decision 0010: close paid scaled evidence without provider execution

## Status

Accepted on 2026-08-19.

## Decision

Close the temporary Fabric and Power BI execution milestone without provisioning provider resources. Retain the verified local full-data pipeline, the 442,211,685-row public Parquet release, and the source-controlled Power BI semantic contract as evidence of scale and implementation readiness. Keep actual Fabric runtime, Direct Lake behavior, and Power BI engine reconciliation explicitly unverified.

## Why

The owner required completion with no additional cost. A Fabric capacity run cannot be guaranteed to remain free, and a fabricated provider screenshot would be weaker than an honest limitation. The project already demonstrates full-volume ingestion, governed marts, a calibrated churn model, scenario arithmetic, public row-level distribution, and a static production product without request-time compute.

## Alternatives rejected

- Starting a Fabric trial risks a billing or capacity commitment outside the zero-cost mandate.
- Treating DAX-equivalent local checks as Power BI engine evidence would overstate what was executed.
- Leaving the milestone indefinitely pending would misrepresent a deliberate product decision as unfinished work.

## Not done

No Fabric workspace, capacity, lakehouse, Direct Lake model, Power BI Service report, or paid resource was created. No provider runtime or engine performance claim is made.

## Changed

Scaled evidence is closed as a zero-cost exception with explicit limitations. Reopening it requires a new budget and exact provider approval.
