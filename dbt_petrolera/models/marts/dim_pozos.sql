-- ===============================================================================
-- dim_pozos: dimensión de pozos con estado actual e historial.
-- Combina el maestro de pozos (OLTP) con la última calidad de crudo (lab) y el
-- conteo histórico de mantenimientos. El historial completo de estados vive en
-- el snapshot snap_pozos_estado (SCD Type 2).
-- ===============================================================================
with lab_reciente as (
    select
        pozo_id,
        grados_api,
        pct_agua,
        pct_sedimentos,
        row_number() over (partition by pozo_id order by fecha desc) as rn
    from {{ ref('stg_laboratorio') }}
),
manto_stats as (
    select
        pozo_id,
        count(*)                                  as n_mantenimientos,
        max(fecha)                                as ultimo_mantenimiento,
        sum(case when tipo = 'correctivo' then 1 else 0 end) as n_correctivos
    from {{ ref('stg_mantenimientos') }}
    group by pozo_id
),
estado_actual as (
    select *
    from {{ ref('snap_pozos_estado') }}
    where dbt_valid_to is null
)
select
    p.pozo_id,
    p.oltp_id,
    p.cuenca,
    p.fecha_perforacion,
    p.estado                          as estado_actual,
    l.grados_api,
    l.pct_agua,
    l.pct_sedimentos,
    m.n_mantenimientos,
    m.ultimo_mantenimiento,
    m.n_correctivos,
    e.dbt_valid_from                  as estado_desde
from {{ ref('stg_pozos') }} p
left join lab_reciente l on l.pozo_id = p.pozo_id and l.rn = 1
left join manto_stats m on m.pozo_id = p.pozo_id
left join estado_actual e on e.pozo_id = p.pozo_id