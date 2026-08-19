from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import tempfile
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]


def escaped(path: Path) -> str:
    return str(path).replace("'", "''")


def salt_value(path: Path) -> str:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w") as output:
            output.write(secrets.token_hex(32))
    value = path.read_text().strip()
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError("Publication salt must be 32 bytes encoded as lowercase hexadecimal")
    return value


def token(expression: str, salt: str) -> str:
    return f"cast('0x' || substr(sha256(hex({expression}) || '{salt}'), 1, 16) as ubigint)"


def copy(database: duckdb.DuckDBPyConnection, query: str, output: Path) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    result = database.execute(
        f"COPY ({query}) TO '{escaped(output)}' (FORMAT PARQUET, COMPRESSION ZSTD)"
    ).fetchone()
    return int(result[0])


def build(facts: Path, output: Path, salt_file: Path, release_id: str) -> dict:
    if output.exists():
        raise FileExistsError(f"Output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    required = (
        facts / "dim_member/data.parquet",
        facts / "fact_subscription_transaction/data.parquet",
        facts / "fact_churn_label/window=2017-02/data.parquet",
        facts / "fact_churn_label/window=2017-03/data.parquet",
    )
    missing = [str(path) for path in required if not path.exists()]
    listening = sorted((facts / "fact_listening_day").rglob("*.parquet"))
    if missing or not listening:
        raise FileNotFoundError(f"Detailed facts incomplete: {missing or ['listening partitions']}")

    salt = salt_value(salt_file)
    stage = Path(tempfile.mkdtemp(prefix=f".{output.name}-", dir=output.parent))
    database = duckdb.connect()
    database.execute("set threads = 1")
    database.execute("set memory_limit = '4GB'")
    files: list[dict] = []

    def publish(destination: Path, select: str) -> None:
        rows = copy(database, select, stage / destination)
        files.append(
            {
                "path": destination.as_posix(),
                "rows": rows,
                "bytes": (stage / destination).stat().st_size,
            }
        )

    try:
        member_source = escaped(required[0])
        publish(
            Path("member/data.parquet"),
            f"""
            select
                {token('subscriber_token', salt)} as subscriber_key,
                city_code,
                case
                    when age_reported between 10 and 99
                    then cast(floor(age_reported / 10) * 10 as integer)
                    else null
                end as age_band_start,
                case when gender in ('female', 'male') then gender else null end as gender,
                registration_method_code,
                date_trunc('month', registration_date)::date as registration_month
            from read_parquet('{member_source}', hive_partitioning = false)
            """,
        )

        transaction_source = escaped(required[1])
        event_key = token("event_key", salt)
        for part in range(2):
            publish(
                Path(f"subscription_transaction/part={part}/data.parquet"),
                f"""
                select
                    {event_key} as event_key,
                    {token('subscriber_token', salt)} as subscriber_key,
                    payment_method_id,
                    payment_plan_days,
                    plan_list_price,
                    actual_amount_paid,
                    is_auto_renew,
                    transaction_date,
                    membership_expire_date,
                    is_cancel,
                    source_versions
                from read_parquet('{transaction_source}', hive_partitioning = false)
                where {event_key} % 2 = {part}
                """,
            )

        for source in required[2:]:
            window = source.parent.name.split("=", 1)[1]
            publish(
                Path(f"churn_label/window={window}/data.parquet"),
                f"""
                select
                    {token('subscriber_token', salt)} as subscriber_key,
                    label_window,
                    is_churn
                from read_parquet('{escaped(source)}', hive_partitioning = false)
                """,
            )

        for source in listening:
            relative = source.relative_to(facts / "fact_listening_day")
            destination = Path("listening_day") / relative.parent / "data.parquet"
            publish(
                destination,
                f"""
                select
                    {token('subscriber_token', salt)} as subscriber_key,
                    activity_date,
                    num_25,
                    num_50,
                    num_75,
                    num_985,
                    num_100,
                    num_unq,
                    total_secs,
                    total_secs_was_negative,
                    source_version
                from read_parquet('{escaped(source)}', hive_partitioning = false)
                """,
            )

        manifest = {
            "release_id": release_id,
            "format": "parquet",
            "compression": "zstd",
            "grain": "row_level",
            "subscriber_key": "release-specific collision-checked 64-bit one-way pseudonym",
            "member_generalization": {
                "age": "10-year band start; implausible or missing values are null",
                "registration": "month",
                "source_identifier": "excluded",
            },
            "rows": sum(item["rows"] for item in files),
            "bytes": sum(item["bytes"] for item in files),
            "files": files,
        }
        (stage / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        os.replace(stage, output)
        return manifest
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    finally:
        database.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build re-keyed row-level public Parquet data.")
    parser.add_argument("--facts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--salt-file", type=Path, required=True)
    parser.add_argument("--release-id", default="public-m12")
    arguments = parser.parse_args()
    result = build(arguments.facts, arguments.output, arguments.salt_file, arguments.release_id)
    print(json.dumps({key: result[key] for key in ("release_id", "rows", "bytes")}, indent=2))
