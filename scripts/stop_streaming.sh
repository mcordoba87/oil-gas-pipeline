#!/usr/bin/env bash
# ===============================================================================
# Detiene los procesos continuos de la Fase 1
# Uso: bash scripts/stop_streaming.sh
# ===============================================================================
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$(dirname "$SCRIPT_DIR")/logs"

for name in sensor_simulator mqtt_worker; do
  pidfile="$LOG_DIR/$name.pid"
  if [ -f "$pidfile" ]; then
    pid="$(cat "$pidfile")"
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" && echo "$name detenido (pid $pid)"
    else
      echo "$name ya no estaba corriendo"
    fi
    rm -f "$pidfile"
  fi
done