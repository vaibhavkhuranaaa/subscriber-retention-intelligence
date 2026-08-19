{% set facts_dir = env_var('RETENTION_FACTS_DIR', '../subscriber-retention-intelligence-ops/data/private/facts') %}

select
    subscriber_token,
    city_code,
    age_reported,
    gender,
    registration_method_code,
    registration_date
from read_parquet('{{ facts_dir }}/dim_member/data.parquet')
