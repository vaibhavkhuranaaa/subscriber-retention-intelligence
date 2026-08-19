from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
WINDOWS = ("2017-02", "2017-03")
DIMENSIONS = ("engagement", "payment_method", "plan_days", "registration_method", "auto_renew")
FORBIDDEN_KEYS = {
    "subscriber_token",
    "msno",
    "user_id",
    "email",
    "phone",
    "address",
    "age_reported",
    "gender",
    "city_code",
    "registration_method_code",
    "model_score",
}


def assert_public(payload: Any) -> None:
    if isinstance(payload, dict):
        overlap = FORBIDDEN_KEYS.intersection(payload)
        if overlap:
            raise ValueError(f"Private fields found in public snapshot: {sorted(overlap)}")
        for value in payload.values():
            assert_public(value)
    elif isinstance(payload, list):
        for value in payload:
            assert_public(value)


def build(output: Path, release_id: str) -> None:
    os.environ["RETENTION_MODE"] = "public"
    os.environ["RETENTION_RELEASE_ID"] = release_id

    from retention_api.main import create_app

    client = TestClient(create_app("public"))

    def read(path: str) -> dict[str, Any]:
        response = client.get(path)
        response.raise_for_status()
        return response.json()

    snapshot = {
        "status": read("/api/v1/status"),
        "overview": {window: read(f"/api/v1/overview?label_window={window}") for window in WINDOWS},
        "cohorts": {
            window: read(f"/api/v1/cohorts?label_window={window}&limit=240") for window in WINDOWS
        },
        "segments": {
            window: {
                dimension: read(f"/api/v1/segments?label_window={window}&dimension={dimension}")
                for dimension in DIMENSIONS
            }
            for window in WINDOWS
        },
        "definitions": read("/api/v1/definitions"),
    }
    assert_public(snapshot)

    data_dir = output / "data"
    export_dir = output / "exports"
    data_dir.mkdir(parents=True, exist_ok=True)
    export_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "public-snapshot.json").write_text(
        json.dumps(snapshot, separators=(",", ":"), sort_keys=True), encoding="utf-8"
    )
    for window in WINDOWS:
        response = client.get(f"/api/v1/export/overview.csv?label_window={window}")
        response.raise_for_status()
        (export_dir / f"retention-overview-{window}.csv").write_bytes(response.content)

    print(
        json.dumps(
            {
                "release_id": release_id,
                "windows": list(WINDOWS),
                "dimensions": list(DIMENSIONS),
                "snapshot_bytes": (data_dir / "public-snapshot.json").stat().st_size,
                "private_fields": 0,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build aggregate-only static release data.")
    parser.add_argument("--output", type=Path, default=ROOT / "web/public")
    parser.add_argument("--release-id", default="public-m9")
    arguments = parser.parse_args()
    build(arguments.output, arguments.release_id)
