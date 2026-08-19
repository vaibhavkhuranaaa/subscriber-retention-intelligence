select
    p.subscriber_token,
    p.label_window,
    t.transaction_date,
    t.membership_expire_date,
    t.payment_plan_days,
    t.actual_amount_paid,
    t.is_auto_renew,
    t.is_cancel,
    t.same_day_sequence
from {{ ref('mart_private_review_population') }} p
join {{ ref('stg_subscription_transactions') }} t
  on p.subscriber_token = t.subscriber_token
 and t.transaction_date <= p.history_cutoff
qualify row_number() over (
    partition by p.subscriber_token, p.label_window
    order by t.transaction_date desc, t.same_day_sequence desc
) <= 24
