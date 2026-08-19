select *
from {{ ref('fct_subscriber_snapshot') }}
qualify row_number() over (
    partition by label_window
    order by gross_receipts_90d desc, subscriber_token
) <= 500
