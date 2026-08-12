import random
from datetime import datetime, timezone

from fastapi import FastAPI

app = FastAPI(title="Mock Prices API", version="1.0.0")

BASE_WTI = 72.0
BASE_BRENT = 76.0


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/precios")
def get_prices():
    now = datetime.now(timezone.utc)
    wti = round(BASE_WTI + random.uniform(-1.5, 1.5), 2)
    brent = round(BASE_BRENT + random.uniform(-1.5, 1.5), 2)
    return {
        "fecha": now.date().isoformat(),
        "timestamp": now.isoformat(),
        "wti_usd_bbl": wti,
        "brent_usd_bbl": brent,
        "fuente": "mock",
    }


@app.get("/")
def root():
    return {"servicio": "Mock Prices API", "endpoints": ["/health", "/api/precios"]}
