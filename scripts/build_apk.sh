#!/usr/bin/env bash
# ===============================================================================
# Build del APK (debug) de la App móvil de campo (Fase 4, item 4.4).
# Requiere: Android SDK + JDK. En WSL usa el SDK de Windows vía ANDROID_HOME
# (p. ej. export ANDROID_HOME=/mnt/c/Users/<usuario>/AppData/Local/Android/Sdk).
# Uso: bash scripts/build_apk.sh
# Salida: app_movil/android/app/build/outputs/apk/debug/app-debug.apk
# ===============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")/app_movil"

if [ ! -d "$APP_DIR/android" ]; then
  echo "ERROR: no existe app_movil/android. Scaffold primero el proyecto React Native."
  exit 1
fi

echo "ANDROID_HOME=${ANDROID_HOME:-<no definido>}"
echo "=== Build APK debug ==="
(cd "$APP_DIR/android" && ./gradlew assembleDebug)

APK="$APP_DIR/android/app/build/outputs/apk/debug/app-debug.apk"
echo "=== APK generado: $APK ==="
ls -lh "$APK"
