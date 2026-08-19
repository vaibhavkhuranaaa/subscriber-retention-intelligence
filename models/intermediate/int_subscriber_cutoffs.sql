select
    subscriber_token,
    label_window,
    cast(is_churn as tinyint) as is_churn,
    case label_window
        when '2017-02' then date '2017-01-31'
        when '2017-03' then date '2017-02-28'
    end as history_cutoff,
    case label_window
        when '2017-02' then date '2017-02-01'
        when '2017-03' then date '2017-03-01'
    end as expiration_window_start,
    case label_window
        when '2017-02' then date '2017-02-28'
        when '2017-03' then date '2017-03-31'
    end as expiration_window_end,
    case label_window
        when '2017-02' then date '2017-03-31'
        when '2017-03' then date '2017-04-30'
    end as renewal_observation_end
from {{ ref('stg_churn_labels') }}
