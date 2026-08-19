select label_window
from {{ ref('mart_retention_overview') }}
where eligible_subscribers
      <> observed_renewed_subscribers + observed_churned_subscribers
   or abs(observed_renewal_rate + observed_churn_rate - 1.0) > 0.000000001
