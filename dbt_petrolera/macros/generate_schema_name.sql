-- ===============================================================================
-- generate_schema_name: usa el nombre de esquema configurado por modelo tal cual
-- (staging, intermediate, marts) en vez de anteponer el schema del perfil
-- (evita public_staging, public_public, etc.).
-- ===============================================================================
{% macro generate_schema_name(custom_schema_name, node) -%}
    {{ return(custom_schema_name or target.schema) }}
{%- endmacro %}