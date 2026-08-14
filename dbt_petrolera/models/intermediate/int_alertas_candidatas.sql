-- ===============================================================================
-- int_alertas_candidatas: detección de anomalías según las 4 reglas del roadmap.
--   1) z-score de presión > umbral (3) en ventana móvil (int_deteccion_outliers)
--   2) caída abrupta de caudal: hora actual < 50% del promedio 24h previo
--   3) mantenimiento vencido según CMMS: días desde el último mantenimiento
--      supera el umbral del tipo (var: mantenimiento_dias_por_tipo)
--   4) lectura fuera de rango físico esperado (presión, temperatura, caudal, gas)
-- Este CTE alimenta fct_alertas_anomalias (incremental sobre la hypertable
-- alertas). Se limita a la ventana reciente para no reprocesar todo el histórico.
-- ===============================================================================
{% set z_umbral = var('alert_zscore_umbral') %}
{% set drop_factor = var('alert_caudal_drop_factor') %}
{% set ventana_h = var('alert_caudal_ventana_horas', 24) %}
{% set presion_min, presion_max = var('alert_rango_presion') %}
{% set temp_min, temp_max = var('alert_rango_temp') %}

-- Regla 1: z-score de presión
with regla_1 as (
    select
        hora                    as time,
        pozo_id,
        'presion_zscore'        as tipo,
        'warning'               as severidad,
        'Presión con desviación extrema (z-score > ' || {{ z_umbral }} || ')' as mensaje
    from {{ ref('int_deteccion_outliers') }}
    where presion_zscore > {{ z_umbral }}
),

-- Regla 2: caída abrupta de caudal en ventana móvil
regla_2 as (
    with caudal_hora as (
        select
            bucket as hora,
            pozo_id,
            caudal_prom
        from {{ source('timescale', 'lecturas_hora') }}
    ),
    con_promedio as (
        select
            c.hora,
            c.pozo_id,
            c.caudal_prom,
            avg(c.caudal_prom) over (
                partition by c.pozo_id
                order by c.hora
                rows between {{ ventana_h }} preceding and 1 preceding
            ) as caudal_prom_24h
        from caudal_hora c
    )
    select
        hora                    as time,
        pozo_id,
        'caudal_bajo'           as tipo,
        'warning'               as severidad,
        'Caída abrupta de caudal (actual < ' || ({{ drop_factor }} * 100)::int || '% del promedio ' || {{ ventana_h }} || 'h)' as mensaje
    from con_promedio
    where caudal_prom < ({{ drop_factor }} * caudal_prom_24h)
),

-- Regla 3: mantenimiento vencido según CMMS
regla_3 as (
    select
        date_trunc('hour', now()) as time,
        m.pozo_id,
        'mantenimiento_vencido'  as tipo,
        'warning'                 as severidad,
        'Mantenimiento vencido por más de ' || (current_date - m.fecha) || ' días (tipo: ' || m.tipo || ')' as mensaje
    from (
        select distinct on (pozo_id)
            pozo_id,
            fecha,
            tipo
        from {{ ref('stg_mantenimientos') }}
        order by pozo_id, fecha desc
    ) m
    where (current_date - m.fecha) > case m.tipo
        {% for tipo, dias in var('mantenimiento_dias_por_tipo').items() %}
        when '{{ tipo }}' then {{ dias }}
        {% endfor %}
        else 90
    end
),

-- Regla 4: lectura fuera de rango físico esperado
regla_4 as (
    select
        time,
        pozo_id,
        'fuera_rango_fisico'   as tipo,
        'critical'              as severidad,
        case
            when presion_psi < {{ presion_min }} or presion_psi > {{ presion_max }} then 'Presión fuera de rango físico'
            when temperatura_c < {{ temp_min }} or temperatura_c > {{ temp_max }} then 'Temperatura fuera de rango físico'
            when caudal_bpd < 0 then 'Caudal negativo'
            when gas_mcfd < 0 then 'Gas negativo'
        end as mensaje
    from {{ ref('stg_lecturas_sensores') }}
    where time > now() - interval '1 day'
      and (presion_psi < {{ presion_min }} or presion_psi > {{ presion_max }}
           or temperatura_c < {{ temp_min }} or temperatura_c > {{ temp_max }}
           or caudal_bpd < 0 or gas_mcfd < 0)
),

todas as (
    select * from regla_1
    union all
    select * from regla_2
    union all
    select * from regla_3
    union all
    select * from regla_4
)
select
    time,
    pozo_id,
    tipo,
    severidad,
    mensaje
from todas
where time > now() - interval '2 days'