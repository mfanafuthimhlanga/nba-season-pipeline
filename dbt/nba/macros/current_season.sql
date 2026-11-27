{% macro current_season(rel) %}
    (select max(season) from {{ rel }} where is_regular_season)
{% endmacro %}
