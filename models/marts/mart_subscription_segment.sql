with snapshots as (
    select * from {{ ref('fct_subscriber_snapshot') }}
),
segments as (
    select
        label_window,
        'payment_method' as dimension,
        cast(latest_payment_method_id as varchar) as segment_key,
        'Method ' || cast(latest_payment_method_id as varchar) as segment_label,
        observed_renewed_within_30_days,
        is_churn,
        gross_receipts_90d
    from snapshots
    where latest_payment_method_id is not null

    union all

    select
        label_window,
        'plan_days' as dimension,
        cast(latest_payment_plan_days as varchar) as segment_key,
        cast(latest_payment_plan_days as varchar) || ' days' as segment_label,
        observed_renewed_within_30_days,
        is_churn,
        gross_receipts_90d
    from snapshots
    where latest_payment_plan_days is not null

    union all

    select
        label_window,
        'registration_method' as dimension,
        cast(registration_method_code as varchar) as segment_key,
        'Channel ' || cast(registration_method_code as varchar) as segment_label,
        observed_renewed_within_30_days,
        is_churn,
        gross_receipts_90d
    from snapshots
    where registration_method_code is not null

    union all

    select
        label_window,
        'auto_renew' as dimension,
        cast(latest_is_auto_renew as varchar) as segment_key,
        case latest_is_auto_renew when 1 then 'Auto-renew on' else 'Auto-renew off' end as segment_label,
        observed_renewed_within_30_days,
        is_churn,
        gross_receipts_90d
    from snapshots
    where latest_is_auto_renew is not null
)
select
    label_window,
    dimension,
    segment_key,
    segment_label,
    count(*) as eligible_subscribers,
    sum(observed_renewed_within_30_days) as observed_renewed_subscribers,
    sum(is_churn) as observed_churned_subscribers,
    avg(observed_renewed_within_30_days) as observed_renewal_rate,
    avg(is_churn) as observed_churn_rate,
    sum(gross_receipts_90d) as gross_receipts_90d
from segments
group by label_window, dimension, segment_key, segment_label
