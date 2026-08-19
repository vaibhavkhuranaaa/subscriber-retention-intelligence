select *
from {{ ref('mart_engagement_segment') }}
where eligible_subscribers >= {{ var('minimum_public_group_size') }}
