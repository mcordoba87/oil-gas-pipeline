# ===============================================================================
# Config de Apache Superset (Fase 4, item 4.2)
# Montada en /app/pythonpath/superset_config.py (PYTHONPATH de la imagen).
# SQL Lab requiere un results backend: se usa Redis (servicio `redis` del
# docker-compose). Tambien se cachea en Redis.
# ===============================================================================
import os

from cachelib.redis import RedisCache
from flask_caching import Cache

REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_CELERY_DB = 0
REDIS_RESULTS_DB = 1
REDIS_CACHE_DB = 2


class CeleryConfig:
    broker_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_CELERY_DB}"
    result_backend = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_CELERY_DB}"
    imports = ("superset.sql_lab",)
    task_ignore_result = True
    timezone = "UTC"


CELERY_CONFIG = CeleryConfig

# Backend de resultados para consultas de SQL Lab (requiere un objeto cachelib)
RESULTS_BACKEND = RedisCache(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_RESULTS_DB,
    key_prefix="superset_results",
    default_timeout=300,
)
RESULTS_BACKEND_USE_MSGPACK = True

# Cache general y de datos (filtros, metadatos, consultas frecuentes)
CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 300,
    "CACHE_KEY_PREFIX": "superset_",
    "CACHE_REDIS_HOST": REDIS_HOST,
    "CACHE_REDIS_PORT": REDIS_PORT,
    "CACHE_REDIS_DB": REDIS_CACHE_DB,
    "CACHE_REDIS_SSL": False,
}
DATA_CACHE_CONFIG = CACHE_CONFIG