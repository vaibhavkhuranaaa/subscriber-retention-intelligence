select
    label_window,
    max(history_cutoff) as history_cutoff,
    count(*) as eligible_subscribers,
    count(*) filter (where is_active_at_cutoff) as active_subscribers,
    sum(observed_renewed_within_30_days) as observed_renewed_subscribers,
    sum(is_churn) as observed_churned_subscribers,
    avg(observed_renewed_within_30_days) as observed_renewal_rate,
    avg(is_churn) as observed_churn_rate,
    sum(gross_receipts_lifetime) as gross_receipts_lifetime,
    sum(gross_receipts_30d) as gross_receipts_30d,
    sum(gross_receipts_90d) as gross_receipts_90d,
    sum(subscription_event_count_lifetime) as subscription_event_count_lifetime,
    sum(cancellation_event_count_lifetime) as cancellation_event_count_lifetime,
    sum(cancellation_event_count_lifetime)::double
        / nullif(sum(subscription_event_count_lifetime), 0) as cancellation_event_rate,
    sum(listening_active_days_30d) as listening_active_days_30d,
    sum(listening_active_days_90d) as listening_active_days_90d,
    sum(full_completion_count_30d) as full_completion_count_30d,
    sum(negative_duration_rows_90d) as negative_duration_rows_90d
from {{ ref('fct_subscriber_snapshot') }}
group by label_window
