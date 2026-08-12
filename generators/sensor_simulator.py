"""Simulador de sensores IoT de campo (Fase 1 item 1).

Publica por cada pozo lecturas de presión, temperatura y caudal en topics:
    pozos/{pozo_id}/presion
    pozos/{pozo_id}/temperatura
    pozos/{pozo_id}/caudal

Simula ruido realista, mensajes fuera de orden, delays y pérdida de mensajes
(probabilidades configurables por entorno).

Uso:
    python generators/sensor_simulator.py                  # solo pozos PZ-001..PZ-025
    python generators/sensor_simulator.py --pozoz 3        # solo 3 pozos (test rápido)
"""
import argparse
import json
import logging
import random
import signal
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

import paho.mqtt.client as mqtt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from oil_commons import active_wells, broker_url, getenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("sensor_simulator")

running = True


def _random_walk(value, min_val, max_val, step):
    value += random.uniform(-step, step)
    return max(min_val, min(max_val, value))


class WellStatus:
    def __init__(self, well_id):
        self.well_id = well_id
        self.presion = random.uniform(800, 2000)      # psi
        self.temperatura = random.uniform(30, 90)     # °C
        self.caudal = random.uniform(50, 800)         # BPD
        self.seq = random.randint(0, 10000)


def on_disconnect(client, userdata, flags, rc, properties=None):
    log.warning("Desconexión del broker (rc=%s). Reintentando...", rc)
    while running:
        try:
            client.reconnect()
            log.info("Reconectado al broker MQTT.")
            return
        except Exception as exc:  # noqa: BLE001
            log.warning("Reintento fallido: %s", exc)
            time.sleep(2)


def main():
    global running

    parser = argparse.ArgumentParser()
    parser.add_argument("--pozos", type=int, default=None, help="Cantidad de pozos a simular (default: todos los del OLTP)")
    parser.add_argument("--duracion", type=int, default=0, help="Segundos a ejecutar (0 = infinito)")
    args = parser.parse_args()

    def stop(_signum, _frame):
        global running
        running = False
        log.info("Deteniendo simulador...")

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    wells = active_wells()
    if args.pozos:
        wells = wells[: args.pozos]
    if not wells:
        log.error("No hay pozos disponibles para simular.")
        sys.exit(1)

    interval = float(getenv("SENSOR_INTERVAL_SEC", "2"))
    ooo_prob = float(getenv("SENSOR_OUT_OF_ORDER_PROB", "0.15"))
    loss_prob = float(getenv("SENSOR_LOSS_PROB", "0.05"))
    delay_prob = float(getenv("SENSOR_DELAY_PROB", "0.15"))

    parsed = urlparse(broker_url())
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"sensor-sim-{random.randint(0, 99999)}")
    client.on_disconnect = on_disconnect
    client.connect(parsed.hostname, parsed.port or 1883, keepalive=60)
    client.loop_start()

    statuses = [WellStatus(w) for w in wells]
    log.info("Simulador iniciado: %d pozos, interval=%.1fs (ooo=%.0f%%, loss=%.0f%%, delay=%.0f%%)",
             len(statuses), interval, ooo_prob * 100, loss_prob * 100, delay_prob * 100)

    start = time.time()
    try:
        while running:
            for st in statuses:
                st.seq += 1
                st.presion = _random_walk(st.presion, 500, 3000, 25)
                st.temperatura = _random_walk(st.temperatura, 15, 120, 0.8)
                st.caudal = _random_walk(st.caudal, 0, 1200, 40)
                ts = datetime.now(timezone.utc).isoformat()

                # Delays: algunos mensajes salen con timestamps del pasado cercano
                ts_offset = 0
                if random.random() < delay_prob:
                    ts_offset = random.uniform(0, 120)

                payload = {"pozo_id": st.well_id, "ts_pub": ts, "seq": st.seq, "valor": None}

                for metric, value in (("presion", st.presion), ("temperatura", st.temperatura), ("caudal", st.caudal)):
                    if random.random() < loss_prob:
                        continue  # pérdida de mensaje simulada
                    p = dict(payload)
                    p["valor"] = round(value, 2)
                    if ts_offset:
                        p["ts_pub"] = (datetime.now(timezone.utc) - timedelta(seconds=ts_offset)).isoformat()
                    topic = f"pozos/{st.well_id}/{metric}"
                    client.publish(topic, json.dumps(p), qos=1)
            time.sleep(interval)

            if args.duracion and time.time() - start > args.duracion:
                running = False
    finally:
        client.loop_stop()
        client.disconnect()
        log.info("Simulador finalizado.")


if __name__ == "__main__":
    main()