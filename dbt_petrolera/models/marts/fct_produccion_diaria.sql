-- ===============================================================================
-- fct_produccion_diaria: producción acumulada por pozo/cuenca/día.
-- Grain: pozo + fecha (materializada como tabla, agrega el CSV de producción).
-- ===============================================================================
select
    pd.fecha                     as fecha,
    pd.pozo_id,
    p.cuenca,
    sum(pd.bpd_producido)        as bpd_producido,
    sum(pd.gas_mcfd)             as gas_mcfd,
    sum(pd.horas_operativas)     as horas_operativas,
    avg(pd.bpd_producido)        as bpd_promedio,
    count(*)                     as n_registros
from {{ ref('stg_produccion_diaria') }} pd
left join {{ ref('dim_pozos') }} p
    on p.pozo_id = pd.pozo_id
group by pd.fecha, pd.pozo_id, p.cuenca