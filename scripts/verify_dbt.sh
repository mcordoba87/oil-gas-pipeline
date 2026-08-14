#!/usr/bin/env bash
# ===============================================================================
# Smoke test de la Fase 3: verifica las capas dbt (staging/intermediate/marts)
# y las tablas raw cargadas desde MinIO. Requiere stack arriba + datos cargados.
# Uso: bash scripts/verify_dbt.sh
# ===============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

set -a
# shellcheck disable=SC1091
source "$PROJECT_DIR/.env"
set +a

DBT="$PROJECT_DIR/.venv/bin/dbt"
DBT_DIR="$PROJECT_DIR/dbt_petrolera"
SERVICE="timescaledb"
COMPOSE=(docker compose -f "$PROJECT_DIR/docker-compose.yml")

run_psql() {
  "${COMPOSE[@]}" exec -T "$SERVICE" \
    psql -U "$TSDB_POSTGRES_USER" -d "$TSDB_POSTGRES_DB" -c "$1"
}

echo "===== 1. Esquema raw (loader MinIO) ====="
run_psql "SELECT table_name FROM information_schema.tables
          WHERE table_schema='raw' ORDER BY table_name;"

echo "===== 2. Conteos raw ====="
run_psql "SELECT (SELECT count(*) FROM raw.produccion_diaria)  AS produccion,
                 (SELECT count(*) FROM raw.laboratorio)        AS laboratorio,
                 (SELECT count(*) FROM raw.oltp_pozos)         AS pozos_oltp,
                 (SELECT count(*) FROM raw.oltp_mantenimientos) AS mantenimientos,
                 (SELECT count(*) FROM raw.precios)            AS precios,
                 (SELECT count(*) FROM raw.scada_logs)         AS scada_logs;"

echo "===== 3. dbt run (todas las capas) ====="
cd "$DBT_DIR"
"$DBT" run --no-partial-parse

echo "===== 4. dbt test ====="
"$DBT" test --no-partial-parse

echo "===== 5. dbt snapshot ====="
"$DBT" snapshot --no-partial-parse

echo "===== 6. Conteos de marts ====="
run_psql "SELECT (SELECT count(*) FROM marts.fct_produccion_diaria) AS prod_diaria,
                 (SELECT count(*) FROM marts.fct_boe)              AS boe,
                 (SELECT count(*) FROM marts.fct_curvas_declinacion) AS declinacion,
                 (SELECT count(*) FROM public.alertas)             AS alertas;"

echo "===== 7. Muestras de marts ====="
run_psql "SELECT pozo_id, fecha, round(bpd_producido::numeric,1) AS bpd,
                 round(gas_mcfd::numeric,1) AS gas
          FROM marts.fct_produccion_diaria ORDER BY fecha DESC, pozo_id LIMIT 5;"
run_psql "SELECT pozo_id, fecha, round(boe_bbl::numeric,1) AS boe_bbl
          FROM marts.fct_boe ORDER BY fecha DESC, pozo_id LIMIT 5;"
run_psql "SELECT pozo_id, round(qi_bpd::numeric,1) AS qi, round(tasa_declinacion_d::numeric,4) AS D,
                 round(r2::numeric,3) AS r2
          FROM marts.fct_curvas_declinacion ORDER BY r2 DESC LIMIT 5;"
run_psql "SELECT pozo_id, tipo, severidad, estado, count(*)
          FROM public.alertas GROUP BY pozo_id, tipo, severidad, estado
          ORDER BY count(*) DESC LIMIT 10;"

echo "===== 8. Snapshot SCD Type 2 (historial de estados) ====="
run_psql "SELECT pozo_id, estado, count(*) AS versiones
          FROM snapshots.snap_pozos_estado
          GROUP BY pozo_id, estado ORDER BY versiones DESC LIMIT 10;"