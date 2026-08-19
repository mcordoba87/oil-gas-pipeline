#!/usr/bin/env bash
# ===============================================================================
# Smoke test de la App móvil de campo (Fase 4, item 4.4): verifica que el
# servicio esté sano, que pueda registrar un dispositivo, que un push inyectado
# llegue por MQTT (topic notificaciones/{device_id}) y quede en el inbox (REST).
# Uso: bash scripts/verify_campo_app.sh
# ===============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

set -a
# shellcheck disable=SC1091
source "$PROJECT_DIR/.env"
set +a

BASE="http://localhost:${CAMPO_APP_PORT:-8010}"
DEVICE="verify-campo-app-$$"
SUB_LOG="$(mktemp)"
trap 'rm -f "$SUB_LOG"' EXIT

api() { curl -sf -H "X-API-Key: $API_KEY" "$@"; }

echo "===== 1. Estado del servicio ====="
docker compose -f "$PROJECT_DIR/docker-compose.yml" ps campo_app

echo "===== 2. Health ====="
curl -sf "$BASE/health" | python3 -m json.tool

echo "===== 3. Registrar dispositivo ====="
api -X POST "$BASE/dispositivos" -H "Content-Type: application/json" \
  -d "{\"device_id\":\"$DEVICE\",\"operador\":\"operador-verify\",\"plataforma\":\"web\"}" \
  | python3 -m json.tool

echo "===== 4. Suscribir a MQTT (notificaciones/$DEVICE) ====="
docker compose -f "$PROJECT_DIR/docker-compose.yml" exec -T mosquitto \
  mosquitto_sub -h localhost -p 1883 -t "notificaciones/$DEVICE" -C 1 -W 15 \
  > "$SUB_LOG" 2>/dev/null &
SUB_PID=$!
sleep 1

echo "===== 5. Inyectar push de presión ====="
api -X POST "$BASE/push/inyectar" -H "Content-Type: application/json" \
  -d '{"pozo_id":"PZ-001","severidad":"critical","mensaje":"PRUEBA verify_campo_app (presión)"}' \
  | python3 -m json.tool

wait "$SUB_PID" || true
echo "  Mensaje MQTT recibido:"
cat "$SUB_LOG"

echo "===== 6. Inbox del dispositivo ====="
api "$BASE/dispositivos/$DEVICE/notificaciones?leida=no_leidas" | python3 -c "
import sys, json
p = json.load(sys.stdin)
print('  notificaciones no leidas =', p['total'])
for n in p['notificaciones']:
    print('   -', n['id'], n['pozo_id'], n['tipo'], n['severidad'], '|', n['mensaje'])
assert p['total'] >= 1, 'debe existir al menos 1 notificacion en el inbox'
"

echo "===== 7. Marcar como leída ====="
NID=$(api "$BASE/dispositivos/$DEVICE/notificaciones?leida=no_leidas" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['notificaciones'][0]['id'])")
api -X POST "$BASE/notificaciones/$NID/leida"

echo ""
echo "===== App móvil de campo OK ====="
