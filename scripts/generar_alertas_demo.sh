#!/usr/bin/env bash
# ===============================================================================
# Genera alertas de PRESIÓN abiertas en TimescaleDB para que el dispatcher de la
# app móvil las entregue al teléfono (inbox + MQTT). Útil para demos.
# Las alertas reales las genera dbt (fct_alertas_anomalias); este script es un
# atajo para demostrar el flujo de notificaciones al instante.
# Uso: bash scripts/generar_alertas_demo.sh [N]
# ===============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
N="${1:-3}"

set -a
# shellcheck disable=SC1091
source "$PROJECT_DIR/.env"
set +a

WELLS="PZ-005 PZ-012 PZ-020 PZ-014 PZ-023 PZ-007 PZ-010 PZ-017"

echo "=== Insertando $N alerta(s) de presión abierta ==="
for i in $(seq 1 "$N"); do
  POZO=$(echo $WELLS | tr ' ' '\n' | shuf -n 1)
  TIPO=$([ $((RANDOM % 2)) -eq 0 ] && echo "presion_zscore" || echo "fuera_rango_fisico")
  SEV=$([ "$TIPO" = "presion_zscore" ] && echo "warning" || echo "critical")
  docker compose -f "$PROJECT_DIR/docker-compose.yml" exec -T timescaledb \
    psql -v ON_ERROR_STOP=1 -U "$TSDB_POSTGRES_USER" -d "$TSDB_POSTGRES_DB" -c \
    "INSERT INTO alertas (time, pozo_id, tipo, severidad, mensaje)
     VALUES (now(), '$POZO', '$TIPO', '$SEV', 'Demo: alerta de presión en $POZO')
     RETURNING pozo_id, tipo, severidad;" | tail -3
done

echo "=== El dispatcher (intervalo ${CAMPO_APP_PUSH_INTERVAL_SEC:-10}s) las entregará al teléfono. ==="