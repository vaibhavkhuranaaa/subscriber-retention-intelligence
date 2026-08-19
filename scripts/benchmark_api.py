#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from retention_api.main import create_app


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(len(ordered) * fraction))]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=25)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    client = TestClient(create_app("private"))
    requests = [
        ("/api/v1/overview?label_window=2017-03", None),
        ("/api/v1/cohorts?label_window=2017-03&limit=48", None),
        ("/api/v1/segments?label_window=2017-03&dimension=engagement", None),
        ("/api/v1/segments?label_window=2017-03&dimension=payment_method", None),
        ("/api/v1/definitions", None),
        ("/api/v1/subscribers?label_window=2017-03&limit=20", None),
    ]
    token = client.get(requests[-1][0]).json()["data"][0]["subscriber_token"].lower()
    requests.extend(
        [
            (f"/api/v1/subscribers/{token}?label_window=2017-03", None),
            (
                "POST /api/v1/scenario",
                {
                    "capacity": 50000,
                    "minimum_score": 0.1,
                    "contact_cost": 0.5,
                    "offer_cost": 2.0,
                    "assumed_lift": 0.12,
                    "lift_uncertainty": 0.04,
                },
            ),
        ]
    )
    timings: dict[str, list[float]] = {route: [] for route, _ in requests}
    for _ in range(arguments.iterations):
        for route, payload in requests:
            started = time.perf_counter()
            response = (
                client.post("/api/v1/scenario", json=payload) if payload else client.get(route)
            )
            elapsed = (time.perf_counter() - started) * 1000
            if response.status_code != 200:
                raise RuntimeError(f"{route} returned {response.status_code}")
            timings[route].append(elapsed)
    all_values = [value for values in timings.values() for value in values]
    report = {
        "status": "passed",
        "iterations_per_route": arguments.iterations,
        "request_count": len(all_values),
        "overall_p95_ms": percentile(all_values, 0.95),
        "overall_median_ms": statistics.median(all_values),
        "routes": {
            route: {
                "p95_ms": percentile(values, 0.95),
                "median_ms": statistics.median(values),
                "max_ms": max(values),
            }
            for route, values in timings.items()
        },
    }
    rendered = json.dumps(report, indent=2)
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(rendered + "\n")
    print(rendered)
    return 0 if report["overall_p95_ms"] <= 500 else 1


if __name__ == "__main__":
    raise SystemExit(main())
