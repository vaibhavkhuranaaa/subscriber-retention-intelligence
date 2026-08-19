{% set facts_dir = env_var('RETENTION_FACTS_DIR', '../subscriber-retention-intelligence-ops/data/private/facts') %}

select
    event_key,
    subscriber_token,
    payment_method_id,
    payment_plan_days,
    plan_list_price,
    actual_amount_paid,
    is_auto_renew,
    transaction_date,
    membership_expire_date,
    is_cancel,
    source_versions,
    row_number() over (
        partition by subscriber_token, transaction_date
        order by
            plan_list_price desc,
            actual_amount_paid desc,
            payment_plan_days desc,
            payment_method_id desc,
            is_auto_renew desc,
            case when is_cancel = 0 then membership_expire_date end asc nulls last,
            case when is_cancel = 1 then membership_expire_date end desc nulls last,
            is_cancel asc,
            event_key
    ) as same_day_sequence
from read_parquet('{{ facts_dir }}/fact_subscription_transaction/data.parquet')
