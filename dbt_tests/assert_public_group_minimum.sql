select label_window, cast(registration_cohort_month as varchar) as group_value
from {{ ref('public_renewal_cohort') }}
where eligible_subscribers < {{ var('minimum_public_group_size') }}
union all
select label_window, engagement_segment as group_value
from {{ ref('public_engagement_segment') }}
where eligible_subscribers < {{ var('minimum_public_group_size') }}
union all
select label_window, dimension || ':' || segment_key as group_value
from {{ ref('public_subscription_segment') }}
where eligible_subscribers < {{ var('minimum_public_group_size') }}
