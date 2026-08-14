-- ===============================================================================
-- fct_lecturas: hechos de series temporales unificadas.
-- Grain: una lectura de sensor por (time, pozo_id). Enriquecida con la
-- dimensión de pozos (cuenca) para análisis por cuenca.
-- ===============================================================================
select
    l.time,
    l.pozo_id,
    p.cuenca,
    l.presion_psi,
    l.temperatura_c,
    l.caudal_bpd,
    l.gas_mcfd
from {{ ref('stg_lecturas_sensores') }} l
left join {{ ref('dim_pozos') }} p
    on p.pozo_id = l.pozo_id