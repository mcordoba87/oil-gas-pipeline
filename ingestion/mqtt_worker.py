"""Worker de ingesta MQTT -> TimescaleDB + MinIO (Fase 1 item 2).

Se suscribe a pozos/+/+ y:
  1) valida payload contra JSON schema
  2) maneja datos out-of-order con buffer/watermarking (~5 min de tolerancia)
  3) reensambla las 3 métricas (presion, temperatura, caudal) por (pozo_id, seq)
  4) escribe batches ordenados en la hypertable lecturas_sensores
  5) espeja el dato crudo en s3://oil-lakehouse/raw/sensores/

Uso:
    python ingestion/mqtt_worker.py
"""
import json
import logging
import os
import sys
import threading
import time
import urllib.parse
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import jsonschema
import paho.mqtt.client as mqtt
import psycopg2.extras

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from oil_commons import minio_bucket, s3_client, tsdb_conn

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("mqtt_worker")

SCHEMA_FILE = Path(__file__).parent / "schema" / "lecturas_schema.json"
RAW_PREFIX = "raw/sensores"
WATERMARK_TOLERANCE_SEC = 300   # 5 min


class ReadingBuffer:
    """Agrupa lecturas por (pozo_id, seq) hasta completar las 4 métricas."""

    REQUIRED_METRICS = 4  # presion, temperatura, caudal, gas

    def __init__(self, tolerance_sec=WATERMARK_TOLERANCE_SEC):
        self.groups = {}                      # key -> {metrica: (ts_rx, payload)}
        self.tolerance_sec = tolerance_sec

    def add(self, pozo_id, seq, metric, ts_pub, payload):
        key = (pozo_id, seq)
        group = self.groups.setdefault(key, {"metrics": {}, "ts_pub": None, "first_rx": time.time()})
        group["metrics"][metric] = payload
        t = datetime.fromisoformat(ts_pub).timestamp()
        if group["ts_pub"] is None or t < group["ts_pub"]:
            group["ts_pub"] = t

    def ready(self, now=None):
        now = now or time.time()
        return [k for k, g in self.groups.items()
                if len(g["metrics"]) == self.REQUIRED_METRICS]

    def expired(self, now=None):
        now = now or time.time()
        return [k for k, g in self.groups.items()
                if len(g["metrics"]) < 3 and now - g["first_rx"] > self.tolerance_sec]

    def pop(self, key):
        return self.groups.pop(key)


class MqttWorker:
    def __init__(self):
        self.buffer = ReadingBuffer()
        self.schema = json.loads(SCHEMA_FILE.read_text())
        self.raw_lines = []
        self.lock = threading.Lock()
        self.loop_active = True

    # --------------------------------------------------------------- MQTT
    def on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            log.info("Conectado al broker. Suscribiendo a pozos/+/+")
            client.subscribe("pozos/+/+", qos=1)
        else:
            log.error("Conexión MQTT fallida rc=%s", rc)

    def on_disconnect(self, client, userdata, flags, rc, properties=None):
        log.warning("Desconectado del broker (rc=%s). Reintentando...", rc)

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        parts = topic.split("/")
        if len(parts) != 3 or parts[0] != "pozos":
            return
        pozo_id, metric = parts[1], parts[2]
        if metric not in {"presion", "temperatura", "caudal", "gas"}:
            return

        try:
            payload = json.loads(msg.payload.decode())
        except json.JSONDecodeError:
            log.warning("Payload no-JSON en %s: %s", topic, msg.payload[:120])
            return

        try:
            jsonschema.validate(instance=payload, schema=self.schema)
        except jsonschema.ValidationError as exc:
            log.warning("Payload inválido en %s: %s", topic, exc.message)
            return

        ts_pub = payload["ts_pub"]
        seq = payload["seq"]
        serie = {metric: payload["valor"]}

        with self.lock:
            self.buffer.add(pozo_id, seq, metric, ts_pub, payload)
            self.raw_lines.append(json.dumps(payload))

        if metric == "gas":  # última métrica: intentar flush inmediato
            self.flush()

    # ------------------------------------------------------------ flushing
    def flush(self):
        with self.lock:
            ready = self.buffer.ready()
            expired = self.buffer.expired()
            rows = []
            for key in sorted(ready, key=lambda k: self.buffer.groups[k]["ts_pub"]):
                group = self.buffer.pop(key)
                m = group["metrics"]
                rows.append((
                    datetime.fromtimestamp(group["ts_pub"], tz=timezone.utc),
                    key[0],
                    m["presion"]["valor"],
                    m["temperatura"]["valor"],
                    m["caudal"]["valor"],
                    m["gas"]["valor"],
                ))
            for key in expired:
                group = self.buffer.pop(key)
                log.warning("Descartando lecturas incompletas de %s seq=%s (watermark)",
                            key[0], key[1])
            raw_snapshot = list(self.raw_lines)
            self.raw_lines.clear()

        self._write_batch(rows)
        self._write_raw(raw_snapshot)

    def _write_batch(self, rows):
        if not rows:
            return
        conn = tsdb_conn()
        try:
            cur = conn.cursor()
            psycopg2.extras.execute_values(
                cur,
                "INSERT INTO lecturas_sensores (time, pozo_id, presion_psi, temperatura_c, caudal_bpd, gas_mcfd) "
                "VALUES %s ON CONFLICT DO NOTHING",
                rows,
            )
            conn.commit()
            log.info("Batch escrito en TimescaleDB: %d filas", len(rows))
        except Exception as exc:  # noqa: BLE001
            conn.rollback()
            log.error("Error escribiendo en TimescaleDB: %s", exc)
        finally:
            conn.close()

    def _write_raw(self, lines):
        if not lines:
            return
        prefix = f"{RAW_PREFIX}/{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
        key = f"{prefix}/lecturas_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{os.getpid()}.jsonl"
        body = "\n".join(lines) + "\n"
        try:
            s3 = s3_client()
            s3.put_object(Bucket=minio_bucket(), Key=key, Body=body.encode())
            log.info("Crudo espejado en MinIO: %s (%d líneas)", key, len(lines))
        except Exception as exc:  # noqa: BLE001
            log.error("Error escribiendo crudo en MinIO: %s", exc)

    # -------------------------------------------------------------- loop
    def run(self):
        parsed = urllib.parse.urlparse(os.environ.get("MQTT_BROKER_URL", "mqtt://localhost:1883"))
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                             client_id=f"mqtt-worker-{os.getpid()}")
        client.on_connect = self.on_connect
        client.on_message = self.on_message
        client.on_disconnect = self.on_disconnect
        client.reconnect_delay_set(min_delay=1, max_delay=30)

        try:
            client.connect(parsed.hostname, parsed.port or 1883, keepalive=60)
        except Exception as exc:  # noqa: BLE001
            log.error("No se pudo conectar al broker: %s", exc)
            return

        client.loop_start()
        last_flush = time.time()
        try:
            while self.loop_active:
                time.sleep(1)
                if time.time() - last_flush >= 5:
                    self.flush()
                    last_flush = time.time()
        except KeyboardInterrupt:
            pass
        finally:
            self.flush()
            client.loop_stop()
            client.disconnect()
            log.info("Worker detenido.")


if __name__ == "__main__":
    MqttWorker().run()