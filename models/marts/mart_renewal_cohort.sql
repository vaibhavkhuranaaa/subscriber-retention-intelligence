select
    label_window,
    registration_cohort_month,
    count(*) as eligible_subscribers,
    sum(observed_renewed_within_30_days) as observed_renewed_subscribers,
    sum(is_churn) as observed_churned_subscribers,
    avg(observed_renewed_within_30_days) as observed_renewal_rate,
    avg(is_churn) as observed_churn_rate,
    sum(gross_receipts_90d) as gross_receipts_90d
from {{ ref('fct_subscriber_snapshot') }}
where registration_cohort_month <= date_trunc('month', history_cutoff)::date
group by label_window, registration_cohort_month
