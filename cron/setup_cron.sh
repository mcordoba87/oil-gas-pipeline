#!/usr/bin/env bash
# ===============================================================================
# Instala el crontab de jobs batch de la Fase 1
# Uso: bash cron/setup_cron.sh
# ===============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

PYTHON="$(command -v python3 || command -v python)"
CRON_FILE="$SCRIPT_DIR/crontab.example"
FINAL_CRON="$(mktemp)"

if [ ! -f "$PROJECT_DIR/logs" ]; then
  mkdir -p "$PROJECT_DIR/logs"
fi

sed "s|/ruta/proyecto|$PROJECT_DIR|g; s|/usr/bin/python3|$PYTHON|g" "$CRON_FILE" > "$FINAL_CRON"

# Mantener las líneas crontab ya existentes que no sean del proyecto
crontab -l 2>/dev/null | grep -v "oil&gas" > /tmp/crontab_existing || true

cat /tmp/crontab_existing "$FINAL_CRON" | crontab -

echo "Crontab instalado con jobs de $PROJECT_DIR:"
crontab -l | grep "oil&gas"
rm -f "$FINAL_CRON" /tmp/crontab_existing