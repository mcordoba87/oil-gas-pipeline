-- ===============================================================================
-- stg_paradas: normalización de paradas programadas OLTP (insumo de alertas).
-- Convierte el id interno del pozo al pozo_id de negocio.
-- ===============================================================================
select
    pd.id::integer        as parada_id,
    p.pozo_id             as pozo_id,
    pd.fecha_inicio::timestamp as fecha_inicio,
    pd.fecha_fin::timestamp  as fecha_fin,
    pd.motivo::text       as motivo
from {{ source('raw', 'oltp_paradas') }} pd
left join {{ ref('stg_pozos') }} p
    on p.oltp_id = pd.pozo_id::integer