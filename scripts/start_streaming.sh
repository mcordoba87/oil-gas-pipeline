#!/usr/bin/env bash
# ===============================================================================
# Levanta los procesos continuos de la Fase 1 (simulador + worker) en background
# Uso: bash scripts/start_streaming.sh
# ===============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"

mkdir -p "$LOG_DIR"

cd "$PROJECT_DIR"

if [ ! -d ".venv" ]; then
  echo "No hay .venv. Creando e instalando requirements..."
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
fi

nohup .venv/bin/python generators/sensor_simulator.py >> "$LOG_DIR/sensor_simulator.log" 2>&1 &
echo $! > "$LOG_DIR/sensor_simulator.pid"
echo "sensor_simulator.py iniciado (pid $(cat "$LOG_DIR/sensor_simulator.pid"))"

nohup .venv/bin/python ingestion/mqtt_worker.py >> "$LOG_DIR/mqtt_worker.log" 2>&1 &
echo $! > "$LOG_DIR/mqtt_worker.pid"
echo "mqtt_worker.py iniciado (pid $(cat "$LOG_DIR/mqtt_worker.pid"))"

echo "Logs en: $LOG_DIR/"