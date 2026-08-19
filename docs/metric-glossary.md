# Metric glossary

| Metric | Definition |
| --- | --- |
| Active subscribers | Subscribers with reconstructed valid membership on the snapshot date |
| Gross receipts | Sum actual amount paid in source currency; not recognized revenue |
| Eligible expirations | Subscribers whose reconstructed membership expires in the declared decision window |
| Renewal rate | Eligible expirations renewed inside the documented renewal grace window |
| Churn rate | Challenge-compatible failure to renew within the defined gap |
| Cancellation rate | Cancellation-marked transactions divided by eligible subscription transactions |
| Cohort retention | Active subscribers after N periods divided by eligible cohort starters |
| Listening active days | Subscriber-days with recorded listening before cutoff |
| Completion activity | Counts of full and partial listening categories before cutoff |
| Log loss | Probabilistic error on held-out future churn labels |
| Calibration error | Weighted gap between predicted and observed future churn |
| Top-decile lift | Churn rate in the highest-risk decile divided by population churn rate |
| Modeled churn exposure | Sum of calibrated historical churn probabilities across selected repeat subscribers |
| Assumed retention lift | User-entered share of modeled churn prevented; not an observed treatment effect |
| Simulated retained subscribers | Modeled churn exposure multiplied by assumed retention lift |
| Simulated retained gross-receipt proxy | Risk-weighted latest payment proxy multiplied by assumed retention lift; not revenue or CLV |
| Simulated net gross-receipt proxy | Simulated retained gross-receipt proxy minus contact and offer spend |
| Break-even assumed lift | Total assumed spend divided by risk-weighted latest payment proxy |

Scenario outputs use user-supplied lift and cost assumptions and are simulated, not observed causal outcomes.
