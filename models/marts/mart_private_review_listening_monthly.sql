select
    p.subscriber_token,
    p.label_window,
    date_trunc('month', l.activity_date)::date as activity_month,
    count(*) as active_days,
    sum(l.total_secs) as listening_seconds,
    sum(l.num_unq) as unique_track_count
from {{ ref('mart_private_review_population') }} p
join {{ ref('stg_listening_daily') }} l
  on p.subscriber_token = l.subscriber_token
 and l.activity_date <= p.history_cutoff
 and l.activity_date > p.history_cutoff - interval '180 days'
group by p.subscriber_token, p.label_window, activity_month
