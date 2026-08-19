#!/usr/bin/env bash
# ===============================================================================
# Instala el APK de la App móvil de campo en un teléfono Android conectado por
# USB (depuración USB activada) o por red (adb connect <ip>:5555).
# Uso: bash scripts/install_app.sh
# ===============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
APK="$PROJECT_DIR/app_movil/android/app/build/outputs/apk/debug/app-debug.apk"

if [ ! -f "$APK" ]; then
  echo "ERROR: no existe el APK ($APK). Corré primero: bash scripts/build_apk.sh"
  exit 1
fi

echo "=== Dispositivos conectados ==="
adb devices

echo "=== Instalando APK ==="
adb install -r "$APK"

echo "=== Listo. Abrí la app 'campo_app' en el teléfono. ==="
echo "Recordá configurar en los ajustes de la app el IP LAN del PC (ver .env: CAMPO_APP_LAN_IP)."
