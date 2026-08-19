select subscriber_token, label_window
from {{ ref('fct_subscriber_snapshot') }}
where latest_transaction_date > history_cutoff
   or latest_activity_date > history_cutoff
