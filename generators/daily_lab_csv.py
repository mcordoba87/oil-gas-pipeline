"""Generador de análisis diario de laboratorio (Fase 1 item 4).

Genera un CSV simulando el análisis de calidad de crudo del ingeniero de
yacimiento y lo sube a:
    s3://oil-lakehouse/landing/laboratorio/YYYY-MM-DD/analisis.csv

SOLO landing (sin loader): dbt lo lee directo en Fase 3.
Uso:
    python generators/daily_lab_csv.py [--fecha YYYY-MM-DD]
"""
import argparse
import csv
import io
import random
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from oil_commons import active_wells, minio_bucket, s3_client


def build_rows(fecha):
    rows = []
    for pozo_id in active_wells():
        rows.append({
            "pozo_id": pozo_id,
            "fecha": fecha.isoformat(),
            "grados_api": round(random.uniform(18, 42), 1),
            "pct_agua": round(random.uniform(0.5, 25), 2),
            "pct_sedimentos": round(random.uniform(0.1, 5), 2),
        })
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fecha", default=(date.today() - timedelta(days=1)).isoformat())
    args = parser.parse_args()

    fecha = date.fromisoformat(args.fecha)
    rows = build_rows(fecha)

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["pozo_id", "fecha", "grados_api", "pct_agua", "pct_sedimentos"])
    writer.writeheader()
    writer.writerows(rows)

    key = f"landing/laboratorio/{fecha.isoformat()}/analisis.csv"
    s3 = s3_client()
    s3.put_object(Bucket=minio_bucket(), Key=key, Body=buf.getvalue().encode())
    print(f"OK: {key} ({len(rows)} pozos)")


if __name__ == "__main__":
    main()