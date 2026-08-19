#!/usr/bin/env python3
"""Build replayable private detailed facts from compressed source archives."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import statistics
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from profile_sources import (
    GIB,
    archive_header,
    archive_listing,
    sql_columns,
    validate_contract,
)

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = Path(
    os.getenv("RETENTION_EVIDENCE_DIR", ROOT.parent / f"{ROOT.name}-ops" / "evidence")
)


def require_disk(path: Path, reserve_bytes: int, available_bytes: int | None = None) -> int:
    available = shutil.disk_usage(path).free if available_bytes is None else available_bytes
    if available < reserve_bytes:
        raise RuntimeError(
            f"free disk {available / GIB:.3f} GiB is below {reserve_bytes / GIB:.3f} GiB reserve"
        )
    return available


def validate_header(expected: str, observed: str) -> None:
    if observed != expected:
        raise RuntimeError(f"header drift: expected {expected!r}, observed {observed!r}")


def source_fingerprint(contract_path: Path, source_dir: Path, archives: list[dict]) -> str:
    digest = hashlib.sha256(contract_path.read_bytes())
    for declaration in archives:
        if not declaration["selected"]:
            continue
        archive = source_dir / declaration["name"]
        stat = archive.stat()
        digest.update(f"{declaration['name']}|{stat.st_size}|{stat.st_mtime_ns}".encode())
    return digest.hexdigest()


def subscriber_token_expression() -> str:
    return "unhex(substr(sha256(msno), 1, 24))"


def allocated_bytes(path: Path) -> int:
    return sum(item.stat().st_blocks * 512 for item in path.rglob("*") if item.is_file())


def verify_existing_output(output_dir: Path, controls: dict) -> None:
    required = (
        output_dir / "dim_member" / "data.parquet",
        output_dir / "fact_subscription_transaction" / "data.parquet",
        output_dir / "fact_churn_label",
        output_dir / "fact_listening_day",
    )
    if not all(path.exists() for path in required):
        raise RuntimeError("existing fact output is incomplete")
    parquet_bytes = sum(item.stat().st_blocks * 512 for item in output_dir.rglob("*.parquet"))
    if parquet_bytes != controls["storage"]["allocated_bytes"]:
        raise RuntimeError("existing fact output allocated bytes changed")
    if list(output_dir.rglob("*.csv")):
        raise RuntimeError("expanded CSV detected in fact output")


def read_controls(output_dir: Path) -> dict | None:
    path = output_dir / "controls.json"
    return json.loads(path.read_text()) if path.is_file() else None


def promote(stage: Path, output: Path, fail_after_backup: bool = False) -> None:
    backup = output.with_name(f".{output.name}-backup")
    if backup.exists() and not output.exists():
        os.replace(backup, output)
    elif backup.exists():
        shutil.rmtree(backup)
    if output.exists():
        os.replace(output, backup)
    try:
        if fail_after_backup:
            raise RuntimeError("injected promotion failure")
        os.replace(stage, output)
    except Exception:
        if backup.exists() and not output.exists():
            os.replace(backup, output)
        raise
    if backup.exists():
        shutil.rmtree(backup)


def duckdb_connection(temp_dir: Path):
    import duckdb

    temp_dir.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect()
    escaped = str(temp_dir).replace("'", "''")
    connection.execute("SET memory_limit = '8GB'")
    connection.execute(f"SET temp_directory = '{escaped}'")
    return connection


def csv_relation(fields: dict) -> str:
    return (
        "read_csv('/dev/stdin', header=true, auto_detect=false, delim=',', quote='', "
        f"escape='', strict_mode=true, null_padding=false, columns={sql_columns(fields)})"
    )


def date_expression(field: str) -> str:
    return f"strptime(cast({field} AS VARCHAR), '%Y%m%d')::DATE"


def conversion_query(contract: dict, family: str, source_version: str, label_window: str) -> str:
    relation = csv_relation(contract["families"][family]["fields"])
    token = f"{subscriber_token_expression()} AS subscriber_token"
    if family == "members":
        registration = (
            "CASE WHEN registration_init_time IS NULL OR registration_init_time = 0 THEN NULL "
            f"ELSE {date_expression('registration_init_time')} END AS registration_date"
        )
        return (
            f"SELECT {token}, city AS city_code, bd AS age_reported, nullif(gender, '') AS gender, "
            f"nullif(registered_via, -1) AS registration_method_code, {registration} FROM {relation}"
        )
    if family == "labels":
        return (
            f"SELECT {token}, '{label_window}' AS label_window, cast(is_churn AS UTINYINT) AS is_churn "
            f"FROM {relation}"
        )
    if family == "transactions":
        return (
            f"SELECT {token}, payment_method_id, payment_plan_days, plan_list_price, "
            "actual_amount_paid, cast(is_auto_renew AS UTINYINT) AS is_auto_renew, "
            f"{date_expression('transaction_date')} AS transaction_date, "
            f"{date_expression('membership_expire_date')} AS membership_expire_date, "
            f"cast(is_cancel AS UTINYINT) AS is_cancel, '{source_version}' AS source_version FROM {relation}"
        )
    if family == "listening":
        activity_date = date_expression("date")
        return (
            f"SELECT {token}, {activity_date} AS activity_date, cast(date / 100 AS INTEGER) AS activity_month, "
            "num_25, num_50, num_75, num_985, num_100, num_unq, greatest(total_secs, 0) AS total_secs, "
            "total_secs < 0 AS total_secs_was_negative, "
            f"'{source_version}' AS source_version FROM {relation}"
        )
    raise ValueError(f"unsupported family: {family}")


def convert_stream(
    contract: dict,
    family: str,
    output: Path,
    source_version: str,
    label_window: str,
) -> None:
    import duckdb

    query = conversion_query(contract, family, source_version, label_window)
    escaped = str(output).replace("'", "''")
    options = "FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 100000"
    if family == "listening":
        options += ", PARTITION_BY(activity_month), FILENAME_PATTERN 'part_{uuid}'"
    duckdb.sql(f"COPY ({query}) TO '{escaped}' ({options})")
    pattern = f"{escaped}/**/*.parquet" if family == "listening" else escaped
    rows = duckdb.sql(
        f"SELECT count(*) FROM read_parquet('{pattern}', hive_partitioning=true)"
    ).fetchone()[0]
    print(json.dumps({"rows": rows}))


def run_conversion(
    bsdtar: str,
    archive: Path,
    contract_path: Path,
    declaration: dict,
    output: Path,
    reserve_bytes: int,
) -> int:
    producer = subprocess.Popen(
        [bsdtar, "-xOf", str(archive)], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    assert producer.stdout
    worker = subprocess.Popen(
        [
            sys.executable,
            __file__,
            "--contract",
            str(contract_path),
            "--convert-stream",
            declaration["family"],
            "--convert-output",
            str(output),
            "--source-version",
            declaration.get("version", ""),
            "--label-window",
            declaration.get("window", ""),
        ],
        stdin=producer.stdout,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    producer.stdout.close()
    while worker.poll() is None:
        if shutil.disk_usage(output.parent).free < reserve_bytes:
            worker.terminate()
            producer.terminate()
            worker.wait()
            producer.wait()
            raise RuntimeError("free disk fell below configured reserve during archive conversion")
        time.sleep(1)
    worker_stdout, worker_stderr = worker.communicate()
    producer_stderr = producer.stderr.read().decode() if producer.stderr else ""
    producer_code = producer.wait()
    if worker.returncode:
        raise RuntimeError(worker_stderr.strip() or f"conversion failed: {archive.name}")
    if producer_code:
        raise RuntimeError(producer_stderr.strip() or f"bsdtar failed: {archive.name}")
    return json.loads(worker_stdout)["rows"]


def assert_unique(connection, parquet_pattern: str, columns: tuple[str, ...], label: str) -> None:
    escaped = parquet_pattern.replace("'", "''")
    expression = ", ".join(columns)
    total, unique = connection.execute(
        f"SELECT count(*), count(DISTINCT ({expression})) FROM read_parquet('{escaped}', hive_partitioning=true)"
    ).fetchone()
    if total != unique:
        raise RuntimeError(f"{label}: {total - unique} duplicate keys")


def validate_members(connection, path: Path) -> dict:
    escaped = str(path).replace("'", "''")
    row = connection.execute(
        "SELECT count(*), count(DISTINCT subscriber_token), count(*) FILTER (WHERE subscriber_token IS NULL "
        "OR city_code < 0 OR registration_method_code < 0 OR gender NOT IN ('female', 'male')) "
        "FROM read_parquet('" + escaped + "')"
    ).fetchone()
    if row[0] != row[1] or row[2]:
        raise RuntimeError(
            f"member controls failed: rows={row[0]} unique={row[1]} invalid={row[2]}"
        )
    nulls = connection.execute(
        f"SELECT count(*) FILTER (WHERE city_code IS NULL), count(*) FILTER (WHERE age_reported IS NULL), "
        "count(*) FILTER (WHERE gender IS NULL), count(*) FILTER (WHERE registration_method_code IS NULL), "
        f"count(*) FILTER (WHERE registration_date IS NULL) FROM read_parquet('{escaped}')"
    ).fetchone()
    return {
        "rows": row[0],
        "unique_subscribers": row[1],
        "invalid_rows": row[2],
        "null_counts": dict(
            zip(
                (
                    "city_code",
                    "age_reported",
                    "gender",
                    "registration_method_code",
                    "registration_date",
                ),
                nulls,
                strict=True,
            )
        ),
    }


def validate_labels(connection, pattern: str) -> dict:
    escaped = pattern.replace("'", "''")
    rows = connection.execute(
        f"SELECT label_window, count(*), count(DISTINCT subscriber_token), sum(is_churn), "
        f"count(*) FILTER (WHERE subscriber_token IS NULL OR is_churn NOT IN (0, 1)) "
        f"FROM read_parquet('{escaped}', hive_partitioning=true) GROUP BY label_window ORDER BY label_window"
    ).fetchall()
    if any(total != unique or invalid for _, total, unique, _, invalid in rows):
        raise RuntimeError(f"label controls failed: {rows}")
    return {
        window: {"rows": total, "unique_subscribers": unique, "churn_rows": churn}
        for window, total, unique, churn, _ in rows
    }


def build_transactions(connection, raw_pattern: str, output: Path) -> dict:
    escaped_raw = raw_pattern.replace("'", "''")
    escaped_output = str(output).replace("'", "''")
    invalid = connection.execute(
        f"SELECT count(*) FROM read_parquet('{escaped_raw}') WHERE subscriber_token IS NULL "
        "OR payment_method_id <= 0 OR payment_plan_days < 0 OR plan_list_price < 0 "
        "OR actual_amount_paid < 0 OR is_auto_renew NOT IN (0, 1) OR is_cancel NOT IN (0, 1)"
    ).fetchone()[0]
    if invalid:
        raise RuntimeError(f"transactions: {invalid} invalid rows")
    columns = (
        "subscriber_token, payment_method_id, payment_plan_days, plan_list_price, "
        "actual_amount_paid, is_auto_renew, transaction_date, membership_expire_date, is_cancel"
    )
    event = "unhex(substr(sha256(concat_ws('|', " + columns + ")), 1, 24))"
    within_duplicates = connection.execute(
        f"SELECT coalesce(sum(rows - 1), 0) FROM (SELECT source_version, {columns}, count(*) AS rows "
        f"FROM read_parquet('{escaped_raw}') GROUP BY source_version, {columns})"
    ).fetchone()[0]
    cross_duplicates = connection.execute(
        f"SELECT count(*) FROM (SELECT {columns} FROM read_parquet('{escaped_raw}') "
        f"GROUP BY {columns} HAVING count(DISTINCT source_version) > 1)"
    ).fetchone()[0]
    output.parent.mkdir(parents=True, exist_ok=True)
    connection.execute(
        f"COPY (SELECT {event} AS event_key, {columns}, "
        "CASE count(DISTINCT source_version) WHEN 1 THEN min(source_version) ELSE 'v1+v2' END AS source_versions "
        f"FROM read_parquet('{escaped_raw}') GROUP BY {columns}) TO '{escaped_output}' "
        "(FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 100000)"
    )
    source = connection.execute(
        f"SELECT count(*), sum(plan_list_price), sum(actual_amount_paid) FROM read_parquet('{escaped_raw}')"
    ).fetchone()
    accepted = connection.execute(
        f"SELECT count(*), count(DISTINCT event_key), sum(plan_list_price), sum(actual_amount_paid) FROM read_parquet('{escaped_output}')"
    ).fetchone()
    if accepted[0] != accepted[1]:
        raise RuntimeError("transaction event keys are not unique")
    return {
        "source_rows": source[0],
        "accepted_rows": accepted[0],
        "duplicate_rows_removed": source[0] - accepted[0],
        "within_version_duplicate_rows_removed": within_duplicates,
        "cross_version_duplicate_rows_removed": cross_duplicates,
        "source_plan_list_total": source[1],
        "accepted_plan_list_total": accepted[2],
        "source_gross_receipts": source[2],
        "accepted_gross_receipts": accepted[3],
    }


def validate_listening(connection, root: Path) -> dict:
    controls: dict[str, dict] = {}
    total_rows = 0
    total_seconds = 0.0
    for version_dir in sorted(root.glob("source_version=*")):
        version = version_dir.name.split("=", 1)[1]
        version_rows = 0
        version_measures = {
            name: 0.0
            for name in (
                "num_25",
                "num_50",
                "num_75",
                "num_985",
                "num_100",
                "num_unq",
                "total_secs",
            )
        }
        corrected_durations = 0
        minimum = maximum = None
        for month_dir in sorted(version_dir.glob("activity_month=*")):
            pattern = str(month_dir / "*.parquet").replace("'", "''")
            row = connection.execute(
                f"SELECT count(*), count(DISTINCT (subscriber_token, activity_date)), "
                "count(*) FILTER (WHERE subscriber_token IS NULL OR num_25 < 0 OR num_50 < 0 "
                "OR num_75 < 0 OR num_985 < 0 OR num_100 < 0 OR num_unq < 0 OR total_secs < 0), "
                "sum(num_25), sum(num_50), sum(num_75), sum(num_985), sum(num_100), sum(num_unq), "
                f"sum(total_secs), count(*) FILTER (WHERE total_secs_was_negative), min(activity_date), max(activity_date) FROM read_parquet('{pattern}')"
            ).fetchone()
            if row[0] != row[1] or row[2]:
                raise RuntimeError(
                    f"listening {version}/{month_dir.name}: duplicates={row[0] - row[1]} invalid={row[2]}"
                )
            version_rows += row[0]
            for index, name in enumerate(version_measures, start=3):
                version_measures[name] += float(row[index] or 0)
            corrected_durations += row[10]
            minimum = row[11] if minimum is None or row[11] < minimum else minimum
            maximum = row[12] if maximum is None or row[12] > maximum else maximum
        controls[version] = {
            "rows": version_rows,
            "measure_totals": version_measures,
            "negative_duration_rows_canonicalized": corrected_durations,
            "min_activity_date": str(minimum),
            "max_activity_date": str(maximum),
        }
        total_rows += version_rows
        total_seconds += version_measures["total_secs"]
    if (
        set(controls) == {"v1", "v2"}
        and controls["v1"]["max_activity_date"] >= controls["v2"]["min_activity_date"]
    ):
        raise RuntimeError("listening version date ranges overlap")
    return {"rows": total_rows, "total_seconds": total_seconds, "versions": controls}


def write_report(path: Path, controls: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(controls, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, default=Path("contracts/sources.json"))
    parser.add_argument(
        "--source-manifest", type=Path, default=EVIDENCE_DIR / "m2-source-manifest.json"
    )
    parser.add_argument("--source-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--fail-after-backup", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--convert-stream")
    parser.add_argument("--convert-output", type=Path)
    parser.add_argument("--source-version", default="")
    parser.add_argument("--label-window", default="")
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text())

    if args.convert_stream:
        if not args.convert_output:
            parser.error("--convert-output is required")
        convert_stream(
            contract,
            args.convert_stream,
            args.convert_output,
            args.source_version,
            args.label_window,
        )
        return 0
    if not all((args.source_dir, args.output_dir, args.report)):
        parser.error("--source-dir, --output-dir, and --report are required")

    validate_contract(contract)
    source_manifest = json.loads(args.source_manifest.read_text())
    expected_rows = {
        item["name"]: item["profile"]["row_count"]
        for item in source_manifest["archives"]
        if item["selected"]
    }
    expected_bytes = {
        item["name"]: item["compressed_bytes"]
        for item in source_manifest["archives"]
        if item["selected"]
    }
    archives = [item for item in contract["archives"] if item["selected"]]
    fingerprint = source_fingerprint(args.contract, args.source_dir, archives)
    previous = read_controls(args.output_dir)
    if previous and previous.get("source_fingerprint") == fingerprint and not args.force:
        verify_existing_output(args.output_dir, previous)
        replay = {
            **previous,
            "last_replay": {
                "status": "no_op",
                "verified_at": datetime.now(UTC).isoformat(),
                "source_fingerprint_match": True,
            },
        }
        write_report(args.report, replay)
        print(json.dumps({"status": "no_op", "rows": previous["reconciliation"]["output_rows"]}))
        return 0

    bsdtar = shutil.which("bsdtar")
    if not bsdtar:
        raise SystemExit("bsdtar is required")
    reserve = int(contract["storage"]["free_disk_reserve_gib"] * GIB)
    free_before = require_disk(args.source_dir, reserve)
    projected_stage_bytes = source_manifest["storage_pilot"]["projected_full_parquet_bytes"]
    require_disk(args.source_dir, reserve + projected_stage_bytes)
    started = time.monotonic()
    stage = args.output_dir.with_name(f".{args.output_dir.name}-stage-{uuid.uuid4().hex}")
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    try:
        raw_transactions = stage / ".raw-transactions"
        raw_transactions.mkdir()
        outputs = {
            "members_v3.csv.7z": stage / "dim_member" / "data.parquet",
            "train.csv.7z": stage / "fact_churn_label" / "window=2017-02" / "data.parquet",
            "train_v2.csv.7z": stage / "fact_churn_label" / "window=2017-03" / "data.parquet",
            "transactions.csv.7z": raw_transactions / "v1.parquet",
            "transactions_v2.csv.7z": raw_transactions / "v2.parquet",
            "user_logs.csv.7z": stage / "fact_listening_day" / "source_version=v1",
            "user_logs_v2.csv.7z": stage / "fact_listening_day" / "source_version=v2",
        }
        converted: dict[str, int] = {}
        for declaration in archives:
            require_disk(args.source_dir, reserve)
            archive = args.source_dir / declaration["name"]
            if archive.stat().st_size != expected_bytes[declaration["name"]]:
                raise RuntimeError(f"archive byte drift: {declaration['name']}")
            member, _ = archive_listing(bsdtar, archive)
            if member != declaration["member"]:
                raise RuntimeError(f"archive member drift: {declaration['name']}")
            expected_header = ",".join(contract["families"][declaration["family"]]["fields"])
            validate_header(expected_header, archive_header(bsdtar, archive))
            output = outputs[declaration["name"]]
            output.parent.mkdir(parents=True, exist_ok=True)
            rows = run_conversion(bsdtar, archive, args.contract, declaration, output, reserve)
            if rows != expected_rows[declaration["name"]]:
                raise RuntimeError(
                    f"row drift {declaration['name']}: expected {expected_rows[declaration['name']]}, got {rows}"
                )
            converted[declaration["name"]] = rows

        connection = duckdb_connection(stage / ".duckdb-temp")
        members = validate_members(connection, outputs["members_v3.csv.7z"])
        labels = validate_labels(connection, str(stage / "fact_churn_label" / "**/*.parquet"))
        transactions = build_transactions(
            connection,
            str(raw_transactions / "*.parquet"),
            stage / "fact_subscription_transaction" / "data.parquet",
        )
        listening = validate_listening(connection, stage / "fact_listening_day")
        connection.close()
        shutil.rmtree(raw_transactions)
        shutil.rmtree(stage / ".duckdb-temp", ignore_errors=True)

        expected_member = converted["members_v3.csv.7z"]
        expected_labels = converted["train.csv.7z"] + converted["train_v2.csv.7z"]
        expected_listening = converted["user_logs.csv.7z"] + converted["user_logs_v2.csv.7z"]
        accepted_source_rows = (
            expected_member + expected_labels + expected_listening + transactions["accepted_rows"]
        )
        output_rows = (
            members["rows"]
            + sum(item["rows"] for item in labels.values())
            + listening["rows"]
            + transactions["accepted_rows"]
        )
        ratio = output_rows / accepted_source_rows
        if ratio != 1.0:
            raise RuntimeError(f"row reconciliation failed: {output_rows}/{accepted_source_rows}")
        require_disk(args.source_dir, reserve)
        elapsed_minutes = (time.monotonic() - started) / 60
        runtime_history = list((previous or {}).get("runtime", {}).get("full_run_minutes", []))
        runtime_history.append(elapsed_minutes)
        footprint = allocated_bytes(stage) / GIB
        forecast = footprint * (1 + contract["storage"]["downstream_allowance_fraction"])
        if forecast > contract["storage"]["projected_derived_limit_gib"]:
            raise RuntimeError(
                f"fact plus allowance footprint {forecast:.3f} GiB exceeds 11 GiB limit"
            )
        controls = {
            "version": 1,
            "status": "passed",
            "generated_at": datetime.now(UTC).isoformat(),
            "source_fingerprint": fingerprint,
            "tooling": {
                "duckdb": __import__("duckdb").__version__,
                "bsdtar": subprocess.run(
                    [bsdtar, "--version"], text=True, capture_output=True
                ).stdout.strip(),
            },
            "preflight": {
                "free_bytes_before": free_before,
                "free_bytes_before_promotion": shutil.disk_usage(args.source_dir).free,
                "reserve_bytes": reserve,
                "projected_stage_bytes": projected_stage_bytes,
            },
            "converted_source_rows": converted,
            "facts": {
                "member": members,
                "labels": labels,
                "transactions": transactions,
                "listening": listening,
            },
            "reconciliation": {
                "accepted_source_rows": accepted_source_rows,
                "output_rows": output_rows,
                "ratio": ratio,
            },
            "runtime": {
                "full_run_minutes": runtime_history,
                "median_minutes": statistics.median(runtime_history),
                "maximum_minutes": max(runtime_history),
            },
            "storage": {
                "allocated_bytes": round(footprint * GIB),
                "allocated_gib": footprint,
                "downstream_allowance_fraction": contract["storage"][
                    "downstream_allowance_fraction"
                ],
                "forecast_with_allowance_gib": forecast,
                "expanded_csv_retained": False,
            },
            "privacy": {
                "source_identifier_columns": 0,
                "subscriber_token": "96-bit SHA-256 prefix",
                "collision_check": "distinct token count equals source grain uniqueness controls",
                "public_output": False,
            },
            "limitations": [
                "Archive replay fingerprint uses immutable file size and modification time plus contract content, not a full archive content digest.",
                "Byte-identical transaction events have no source event ID and are treated as duplicates.",
                "Private subscriber and event keys use 96-bit SHA-256 prefixes; collision checks fail promotion and birthday collision risk at observed scale is approximately 3e-16.",
            ],
        }
        (stage / "controls.json").write_text(json.dumps(controls, indent=2) + "\n")
        promote(stage, args.output_dir, args.fail_after_backup)
        write_report(args.report, controls)
        print(
            json.dumps(
                {
                    "status": "passed",
                    "minutes": elapsed_minutes,
                    "rows": output_rows,
                    "allocated_gib": footprint,
                },
                indent=2,
            )
        )
        return 0
    except BaseException:
        if stage.exists():
            shutil.rmtree(stage)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
