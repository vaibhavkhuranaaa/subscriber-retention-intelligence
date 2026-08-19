# Decision 0005: Serve a bounded descriptive retention product

## Decision

Serve the governed DuckDB marts through a versioned FastAPI boundary and a local React evidence docket. Register pseudonymous subscriber routes only in private mode. Keep public mode aggregate-only, cap every list and export, read the warehouse with one DuckDB thread, and precompute a 500-record-per-window private inspection set with bounded transaction and listening history.

## Why

The product must connect executive movement, cohorts, operating segments, definitions, and one private subscriber journey without scanning 442 million detailed rows during interaction. A small API boundary preserves the dbt metric contract, makes privacy testable at route level, and supports honest loading, empty, and failure states. The bounded inspection set is explicitly ordered for evidence review, not intervention priority.

## Alternatives rejected

- Query detailed Parquet from the browser: duplicates semantic logic and exposes private grains.
- Hide subscriber controls in public UI: hidden controls are not a privacy boundary.
- Rank records as retention targets: M5 has no calibrated model or causal treatment evidence.
- Run the application in Docker: adds unnecessary local compute and memory overhead.
- Materialize all subscriber journeys: increases storage and refresh cost without improving the descriptive decision.

## Not done

No predictive scoring, intervention scenario, deployment, Fabric run, Power BI publication, Git mutation, or public exposure is part of this decision.

## Changed

M5 adds governed plan, payment, registration, and auto-renew segments; bounded private review marts; aggregate CSV exports; versioned public/private API modes; responsive desktop/mobile workflows; and automated API, browser, accessibility, privacy, and latency evidence.
