-- ===============================================================================
-- stg_scada_logs: normalización de logs SCADA semi-estructurados (JSON lines).
-- Ejemplo de procesamiento de datos no relacionales dentro del lakehouse.
-- ===============================================================================
select
    timestamp::timestamptz   as timestamp,
    evento::text             as evento,
    descripcion::text        as descripcion,
    pozo_id::text            as pozo_id,
    upper(nivel::text)       as nivel,
    fuente::text             as fuente
from {{ source('raw', 'scada_logs') }}