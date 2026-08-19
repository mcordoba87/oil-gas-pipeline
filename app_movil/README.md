# Campo O&G — App móvil de campo

App Android (React Native + TypeScript) del roadmap Fase 4, item 4.4: el
"celular del operador de campo". Muestra pozos con lecturas en vivo y recibe
notificaciones push de alertas de presión en tiempo real.

## Backend requerido

El backend vive en el contenedor `campo_app` (api/campo_app_api.py) y corre con
el resto del stack:

    docker compose up -d campo_app

Endpoints (Swagger en http://localhost:8010/docs):
- `POST /dispositivos` — registro del dispositivo.
- `GET /dispositivos/{device_id}/notificaciones` — inbox.
- `POST /notificaciones/{id}/leida` — marcar leída.
- `GET /pozos` y `GET /pozos/{id}/lecturas` — datos en vivo.
- `POST /push/inyectar` — simular un push de presión (demos/verificación).

El dispatcher del backend detecta alertas de presión (`presion_zscore`,
`fuera_rango_fisico`) en la hypertable `alertas` y las entrega al teléfono por
**inbox (REST)** y por **MQTT/WebSocket** (topic `notificaciones/{device_id}`,
puerto 9001) para push en tiempo real.

## Configuración de la app

El teléfono debe estar en la **misma red Wi-Fi que el PC** que corre Docker.
En la pantalla de Ajustes de la app configurá:

- `URL API (REST)` → `http://<IP_LAN_DEL_PC>:8010`
- `URL MQTT (WebSocket)` → `ws://<IP_LAN_DEL_PC>:9001`
- `API Key` → el valor de `API_KEY` en `.env`

Los puertos 8010 y 9001 deben estar abiertos en el firewall del PC.

## Instalación en el teléfono

Con depuración USB activada y el teléfono conectado:

    bash scripts/build_apk.sh      # gradle assembleDebug
    bash scripts/install_app.sh    # adb install -r app-debug.apk

O compartir el APK
(`app_movil/android/app/build/outputs/apk/debug/app-debug.apk`) por WhatsApp/Drive.

### Nota de entorno (WSL + Windows)

El proyecto vive en una ruta con `&` (`.../oil&gas`), lo que rompe los `.bat`/`.cmd`
de Windows. Desde WSL se usa el `gradlew` (script shell) que no sufre ese problema;
asegurate de exportar `ANDROID_HOME` apuntando al SDK de Windows, p. ej.:

    export ANDROID_HOME=/mnt/c/Users/<usuario>/AppData/Local/Android/Sdk

## Verificación

    bash scripts/verify_campo_app.sh   # E2E del backend (health, registro, push MQTT + inbox)

## Desarrollo

    npm install
    npx tsc --noEmit        # tipos (si npm falla por el & de la ruta, invocar tsc vía node.exe)
    npm test                # jest
    npm run lint            # eslint