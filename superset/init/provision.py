#!/usr/bin/env python3
# ===============================================================================
# Provision de Apache Superset (Fase 4, item 4.2)
# One-shot (patron minio-init): registra TimescaleDB como database y crea los
# datasets de los marts de dbt para poder armar graficos drag-and-drop.
# Usa la REST API de Superset (estable entre versiones). Idempotente.
# Sin dependencias externas (solo stdlib).
# ===============================================================================
import http.cookiejar
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = os.environ.get("SUPERSET_BASE_URL", "http://superset:8088")
ADMIN_USER = os.environ.get("SUPERSET_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("SUPERSET_ADMIN_PASSWORD", "admin")
DB_NAME = os.environ.get("SUPERSET_DB_NAME", "TimescaleDB")
TSDB_URI = os.environ.get("TIMESDB_SQLALCHEMY_URI", "")

# Datasets (marts de dbt) a crear: (schema, tabla)
MART_DATASETS = [
    ("marts", "dim_pozos"),
    ("marts", "fct_lecturas"),
    ("marts", "fct_produccion_diaria"),
    ("marts", "fct_boe"),
    ("marts", "fct_curvas_declinacion"),
    ("public", "alertas"),
]

MAX_HEALTH_ATTEMPTS = 60

# Cookie jar para mantener la sesion (Flask) entre llamadas. El token CSRF se
# obtiene del endpoint dedicado tras el login (header X-CSRF-Token).
COOKIE_JAR = http.cookiejar.CookieJar()
OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(COOKIE_JAR))
CSRF_TOKEN = None


def request(path, method="GET", body=None, token=None):
    url = BASE_URL + path
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    if CSRF_TOKEN:
        headers["X-CSRF-Token"] = CSRF_TOKEN
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with OPENER.open(req, timeout=30) as resp:
            raw = resp.read().decode()
            if not raw:
                return resp.status, {}
            try:
                return resp.status, json.loads(raw)
            except ValueError:
                return resp.status, {"_raw": raw}
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        print(f"  ! HTTP {e.code} en {method} {path}: {raw[:300]}", file=sys.stderr)
        try:
            return e.code, (json.loads(raw) if raw else {})
        except ValueError:
            return e.code, {"_raw": raw}


def wait_for_superset():
    print("Esperando a que el servidor Superset este disponible...", flush=True)
    for i in range(MAX_HEALTH_ATTEMPTS):
        try:
            with OPENER.open(BASE_URL + "/health", timeout=5) as resp:
                if resp.status == 200:
                    print(f"  Superset saludable (intento {i + 1}).", flush=True)
                    return
        except Exception:
            pass
        time.sleep(3)
    print("ERROR: Superset no respondio en /health a tiempo.", file=sys.stderr)
    sys.exit(1)


def login():
    print("Login como admin...")
    status, payload = request(
        "/api/v1/security/login",
        method="POST",
        body={
            "username": ADMIN_USER,
            "password": ADMIN_PASSWORD,
            "provider": "db",
            "refresh": True,
        },
    )
    if status != 200:
        print("ERROR: no se pudo autenticar contra Superset.", file=sys.stderr)
        sys.exit(1)
    print("  Autenticado OK.")
    token = payload["access_token"]

    global CSRF_TOKEN
    status, payload = request("/api/v1/security/csrf_token/", token=token)
    if status == 200:
        CSRF_TOKEN = payload.get("result")
        print("  Token CSRF obtenido.")
    else:
        print("  WARN: no se pudo obtener token CSRF; POSTs podrian fallar.",
              file=sys.stderr)
    return token


def find_database(token):
    q = urllib.parse.quote(
        "(filters:!((col:database_name,opr:eq,value:%s)))" % DB_NAME
    )
    status, payload = request(f"/api/v1/database/?q={q}", token=token)
    if status == 200 and payload.get("count", 0) > 0:
        return payload["result"][0]["id"]
    return None


def create_database(token):
    body = {
        "database_name": DB_NAME,
        "sqlalchemy_uri": TSDB_URI,
        "expose_in_sqllab": True,
        "allow_run_async": True,
        "allow_ctas": True,
        "allow_cvas": True,
        "extra": json.dumps(
            {
                "metadata_params": {},
                "engine_params": {},
                "schemas_allowed_for_csv_upload": [],
            }
        ),
    }
    status, payload = request("/api/v1/database/", method="POST", body=body, token=token)
    if status != 201:
        print("ERROR: no se pudo crear la database TimescaleDB.", file=sys.stderr)
        sys.exit(1)
    return payload["id"]


def dataset_exists(token, db_id, schema, table):
    q = urllib.parse.quote(
        "(filters:!((col:table_name,opr:eq,value:%s),(col:schema,opr:eq,value:%s),"
        "(col:database,opr:rel_o_m,value:%d)))" % (table, schema, db_id)
    )
    status, payload = request(f"/api/v1/dataset/?q={q}", token=token)
    return status == 200 and payload.get("count", 0) > 0


def create_dataset(token, db_id, schema, table):
    body = {
        "database": db_id,
        "schema": schema,
        "table_name": table,
        "owners": [1],
    }
    status, payload = request("/api/v1/dataset/", method="POST", body=body, token=token)
    return status == 201


def main():
    if not TSDB_URI:
        print("ERROR: falta TIMESDB_SQLALCHEMY_URI.", file=sys.stderr)
        sys.exit(1)

    wait_for_superset()
    token = login()

    # 1. Database TimescaleDB
    db_id = find_database(token)
    if db_id is None:
        print("Registrando database TimescaleDB...")
        db_id = create_database(token)
        print(f"  Database creada (id={db_id}).")
    else:
        print(f"  Database {DB_NAME} ya existe (id={db_id}).")

    # 2. Datasets de marts
    created, existing = [], []
    for schema, table in MART_DATASETS:
        if dataset_exists(token, db_id, schema, table):
            existing.append(f"{schema}.{table}")
        elif create_dataset(token, db_id, schema, table):
            created.append(f"{schema}.{table}")
        else:
            print(f"  ! No se pudo crear dataset {schema}.{table}", file=sys.stderr)

    print("===== Resumen de provision =====")
    print(f"Database: {DB_NAME} (id={db_id})")
    print(f"Datasets creados: {created}")
    print(f"Datasets ya existentes: {existing}")


if __name__ == "__main__":
    main()