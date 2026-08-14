-- ===============================================================================
-- int_lecturas_interpoladas: relleno de huecos horarios por pozo (forward-fill).
-- Los sensores pierden mensajes (probabilidad simulada) -> hay buckets horarios
-- sin datos. Estrategia: forward-fill (último valor conocido por métrica) usando
-- el patrón count+max de Postgres (no soporta IGNORE NULLS nativamente).
-- Los huecos iniciales (sin valor previo) quedan NULL y se marcan es_interpolado.
-- Basado en los promedios horarios (lecturas_hora, continuous aggregate).
-- NOTA: interpolación lineal queda como mejora futura (requiere ventanas con
-- IGNORE NULLS no disponibles en Postgres vanilla).
-- ===============================================================================
with grilla as (
    select
        p.pozo_id,
        generate_series(min(h.bucket), max(h.bucket), interval '1 hour') as hora
    from {{ source('timescale', 'pozos') }} p
    join {{ source('timescale', 'lecturas_hora') }} h
        on h.pozo_id = p.pozo_id
    group by p.pozo_id
),
datos as (
    select
        grilla.pozo_id,
        grilla.hora,
        h.presion_prom,
        h.temperatura_prom,
        h.caudal_prom,
        h.n_lecturas
    from grilla
    left join {{ source('timescale', 'lecturas_hora') }} h
        on h.pozo_id = grilla.pozo_id
        and h.bucket = grilla.hora
),
con_grupos as (
    select
        pozo_id,
        hora,
        presion_prom,
        temperatura_prom,
        caudal_prom,
        n_lecturas,
        count(presion_prom) over (partition by pozo_id order by hora)   as grp_presion,
        count(temperatura_prom) over (partition by pozo_id order by hora) as grp_temp,
        count(caudal_prom) over (partition by pozo_id order by hora)    as grp_caudal
    from datos
)
select
    pozo_id,
    hora,
    round(coalesce(
        presion_prom,
        max(presion_prom) over (partition by pozo_id, grp_presion)
    )::numeric, 2) as presion_psi,
    round(coalesce(
        temperatura_prom,
        max(temperatura_prom) over (partition by pozo_id, grp_temp)
    )::numeric, 2) as temperatura_c,
    round(coalesce(
        caudal_prom,
        max(caudal_prom) over (partition by pozo_id, grp_caudal)
    )::numeric, 2) as caudal_bpd,
    coalesce(n_lecturas, 0) as n_lecturas,
    case when n_lecturas is null then true else false end as es_interpolado
from con_grupos