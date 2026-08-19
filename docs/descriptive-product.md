# Descriptive retention product

The local product is a historical retention evidence docket over the governed M4 marts. It supports February and March label windows, executive movement, renewal cohorts, engagement and subscription segments, metric definitions, bounded exports, and private pseudonymous subscriber journeys.

## Run locally

Build the client once, then serve API and static assets with one worker:

```sh
cd web
npm ci
npm run build
cd ..
.venv/bin/uvicorn retention_api.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Open `http://127.0.0.1:8000`. Docker is not required.

For aggregate-only mode, set `RETENTION_MODE=public` before starting Uvicorn. Public mode does not register either subscriber route. It does not merely hide row-level controls.

## Interface contract

- `/api/v1/status` reports historical freshness, release, mode, and available windows.
- `/api/v1/overview`, `/cohorts`, `/segments`, and `/definitions` query governed marts.
- `/api/v1/export/{overview|cohorts|segments}.csv` returns bounded aggregate data.
- `/api/v1/subscribers` and `/api/v1/subscribers/{token}` exist only in private mode.
- Window, dimension, token, and limit inputs are allow-listed or bounded.
- Every DuckDB request is read-only and limited to one thread.

The private inspection population contains at most 500 records per label window, ordered by 90-day gross receipts for review. It is not a risk score, intervention queue, or causal recommendation. A journey returns at most 24 recent subscription events plus a 180-day monthly listening summary.

## Verify

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/benchmark_api.py --iterations 25
cd web
npm run build
npx playwright test
```

The browser suite covers desktop and 390-pixel mobile layouts, keyboard skip navigation, observed-window switching, private journey loading, console errors, horizontal overflow, and serious/critical axe findings.
