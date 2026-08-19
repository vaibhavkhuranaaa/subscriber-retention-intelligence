select
    label_window,
    engagement_segment,
    count(*) as eligible_subscribers,
    sum(observed_renewed_within_30_days) as observed_renewed_subscribers,
    sum(is_churn) as observed_churned_subscribers,
    avg(is_churn) as observed_churn_rate,
    avg(listening_active_days_30d) as average_listening_active_days_30d,
    avg(listening_seconds_30d) as average_listening_seconds_30d,
    sum(full_completion_count_30d) as full_completion_count_30d
from {{ ref('fct_subscriber_snapshot') }}
group by label_window, engagement_segment
