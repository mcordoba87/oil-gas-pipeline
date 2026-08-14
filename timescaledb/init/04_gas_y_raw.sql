-- ===============================================================================
-- Fase 3 - Soporte de gas y esquema raw para el loader de landing (MinIO -> TSDB)
-- 1) Agrega la columna gas_mcfd a lecturas_sensores (métrica de gas del simulador).
-- 2) Crea el esquema raw con las tablas de staging donde dbt consume los datos
--    que vienen de MinIO (producción, laboratorio, OLTP, precios, logs SCADA).
-- Idempotente: seguro de re-ejecutar (IF NOT EXISTS).
-- ===============================================================================

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ---------------------------------------------------------------------------
-- 1. Gas en lecturas de sensores (decisión Fase 3: BOE necesita gas)
-- ---------------------------------------------------------------------------
ALTER TABLE lecturas_sensores
    ADD COLUMN IF NOT EXISTS gas_mcfd DOUBLE PRECISION NOT NULL DEFAULT 0;

-- ---------------------------------------------------------------------------
-- 2. Esquema raw: tablas cargadas desde MinIO por ingestion/load_landing_to_raw.py
-- ---------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS raw;

-- Reporte manual de producción diaria (landing/produccion_diaria/YYYY-MM-DD/reporte.csv)
CREATE TABLE IF NOT EXISTS raw.produccion_diaria (
    pozo_id          TEXT,
    fecha            DATE,
    bpd_producido    DOUBLE PRECISION,
    horas_operativas DOUBLE PRECISION,
    observaciones    TEXT,
    gas_mcfd         DOUBLE PRECISION
);

-- Análisis de laboratorio (landing/laboratorio/YYYY-MM-DD/analisis.csv)
CREATE TABLE IF NOT EXISTS raw.laboratorio (
    pozo_id        TEXT,
    fecha          DATE,
    grados_api     DOUBLE PRECISION,
    pct_agua       DOUBLE PRECISION,
    pct_sedimentos DOUBLE PRECISION
);

-- Snapshot de pozos desde OLTP (raw/oltp/YYYY-MM-DD/pozos.csv)
CREATE TABLE IF NOT EXISTS raw.oltp_pozos (
    id                INTEGER,
    nombre            TEXT,
    cuenca            TEXT,
    fecha_perforacion DATE,
    estado            TEXT
);

-- Mantenimientos desde OLTP (raw/oltp/YYYY-MM-DD/mantenimientos.csv)
CREATE TABLE IF NOT EXISTS raw.oltp_mantenimientos (
    id      INTEGER,
    pozo_id INTEGER,
    fecha   DATE,
    tipo    TEXT,
    costo   DOUBLE PRECISION,
    tecnico TEXT
);

-- Paradas programadas desde OLTP (raw/oltp/YYYY-MM-DD/paradas_programadas.csv)
CREATE TABLE IF NOT EXISTS raw.oltp_paradas (
    id           INTEGER,
    pozo_id      INTEGER,
    fecha_inicio TIMESTAMP,
    fecha_fin    TIMESTAMP,
    motivo       TEXT
);

-- Precios WTI/Brent (raw/precios/YYYY-MM-DD.json)
CREATE TABLE IF NOT EXISTS raw.precios (
    fecha          DATE,
    timestamp      TIMESTAMPTZ,
    wti_usd_bbl    DOUBLE PRECISION,
    brent_usd_bbl  DOUBLE PRECISION,
    fuente         TEXT
);

-- Logs SCADA semi-estructurados (raw/logs_scada/YYYY-MM-DD/scada.jsonl)
CREATE TABLE IF NOT EXISTS raw.scada_logs (
    timestamp   TIMESTAMPTZ,
    evento      TEXT,
    descripcion TEXT,
    pozo_id     TEXT,
    nivel       TEXT,
    fuente      TEXT
);

-- Registro de objetos de MinIO ya cargados (evita duplicados en modo append y
-- controla el snapshot más reciente en modo replace).
CREATE TABLE IF NOT EXISTS raw.carga_registros (
    tabla      TEXT NOT NULL,
    key        TEXT NOT NULL,
    cargado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tabla, key)
);