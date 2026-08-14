-- ===============================================================================
-- fct_alertas_anomalias: persiste las anomalías detectadas en la hypertable
-- `alertas` (schema public). Consumida por la API (Fase 4) y Grafana.
--
-- Estrategia incremental (delete+insert sobre unique_key time+pozo_id+tipo):
--   * inserciones nuevas solo si no hay ya una alerta abierta del mismo
--     (pozo_id, tipo) -> evita duplicar la regla de mantenimiento.
--   * pre-hook de resolución: cierra (estado='resuelta') las alertas abiertas
--     cuya condición ya no se cumple en el set de candidatas actual.
-- ===============================================================================
{{ config(
    materialized='incremental',
    incremental_strategy='delete+insert',
    alias='alertas',
    unique_key=['time', 'pozo_id', 'tipo'],
    pre_hook="""
        update public.alertas a
        set estado = 'resuelta', fecha_resolucion = now()
        where a.estado = 'abierta'
          and not exists (
              select 1 from {{ ref('int_alertas_candidatas') }} c
              where c.pozo_id = a.pozo_id and c.tipo = a.tipo
          )
    """,
) }}

select
    c.time,
    c.pozo_id,
    c.tipo,
    c.severidad,
    c.mensaje,
    'abierta'                          as estado,
    null::timestamptz                  as fecha_resolucion
from {{ ref('int_alertas_candidatas') }} c

{% if is_incremental() %}
where not exists (
        select 1
        from {{ this }} a
        where a.estado = 'abierta'
          and a.pozo_id = c.pozo_id
          and a.tipo = c.tipo
    )
  and c.time > (select coalesce(max(time) - interval '1 day', 'epoch'::timestamptz) from {{ this }})
{% endif %}