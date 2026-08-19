{% set public_relations = [
    ref('public_retention_overview'),
    ref('public_renewal_cohort'),
    ref('public_engagement_segment'),
    ref('public_subscription_segment'),
    ref('public_metric_definition')
] %}
{% set forbidden = ['subscriber_token', 'city_code', 'age_reported', 'gender', 'registration_method_code'] %}

{% for relation in public_relations %}
    {% set columns = adapter.get_columns_in_relation(relation) %}
    {% for column in columns %}
        {% if column.name | lower in forbidden %}
select '{{ relation }}' as relation_name, '{{ column.name }}' as forbidden_column
        {% else %}
select null::varchar as relation_name, null::varchar as forbidden_column where false
        {% endif %}
        {% if not loop.last %} union all {% endif %}
    {% endfor %}
    {% if not loop.last %} union all {% endif %}
{% endfor %}
