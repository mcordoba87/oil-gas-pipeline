-- ===============================================================================
-- stg_produccion_diaria: limpieza del CSV de producción manual (landing).
-- Casting de tipos, normalización de observaciones y valores no negativos.
-- ===============================================================================
select
    pozo_id::text                          as pozo_id,
    fecha::date                            as fecha,
    greatest(bpd_producido::double precision, 0) as bpd_producido,
    horas_operativas::double precision     as horas_operativas,
    case
        when bpd_producido::double precision > 0 and horas_operativas::double precision > 24
        then nullif(observaciones, '')
        else coalesce(nullif(trim(observaciones), ''), 'sin observaciones')
    end                                    as observaciones,
    greatest(gas_mcfd::double precision, 0) as gas_mcfd
from {{ source('raw', 'produccion_diaria') }}