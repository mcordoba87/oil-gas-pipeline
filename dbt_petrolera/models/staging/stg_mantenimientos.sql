-- ===============================================================================
-- stg_mantenimientos: normalización de mantenimientos OLTP.
-- El campo pozo_id de la tabla OLTP referencia el id interno del pozo; lo
-- convertimos al pozo_id de negocio (nombre) vía stg_pozos.
-- ===============================================================================
select
    m.id::integer          as mantenimiento_id,
    p.pozo_id              as pozo_id,
    m.fecha::date          as fecha,
    m.tipo::text           as tipo,
    m.costo::double precision as costo,
    m.tecnico::text        as tecnico
from {{ source('raw', 'oltp_mantenimientos') }} m
left join {{ ref('stg_pozos') }} p
    on p.oltp_id = m.pozo_id::integer