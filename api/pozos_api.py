"""API FastAPI de pozos (roadmap Fase 4, item 4.3).

Sirve datos analíticos y de monitoreo desde TimescaleDB:
  - lecturas en tiempo real (hot path public.lecturas_sensores)
  - alertas operativas (hypertable public.alertas, alimentada por dbt)
  - resumen de producción / BOE (marts.fct_boe de dbt)

Autenticación por API Key (header X-API-Key, env API_KEY).
Documentación automática: /docs (Swagger) y /redoc.

Uso local:
    uvicorn api.pozos_api:app --reload --port 8000
Uso en contenedor:
    docker compose up pozos_api
"""
import os
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import psycopg2
import psycopg2.extras
import psycopg2.pool
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Query

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)

DSN = os.getenv(
    "TIMESDB_DB_URL",
    "postgresql://tsdb:tsdb@localhost:5432/oil_tsdb",
)

_pool = None


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    if _pool is not None:
        _pool.closeall()


app = FastAPI(
    title="Pozos API - Monitoreo IoT de pozos petroleros",
    description=(
        "Endpoints de lecturas, alertas y resumen de producción/BOE. "
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


@app.get("/", tags=["meta"])
def root():
    return {
        "servicio": "Pozos API",
        "documentacion": "/docs",
        "endpoints": [
            "/health",
            "/pozos",
            "/pozos/{id}/lecturas",
            "/pozos/{id}/alertas",
            "/produccion/resumen",
        ],
    }


@app.get("/health", tags=["meta"])
def health():
    try:
        fetch("SELECT 1")
        db = "ok"
    except Exception as exc:  # noqa: BLE001
        db = f"error: {exc}"
    return {"status": "ok", "database": db}


@app.get("/pozos", tags=["pozos"])
def listar_pozos(_: str = Depends(require_api_key)):
    rows = fetch(
        """
        SELECT pozo_id, cuenca, estado_actual, fecha_perforacion
        FROM marts.dim_pozos
        ORDER BY pozo_id
        """
    )
    return {"pozos": rows, "total": len(rows)}


@app.get("/pozos/{pozo_id}/lecturas", tags=["pozos"])
def lecturas_pozo(
    pozo_id: str,
    limit: int = Query(default=100, ge=1, le=1000),
    _: str = Depends(require_api_key),
):
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
    if not rows:
        raise HTTPException(status_code=404, detail=f"Sin lecturas para pozo {pozo_id}")
    return {"pozo_id": pozo_id, "lecturas": rows}


@app.get("/pozos/{pozo_id}/alertas", tags=["pozos"])
def alertas_pozo(
    pozo_id: str,
    estado: str = Query(default="abierta", pattern="^(abierta|resuelta)$"),
    _: str = Depends(require_api_key),
):
    rows = fetch(
        """
        SELECT time, pozo_id, tipo, severidad, mensaje, estado, fecha_resolucion
        FROM alertas
        WHERE pozo_id = %s AND estado = %s
        ORDER BY time DESC
        """,
        (pozo_id, estado),
    )
    return {"pozo_id": pozo_id, "estado": estado, "alertas": rows}


@app.get("/produccion/resumen", tags=["produccion"])
def resumen_produccion(
    por: str = Query(default="cuenca", pattern="^(cuenca|pozo)$"),
    _: str = Depends(require_api_key),
):
    if por == "cuenca":
        rows = fetch(
            """
            SELECT cuenca,
                   sum(bpd_producido)  AS bpd_acumulado,
                   sum(boe_bbl)        AS boe_acumulado,
                   count(DISTINCT fecha) AS dias,
                   count(DISTINCT pozo_id) AS pozos
            FROM marts.fct_boe
            GROUP BY cuenca
            ORDER BY boe_acumulado DESC
            """
        )
    else:
        rows = fetch(
            """
            SELECT pozo_id, cuenca,
                   sum(bpd_producido) AS bpd_acumulado,
                   sum(boe_bbl)       AS boe_acumulado
            FROM marts.fct_boe
            GROUP BY pozo_id, cuenca
            ORDER BY boe_acumulado DESC
            """
        )
    return {"por": por, "resumen": rows}