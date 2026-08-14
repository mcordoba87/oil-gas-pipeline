-- ===============================================================================
-- stg_pozos: normalización del snapshot de pozos OLTP.
-- En OLTP la clave primaria es `id`; `nombre` (PZ-001) es el pozo_id de negocio
-- que usan los sensores, los CSV de producción/lab y la TSDB.
-- ===============================================================================
select
    id::integer                          as oltp_id,
    nombre::text                         as pozo_id,
    cuenca::text                         as cuenca,
    fecha_perforacion::date              as fecha_perforacion,
    lower(estado::text)                  as estado
from {{ source('raw', 'oltp_pozos') }}