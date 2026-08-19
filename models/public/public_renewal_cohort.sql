select *
from {{ ref('mart_renewal_cohort') }}
where eligible_subscribers >= {{ var('minimum_public_group_size') }}
