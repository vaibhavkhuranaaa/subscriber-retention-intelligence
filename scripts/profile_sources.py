#!/usr/bin/env python3
"""Validate source contracts and stream archive profiles plus Parquet pilots."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

GIB = 1024**3
REQUIRED_FIELD_KEYS = {
    "type",
    "null_policy",
    "allowed",
    "sensitivity",
    "downstream_owner",
}
DATE_FIELDS = {
    "members": ["registration_init_time"],
    "transactions": ["transaction_date", "membership_expire_date"],
    "listening": ["date"],
    "labels": [],
}


def validate_contract(contract: dict) -> tuple[int, int]:
    required = complete = 0
    archive_names: set[str] = set()
    for family_name, family in contract["families"].items():
        fields = family["fields"]
        if not fields or not family["duplicate_key"]:
            raise ValueError(f"{family_name}: fields and duplicate_key are required")
        for name, declaration in fields.items():
            required += 1
            missing = REQUIRED_FIELD_KEYS - declaration.keys()
            if missing:
                raise ValueError(f"{family_name}.{name}: missing {sorted(missing)}")
            if declaration["sensitivity"] not in contract["privacy"]:
                raise ValueError(f"{family_name}.{name}: unknown sensitivity")
            complete += 1
    for archive in contract["archives"]:
        if archive["name"] in archive_names:
            raise ValueError(f"duplicate archive contract: {archive['name']}")
        archive_names.add(archive["name"])
        if archive["family"] not in contract["families"]:
            raise ValueError(f"{archive['name']}: unknown family")
        if not archive["selected"] and not archive.get("exclusion"):
            raise ValueError(f"{archive['name']}: excluded archive needs a reason")
    return complete, required


def churn_from_gap(first_valid_renewal_gap_days: int | None) -> int:
    return int(first_valid_renewal_gap_days is None or first_valid_renewal_gap_days >= 30)


def transaction_order_key(row: dict) -> tuple:
    plan = (row["plan_list_price"], row["payment_plan_days"], row["payment_method_id"])
    cancel = row["is_cancel"]
    expiry = row["membership_expire_date"]
    same_action_expiry = expiry if cancel == 0 else -expiry
    return (
        row["transaction_date"],
        tuple(-value for value in plan),
        cancel,
        same_action_expiry,
    )


def projected_storage_gib(projected_parquet_bytes: int, allowance_fraction: float) -> float:
    return projected_parquet_bytes * (1 + allowance_fraction) / GIB


def sql_columns(fields: dict) -> str:
    pairs = ", ".join(f"'{name}': '{value['type']}'" for name, value in fields.items())
    return "{" + pairs + "}"


def scan_stream(contract: dict, family_name: str) -> None:
    import duckdb

    fields = contract["families"][family_name]["fields"]
    stats = [
        "count(*) AS row_count",
        "approx_count_distinct(msno) AS approximate_subscribers",
    ]
    for field in DATE_FIELDS[family_name]:
        stats.extend((f"min({field}) AS min_{field}", f"max({field}) AS max_{field}"))
    if family_name == "labels":
        stats.append("sum(is_churn) AS churn_rows")
    null_terms = " + ".join(f"count(*) FILTER (WHERE {field} IS NULL)" for field in fields)
    stats.append(f"({null_terms}) AS null_cells")
    query = (
        f"SELECT {', '.join(stats)} FROM read_csv('/dev/stdin', header=true, "
        f"columns={sql_columns(fields)}, auto_detect=false, delim=',', quote='', escape='', strict_mode=true, null_padding=false)"
    )
    result = duckdb.sql(query)
    names = [item[0] for item in result.description]
    print(json.dumps(dict(zip(names, result.fetchone(), strict=True))))


def pilot_stream(contract: dict, family_name: str, output: Path, rows: int) -> None:
    import duckdb

    fields = contract["families"][family_name]["fields"]
    quoted_output = str(output).replace("'", "''")
    query = (
        f"COPY (SELECT * FROM read_csv('/dev/stdin', header=true, columns={sql_columns(fields)}, "
        f"auto_detect=false, delim=',', quote='', escape='', strict_mode=true, null_padding=false) LIMIT {rows}) TO '{quoted_output}' "
        "(FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 100000)"
    )
    duckdb.sql(query)
    written = duckdb.sql(f"SELECT count(*) FROM read_parquet('{quoted_output}')").fetchone()[0]
    print(json.dumps({"rows": written, "bytes": output.stat().st_size}))


def archive_listing(bsdtar: str, archive: Path) -> tuple[str, int]:
    output = subprocess.run(
        [bsdtar, "-tvf", str(archive)], check=True, text=True, capture_output=True
    ).stdout.strip()
    parts = output.split()
    if len(parts) < 9:
        raise RuntimeError(f"unable to parse archive listing: {archive.name}")
    return parts[-1], int(parts[4])


def archive_header(bsdtar: str, archive: Path) -> str:
    producer = subprocess.Popen(
        [bsdtar, "-xOf", str(archive)],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    assert producer.stdout
    header = producer.stdout.readline().decode().rstrip("\r\n")
    producer.stdout.close()
    producer.wait()
    return header


def run_stream_worker(
    bsdtar: str, archive: Path, args: list[str], allow_broken_pipe: bool = False
) -> dict:
    producer = subprocess.Popen(
        [bsdtar, "-xOf", str(archive)], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    assert producer.stdout
    worker = subprocess.run(
        [sys.executable, __file__, *args],
        stdin=producer.stdout,
        text=True,
        capture_output=True,
    )
    producer.stdout.close()
    producer_stderr = producer.stderr.read().decode() if producer.stderr else ""
    producer_code = producer.wait()
    if worker.returncode:
        raise RuntimeError(worker.stderr.strip() or f"stream worker failed for {archive.name}")
    if producer_code and not allow_broken_pipe:
        raise RuntimeError(producer_stderr.strip() or f"bsdtar failed for {archive.name}")
    return json.loads(worker.stdout)


def free_bytes(path: Path) -> int:
    return shutil.disk_usage(path).free


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, default=Path("contracts/sources.json"))
    parser.add_argument("--source-dir", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--pilot-dir", type=Path)
    parser.add_argument("--pilot-rows", type=int, default=200_000)
    parser.add_argument("--scan-stream")
    parser.add_argument("--pilot-stream")
    parser.add_argument("--pilot-output", type=Path)
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text())

    if args.scan_stream:
        scan_stream(contract, args.scan_stream)
        return 0
    if args.pilot_stream:
        if not args.pilot_output:
            parser.error("--pilot-output is required")
        pilot_stream(contract, args.pilot_stream, args.pilot_output, args.pilot_rows)
        return 0
    if not all((args.source_dir, args.output, args.pilot_dir)):
        parser.error("--source-dir, --output, and --pilot-dir are required")

    complete, required = validate_contract(contract)
    bsdtar = shutil.which("bsdtar")
    if not bsdtar:
        raise SystemExit("bsdtar is required")
    reserve = contract["storage"]["free_disk_reserve_gib"] * GIB
    before = free_bytes(args.source_dir)
    if before < reserve:
        raise SystemExit("free disk is below the configured safety reserve")

    args.pilot_dir.mkdir(parents=True, exist_ok=True)
    inventory = []
    projected_parquet_bytes = 0
    for declaration in contract["archives"]:
        archive = args.source_dir / declaration["name"]
        if not archive.is_file():
            raise SystemExit(f"missing archive: {archive.name}")
        member, expanded_bytes = archive_listing(bsdtar, archive)
        if member != declaration["member"]:
            raise SystemExit(f"archive member drift: {archive.name}")
        expected_header = ",".join(contract["families"][declaration["family"]]["fields"])
        observed_header = archive_header(bsdtar, archive)
        if observed_header != expected_header:
            raise SystemExit(f"header drift: {archive.name}: {observed_header}")
        profile = run_stream_worker(
            bsdtar,
            archive,
            ["--contract", str(args.contract), "--scan-stream", declaration["family"]],
        )
        item = {
            **declaration,
            "compressed_bytes": archive.stat().st_size,
            "expanded_bytes": expanded_bytes,
            "header": observed_header.split(","),
            "profile": profile,
            "duplicate_rule": contract["families"][declaration["family"]]["duplicate_key"],
        }
        if declaration["selected"]:
            if free_bytes(args.source_dir) < reserve:
                raise SystemExit("free disk fell below the configured safety reserve")
            pilot_path = args.pilot_dir / declaration["name"].replace(".csv.7z", ".parquet")
            pilot = run_stream_worker(
                bsdtar,
                archive,
                [
                    "--contract",
                    str(args.contract),
                    "--pilot-stream",
                    declaration["family"],
                    "--pilot-output",
                    str(pilot_path),
                    "--pilot-rows",
                    str(args.pilot_rows),
                ],
                allow_broken_pipe=True,
            )
            estimated_sample_csv_bytes = expanded_bytes * pilot["rows"] / profile["row_count"]
            pilot["estimated_sample_csv_bytes"] = round(estimated_sample_csv_bytes)
            pilot["compression_ratio"] = pilot["bytes"] / estimated_sample_csv_bytes
            pilot["projected_full_parquet_bytes"] = round(
                expanded_bytes * pilot["compression_ratio"]
            )
            projected_parquet_bytes += pilot["projected_full_parquet_bytes"]
            item["pilot"] = pilot
        inventory.append(item)

    allowance = contract["storage"]["downstream_allowance_fraction"]
    projected_gib = projected_storage_gib(projected_parquet_bytes, allowance)
    limit = contract["storage"]["projected_derived_limit_gib"]
    if projected_gib > limit:
        raise SystemExit(
            f"projected derived storage {projected_gib:.3f} GiB exceeds {limit:.3f} GiB"
        )
    manifest = {
        "version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "source": contract["source"],
        "tooling": {
            "bsdtar": subprocess.run(
                [bsdtar, "--version"], text=True, capture_output=True
            ).stdout.strip(),
            "duckdb": __import__("duckdb").__version__,
        },
        "preflight": {
            "free_bytes_before": before,
            "free_bytes_after": free_bytes(args.source_dir),
            "reserve_bytes": round(reserve),
        },
        "contract": {
            "complete_fields": complete,
            "required_fields": required,
            "coverage": complete / required,
            "overlap_rules": contract["overlap_rules"],
            "churn_windows": contract["churn_windows"],
            "privacy": contract["privacy"],
        },
        "storage_pilot": {
            "rows_per_archive": args.pilot_rows,
            "codec": contract["storage"]["codec"],
            "projected_full_parquet_bytes": projected_parquet_bytes,
            "downstream_allowance_fraction": allowance,
            "projected_derived_storage_gib": projected_gib,
            "limit_gib": limit,
            "passes": projected_gib <= limit,
            "limitation": "Projection uses per-archive leading-row pilots; M3 measures the full build and may stop on different cardinality or compression.",
        },
        "archives": inventory,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + "\n")
    print(
        json.dumps(
            {
                "archives": len(inventory),
                "contract_coverage": complete / required,
                "projected_derived_storage_gib": projected_gib,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
