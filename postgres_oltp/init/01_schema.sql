-- ===============================================================================
-- Schema Postgres OLTP - ERP/CMMS (roadmap item 5)
-- Se ejecuta automáticamente la primera vez que se inicializa el contenedor.
-- El poblado de datos reales lo hace generators/seed_oltp.py (Fase 1).
-- ===============================================================================

CREATE TABLE IF NOT EXISTS pozos (
    id                 SERIAL PRIMARY KEY,
    nombre             VARCHAR(50)  NOT NULL,
    cuenca             VARCHAR(50)  NOT NULL,
    fecha_perforacion  DATE         NOT NULL,
    estado             VARCHAR(20)  NOT NULL DEFAULT 'activo'
);

CREATE TABLE IF NOT EXISTS mantenimientos (
    id         SERIAL PRIMARY KEY,
    pozo_id    INTEGER      NOT NULL REFERENCES pozos(id),
    fecha      DATE         NOT NULL,
    tipo       VARCHAR(50)  NOT NULL,
    costo      NUMERIC(12,2),
    tecnico    VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS paradas_programadas (
    id           SERIAL PRIMARY KEY,
    pozo_id      INTEGER      NOT NULL REFERENCES pozos(id),
    fecha_inicio TIMESTAMP    NOT NULL,
    fecha_fin    TIMESTAMP    NOT NULL,
    motivo       TEXT
);

CREATE INDEX IF NOT EXISTS idx_mantenimientos_pozo  ON mantenimientos(pozo_id);
CREATE INDEX IF NOT EXISTS idx_paradas_pozo         ON paradas_programadas(pozo_id);