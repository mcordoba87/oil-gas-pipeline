-- ===============================================================================
-- stg_precios: normalización de precios WTI/Brent (mock API -> raw/precios/*.json).
-- ===============================================================================
select
    fecha::date                 as fecha,
    timestamp::timestamptz      as timestamp,
    wti_usd_bbl::double precision   as wti_usd_bbl,
    brent_usd_bbl::double precision as brent_usd_bbl,
    fuente::text                as fuente
from {{ source('raw', 'precios') }}