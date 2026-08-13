-- ===============================================================================
-- Fase 2 - Continuous Aggregates (roadmap 2.3)
-- Promedios por hora/día por pozo, más vista de negocio por cuenca.
-- Real-time (materialized_only = false): los buckets recientes se calculan
-- sobre el dato en vivo, los antiguos se sirven del materializado.
-- ===============================================================================

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ---------------------------------------------------------------------------
-- Agregado horario por pozo
-- ---------------------------------------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS lecturas_hora
WITH (timescaledb.continuous, timescaledb.materialized_only = false) AS
SELECT
    time_bucket('1 hour', time) AS bucket,
    pozo_id,
    avg(presion_psi)    AS presion_prom,
    min(presion_psi)    AS presion_min,
    max(presion_psi)    AS presion_max,
    avg(temperatura_c)  AS temperatura_prom,
    avg(caudal_bpd)     AS caudal_prom,
    min(caudal_bpd)     AS caudal_min,
    max(caudal_bpd)     AS caudal_max,
    count(*)            AS n_lecturas
FROM lecturas_sensores
GROUP BY bucket, pozo_id
WITH NO DATA;

-- ---------------------------------------------------------------------------
-- Agregado diario por pozo
-- ---------------------------------------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS lecturas_dia
WITH (timescaledb.continuous, timescaledb.materialized_only = false) AS
SELECT
    time_bucket('1 day', time) AS bucket,
    pozo_id,
    avg(presion_psi)    AS presion_prom,
    min(presion_psi)    AS presion_min,
    max(presion_psi)    AS presion_max,
    avg(temperatura_c)  AS temperatura_prom,
    avg(caudal_bpd)     AS caudal_prom,
    min(caudal_bpd)     AS caudal_min,
    max(caudal_bpd)     AS caudal_max,
    count(*)            AS n_lecturas
FROM lecturas_sensores
GROUP BY bucket, pozo_id
WITH NO DATA;

-- ---------------------------------------------------------------------------
-- Agregado horario por cuenca (vista de negocio)
-- ---------------------------------------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS lecturas_hora_cuenca
WITH (timescaledb.continuous, timescaledb.materialized_only = false) AS
SELECT
    time_bucket('1 hour', l.time) AS bucket,
    p.cuenca_id,
    avg(l.presion_psi)   AS presion_prom,
    avg(l.temperatura_c) AS temperatura_prom,
    avg(l.caudal_bpd)    AS caudal_prom,
    count(*)             AS n_lecturas
FROM lecturas_sensores l
JOIN pozos p ON p.pozo_id = l.pozo_id
GROUP BY bucket, p.cuenca_id
WITH NO DATA;

-- ---------------------------------------------------------------------------
-- Índices para queries por pozo + bucket
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_lecturas_hora_pozo_bucket
    ON lecturas_hora (pozo_id, bucket DESC);

CREATE INDEX IF NOT EXISTS idx_lecturas_dia_pozo_bucket
    ON lecturas_dia (pozo_id, bucket DESC);

CREATE INDEX IF NOT EXISTS idx_lecturas_hora_cuenca_bucket
    ON lecturas_hora_cuenca (cuenca_id, bucket DESC);

-- ---------------------------------------------------------------------------
-- Políticas de refresh
--   lecturas_hora:          materializa hasta hace 1h, refresca cada 1h, 3 días atrás
--   lecturas_dia:           materializa hasta ayer, refresca cada 1 día, 7 días atrás
--   lecturas_hora_cuenca:   igual que lecturas_hora
-- ---------------------------------------------------------------------------
SELECT add_continuous_aggregate_policy(
    'lecturas_hora',
    start_offset => INTERVAL '3 days',
    end_offset   => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

SELECT add_continuous_aggregate_policy(
    'lecturas_dia',
    start_offset => INTERVAL '7 days',
    end_offset   => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

SELECT add_continuous_aggregate_policy(
    'lecturas_hora_cuenca',
    start_offset => INTERVAL '3 days',
    end_offset   => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- Materialización inicial del histórico ya existente
CALL refresh_continuous_aggregate('lecturas_hora', NOW() - INTERVAL '90 days', NOW());
CALL refresh_continuous_aggregate('lecturas_dia', NOW() - INTERVAL '90 days', NOW());
CALL refresh_continuous_aggregate('lecturas_hora_cuenca', NOW() - INTERVAL '90 days', NOW());