with cutoffs as (
    select * from {{ ref('int_subscriber_cutoffs') }}
),
eligible_events as (
    select
        c.subscriber_token,
        c.label_window,
        c.history_cutoff,
        t.* exclude (subscriber_token)
    from cutoffs c
    left join {{ ref('stg_subscription_transactions') }} t
        on c.subscriber_token = t.subscriber_token
        and t.transaction_date <= c.history_cutoff
),
aggregates as (
    select
        subscriber_token,
        label_window,
        count(event_key) as subscription_event_count_lifetime,
        count(event_key) filter (
            where transaction_date > history_cutoff - interval '30 days'
        ) as subscription_event_count_30d,
        count(event_key) filter (
            where transaction_date > history_cutoff - interval '90 days'
        ) as subscription_event_count_90d,
        coalesce(sum(actual_amount_paid), 0) as gross_receipts_lifetime,
        coalesce(sum(actual_amount_paid) filter (
            where transaction_date > history_cutoff - interval '30 days'
        ), 0) as gross_receipts_30d,
        coalesce(sum(actual_amount_paid) filter (
            where transaction_date > history_cutoff - interval '90 days'
        ), 0) as gross_receipts_90d,
        count(event_key) filter (where is_cancel = 1) as cancellation_event_count_lifetime,
        count(event_key) filter (
            where is_cancel = 1
              and transaction_date > history_cutoff - interval '30 days'
        ) as cancellation_event_count_30d,
        max(transaction_date) as latest_transaction_date
    from eligible_events
    group by subscriber_token, label_window
),
latest_event as (
    select
        subscriber_token,
        label_window,
        payment_method_id as latest_payment_method_id,
        payment_plan_days as latest_payment_plan_days,
        plan_list_price as latest_plan_list_price,
        actual_amount_paid as latest_actual_amount_paid,
        is_auto_renew as latest_is_auto_renew,
        is_cancel as latest_is_cancel,
        membership_expire_date as effective_expiration_date
    from eligible_events
    where event_key is not null
    qualify row_number() over (
        partition by subscriber_token, label_window
        order by transaction_date desc, same_day_sequence desc
    ) = 1
)
select
    a.*,
    l.latest_payment_method_id,
    l.latest_payment_plan_days,
    l.latest_plan_list_price,
    l.latest_actual_amount_paid,
    l.latest_is_auto_renew,
    l.latest_is_cancel,
    l.effective_expiration_date
from aggregates a
left join latest_event l using (subscriber_token, label_window)
