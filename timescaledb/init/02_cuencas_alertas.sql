-- ===============================================================================
-- Fase 2 - Diseño de esquema (roadmap 2.1/2.2)
-- Dimensiones (cuencas), enriquecimiento de pozos y hypertable de alertas.
-- Idempotente: seguro de re-ejecutar (IF NOT EXISTS).
-- ===============================================================================

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ---------------------------------------------------------------------------
-- Dimensión de cuencas
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cuencas (
    cuenca_id   SERIAL PRIMARY KEY,
    nombre      TEXT UNIQUE NOT NULL,
    region      TEXT,
    descripcion TEXT
);

-- Enriquecer tabla de pozos (el maestro real vive en OLTP; acá solo espejo
-- de trabajo para joins y agregados en TSDB).
ALTER TABLE pozos
    ADD COLUMN IF NOT EXISTS cuenca_id        INTEGER REFERENCES cuencas(cuenca_id),
    ADD COLUMN IF NOT EXISTS fecha_perforacion DATE,
    ADD COLUMN IF NOT EXISTS tipo             TEXT;

CREATE INDEX IF NOT EXISTS idx_pozos_cuenca_id ON pozos (cuenca_id);

-- ---------------------------------------------------------------------------
-- Hypertable de alertas (consumida por Fase 3 fct_alertas_anomalias y Fase 4 API)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS alertas (
    time              TIMESTAMPTZ NOT NULL,
    pozo_id           TEXT        NOT NULL,
    tipo              TEXT        NOT NULL,  -- presion_critica, caudal_bajo, mantenimiento_vencido, ...
    severidad         TEXT        NOT NULL,  -- info, warning, critical
    mensaje           TEXT,
    estado            TEXT        NOT NULL DEFAULT 'abierta',  -- abierta, resuelta
    fecha_resolucion  TIMESTAMPTZ
);

SELECT create_hypertable(
    'alertas',
    by_range('time', INTERVAL '7 days'),
    if_not_exists => TRUE
);

-- Índices para consultas por pozo + rango temporal y por estado abierto
CREATE INDEX IF NOT EXISTS idx_alertas_pozo_time
    ON alertas (pozo_id, time DESC);

CREATE INDEX IF NOT EXISTS idx_alertas_estado
    ON alertas (estado) WHERE estado = 'abierta';

-- Políticas de ciclo de vida de alertas (roadmap 2.2)
SELECT add_retention_policy('alertas', INTERVAL '1 year', if_not_exists => TRUE);

ALTER TABLE alertas SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'pozo_id'
);
SELECT add_compression_policy('alertas', INTERVAL '30 days', if_not_exists => TRUE);