"""Cliente de la API de precios WTI/Brent (Fase 1 item 8).

Consulta el mock local (o API externa) y guarda el resultado en:
    s3://oil-lakehouse/raw/precios/YYYY-MM-DD.json

Uso:
    python generators/fetch_prices.py
"""
import json
import sys
from datetime import date
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from oil_commons import getenv, minio_bucket, s3_client

PRICES_URL = getenv("PRICES_API_URL", "http://localhost:8001/api/precios")


def main():
    resp = requests.get(PRICES_URL, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    fecha = data.get("fecha", date.today().isoformat())
    key = f"raw/precios/{fecha}.json"
    s3 = s3_client()
    s3.put_object(Bucket=minio_bucket(), Key=key, Body=json.dumps(data, ensure_ascii=False).encode())
    print(f"OK: {key} -> WTI={data['wti_usd_bbl']}, Brent={data['brent_usd_bbl']}")


if __name__ == "__main__":
    main()