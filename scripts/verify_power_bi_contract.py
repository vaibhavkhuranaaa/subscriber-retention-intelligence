#!/usr/bin/env python3
"""Validate the browser-authored Power BI contract without claiming engine execution."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import duckdb

ROOT = Path(__file__).resolve().parents[1]


def quoted(columns: list[str]) -> str:
    return ", ".join(f'"{column}"' for column in columns)


def compare_controls(expected: list[dict[str, Any]], actual_path: Path) -> list[str]:
    with actual_path.open(newline="") as source:
        actual = {row["control_id"]: row for row in csv.DictReader(source)}
    expected_ids = {row["control_id"] for row in expected}
    problems = []
    if set(actual) != expected_ids:
        problems.append("Power BI control IDs differ from the fixed contract")
    for row in expected:
        observed = actual.get(row["control_id"])
        if observed and abs(float(observed["actual_value"]) - float(row["expected_value"])) > 1e-9:
            problems.append(f"Power BI control mismatch: {row['control_id']}")
    return problems


def verify(warehouse: Path, contract_path: Path, actual_path: Path | None = None) -> dict[str, Any]:
    contract_text = contract_path.read_text()
    contract = json.loads(contract_text)
    problems: list[str] = []
    public_contract = json.dumps(
        {"tables": contract["tables"], "relationships": contract["relationships"]}
    ).lower()
    for forbidden in contract["forbidden_columns"]:
        if forbidden.lower() in public_contract:
            problems.append(f"forbidden field appears in contract: {forbidden}")
    measures = (ROOT / contract["measure_file"]).read_text()
    for required in (
        "HASONEVALUE('dim_label_window'",
        "HASONEVALUE('dim_subscription_segment'[dimension])",
        "SUMX('fct_engagement_segment'",
    ):
        if required not in measures:
            problems.append(f"missing DAX guard: {required}")
    database = duckdb.connect(str(warehouse), read_only=True)
    try:
        for table in contract["tables"]:
            name = table["name"]
            database.execute(f"create temp view {name} as {table['source_sql']}")
            observed_columns = [row[0] for row in database.execute(f"describe {name}").fetchall()]
            expected_columns = [column["name"] for column in table["columns"]]
            if observed_columns != expected_columns:
                problems.append(f"schema mismatch: {name}")
            grain = table["grain"]
            row_count, unique_count = database.execute(
                f"select count(*), count(distinct ({quoted(grain)})) from {name}"
            ).fetchone()
            if row_count != unique_count:
                problems.append(f"duplicate grain: {name}")
            nulls = database.execute(
                f"select count(*) from {name} where "
                + " or ".join(f'"{column}" is null' for column in grain)
            ).fetchone()[0]
            if nulls:
                problems.append(f"null grain key: {name}")
            if table["kind"] == "fact" and "eligible_subscribers" in observed_columns:
                invalid = database.execute(
                    f"select count(*) from {name} where eligible_subscribers != observed_renewed_subscribers + observed_churned_subscribers"
                ).fetchone()[0]
                if invalid:
                    problems.append(f"subscriber arithmetic mismatch: {name}")
        for relationship in contract["relationships"]:
            if (
                relationship["cardinality"] != "one_to_many"
                or relationship["cross_filter"] != "single"
                or not relationship["active"]
            ):
                problems.append("relationship policy mismatch")
                continue
            parent = relationship["from_table"]
            child = relationship["to_table"]
            parent_key = relationship["from_column"]
            child_key = relationship["to_column"]
            orphans = database.execute(
                f'select count(*) from {child} c left join {parent} p on c."{child_key}" = p."{parent_key}" where p."{parent_key}" is null'
            ).fetchone()[0]
            if orphans:
                problems.append(f"relationship orphan: {parent} to {child}")
        expected = []
        for window in ("2017-02", "2017-03"):
            row = database.execute(
                "select eligible_subscribers, observed_renewed_subscribers, observed_churned_subscribers, gross_receipts_lifetime from fct_retention_overview where label_window = ?",
                [window],
            ).fetchone()
            for name, value in zip(
                ("eligible", "renewed", "churned", "gross_receipts_lifetime"),
                row,
                strict=True,
            ):
                expected.append({"control_id": f"{window}:{name}", "expected_value": float(value)})
        if actual_path:
            problems.extend(compare_controls(expected, actual_path))
    finally:
        database.close()
    return {
        "status": "passed" if not problems else "failed",
        "contract_reconciliation_pass_rate": 1.0 if not problems else 0.0,
        "power_bi_engine_reconciliation": "passed"
        if actual_path and not problems
        else "failed"
        if actual_path
        else "not_run",
        "power_bi_engine_limitation": "Requires an approved browser-authored Power BI execution and exported fixed-context results.",
        "expected_controls": expected,
        "problems": problems,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--warehouse", type=Path, required=True)
    parser.add_argument("--contract", type=Path, default=ROOT / "powerbi/semantic-contract.json")
    parser.add_argument("--actual", type=Path)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = verify(
        arguments.warehouse.resolve(),
        arguments.contract.resolve(),
        arguments.actual.resolve() if arguments.actual else None,
    )
    rendered = json.dumps(report, indent=2)
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(rendered + "\n")
    print(rendered)
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
