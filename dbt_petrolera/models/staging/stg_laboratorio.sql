-- ===============================================================================
-- stg_laboratorio: limpieza del CSV de análisis de laboratorio (calidad de crudo).
-- Grados API típicos entre 10 y 60; agua/sedimentos son porcentajes 0-100.
-- ===============================================================================
select
    pozo_id::text                  as pozo_id,
    fecha::date                    as fecha,
    grados_api::double precision   as grados_api,
    pct_agua::double precision     as pct_agua,
    pct_sedimentos::double precision as pct_sedimentos
from {{ source('raw', 'laboratorio') }}