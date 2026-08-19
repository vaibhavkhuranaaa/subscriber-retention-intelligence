select
    c.subscriber_token,
    c.label_window,
    c.history_cutoff,
    c.expiration_window_start,
    c.expiration_window_end,
    c.renewal_observation_end,
    c.is_churn,
    cast(1 - c.is_churn as tinyint) as observed_renewed_within_30_days,
    m.registration_date,
    date_trunc('month', m.registration_date)::date as registration_cohort_month,
    date_diff('day', m.registration_date, c.history_cutoff) as tenure_days,
    m.registration_method_code,
    m.city_code,
    m.age_reported,
    m.gender,
    coalesce(t.subscription_event_count_lifetime, 0) as subscription_event_count_lifetime,
    coalesce(t.subscription_event_count_30d, 0) as subscription_event_count_30d,
    coalesce(t.subscription_event_count_90d, 0) as subscription_event_count_90d,
    coalesce(t.gross_receipts_lifetime, 0) as gross_receipts_lifetime,
    coalesce(t.gross_receipts_30d, 0) as gross_receipts_30d,
    coalesce(t.gross_receipts_90d, 0) as gross_receipts_90d,
    coalesce(t.cancellation_event_count_lifetime, 0) as cancellation_event_count_lifetime,
    coalesce(t.cancellation_event_count_30d, 0) as cancellation_event_count_30d,
    t.latest_transaction_date,
    t.latest_payment_method_id,
    t.latest_payment_plan_days,
    t.latest_plan_list_price,
    t.latest_actual_amount_paid,
    t.latest_is_auto_renew,
    t.latest_is_cancel,
    t.effective_expiration_date,
    cast(
        coalesce(t.effective_expiration_date >= c.history_cutoff, false)
        as boolean
    ) as is_active_at_cutoff,
    coalesce(l.listening_active_days_30d, 0) as listening_active_days_30d,
    coalesce(l.listening_active_days_90d, 0) as listening_active_days_90d,
    coalesce(l.listening_seconds_30d, 0) as listening_seconds_30d,
    coalesce(l.listening_seconds_90d, 0) as listening_seconds_90d,
    coalesce(l.unique_track_count_30d, 0) as unique_track_count_30d,
    coalesce(l.unique_track_count_90d, 0) as unique_track_count_90d,
    coalesce(l.full_completion_count_30d, 0) as full_completion_count_30d,
    coalesce(l.full_completion_count_90d, 0) as full_completion_count_90d,
    coalesce(l.play_count_30d, 0) as play_count_30d,
    coalesce(l.play_count_90d, 0) as play_count_90d,
    coalesce(l.negative_duration_rows_90d, 0) as negative_duration_rows_90d,
    l.latest_activity_date,
    case
        when coalesce(l.listening_active_days_30d, 0) = 0 then 'Dormant'
        when l.listening_active_days_30d <= 5 then 'Light'
        when l.listening_active_days_30d <= 15 then 'Steady'
        else 'High'
    end as engagement_segment
from {{ ref('int_subscriber_cutoffs') }} c
left join {{ ref('stg_members') }} m using (subscriber_token)
left join {{ ref('int_subscription_features') }} t using (subscriber_token, label_window)
left join {{ ref('int_listening_features') }} l using (subscriber_token, label_window)
