-- override macro default: use +schema in profiles.yml, dont connect with prefix target.schema

{% macro generate_schema_name(customer_schema_name, node) -%}
    {%- if customer_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ customer_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}