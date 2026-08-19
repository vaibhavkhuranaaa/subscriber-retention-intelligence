{% set facts_dir = env_var('RETENTION_FACTS_DIR', '../subscriber-retention-intelligence-ops/data/private/facts') %}

select
    subscriber_token,
    "window" as label_window,
    is_churn
from read_parquet(
    '{{ facts_dir }}/fact_churn_label/window=*/data.parquet',
    hive_partitioning = true
)
