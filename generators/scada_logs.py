"""Generador de logs SCADA (Fase 1 item 9).

Simula eventos del sistema SCADA en formato JSON lines y los deja en:
    s3://oil-lakehouse/raw/logs_scada/YYYY-MM-DD/scada.jsonl

Uso:
    python generators/scada_logs.py [--n 200]
"""
import argparse
import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from oil_commons import active_wells, minio_bucket, s3_client

EVENTOS = [
    ("sensor_reinicio", "Sensor reiniciado tras timeout de lectura"),
    ("error_conexion", "Error de conexión con el RTU de campo"),
    ("caida_comunicacion", "Caída de comunicación SCADA (perdida de telemetría)"),
    ("timeout_respuesta", "Timeout en respuesta del protocolo Modbus"),
    ("alerta_baja_calidad", "Calidad de señal degradada (< 60%)"),
    ("evento_normal", "Operación normal del enlace SCADA"),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=200)
    args = parser.parse_args()

    wells = active_wells()
    now = datetime.now(timezone.utc)
    lines = []
    for _ in range(args.n):
        ts = now - timedelta(seconds=random.randint(0, 86400))
        evento, desc = random.choice(EVENTOS)
        lines.append(json.dumps({
            "timestamp": ts.isoformat(),
            "evento": evento,
            "descripcion": desc,
            "pozo_id": random.choice(wells),
            "nivel": random.choice(["INFO", "WARN", "WARN", "ERROR"]),
            "fuente": "SCADA/v0.9.3",
        }))

    fecha = now.date().isoformat()
    key = f"raw/logs_scada/{fecha}/scada.jsonl"
    body = "\n".join(lines) + "\n"
    s3 = s3_client()
    s3.put_object(Bucket=minio_bucket(), Key=key, Body=body.encode())
    print(f"OK: {key} ({len(lines)} eventos)")


if __name__ == "__main__":
    main()