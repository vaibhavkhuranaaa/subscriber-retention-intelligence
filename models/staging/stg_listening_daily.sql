{% set facts_dir = env_var('RETENTION_FACTS_DIR', '../subscriber-retention-intelligence-ops/data/private/facts') %}

select
    subscriber_token,
    activity_date,
    num_25,
    num_50,
    num_75,
    num_985,
    num_100,
    num_unq,
    total_secs,
    total_secs_was_negative,
    source_version
from read_parquet(
    '{{ facts_dir }}/fact_listening_day/source_version=*/activity_month=*/*.parquet',
    hive_partitioning = true
)
