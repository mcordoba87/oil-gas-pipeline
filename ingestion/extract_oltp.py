"""Extractor OLTP -> Lakehouse (Fase 1 item 7).

Job programado (cron) que extrae pozos/mantenimientos/paradas desde Postgres
OLTP y los deja en:
    s3://oil-lakehouse/raw/oltp/YYYY-MM-DD/{tabla}.csv

Uso:
    python ingestion/extract_oltp.py
"""
import csv
import io
import logging
import sys
from datetime import date
from pathlib import Path

import psycopg2.extras

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from oil_commons import minio_bucket, oltp_conn, s3_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("extract_oltp")

TABLAS = ["pozos", "mantenimientos", "paradas_programadas"]


def extract_table(conn, table):
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(f"SELECT * FROM {table}")
    rows = cur.fetchall()
    cur.close()
    return rows


def to_csv(rows):
    if not rows:
        return ""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def main():
    fecha = date.today().isoformat()
    s3 = s3_client()
    conn = oltp_conn()
    try:
        for table in TABLAS:
            rows = extract_table(conn, table)
            key = f"raw/oltp/{fecha}/{table}.csv"
            s3.put_object(Bucket=minio_bucket(), Key=key, Body=to_csv(rows).encode())
            log.info("OK: %s (%d filas)", key, len(rows))
    finally:
        conn.close()


if __name__ == "__main__":
    main()