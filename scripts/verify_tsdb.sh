#!/usr/bin/env bash
# ===============================================================================
# Smoke test de la Fase 2: verifica esquema, agregados y políticas en TimescaleDB.
# Uso: bash scripts/verify_tsdb.sh
# ===============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

set -a
# shellcheck disable=SC1091
source "$PROJECT_DIR/.env"
set +a

SERVICE="timescaledb"
COMPOSE=(docker compose -f "$PROJECT_DIR/docker-compose.yml")

run_psql() {
  "${COMPOSE[@]}" exec -T "$SERVICE" \
    psql -U "$TSDB_POSTGRES_USER" -d "$TSDB_POSTGRES_DB" -c "$1"
}

echo "===== 1. Tablas de la Fase 2 ====="
run_psql "SELECT table_name FROM information_schema.tables
          WHERE table_schema='public'
            AND table_name IN ('pozos','cuencas','alertas','lecturas_sensores')
          ORDER BY table_name;"

echo "===== 2. Hypertables ====="
run_psql "SELECT hypertable_name FROM timescaledb_information.hypertables;"

echo "===== 3. Continuous aggregates ====="
run_psql "SELECT view_name, materialization_hypertable_name, materialized_only
          FROM timescaledb_information.continuous_aggregates;"

echo "===== 4. Políticas de retención / compresión / refresh ====="
run_psql "SELECT hypertable_name, application_name, schedule_interval, config
          FROM timescaledb_information.jobs
          WHERE application_name LIKE '%Policy%'
          ORDER BY hypertable_name;"

echo "===== 5. Conteos ====="
run_psql "SELECT (SELECT count(*) FROM pozos)          AS pozos,
                 (SELECT count(*) FROM cuencas)        AS cuencas,
                 (SELECT count(*) FROM alertas)        AS alertas,
                 (SELECT count(*) FROM lecturas_sensores) AS lecturas;"

echo "===== 6. Muestras de agregados ====="
run_psql "SELECT bucket, pozo_id, round(presion_prom::numeric,1) AS presion_prom,
                 round(caudal_prom::numeric,1) AS caudal_prom, n_lecturas
          FROM lecturas_hora ORDER BY bucket DESC LIMIT 5;"
run_psql "SELECT bucket, cuenca_id, round(caudal_prom::numeric,1) AS caudal_prom
          FROM lecturas_hora_cuenca ORDER BY bucket DESC LIMIT 5;"