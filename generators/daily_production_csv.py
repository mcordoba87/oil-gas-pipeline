"""Generador de reporte diario de producción por pozo (Fase 1 item 3).

Genera un CSV simulando el reporte manual de producción y lo sube a:
    s3://oil-lakehouse/landing/produccion_diaria/YYYY-MM-DD/reporte.csv
Incluye producción de petróleo (bpd) y gas (mcfd) para el cálculo de BOE en Fase 3.

Uso:
    python generators/daily_production_csv.py [--fecha YYYY-MM-DD]
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
        bpd = round(random.uniform(50, 900), 1)
        gas_mcfd = round(random.uniform(200, 4000), 1)
        horas = random.choice([16, 18, 20, 22, 24])
        obs = random.choice(["", "", "Mantenimiento preventivo", "Corte por parada", "Baja por gas lift"])
        rows.append({
            "pozo_id": pozo_id,
            "fecha": fecha.isoformat(),
            "bpd_producido": bpd,
            "horas_operativas": horas,
            "observaciones": obs,
            "gas_mcfd": gas_mcfd,
        })
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fecha", default=(date.today() - timedelta(days=1)).isoformat())
    args = parser.parse_args()

    fecha = date.fromisoformat(args.fecha)
    rows = build_rows(fecha)

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["pozo_id", "fecha", "bpd_producido", "horas_operativas", "observaciones", "gas_mcfd"])
    writer.writeheader()
    writer.writerows(rows)

    key = f"landing/produccion_diaria/{fecha.isoformat()}/reporte.csv"
    s3 = s3_client()
    s3.put_object(Bucket=minio_bucket(), Key=key, Body=buf.getvalue().encode())
    print(f"OK: {key} ({len(rows)} pozos)")


if __name__ == "__main__":
    main()