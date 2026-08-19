select *
from {{ ref('mart_subscription_segment') }}
where eligible_subscribers >= {{ var('minimum_public_group_size') }}
