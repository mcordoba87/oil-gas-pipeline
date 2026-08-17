#!/usr/bin/env bash
# ===============================================================================
# Smoke test de Superset (Fase 4, item 4.2): verifica que el servicio esté sano,
# que TimescaleDB esté registrada como database y que los datasets de los marts
# existan. Además ejecuta un SELECT de prueba a través del SQL Lab de Superset
# para validar la conexión end-to-end.
# Uso: bash scripts/verify_superset.sh
# ===============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

set -a
# shellcheck disable=SC1091
source "$PROJECT_DIR/.env"
set +a

SUPERSET_URL="${SUPERSET_URL:-http://localhost:${SUPERSET_PORT:-8088}}"
COOKIE_JAR="$(mktemp)"
CSRF=""
trap 'rm -f "$COOKIE_JAR"' EXIT

api() {
  # api <metodo> <path> [body_json]
  local method="$1" path="$2" body="${3:-}"
  if [ -n "$body" ]; then
    curl -sfL -X "$method" "$SUPERSET_URL$path" -H "Content-Type: application/json" \
      -H "Authorization: Bearer $TOKEN" -H "X-CSRF-Token: $CSRF" \
      -b "$COOKIE_JAR" -c "$COOKIE_JAR" -d "$body"
  else
    curl -sfL -X "$method" "$SUPERSET_URL$path" -H "Authorization: Bearer $TOKEN" \
      -H "X-CSRF-Token: $CSRF" -b "$COOKIE_JAR" -c "$COOKIE_JAR"
  fi
}

echo "===== 1. Estado del servicio ====="
docker compose -f "$PROJECT_DIR/docker-compose.yml" ps superset

echo "===== 2. Login admin ====="
LOGIN=$(curl -sf -X POST "$SUPERSET_URL/api/v1/security/login" \
  -H "Content-Type: application/json" \
  -c "$COOKIE_JAR" \
  -d "{\"username\":\"$SUPERSET_ADMIN_USER\",\"password\":\"$SUPERSET_ADMIN_PASSWORD\",\"provider\":\"db\",\"refresh\":true}")
TOKEN=$(python3 -c "import sys,json; print(json.loads('''$LOGIN''')['access_token'])")
CSRF=$(api GET "/api/v1/security/csrf_token/" | python3 -c "import sys,json; print(json.load(sys.stdin)['result'])")
echo "  Token OK."

echo "===== 3. Database TimescaleDB registrada ====="
api GET "/api/v1/database/?q=(filters:!((col:database_name,opr:eq,value:TimescaleDB)))" \
  | python3 -c "import sys,json; p=json.load(sys.stdin); print('  count =', p['count']); [print('   -', r['id'], r['database_name']) for r in p['result']]"

echo "===== 4. Datasets de marts ====="
api GET "/api/v1/dataset/?q=(columns:!(table_name,schema,database.database_name),order_column:table_name,order_direction:asc)" \
  | python3 -c "import sys,json; p=json.load(sys.stdin); print('  count =', p['count']); [print('   -', r['schema']+'.'+r['table_name'], '('+r['database']['database_name']+')') for r in p['result']]"

echo "===== 5. Query de prueba via SQL Lab (marts.fct_boe) ====="
DB_ID=$(api GET "/api/v1/database/?q=(filters:!((col:database_name,opr:eq,value:TimescaleDB)))" \
  | python3 -c "import sys,json; p=json.load(sys.stdin); print(p['result'][0]['id'])")
api POST "/api/v1/sqllab/execute" "{\"database_id\":$DB_ID,\"schema\":\"marts\",\"sql\":\"select pozo_id, fecha, round(boe_bbl::numeric,1) as boe_bbl from marts.fct_boe order by fecha desc limit 5\",\"json\":false,\"runAsync\":false}" \
  | python3 -c "
import sys, json
p = json.load(sys.stdin)
rows = p.get('data', [])
print('  filas devueltas =', len(rows))
for r in rows[:5]:
    print('   ', r)
"

echo "===== Superset OK ====="