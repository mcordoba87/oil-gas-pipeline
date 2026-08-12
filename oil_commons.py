"""Utilidades compartidas para los scripts de generación e ingesta."""
import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env", override=False)


def getenv(key, default=None):
    return os.environ.get(key, default)


def tsdb_conn():
    return psycopg2.connect(getenv("TIMESDB_DB_URL"))


def oltp_conn():
    return psycopg2.connect(getenv("OLTP_DB_URL"))


def s3_client():
    import boto3

    return boto3.client(
        "s3",
        endpoint_url=getenv("MINIO_ENDPOINT", "http://localhost:9000"),
        aws_access_key_id=getenv("MINIO_ACCESS_KEY"),
        aws_secret_access_key=getenv("MINIO_SECRET_KEY"),
        region_name="us-east-1",
    )


def minio_bucket():
    return getenv("MINIO_BUCKET", "oil-lakehouse")


def broker_url():
    return getenv("MQTT_BROKER_URL", "mqtt://localhost:1883")


def active_wells():
    """Devuelve pozo_id de pozos activos desde OLTP (fallback a lista fija si está vacía)."""
    try:
        conn = oltp_conn()
        cur = conn.cursor()
        cur.execute("SELECT nombre FROM pozos WHERE estado IN ('activo', 'mantenimiento')")
        wells = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()
        if wells:
            return wells
    except Exception:
        pass
    return [f"PZ-{i:03d}" for i in range(1, 6)]