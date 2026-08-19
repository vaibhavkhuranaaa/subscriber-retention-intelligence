with cutoffs as (
    select * from {{ ref('int_subscriber_cutoffs') }}
),
eligible_activity as (
    select
        c.subscriber_token,
        c.label_window,
        c.history_cutoff,
        l.* exclude (subscriber_token)
    from cutoffs c
    left join {{ ref('stg_listening_daily') }} l
        on c.subscriber_token = l.subscriber_token
        and l.activity_date <= c.history_cutoff
        and l.activity_date > c.history_cutoff - interval '90 days'
)
select
    subscriber_token,
    label_window,
    count(activity_date) filter (
        where activity_date > history_cutoff - interval '30 days'
    ) as listening_active_days_30d,
    count(activity_date) as listening_active_days_90d,
    coalesce(sum(total_secs) filter (
        where activity_date > history_cutoff - interval '30 days'
    ), 0) as listening_seconds_30d,
    coalesce(sum(total_secs), 0) as listening_seconds_90d,
    coalesce(sum(num_unq) filter (
        where activity_date > history_cutoff - interval '30 days'
    ), 0) as unique_track_count_30d,
    coalesce(sum(num_unq), 0) as unique_track_count_90d,
    coalesce(sum(num_100) filter (
        where activity_date > history_cutoff - interval '30 days'
    ), 0) as full_completion_count_30d,
    coalesce(sum(num_100), 0) as full_completion_count_90d,
    coalesce(sum(num_25 + num_50 + num_75 + num_985 + num_100) filter (
        where activity_date > history_cutoff - interval '30 days'
    ), 0) as play_count_30d,
    coalesce(sum(num_25 + num_50 + num_75 + num_985 + num_100), 0) as play_count_90d,
    count(activity_date) filter (where total_secs_was_negative) as negative_duration_rows_90d,
    max(activity_date) as latest_activity_date
from eligible_activity
group by subscriber_token, label_window
