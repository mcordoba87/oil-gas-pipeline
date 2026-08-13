#!/usr/bin/env bash
# ===============================================================================
# Aplica migraciones de esquema a TimescaleDB (Fase 2)
# El SQL de init/ solo corre al crear el volumen por primera vez; este script
# re-aplica los archivos de init a una base ya existente (todos idempotentes).
# Uso: bash scripts/apply_tsdb_migrations.sh
# ===============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
INIT_DIR="$PROJECT_DIR/timescaledb/init"

# Cargar credenciales del .env del proyecto
set -a
# shellcheck disable=SC1091
source "$PROJECT_DIR/.env"
set +a

CONTAINER="oilgas-timescaledb"

# Flags para docker compose: "-T" evita TTY
COMPOSE=(docker compose -f "$PROJECT_DIR/docker-compose.yml")

if [ ! -d "$INIT_DIR" ]; then
  echo "ERROR: no existe $INIT_DIR" >&2
  exit 1
fi

echo "Aplicando migraciones de $INIT_DIR a $CONTAINER ..."
for f in "$INIT_DIR"/*.sql; do
  echo "--- $(basename "$f")"
  "${COMPOSE[@]}" exec -T "$CONTAINER" \
    psql -v ON_ERROR_STOP=1 \
         -U "$TSDB_POSTGRES_USER" \
         -d "$TSDB_POSTGRES_DB" \
         -f "/docker-entrypoint-initdb.d/$(basename "$f")"
done

echo "=== Migraciones aplicadas. Políticas activas: ==="
"${COMPOSE[@]}" exec -T "$CONTAINER" \
  psql -U "$TSDB_POSTGRES_USER" -d "$TSDB_POSTGRES_DB" -c \
  "SELECT hypertable_name, job_type, schedule_interval FROM timescaledb_information.jobs ORDER BY hypertable_name;"