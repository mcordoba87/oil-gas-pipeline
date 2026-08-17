#!/usr/bin/env bash
# ===============================================================================
# Entrypoint comun de los servicios de Superset (Fase 4, item 4.2)
# 1) Instala las dependencias extra (psycopg2-binary) en el venv de la imagen,
#    que la imagen lean oficial no incluye (necesario para TimescaleDB).
# 2) Ejecuta el comando original.
# Requiere correr como root (user: "0:0" en docker-compose) para escribir en el
# venv, que es de propiedad root en la imagen.
# ===============================================================================
set -euo pipefail

echo "Instalando dependencias extra (psycopg2-binary)..."
uv pip install --python /app/.venv/bin/python --no-cache-dir \
    -r /app/superset-init/requirements-local.txt >/dev/null

exec "$@"