# Decision 0011: publish an evidence-backed portfolio case study

## Status

Accepted on 2026-08-19.

## Decision

Publish a versioned portfolio manifest, release contract, architecture source, and written case study from the public repository. Admit the project to the existing portfolio only after the live dashboard reports the exact current `main` commit through an anonymous static verification file.

## Why

The project is already public, deployed, and independently verifiable. A source-owned manifest keeps portfolio claims tied to exact evidence instead of duplicating prose in another repository. Exact-SHA admission prevents the portfolio from presenting a newer repository state than the deployed product.

## Alternatives rejected

- Manually copying project claims into the portfolio would create an unsynchronized second source of truth.
- Publishing before the dashboard reports the source commit would weaken deployment provenance.
- Adding a server only for release verification would add cost and operational surface to a static product.

## Not done

No private dataset, private subscriber view, model artifact, publication salt, or private delivery record enters the portfolio package.

## Changed

The repository now owns its portfolio contract and case study. The existing zero-cost portfolio workflow can discover and publish the project automatically after live verification succeeds.
