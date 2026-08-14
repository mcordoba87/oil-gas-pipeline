-- ===============================================================================
-- stg_lecturas_sensores: tipado + normalización + dedup de lecturas crudas.
-- Unidades estándar: presion (psi), temperatura (C), caudal (BPD), gas (mcfd).
-- Dedupe defensivo por (time, pozo_id): el unique index de la hypertable ya
-- protege contra re-entregas MQTT, pero lo reforzamos para ventanas de carga.
-- ===============================================================================
with deduped as (
    select
        time,
        pozo_id,
        presion_psi,
        temperatura_c,
        caudal_bpd,
        gas_mcfd,
        row_number() over (partition by time, pozo_id order by time) as rn
    from {{ source('timescale', 'lecturas_sensores') }}
)
select
    time,
    pozo_id,
    presion_psi::double precision        as presion_psi,
    temperatura_c::double precision      as temperatura_c,
    caudal_bpd::double precision         as caudal_bpd,
    gas_mcfd::double precision           as gas_mcfd
from deduped
where rn = 1