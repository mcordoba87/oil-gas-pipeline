"""Loader landing/raw de MinIO -> esquema raw en TimescaleDB (Fase 3).

dbt no puede leer de MinIO: este job descarga los CSV/JSON/JSONL del lakehouse
y los carga con COPY masivo a las tablas del esquema raw que dbt consume.

Estrategia de carga:
  - oltp_pozos / oltp_mantenimientos / oltp_paradas -> TRUNCATE + load del
    snapshot más reciente (el extract OLTP es un dump completo diario; el último
    ya contiene todo el historial).
  - produccion_diaria / laboratorio / precios / scada_logs -> append acumulativo
    (objetos con fecha única por día, sin solaparse).

Uso:
    python ingestion/load_landing_to_raw.py                  # todo
    python ingestion/load_landing_to_raw.py --tables precios # subset
"""
import argparse
import csv
import io
import json
import logging
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from oil_commons import minio_bucket, s3_client, tsdb_conn

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("load_landing_to_raw")

# prefijo MinIO -> tabla raw, con normalizador y modo
#   modo: "replace" = truncate + load | "append" = insert acumulativo
LOADERS = {
    "produccion_diaria": {
        "prefix": "landing/produccion_diaria",
        "table": "raw.produccion_diaria",
        "mode": "append",
        "columns": ["pozo_id", "fecha", "bpd_producido", "horas_operativas", "observaciones", "gas_mcfd"],
        "ext": ".csv",
    },
    "laboratorio": {
        "prefix": "landing/laboratorio",
        "table": "raw.laboratorio",
        "mode": "append",
        "columns": ["pozo_id", "fecha", "grados_api", "pct_agua", "pct_sedimentos"],
        "ext": ".csv",
    },
    "oltp_pozos": {
        "prefix": "raw/oltp",
        "table": "raw.oltp_pozos",
        "mode": "replace",
        "columns": ["id", "nombre", "cuenca", "fecha_perforacion", "estado"],
        "ext": ".csv",
        "file": "pozos.csv",
    },
    "oltp_mantenimientos": {
        "prefix": "raw/oltp",
        "table": "raw.oltp_mantenimientos",
        "mode": "replace",
        "columns": ["id", "pozo_id", "fecha", "tipo", "costo", "tecnico"],
        "ext": ".csv",
        "file": "mantenimientos.csv",
    },
    "oltp_paradas": {
        "prefix": "raw/oltp",
        "table": "raw.oltp_paradas",
        "mode": "replace",
        "columns": ["id", "pozo_id", "fecha_inicio", "fecha_fin", "motivo"],
        "ext": ".csv",
        "file": "paradas_programadas.csv",
    },
    "precios": {
        "prefix": "raw/precios",
        "table": "raw.precios",
        "mode": "append",
        "columns": ["fecha", "timestamp", "wti_usd_bbl", "brent_usd_bbl", "fuente"],
        "ext": ".json",
    },
    "scada_logs": {
        "prefix": "raw/logs_scada",
        "table": "raw.scada_logs",
        "mode": "append",
        "columns": ["timestamp", "evento", "descripcion", "pozo_id", "nivel", "fuente"],
        "ext": ".jsonl",
    },
}


def _list_keys(s3, prefix, ext=None, filename=None):
    """Devuelve las keys de MinIO bajo prefix, filtradas por extensión/archivo."""
    paginator = s3.get_paginator("list_objects_v2")
    keys = []
    for page in paginator.paginate(Bucket=minio_bucket(), Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if ext and not key.endswith(ext):
                continue
            if filename and Path(key).name != filename:
                continue
            keys.append(key)
    return sorted(keys)


def _pendientes(conn, s3, name, spec):
    """Devuelve las keys a cargar, saltando las ya registradas.

    - modo replace: solo la key más reciente (snapshot de estado actual).
    - modo append: todas las keys aún no registradas (evita duplicados).
    """
    keys = _list_keys(s3, spec["prefix"], spec["ext"], spec.get("file"))
    if not keys:
        return [], []

    if spec["mode"] == "replace":
        # el snapshot de estado actual siempre es el objeto más reciente
        return keys[-1:], keys

    cur = conn.cursor()
    cur.execute("SELECT key FROM raw.carga_registros WHERE tabla = %s", (name,))
    ya_cargadas = {r[0] for r in cur.fetchall()}
    cur.close()

    return [k for k in keys if k not in ya_cargadas], keys


def _normalize_rows(loader, keys, s3):
    """Descarga y normaliza los objetos de MinIO a listas de dicts (ordenadas por columna)."""
    rows = []
    for key in sorted(keys):
        body = s3.get_object(Bucket=minio_bucket(), Key=key)["Body"].read().decode()
        if loader["ext"] == ".csv":
            reader = csv.DictReader(io.StringIO(body))
            rows.extend(dict(r) for r in reader)
        elif loader["ext"] == ".json":
            data = json.loads(body)
            row = {
                "fecha": data.get("fecha"),
                "timestamp": data.get("timestamp"),
                "wti_usd_bbl": data.get("wti_usd_bbl"),
                "brent_usd_bbl": data.get("brent_usd_bbl"),
                "fuente": data.get("fuente"),
            }
            rows.append(row)
        elif loader["ext"] == ".jsonl":
            for line in body.splitlines():
                if line.strip():
                    rows.append(json.loads(line))
        log.info("  Leído %s", key)
    return rows


def _clean(rows, columns):
    """Reordena y aplanja a listas de tuplas en el orden de columnas de la tabla."""
    out = []
    for r in rows:
        out.append(tuple(r.get(c) for c in columns))
    return out


def _copy(conn, table, columns, tuples):
    cur = conn.cursor()
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerows(tuples)
    buf.seek(0)
    cur.copy_expert(f"COPY {table} ({', '.join(columns)}) FROM STDIN WITH (FORMAT csv)", buf)
    conn.commit()


def _registrar(conn, name, keys):
    cur = conn.cursor()
    cur.executemany(
        "INSERT INTO raw.carga_registros (tabla, key) VALUES (%s, %s) ON CONFLICT DO NOTHING",
        [(name, k) for k in keys],
    )
    conn.commit()


def load_table(conn, s3, name, spec):
    pendientes, _todas = _pendientes(conn, s3, name, spec)
    if not pendientes:
        log.info("Sin datos nuevos en %s/ para %s", spec["prefix"], name)
        return 0

    rows = _normalize_rows(spec, pendientes, s3)
    tuples = _clean(rows, spec["columns"])
    if not tuples:
        log.info("Sin filas para %s", name)
        return 0

    if spec["mode"] == "replace":
        cur = conn.cursor()
        cur.execute(f"TRUNCATE {spec['table']}")
        conn.commit()

    _copy(conn, spec["table"], spec["columns"], tuples)
    _registrar(conn, name, pendientes)
    log.info("Cargado %s: %d filas (modo %s)", name, len(tuples), spec["mode"])
    return len(tuples)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tables", nargs="*", default=list(LOADERS),
                        help="Subset de tablas a cargar (default: todas)")
    args = parser.parse_args()

    s3 = s3_client()
    conn = tsdb_conn()
    try:
        total = 0
        for name in LOADERS:
            if name not in args.tables:
                continue
            total += load_table(conn, s3, name, LOADERS[name])
        log.info("Loader completado: %d filas totales cargadas.", total)
    finally:
        conn.close()


if __name__ == "__main__":
    main()