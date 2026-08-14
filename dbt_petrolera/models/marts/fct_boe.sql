-- ===============================================================================
-- fct_boe: Barriles Equivalentes de Petróleo (BOE).
-- Conversión a unidad común: 1 bbl de petróleo = 1 BOE; 1 mcf de gas ≈ 1/6 BOE
-- (factor configurable, var: boe_factor_gas). Grain: pozo + día, con cuenca.
-- ===============================================================================
{% set factor = var('boe_factor_gas') %}
select
    fecha,
    pozo_id,
    cuenca,
    bpd_producido,
    gas_mcfd,
    bpd_producido + (gas_mcfd / {{ factor }}) as boe_bbl
from {{ ref('fct_produccion_diaria') }}