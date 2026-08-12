"""Poblador de la base OLTP (ERP/CMMS) con datos ficticios realistas (Fase 1 item 6).

Uso:
    python generators/seed_oltp.py                # siembra inicial
    python generators/seed_oltp.py --refresh     # simula operación: nuevos mantenimientos/estados
"""
import argparse
import random
import sys
from datetime import date, timedelta
from pathlib import Path

from faker import Faker

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from oil_commons import oltp_conn

fake = Faker("es_ES")

CUENCAS = ["Neuquina", "Golfo San Jorge", "Austral", "Cuyana"]

ESTADOS = ["activo", "activo", "activo", "inactivo", "mantenimiento", "abandonado"]

TIPOS_MANTENIMIENTO = [
    ("preventivo", 2000, 15000),
    ("correctivo", 3000, 40000),
    ("bombeo_ES", 10000, 80000),
    ("estimulacion", 15000, 120000),
]

TECNICOS = ["Juan Perez", "Maria Gomez", "Carlos Ruiz", "Ana Torres", "Luis Fernandez"]


def ensure_pozos(conn, num_pozos=25):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM pozos")
    existing = cur.fetchone()[0]
    if existing >= num_pozos:
        conn.commit()
        return []

    created = []
    for i in range(existing + 1, num_pozos + 1):
        nombre = f"PZ-{i:03d}"
        cuenca = fake.random_element(CUENCAS)
        fecha = fake.date_between(start_date="-15y", end_date="-2y")
        estado = fake.random_element(ESTADOS)
        cur.execute(
            "INSERT INTO pozos (nombre, cuenca, fecha_perforacion, estado) VALUES (%s, %s, %s, %s) RETURNING id",
            (nombre, cuenca, fecha, estado),
        )
        pozo_id = cur.fetchone()[0]
        created.append((pozo_id, nombre))
    conn.commit()
    return created


def add_mantenimientos(conn, pozo_id, count=1):
    cur = conn.cursor()
    for _ in range(count):
        tipo, cost_min, cost_max = fake.random_element(TIPOS_MANTENIMIENTO)
        fecha = fake.date_between(start_date="-90d", end_date="today")
        cur.execute(
            """
            INSERT INTO mantenimientos (pozo_id, fecha, tipo, costo, tecnico)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (pozo_id, fecha, tipo, random.randint(cost_min, cost_max), fake.random_element(TECNICOS)),
        )
    conn.commit()


def add_paradas_programadas(conn, pozo_id, count=1):
    cur = conn.cursor()
    for _ in range(count):
        fecha_inicio = fake.date_between(start_date="-30d", end_date="+30d")
        fecha_fin = fecha_inicio + timedelta(days=random.randint(1, 4))
        motivo = fake.sentence(nb_words=6)
        cur.execute(
            """
            INSERT INTO paradas_programadas (pozo_id, fecha_inicio, fecha_fin, motivo)
            VALUES (%s, %s, %s, %s)
            """,
            (pozo_id, fecha_inicio, fecha_fin, motivo),
        )
    conn.commit()


def refresh_operation(conn):
    cur = conn.cursor()
    cur.execute("SELECT id FROM pozos ORDER BY RANDOM() LIMIT 5")
    pozos = [r[0] for r in cur.fetchall()]
    for pozo_id in pozos:
        add_mantenimientos(conn, pozo_id, random.randint(1, 3))
        if random.random() < 0.3:
            add_paradas_programadas(conn, pozo_id, 1)
        if random.random() < 0.15:
            nuevo_estado = fake.random_element(["mantenimiento", "activo"])
            cur.execute("UPDATE pozos SET estado = %s WHERE id = %s", (nuevo_estado, pozo_id))
            conn.commit()
    print(f"Refresh: mantenimientos/paradas/estados actualizados en {len(pozos)} pozos.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="Simular operación continua")
    args = parser.parse_args()

    conn = oltp_conn()
    try:
        if args.refresh:
            refresh_operation(conn)
        else:
            created = ensure_pozos(conn)
            cur = conn.cursor()
            cur.execute("SELECT id FROM pozos")
            pozos = [r[0] for r in cur.fetchall()]
            for pozo_id in pozos:
                add_mantenimientos(conn, pozo_id, random.randint(0, 5))
                if random.random() < 0.4:
                    add_paradas_programadas(conn, pozo_id, 1)
            print(f"Seed OK: {len(pozos)} pozos con mantenimientos y paradas en OLTP.")
            if created:
                print("Pozos nuevos:", ", ".join(n for _, n in created))
    finally:
        conn.close()


if __name__ == "__main__":
    main()