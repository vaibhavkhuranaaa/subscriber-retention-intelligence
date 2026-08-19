#!/usr/bin/env python3
"""Build and atomically promote the resource-bounded dbt warehouse."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path

from reconcile_semantics import reconcile

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = Path(
    os.getenv("RETENTION_EVIDENCE_DIR", ROOT.parent / f"{ROOT.name}-ops" / "evidence")
)
PRIVATE_DIR = Path(
    os.getenv("RETENTION_PRIVATE_DIR", ROOT.parent / f"{ROOT.name}-ops" / "data/private")
)
GIB = 1024**3
RESERVE_BYTES = 30 * GIB
TOTAL_STORAGE_LIMIT_BYTES = 11 * GIB


def allocated_bytes(path: Path) -> int:
    return path.stat().st_blocks * 512


def assert_storage(facts_bytes: int, warehouse_bytes: int) -> None:
    if facts_bytes + warehouse_bytes > TOTAL_STORAGE_LIMIT_BYTES:
        raise RuntimeError("facts plus semantic warehouse exceed 11 GiB")


def build(repository: Path, facts: Path, warehouse: Path, report_path: Path) -> dict:
    free_before = shutil.disk_usage(repository).free
    if free_before < RESERVE_BYTES:
        raise RuntimeError("free disk is below 30 GiB reserve")

    run_id = uuid.uuid4().hex[:12]
    warehouse.parent.mkdir(parents=True, exist_ok=True)
    staging = warehouse.parent / f"{warehouse.stem}_staging_{run_id}.duckdb"
    log_path = Path("/private/tmp") / f"subscriber-retention-dbt-{run_id}.log"
    environment = os.environ.copy()
    environment.update(
        {
            "RETENTION_FACTS_DIR": str(facts),
            "RETENTION_WAREHOUSE_PATH": str(staging),
        }
    )
    command = [
        "uv",
        "tool",
        "run",
        "--from",
        "dbt-duckdb",
        "dbt",
        "build",
        "--profiles-dir",
        ".",
        "--no-use-colors",
    ]
    started = time.monotonic()
    minimum_free = free_before
    process = None
    try:
        with log_path.open("w") as log:
            process = subprocess.Popen(
                command,
                cwd=repository,
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
            )
            while process.poll() is None:
                free = shutil.disk_usage(repository).free
                minimum_free = min(minimum_free, free)
                if free < RESERVE_BYTES:
                    process.terminate()
                    process.wait(timeout=30)
                    raise RuntimeError("dbt build stopped below 30 GiB free-disk reserve")
                time.sleep(1)
        output = log_path.read_text()
        if process.returncode:
            raise RuntimeError(f"dbt build failed\n{output[-4000:]}")

        facts_bytes = json.loads((facts / "controls.json").read_text())["storage"][
            "allocated_bytes"
        ]
        warehouse_bytes = allocated_bytes(staging)
        assert_storage(facts_bytes, warehouse_bytes)
        reconciliation = reconcile(staging, facts)
        if reconciliation["status"] != "passed":
            raise RuntimeError("independent semantic reconciliation failed")

        backup = warehouse.with_suffix(".duckdb.backup")
        if backup.exists():
            backup.unlink()
        if warehouse.exists():
            warehouse.replace(backup)
        try:
            staging.replace(warehouse)
        except Exception:
            if backup.exists():
                backup.replace(warehouse)
            raise
        if backup.exists():
            backup.unlink()

        report = {
            "status": "passed",
            "runtime_minutes": (time.monotonic() - started) / 60,
            "resource_limits": {"threads": 1, "memory_gib": 4, "reserve_gib": 30},
            "free_gib_before": free_before / GIB,
            "minimum_free_gib": minimum_free / GIB,
            "facts_allocated_gib": facts_bytes / GIB,
            "warehouse_allocated_gib": warehouse_bytes / GIB,
            "combined_allocated_gib": (facts_bytes + warehouse_bytes) / GIB,
            "reconciliation": reconciliation,
            "dbt_output": output,
        }
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2) + "\n")
        return report
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
        for path in (staging, Path(f"{staging}.wal")):
            if path.exists():
                path.unlink()
        temp_directory = Path(f"{staging}.tmp")
        if temp_directory.exists():
            shutil.rmtree(temp_directory)
        if log_path.exists():
            log_path.unlink()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    parser.add_argument("--facts", type=Path, default=PRIVATE_DIR / "facts")
    parser.add_argument(
        "--warehouse",
        type=Path,
        default=PRIVATE_DIR / "warehouse/retention.duckdb",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=EVIDENCE_DIR / "m4-dbt-build.json",
    )
    arguments = parser.parse_args()
    report = build(
        arguments.repository.resolve(),
        arguments.facts.resolve(),
        arguments.warehouse.resolve(),
        arguments.report.resolve(),
    )
    print(
        json.dumps(
            {key: value for key, value in report.items() if key != "dbt_output"},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
