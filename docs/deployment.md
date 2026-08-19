# Public deployment

## Boundary

The permanent public product is a static Cloudflare Pages deployment. Its generated snapshot contains only governed `public_*` aggregates. Journeys, subscriber tokens, model scores, intervention scenarios, private facts, and the DuckDB warehouse are not deployed.

The public build uses no Pages Functions or other request-time compute. Static asset delivery is the full serving path, so the request-compute ceiling is zero and recurring infrastructure cost is zero.

## Rebuild

Run from the repository root without Docker:

```sh
.venv/bin/python scripts/build_static_public_release.py --release-id public-m9r
cd web
VITE_RETENTION_STATIC_PUBLIC=1 npm run build
```

The generator reads the semantic warehouse with one DuckDB thread, rejects forbidden private fields, and writes ignored release data under `web/public/data` and `web/public/exports`.

## Deploy

Direct upload does not require a Git provider connection:

```sh
cd web
npx wrangler pages deploy dist \
  --project-name subscriber-retention-intelligence \
  --branch main
```

Production URL: https://subscriber-retention-intelligence.pages.dev/

## Rollback

Cloudflare retains immutable Pages deployments. If a live probe fails, select the last verified deployment in Pages deployment history and promote it. Do not rebuild against private data during incident response.

## Verification

Release verification covers HTTP 200 responses, security headers, public mode, private-navigation absence, zero browser console errors, mobile overflow, governed CSV delivery, minimum public group size 100, and forbidden-field scans. Hosted CI remains a separate publication gate.
