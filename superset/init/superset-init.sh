#!/usr/bin/env bash
# ===============================================================================
# Init de Apache Superset (Fase 4, item 4.2)
# One-shot (patrón minio-init): migra el metastore, crea el admin y aplica los
# permisos base. Idempotente. No levanta el servidor (lo hace el servicio
# `superset` una vez que este job termina con éxito).
# ===============================================================================
set -euo pipefail

ADMIN_USER="${SUPERSET_ADMIN_USER:-admin}"
ADMIN_PASSWORD="${SUPERSET_ADMIN_PASSWORD:-admin}"
ADMIN_EMAIL="${SUPERSET_ADMIN_EMAIL:-admin@oilgas.local}"

echo "===== 1. Aplicando migraciones del metastore ====="
superset db upgrade

echo "===== 2. Creando usuario admin (${ADMIN_USER}) ====="
superset fab create-admin \
    --username "${ADMIN_USER}" \
    --email "${ADMIN_EMAIL}" \
    --password "${ADMIN_PASSWORD}" \
    --firstname "Oilgas" \
    --lastname "Admin" || true

echo "===== 3. Roles y permisos base ====="
superset init

echo "===== Init de Superset completo ====="