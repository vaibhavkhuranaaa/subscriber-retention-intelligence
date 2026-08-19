#!/usr/bin/env python3
"""Reconcile governed marts against independent fact queries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb


def relative_error(actual: float, expected: float) -> float:
    return abs(actual - expected) / max(abs(expected), 1.0)


def reconcile(warehouse: Path, facts: Path) -> dict:
    connection = duckdb.connect(str(warehouse), read_only=True)
    labels = facts / "fact_churn_label/window=*/data.parquet"
    transactions = facts / "fact_subscription_transaction/data.parquet"
    listening = facts / "fact_listening_day/source_version=*/activity_month=*/*.parquet"

    expected_rows = connection.execute(
        f"""
        with cutoffs(label_window, history_cutoff) as (
            values ('2017-02', date '2017-01-31'), ('2017-03', date '2017-02-28')
        ),
        labels as (
            select subscriber_token, "window" as label_window, is_churn
            from read_parquet('{labels}', hive_partitioning = true)
        ),
        label_controls as (
            select
                label_window,
                count(*) as eligible_subscribers,
                sum(is_churn) as observed_churned_subscribers,
                sum(1 - is_churn) as observed_renewed_subscribers
            from labels
            group by label_window
        ),
        transaction_controls as (
            select
                c.label_window,
                sum(t.actual_amount_paid) as gross_receipts_lifetime,
                count(*) as subscription_event_count_lifetime,
                count(*) filter (where t.is_cancel = 1) as cancellation_event_count_lifetime
            from labels l
            join cutoffs c using (label_window)
            join read_parquet('{transactions}') t
              on l.subscriber_token = t.subscriber_token
             and t.transaction_date <= c.history_cutoff
            group by c.label_window
        ),
        listening_controls as (
            select
                c.label_window,
                count(*) filter (
                    where d.activity_date > c.history_cutoff - interval '30 days'
                ) as listening_active_days_30d,
                count(*) as listening_active_days_90d
            from labels l
            join cutoffs c using (label_window)
            join read_parquet('{listening}', hive_partitioning = true) d
              on l.subscriber_token = d.subscriber_token
             and d.activity_date <= c.history_cutoff
             and d.activity_date > c.history_cutoff - interval '90 days'
            group by c.label_window
        )
        select *
        from label_controls
        join transaction_controls using (label_window)
        join listening_controls using (label_window)
        order by label_window
        """
    ).fetchall()
    column_names = [column[0] for column in connection.description]
    expected = [dict(zip(column_names, row, strict=True)) for row in expected_rows]
    actual_rows = connection.execute(
        """
        select
            label_window,
            eligible_subscribers,
            observed_churned_subscribers,
            observed_renewed_subscribers,
            gross_receipts_lifetime,
            subscription_event_count_lifetime,
            cancellation_event_count_lifetime,
            listening_active_days_30d,
            listening_active_days_90d
        from mart_retention_overview
        order by label_window
        """
    ).fetchall()
    actual_columns = [column[0] for column in connection.description]
    actual = [dict(zip(actual_columns, row, strict=True)) for row in actual_rows]
    connection.close()

    if len(expected) != len(actual):
        raise RuntimeError("label-window count mismatch")

    checks = []
    for expected_row, actual_row in zip(expected, actual, strict=True):
        if expected_row["label_window"] != actual_row["label_window"]:
            raise RuntimeError("label-window order mismatch")
        for metric, expected_value in expected_row.items():
            if metric == "label_window":
                continue
            actual_value = actual_row[metric]
            error = relative_error(float(actual_value), float(expected_value))
            checks.append(
                {
                    "label_window": expected_row["label_window"],
                    "metric": metric,
                    "expected": float(expected_value),
                    "actual": float(actual_value),
                    "relative_error": error,
                }
            )

    maximum_error = max(check["relative_error"] for check in checks)
    return {
        "status": "passed" if maximum_error <= 0.000001 else "failed",
        "maximum_relative_error": maximum_error,
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--warehouse", type=Path, required=True)
    parser.add_argument("--facts", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = reconcile(arguments.warehouse.resolve(), arguments.facts.resolve())
    rendered = json.dumps(report, indent=2)
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(rendered + "\n")
    print(rendered)
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
