#!/usr/bin/env python3
"""Build a tiny contract-only fixture for clean-checkout API and browser tests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb


def build(warehouse: Path, curve: Path) -> None:
    if warehouse.exists() or curve.exists():
        raise FileExistsError("release fixture outputs must not already exist")
    warehouse.parent.mkdir(parents=True, exist_ok=True)
    curve.parent.mkdir(parents=True, exist_ok=True)
    database = duckdb.connect(str(warehouse))
    database.execute(
        """
        create table public_retention_overview as
        select * from (values
          ('2017-02', date '2017-01-31', 992931, 942100, 929460, 63471, .936077, .063923, 2850000000, 172000000, 465000000, 18000000, 340000, .018889, 12000000, 34000000, 75000000, 1400),
          ('2017-03', date '2017-02-28', 970960, 913500, 883630, 87330, .910058, .089942, 2980000000, 168000000, 452000000, 18700000, 365000, .019519, 11600000, 32900000, 72000000, 1650)
        ) as t(label_window, history_cutoff, eligible_subscribers, active_subscribers,
          observed_renewed_subscribers, observed_churned_subscribers, observed_renewal_rate,
          observed_churn_rate, gross_receipts_lifetime, gross_receipts_30d, gross_receipts_90d,
          subscription_event_count_lifetime, cancellation_event_count_lifetime,
          cancellation_event_rate, listening_active_days_30d, listening_active_days_90d,
          full_completion_count_30d, negative_duration_rows_90d);
        create table mart_retention_overview as select * from public_retention_overview;

        create table public_renewal_cohort as
        select * from (values
          ('2017-02', date '2016-09-01', 140000, 132000, 8000, .942857, .057143, 68000000),
          ('2017-02', date '2016-10-01', 155000, 144000, 11000, .929032, .070968, 72000000),
          ('2017-03', date '2016-09-01', 138000, 126000, 12000, .913043, .086957, 66000000),
          ('2017-03', date '2016-10-01', 151000, 136000, 15000, .900662, .099338, 70000000)
        ) as t(label_window, registration_cohort_month, eligible_subscribers,
          observed_renewed_subscribers, observed_churned_subscribers, observed_renewal_rate,
          observed_churn_rate, gross_receipts_90d);
        create table mart_renewal_cohort as select * from public_renewal_cohort;

        create table public_subscription_segment as
        select * from (values
          ('2017-02', 'payment_method', '41', 'Method 41', 180000, 169000, 11000, .938889, .061111, 86000000),
          ('2017-03', 'payment_method', '41', 'Method 41', 176000, 159000, 17000, .903409, .096591, 83000000),
          ('2017-02', 'plan_days', '30', '30 days', 210000, 197000, 13000, .938095, .061905, 99000000),
          ('2017-03', 'plan_days', '30', '30 days', 205000, 185000, 20000, .902439, .097561, 96000000),
          ('2017-02', 'registration_method', '7', 'Method 7', 160000, 150000, 10000, .937500, .062500, 76000000),
          ('2017-03', 'registration_method', '7', 'Method 7', 157000, 142000, 15000, .904459, .095541, 74000000),
          ('2017-02', 'auto_renew', '1', 'Auto-renew on', 720000, 690000, 30000, .958333, .041667, 340000000),
          ('2017-03', 'auto_renew', '1', 'Auto-renew on', 700000, 660000, 40000, .942857, .057143, 330000000)
        ) as t(label_window, dimension, segment_key, segment_label, eligible_subscribers,
          observed_renewed_subscribers, observed_churned_subscribers, observed_renewal_rate,
          observed_churn_rate, gross_receipts_90d);
        create table mart_subscription_segment as select * from public_subscription_segment;

        create table public_engagement_segment as
        select * from (values
          ('2017-02', 'steady', 420000, 405000, 15000, .035714, 14.2, 4200.0, 39000000),
          ('2017-02', 'dormant', 190000, 160000, 30000, .157895, 1.8, 520.0, 2500000),
          ('2017-03', 'steady', 410000, 388000, 22000, .053659, 13.9, 4100.0, 37000000),
          ('2017-03', 'dormant', 185000, 145000, 40000, .216216, 1.6, 480.0, 2200000)
        ) as t(label_window, engagement_segment, eligible_subscribers,
          observed_renewed_subscribers, observed_churned_subscribers, observed_churn_rate,
          average_listening_active_days_30d, average_listening_seconds_30d,
          full_completion_count_30d);
        create table mart_engagement_segment as select * from public_engagement_segment;

        create table public_metric_definition as
        select * from (values
          ('observed_churn_rate', 'Observed churned subscribers divided by eligible subscribers.', 'label window', 'lower is favorable', 'Historical challenge outcome, not causal impact.'),
          ('observed_renewal_rate', 'Observed renewed subscribers divided by eligible subscribers.', 'label window', 'higher is favorable', 'Renewal follows the challenge-compatible 30-day rule.'),
          ('gross_receipts_30d', 'Actual amount paid in the 30 days through cutoff.', 'label window', 'context only', 'Source currency; not recognized revenue.'),
          ('listening_active_days_30d', 'Subscriber-days with listening in the 30 days through cutoff.', 'label window', 'context only', 'Missing activity is not proof of inactivity.')
        ) as t(metric_id, definition, grain, direction, limitation);
        create table dim_metric_definition as select * from public_metric_definition;

        create table mart_private_review_population as
        select unhex('00112233445566778899aabb') as subscriber_token, '2017-03' as label_window,
          1::tinyint as is_churn, true as is_active_at_cutoff, date '2017-03-15' as effective_expiration_date,
          'dormant' as engagement_segment, 2400::bigint as gross_receipts_90d,
          3::bigint as listening_active_days_30d, 30 as latest_payment_plan_days,
          1::utinyint as latest_is_auto_renew;
        create table mart_private_review_transaction as
        select unhex('00112233445566778899aabb') as subscriber_token, '2017-03' as label_window,
          date '2017-02-20' as transaction_date, date '2017-03-22' as membership_expire_date,
          30 as payment_plan_days, 149 as actual_amount_paid, 1::utinyint as is_auto_renew,
          0::utinyint as is_cancel, 1::bigint as same_day_sequence;
        create table mart_private_review_listening_monthly as
        select unhex('00112233445566778899aabb') as subscriber_token, '2017-03' as label_window,
          date '2017-02-01' as activity_month, 3::bigint as active_days,
          1200.0 as listening_seconds, 42::bigint as unique_track_count;
        """
    )
    database.close()
    curve.write_text(
        json.dumps(
            {
                "scope": "repeat_subscribers_only",
                "score_window": "2017-03",
                "eligible_subscribers": 881701,
                "group_size": 100,
                "total_expected_churners": 52000.0,
                "value_proxy": "Latest nonnegative payment amount in source currency.",
                "points": [
                    {
                        "contacts": 100,
                        "minimum_score": 0.8,
                        "expected_churners": 62.0,
                        "observed_churners": 60,
                        "risk_weighted_payment_proxy": 9000.0,
                        "selected_payment_proxy": 15000.0,
                    },
                    {
                        "contacts": 30000,
                        "minimum_score": 0.2,
                        "expected_churners": 12000.0,
                        "observed_churners": 11800,
                        "risk_weighted_payment_proxy": 1700000.0,
                        "selected_payment_proxy": 4200000.0,
                    },
                    {
                        "contacts": 50000,
                        "minimum_score": 0.1,
                        "expected_churners": 18000.0,
                        "observed_churners": 17500,
                        "risk_weighted_payment_proxy": 2500000.0,
                        "selected_payment_proxy": 7000000.0,
                    },
                    {
                        "contacts": 881701,
                        "minimum_score": 0.0,
                        "expected_churners": 52000.0,
                        "observed_churners": 51770,
                        "risk_weighted_payment_proxy": 9000000.0,
                        "selected_payment_proxy": 120000000.0,
                    },
                ],
            },
            indent=2,
        )
        + "\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--warehouse", type=Path, required=True)
    parser.add_argument("--curve", type=Path, required=True)
    arguments = parser.parse_args()
    build(arguments.warehouse.resolve(), arguments.curve.resolve())
    print("release fixture: ready (contract testing only; not evaluation evidence)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
