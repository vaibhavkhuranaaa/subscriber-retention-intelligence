# Decision 0009: deploy a static aggregate public product

## Status

Accepted on 2026-08-17.

## Decision

Deploy the permanent public product to Cloudflare Pages by direct upload. Generate a versioned snapshot from governed `public_*` relations, then serve only static HTML, JavaScript, CSS, JSON, and aggregate CSV assets.

Do not deploy FastAPI, DuckDB, private facts, subscriber journeys, model scores, or the intervention scenario. Keep request-time compute at zero. Preserve rollback through immutable Pages deployment history.

## Why

The public experience needs two historical windows and small governed aggregates, not a live analytical database. Static delivery removes a private-data path, avoids recurring infrastructure cost, and does not require unapproved Git history changes.

## Consequences

- Public data changes require an explicit snapshot rebuild and deployment.
- Generated JSON and CSV remain ignored and are never committed.
- Public navigation contains Overview, Cohorts, Segments, and Definitions only.
- Private journeys and scenario planning remain local.
- Hosted CI verifies the clean-checkout backend, browser, build-mode, accessibility, and privacy contracts.

## Alternatives rejected

- A hosted FastAPI service would add request-time access, cost, and operational surface that the public decision does not need.
- Pages Functions would turn every data read into billed compute without improving the two-window product.
- Git-connected deployment would couple provider setup to separately governed history and push actions.

## Not done

No private warehouse, source archive, subscriber record, model artifact, scenario curve, server function, custom domain, Git mutation, or paid resource was deployed.

## Changed

The web client reads the same response envelopes from a generated static snapshot. The release build emits governed CSV files and security headers. The product is live on Cloudflare Pages, and GitHub Actions verifies both required quality jobs. Release records identify the production URL, zero-compute policy, checks, and rollback mechanism.
