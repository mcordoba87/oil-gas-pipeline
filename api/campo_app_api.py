"""API de la App móvil de campo (roadmap Fase 4, item 4.4).

Backend del "celular del operador de campo":
  - Registro de dispositivos (POST /dispositivos).
  - Inbox de notificaciones push (GET /dispositivos/{id}/notificaciones,
    POST /notificaciones/{id}/leida).
  - Lecturas en vivo por pozo y lista de pozos (reusa TimescaleDB).
  - Dispatcher de push en background: cada N segundos consulta alertas de
    PRESIÓN nuevas (tipos presion_zscore / fuera_rango_fisico, estado abierta)
    y por cada dispositivo registrado inserta la notificación en el inbox
    (canal 'poll') y la publica por MQTT en notificaciones/{device_id}
    (canal 'mqtt') para entrega en tiempo real (WebSocket :9001).
  - Endpoint /push/inyectar para simular un push manual (canal 'inyectada'),
    usado por scripts/verify_campo_app.sh y demos.

Autenticación por API Key (header X-API-Key, env API_KEY).
Documentación automática: /docs (Swagger) y /redoc.

Uso local:
    uvicorn api.campo_app_api:app --reload --port 8010
Uso en contenedor:
    docker compose up campo_app
"""
import asyncio
import json
import logging
import os
import time
import urllib.parse
import uuid
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import paho.mqtt.client as mqtt
import psycopg2
import psycopg2.extras
import psycopg2.pool
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("campo_app")

DSN = os.getenv(
    "TIMESDB_DB_URL",
    "postgresql://tsdb:tsdb@localhost:5432/oil_tsdb",
)

# Solo alertas de PRESIÓN generan push (roadmap 4.4). Ver
# dbt_petrolera/models/intermediate/int_alertas_candidatas.sql
PRESS_ALERT_TYPES = ("presion_zscore", "fuera_rango_fisico")

DISPATCH_INTERVAL_SEC = int(os.getenv("CAMPO_APP_PUSH_INTERVAL_SEC", "10"))

_pool = None
_mqtt_client = None


# --------------------------------------------------------------------------
# Conexiones (patrón api/pozos_api.py)
# --------------------------------------------------------------------------
def get_pool():
    """Pool de conexiones lazy (evita fallar si la BD aún no está lista)."""
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.ThreadedConnectionPool(0, 10, DSN)
    return _pool


def jsonable(row):
    """Convierte tipos psycopg2 (Decimal, datetime) a JSON-friendly."""
    out = {}
    for key, value in row.items():
        if isinstance(value, Decimal):
            value = float(value)
        elif isinstance(value, (datetime, date)):
            value = value.isoformat()
        elif isinstance(value, timedelta):
            value = value.total_seconds()
        out[key] = value
    return out


def fetch(sql, params=None):
    conn = get_pool().getconn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or ())
            rows = cur.fetchall()
        return [jsonable(r) for r in rows]
    finally:
        get_pool().putconn(conn)


def execute(sql, params=None):
    conn = get_pool().getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            try:
                row = cur.fetchone()
            except psycopg2.ProgrammingError:
                row = None
        conn.commit()
        return row
    except Exception:
        conn.rollback()
        raise
    finally:
        get_pool().putconn(conn)


# --------------------------------------------------------------------------
# MQTT (publicación de push en tiempo real)
# --------------------------------------------------------------------------
def get_mqtt():
    """Cliente paho conectado al broker (reconnect automático)."""
    global _mqtt_client
    if _mqtt_client is None:
        parsed = urllib.parse.urlparse(os.getenv("MQTT_BROKER_URL", "mqtt://mosquitto:1883"))
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                             client_id=f"campo-app-push-{os.getpid()}")
        client.reconnect_delay_set(min_delay=1, max_delay=30)
        try:
            client.connect(parsed.hostname, parsed.port or 1883, keepalive=60)
            client.loop_start()
            log.info("MQTT conectado en %s:%s", parsed.hostname, parsed.port or 1883)
            _mqtt_client = client
        except Exception as exc:  # noqa: BLE001
            log.warning("MQTT no disponible (%s); se reintenta en cada despacho.", exc)
            client = None
        _mqtt_client = client
    return _mqtt_client


def publish_mqtt(device_id, payload):
    client = get_mqtt()
    if client is None:
        return False
    try:
        client.publish(f"notificaciones/{device_id}",
                       json.dumps(payload, ensure_ascii=False), qos=1)
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("Fallo publicando MQTT a %s: %s", device_id, exc)
        return False


# --------------------------------------------------------------------------
# Dispatcher de push (background)
# --------------------------------------------------------------------------
def get_watermark():
    row = execute("SELECT ultima_alerta_ts FROM push_watermark WHERE id = 1")
    if row:
        return row[0]
    # Primera corrida: tomar alertas de la última hora para no perder lo reciente.
    init_ts = datetime.now().astimezone() - timedelta(hours=1)
    execute(
        "INSERT INTO push_watermark (id, ultima_alerta_ts) VALUES (1, %s) "
        "ON CONFLICT (id) DO NOTHING",
        (init_ts,),
    )
    return init_ts


def dispatch_once():
    """Detecta alertas de presión nuevas y las entrega a todos los dispositivos."""
    devices = fetch(
        "SELECT device_id FROM dispositivos_campo WHERE activo ORDER BY id"
    )
    if not devices:
        return

    watermark = get_watermark()
    alertas = fetch(
        """
        SELECT time, pozo_id, tipo, severidad, mensaje
        FROM alertas
        WHERE estado = 'abierta'
          AND tipo = ANY(%s)
          AND time > %s
        ORDER BY time ASC
        """,
        (list(PRESS_ALERT_TYPES), watermark),
    )
    if not alertas:
        return

    last_ts = watermark
    # Los rows de fetch() vienen con time como ISO string (jsonable); el
    # watermark es datetime. Comparar ambos en ISO para consistencia.
    watermark_iso = watermark.isoformat()
    for alerta in alertas:
        if alerta["time"] > watermark_iso:
            last_ts = datetime.fromisoformat(alerta["time"]).astimezone()
        for dev in devices:
            payload = {
                "id": 0,
                "time": alerta["time"],
                "pozo_id": alerta["pozo_id"],
                "tipo": alerta["tipo"],
                "severidad": alerta["severidad"],
                "mensaje": alerta["mensaje"],
                "canal": "poll",
            }
            row = execute(
                """
                INSERT INTO notificaciones
                    (time, dispositivo_id, pozo_id, tipo, severidad, mensaje, canal)
                VALUES (%s, %s, %s, %s, %s, %s, 'poll')
                RETURNING id
                """,
                (alerta["time"], dev["device_id"], alerta["pozo_id"],
                 alerta["tipo"], alerta["severidad"], alerta["mensaje"]),
            )
            payload["id"] = row[0]
            publish_mqtt(dev["device_id"], payload)
            log.info("Push presion %s -> %s (id=%s)", alerta["tipo"], dev["device_id"], row[0])

    execute("UPDATE push_watermark SET ultima_alerta_ts = %s WHERE id = 1", (last_ts,))


async def dispatcher_loop():
    """Task asyncio que corre dispatch_once cada CAMPO_APP_PUSH_INTERVAL_SEC."""
    log.info("Dispatcher de push iniciado (intervalo %ss).", DISPATCH_INTERVAL_SEC)
    while True:
        try:
            await asyncio.to_thread(dispatch_once)
        except Exception as exc:  # noqa: BLE001
            log.error("Error en dispatch_once: %s", exc)
        await asyncio.sleep(DISPATCH_INTERVAL_SEC)


# --------------------------------------------------------------------------
# App FastAPI
# --------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(dispatcher_loop())
    yield
    task.cancel()
    if _pool is not None:
        _pool.closeall()
    if _mqtt_client is not None:
        _mqtt_client.loop_stop()
        _mqtt_client.disconnect()


app = FastAPI(
    title="App móvil de campo - API",
    description=(
        "Backend del celular de operador de campo: registro de dispositivos, "
        "inbox de notificaciones push (presión) y lecturas en vivo. "
        "Requiere header X-API-Key."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


def require_api_key(x_api_key: str = Header(default="", alias="X-API-Key")):
    expected = os.getenv("API_KEY", "")
    if expected and x_api_key != expected:
        raise HTTPException(status_code=401, detail="API key inválida o ausente")
    return x_api_key


class DispositivoIn(BaseModel):
    device_id: str | None = None
    operador: str | None = None
    plataforma: str = Field(default="android", pattern="^(android|ios|web)$")


class PushSimIn(BaseModel):
    pozo_id: str
    severidad: str = Field(default="critical", pattern="^(info|warning|critical)$")
    mensaje: str | None = None


@app.get("/", tags=["meta"])
def root():
    return {
        "servicio": "App móvil de campo - API",
        "documentacion": "/docs",
        "endpoints": [
            "/health",
            "/dispositivos",
            "/dispositivos/{device_id}/notificaciones",
            "/notificaciones/{id}/leida",
            "/pozos",
            "/pozos/{pozo_id}/lecturas",
            "/push/inyectar",
        ],
    }


@app.get("/health", tags=["meta"])
def health():
    try:
        fetch("SELECT 1")
        db = "ok"
    except Exception as exc:  # noqa: BLE001
        db = f"error: {exc}"
    return {"status": "ok", "database": db, "dispatcher_interval_sec": DISPATCH_INTERVAL_SEC}


# --------------------------------------------------------------------------
# Dispositivos / notificaciones
# --------------------------------------------------------------------------
@app.post("/dispositivos", tags=["dispositivos"])
def registrar_dispositivo(
    body: DispositivoIn,
    _: str = Depends(require_api_key),
):
    device_id = body.device_id or str(uuid.uuid4())
    try:
        execute(
            """
            INSERT INTO dispositivos_campo (device_id, operador, plataforma)
            VALUES (%s, %s, %s)
            ON CONFLICT (device_id)
            DO UPDATE SET last_seen = now(),
                          activo = TRUE,
                          plataforma = EXCLUDED.plataforma
            """,
            (device_id, body.operador, body.plataforma),
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"No se pudo registrar: {exc}") from exc
    rows = fetch(
        "SELECT id, device_id, operador, plataforma, activo, created_at, last_seen "
        "FROM dispositivos_campo WHERE device_id = %s",
        (device_id,),
    )
    return {"dispositivo": rows[0]}


@app.get("/dispositivos", tags=["dispositivos"])
def listar_dispositivos(_: str = Depends(require_api_key)):
    rows = fetch(
        "SELECT id, device_id, operador, plataforma, activo, created_at, last_seen "
        "FROM dispositivos_campo ORDER BY id"
    )
    return {"dispositivos": rows, "total": len(rows)}


class EstadoIn(BaseModel):
    activo: bool


@app.post("/dispositivos/{device_id}/estado", tags=["dispositivos"])
def cambiar_estado(
    device_id: str,
    body: EstadoIn,
    _: str = Depends(require_api_key),
):
    """Activa/desactiva un dispositivo. Desactivado deja de recibir push."""
    row = execute(
        "UPDATE dispositivos_campo SET activo = %s WHERE device_id = %s RETURNING device_id, activo",
        (body.activo, device_id),
    )
    if not row:
        raise HTTPException(status_code=404, detail=f"Dispositivo {device_id} no existe")
    return {"device_id": row[0], "activo": row[1]}


@app.get("/dispositivos/{device_id}/notificaciones", tags=["notificaciones"])
def inbox_dispositivo(
    device_id: str,
    leida: str = Query(default="todas", pattern="^(todas|no_leidas|leidas)$"),
    limit: int = Query(default=50, ge=1, le=500),
    _: str = Depends(require_api_key),
):
    execute("UPDATE dispositivos_campo SET last_seen = now() WHERE device_id = %s",
            (device_id,))
    cond = ""
    if leida == "no_leidas":
        cond = "AND leida = FALSE"
    elif leida == "leidas":
        cond = "AND leida = TRUE"
    rows = fetch(
        f"""
        SELECT id, time, pozo_id, tipo, severidad, mensaje, canal, leida
        FROM notificaciones
        WHERE dispositivo_id = %s {cond}
        ORDER BY time DESC, id DESC
        LIMIT %s
        """,
        (device_id, limit),
    )
    return {"device_id": device_id, "total": len(rows), "notificaciones": rows}


@app.post("/notificaciones/{notif_id}/leida", tags=["notificaciones"])
def marcar_leida(
    notif_id: int,
    _: str = Depends(require_api_key),
):
    row = execute("UPDATE notificaciones SET leida = TRUE WHERE id = %s RETURNING id",
                  (notif_id,))
    if not row:
        raise HTTPException(status_code=404, detail=f"Notificación {notif_id} no existe")
    return {"id": notif_id, "leida": True}


# --------------------------------------------------------------------------
# Pozos / lecturas (reusa lecturas_sensores)
# --------------------------------------------------------------------------
@app.get("/pozos", tags=["pozos"])
def listar_pozos(_: str = Depends(require_api_key)):
    rows = fetch(
        """
        SELECT pozo_id, cuenca, estado_actual
        FROM marts.dim_pozos
        ORDER BY pozo_id
        """
    )
    return {"pozos": rows, "total": len(rows)}


@app.get("/pozos/{pozo_id}/lecturas", tags=["pozos"])
def lecturas_pozo(
    pozo_id: str,
    limit: int = Query(default=50, ge=1, le=1000),
    _: str = Depends(require_api_key),
):
    # 404 solo si el pozo no existe; si existe pero aún no tiene lecturas
    # (p. ej. inactivo), devolver lista vacía para que la app no falle.
    existe = fetch("SELECT 1 FROM marts.dim_pozos WHERE pozo_id = %s", (pozo_id,))
    if not existe:
        raise HTTPException(status_code=404, detail=f"Pozo {pozo_id} no existe")
    rows = fetch(
        """
        SELECT time, pozo_id, presion_psi, temperatura_c, caudal_bpd, gas_mcfd
        FROM lecturas_sensores
        WHERE pozo_id = %s
        ORDER BY time DESC
        LIMIT %s
        """,
        (pozo_id, limit),
    )
    return {"pozo_id": pozo_id, "total": len(rows), "lecturas": rows}


# --------------------------------------------------------------------------
# Push simulado manual (para demos y verify_campo_app.sh)
# --------------------------------------------------------------------------
@app.post("/push/inyectar", tags=["push"])
def inyectar_push(
    body: PushSimIn,
    _: str = Depends(require_api_key),
):
    """Simula un push de presión a todos los dispositivos sin pasar por dbt."""
    devices = fetch("SELECT device_id FROM dispositivos_campo WHERE activo ORDER BY id")
    if not devices:
        raise HTTPException(status_code=400, detail="No hay dispositivos registrados")
    mensaje = body.mensaje or (
        f"ALERTA de presión en {body.pozo_id} (severidad {body.severidad})"
    )
    entregados = []
    for dev in devices:
        row = execute(
            """
            INSERT INTO notificaciones (dispositivo_id, pozo_id, tipo, severidad, mensaje, canal)
            VALUES (%s, %s, 'inyectada', %s, %s, 'inyectada')
            RETURNING id
            """,
            (dev["device_id"], body.pozo_id, body.severidad, mensaje),
        )
        payload = {
            "id": row[0],
            "time": datetime.now().astimezone().isoformat(),
            "pozo_id": body.pozo_id,
            "tipo": "inyectada",
            "severidad": body.severidad,
            "mensaje": mensaje,
            "canal": "inyectada",
        }
        entregados.append({"device_id": dev["device_id"], "notificacion_id": row[0]})
        publish_mqtt(dev["device_id"], payload)
        log.info("Push inyectado -> %s (id=%s)", dev["device_id"], row[0])
    return {"entregados": entregados, "total": len(entregados)}
