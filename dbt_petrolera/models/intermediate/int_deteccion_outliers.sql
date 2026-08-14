-- ===============================================================================
-- int_deteccion_outliers: flagging de outliers por z-score.
-- Sobre los promedios horarios por pozo, se calcula la media y desviación
-- estándar de presión y caudal en una ventana móvil (últimos 7 días) y se
-- marca la lectura como outlier si |z| > umbral (var: alert_zscore_umbral, 3).
-- La ventana se resuelve con self-join en buckets horarios.
-- ===============================================================================
{% set z_umbral = var('alert_zscore_umbral') %}
{% set ventana = var('alert_caudal_ventana_horas', 24) %}
{% set ventana_dias = 7 %}

with base as (
    select
        h.pozo_id,
        h.bucket as hora,
        h.presion_prom,
        h.caudal_prom
    from {{ source('timescale', 'lecturas_hora') }} h
),
estadistica as (
    select
        b.pozo_id,
        b.hora,
        b.presion_prom,
        b.caudal_prom,
        avg(b.presion_prom) over (
            partition by b.pozo_id
            order by b.hora
            rows between ({{ ventana_dias * 24 }}) preceding and current row
        ) as presion_media,
        stddev_samp(b.presion_prom) over (
            partition by b.pozo_id
            order by b.hora
            rows between ({{ ventana_dias * 24 }}) preceding and current row
        ) as presion_stddev,
        avg(b.caudal_prom) over (
            partition by b.pozo_id
            order by b.hora
            rows between ({{ ventana_dias * 24 }}) preceding and current row
        ) as caudal_media,
        stddev_samp(b.caudal_prom) over (
            partition by b.pozo_id
            order by b.hora
            rows between ({{ ventana_dias * 24 }}) preceding and current row
        ) as caudal_stddev
    from base b
)
select
    pozo_id,
    hora,
    presion_prom,
    caudal_prom,
    presion_media,
    presion_stddev,
    case
        when presion_stddev is not null and presion_stddev > 0
        then abs(presion_prom - presion_media) / presion_stddev
        else 0
    end as presion_zscore,
    caudal_media,
    caudal_stddev,
    case
        when caudal_stddev is not null and caudal_stddev > 0
        then abs(caudal_prom - caudal_media) / caudal_stddev
        else 0
    end as caudal_zscore,
    case
        when (presion_stddev is not null and presion_stddev > 0
              and abs(presion_prom - presion_media) / presion_stddev > {{ z_umbral }})
          or (caudal_stddev is not null and caudal_stddev > 0
              and abs(caudal_prom - caudal_media) / caudal_stddev > {{ z_umbral }})
        then true
        else false
    end as es_outlier
from estadistica