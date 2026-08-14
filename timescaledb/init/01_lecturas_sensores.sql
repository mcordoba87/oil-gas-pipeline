-- ===============================================================================
-- Esquema Time-Series (TimescaleDB) - Fase 1 (adelantado del roadmap 2.1/2.2)
-- Hypertable lecturas_sensores: particionada por tiempo y pozo.
-- ===============================================================================

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Tabla de pozos mínima (referencia de campo). El maestro real vive en OLTP.
CREATE TABLE IF NOT EXISTS pozos (
    pozo_id      TEXT PRIMARY KEY,
    nombre       TEXT NOT NULL,
    cuenca       TEXT NOT NULL,
    estado       TEXT NOT NULL DEFAULT 'activo'
);

-- Lecturas de sensores (hot path)
CREATE TABLE IF NOT EXISTS lecturas_sensores (
    time          TIMESTAMPTZ       NOT NULL,
    pozo_id       TEXT              NOT NULL,
    presion_psi   DOUBLE PRECISION  NOT NULL,
    temperatura_c DOUBLE PRECISION  NOT NULL,
    caudal_bpd    DOUBLE PRECISION  NOT NULL,
    gas_mcfd      DOUBLE PRECISION  NOT NULL DEFAULT 0
);

-- Convertir a hypertable particionada por tiempo (chunks ~1 día)
SELECT create_hypertable(
    'lecturas_sensores',
    by_range('time', INTERVAL '1 day'),
    if_not_exists => TRUE
);

-- Índice para consultas por pozo + rango temporal
CREATE INDEX IF NOT EXISTS idx_lecturas_pozo_time
    ON lecturas_sensores (pozo_id, time DESC);

-- Dedupe de re-entregas MQTT: única lectura por (pozo, tiempo)
CREATE UNIQUE INDEX IF NOT EXISTS uq_lecturas_pozo_time
    ON lecturas_sensores (time, pozo_id);

-- Índice de chunks para el planificador (uso de espacio de chunks)
CREATE INDEX IF NOT EXISTS idx_lecturas_pozo
    ON lecturas_sensores (pozo_id);

-- Política de retención: datos crudos a 90 días (roadmap 2.2)
SELECT add_retention_policy('lecturas_sensores', INTERVAL '90 days', if_not_exists => TRUE);

-- Compresión automática de chunks con más de 7 días (roadmap 2.2)
ALTER TABLE lecturas_sensores SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'pozo_id'
);
SELECT add_compression_policy('lecturas_sensores', INTERVAL '7 days', if_not_exists => TRUE);