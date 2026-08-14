-- ===============================================================================
-- fct_curvas_declinacion: ajuste de curvas de declinación de Arps (exponencial).
-- Modelo exponencial: q(t) = q_i * exp(-D * t)  ->  ln(q) = ln(q_i) - D*t.
-- Se ajusta por regresión lineal de ln(bpd) sobre el tiempo (días desde la
-- primera lectura) con regr_slope/intercept/r2 de Postgres, usando la ventana
-- de producción diaria más reciente (var: declinacion_ventana_dias, 90 días).
-- La tasa D resultante es por día. La declinación hiperbólica queda como
-- mejora futura (requiere ajuste no lineal).
-- ===============================================================================
{% set ventana_dias = var('declinacion_ventana_dias') %}
with produccion as (
    select
        pozo_id,
        fecha,
        max(bpd_producido) as bpd
    from {{ ref('stg_produccion_diaria') }}
    where fecha >= (current_date - {{ ventana_dias }})
    group by pozo_id, fecha
),
serie as (
    select
        pozo_id,
        fecha,
        bpd,
        extract(epoch from (fecha - min(fecha) over (partition by pozo_id)) * interval '1 day') / 86400.0 as dias,
        ln(bpd) as ln_bpd
    from produccion
    where bpd > 0
),
ajuste as (
    select
        pozo_id,
        count(*)                                           as n_dias,
        regr_intercept(ln_bpd, dias)                       as intercept,
        regr_slope(ln_bpd, dias)                           as slope,
        regr_r2(ln_bpd, dias)                              as r2,
        min(fecha)                                         as inicio_ventana,
        max(fecha)                                         as fin_ventana
    from serie
    group by pozo_id
)
select
    a.pozo_id,
    p.cuenca,
    case when a.n_dias >= 2 then exp(a.intercept) end as qi_bpd,
    case when a.n_dias >= 2 then -1.0 * a.slope end    as tasa_declinacion_d,
    a.r2,
    a.n_dias,
    a.inicio_ventana,
    a.fin_ventana,
    'exponencial' as tipo
from ajuste a
left join {{ ref('dim_pozos') }} p
    on p.pozo_id = a.pozo_id
where a.n_dias >= 2