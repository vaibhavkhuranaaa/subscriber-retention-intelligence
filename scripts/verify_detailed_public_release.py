from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import duckdb

EXPECTED_ROWS = {
    "member": 6_769_473,
    "subscription_transaction": 22_975_416,
    "churn_label": 1_963_891,
    "listening_day": 410_502_905,
}

EXPECTED_COLUMNS = {
    "member": {
        "subscriber_key",
        "city_code",
        "age_band_start",
        "gender",
        "registration_method_code",
        "registration_month",
    },
    "subscription_transaction": {
        "event_key",
        "subscriber_key",
        "payment_method_id",
        "payment_plan_days",
        "plan_list_price",
        "actual_amount_paid",
        "is_auto_renew",
        "transaction_date",
        "membership_expire_date",
        "is_cancel",
        "source_versions",
    },
    "churn_label": {"subscriber_key", "label_window", "is_churn"},
    "listening_day": {
        "subscriber_key",
        "activity_date",
        "num_25",
        "num_50",
        "num_75",
        "num_985",
        "num_100",
        "num_unq",
        "total_secs",
        "total_secs_was_negative",
        "source_version",
    },
}


def escaped(path: Path) -> str:
    return str(path).replace("'", "''")


def verify(facts: Path, release: Path, salt_file: Path) -> dict:
    manifest = json.loads((release / "manifest.json").read_text())
    files = manifest["files"]
    assert manifest["rows"] == sum(item["rows"] for item in files)
    assert manifest["bytes"] == sum(item["bytes"] for item in files)
    assert len(files) == 32
    for item in files:
        path = release / item["path"]
        assert path.is_file(), path
        assert path.stat().st_size == item["bytes"], path

    patterns = {
        "member": release / "member/data.parquet",
        "subscription_transaction": release / "subscription_transaction/**/*.parquet",
        "churn_label": release / "churn_label/**/*.parquet",
        "listening_day": release / "listening_day/**/*.parquet",
    }
    database = duckdb.connect()
    database.execute("set threads = 1")
    database.execute("set memory_limit = '4GB'")
    rows = {}
    try:
        for name, pattern in patterns.items():
            source = escaped(pattern)
            rows[name] = database.execute(
                f"select count(*) from read_parquet('{source}', hive_partitioning = false)"
            ).fetchone()[0]
            assert rows[name] == EXPECTED_ROWS[name], (name, rows[name])
            columns = {
                row[0]
                for row in database.execute(
                    f"describe select * from read_parquet('{source}', hive_partitioning = false)"
                ).fetchall()
            }
            assert columns == EXPECTED_COLUMNS[name], (name, columns)

        salt = salt_file.read_text().strip()
        private_token = database.execute(
            "select subscriber_token from read_parquet(?) limit 1",
            [str(facts / "dim_member/data.parquet")],
        ).fetchone()[0]
        public_token = int.from_bytes(
            hashlib.sha256((private_token.hex().upper() + salt).encode()).digest()[:8], "big"
        )
        assert public_token != private_token
        match = database.execute(
            "select count(*) from read_parquet(?) where subscriber_key = ?",
            [str(patterns["member"]), public_token],
        ).fetchone()[0]
        assert match == 1

        member_total, member_distinct = database.execute(
            "select count(*), count(distinct subscriber_key) from read_parquet(?)",
            [str(patterns["member"])],
        ).fetchone()
        assert member_total == member_distinct
        event_total, event_distinct = database.execute(
            "select count(*), count(distinct event_key) from read_parquet(?)",
            [str(patterns["subscription_transaction"])],
        ).fetchone()
        assert event_total == event_distinct
    finally:
        database.close()

    assert sum(rows.values()) == 442_211_685
    return {
        "status": "verified",
        "rows": sum(rows.values()),
        "parquet_files": len(files),
        "bytes": manifest["bytes"],
        "pseudonym_collisions": 0,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify a row-level public data release.")
    parser.add_argument("--facts", type=Path, required=True)
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--salt-file", type=Path, required=True)
    arguments = parser.parse_args()
    result = verify(arguments.facts, arguments.release, arguments.salt_file)
    print(json.dumps(result, indent=2))
