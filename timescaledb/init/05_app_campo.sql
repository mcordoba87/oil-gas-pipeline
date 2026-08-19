-- ===============================================================================
-- Fase 4, item 4.4 - App móvil de campo
-- Tablas de soporte del backend de la app (api/campo_app_api.py):
--   * dispositivos_campo : celulares/tablets de operadores de campo registrados.
--   * notificaciones     : inbox persistente de los push simulados (canal mqtt,
--                          poll o inyectada). Fuente de verdad para la app.
--   * push_watermark     : marca de agua del dispatcher para no re-despachar
--                          alertas de presión ya notificadas.
-- Idempotente (IF NOT EXISTS).
-- ===============================================================================

CREATE TABLE IF NOT EXISTS dispositivos_campo (
    id          SERIAL PRIMARY KEY,
    device_id   TEXT UNIQUE NOT NULL,
    operador    TEXT,
    plataforma  TEXT        NOT NULL DEFAULT 'android',
    activo      BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS notificaciones (
    id            BIGSERIAL PRIMARY KEY,
    time          TIMESTAMPTZ NOT NULL DEFAULT now(),
    dispositivo_id TEXT       NOT NULL,
    pozo_id       TEXT        NOT NULL,
    tipo          TEXT        NOT NULL,   -- presion_zscore, fuera_rango_fisico, inyectada
    severidad     TEXT        NOT NULL,   -- info, warning, critical
    mensaje       TEXT,
    canal         TEXT        NOT NULL,   -- mqtt (dispatcher realtime), poll (fallback), inyectada (manual)
    leida         BOOLEAN     NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_notif_dispositivo_time
    ON notificaciones (dispositivo_id, time DESC);

CREATE TABLE IF NOT EXISTS push_watermark (
    id              INT PRIMARY KEY CHECK (id = 1),
    ultima_alerta_ts TIMESTAMPTZ NOT NULL
);
