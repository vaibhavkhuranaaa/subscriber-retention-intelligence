{% test unique_combination(model, combination_of_columns) %}
select
    {% for column in combination_of_columns %}
    {{ column }}{% if not loop.last %}, {% endif %}
    {% endfor %}
from {{ model }}
group by
    {% for column in combination_of_columns %}
    {{ column }}{% if not loop.last %}, {% endif %}
    {% endfor %}
having count(*) > 1
{% endtest %}
