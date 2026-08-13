"""Sincroniza cuencas y pozos desde Postgres OLTP hacia TimescaleDB (Fase 2).

TimescaleDB no es fuente de verdad de maestros: el OLTP (ERP/CMMS) manda.
Este job hace UPSERT del espejo de trabajo (pozos + cuencas) que se usa en
joins y continuous aggregates de TSDB.

Uso:
    python generators/seed_tsdb.py
"""
import logging
import sys
from pathlib import Path

import psycopg2.extras

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from oil_commons import oltp_conn, tsdb_conn

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("seed_tsdb")


def upsert_cuencas(oltp, tsdb):
    """Trae cuencas distintas del OLTP y las inserta en TSDB si faltan."""
    cur_oltp = oltp.cursor()
    cur_oltp.execute("SELECT DISTINCT cuenca FROM pozos ORDER BY cuenca")
    cuencas = [row[0] for row in cur_oltp.fetchall()]
    cur_oltp.close()

    cur = tsdb.cursor()
    for nombre in cuencas:
        cur.execute(
            "INSERT INTO cuencas (nombre) VALUES (%s) ON CONFLICT (nombre) DO NOTHING",
            (nombre,),
        )
    tsdb.commit()
    log.info("Cuencas sincronizadas (%d)", len(cuencas))
    return cuencas


def upsert_pozos(oltp, tsdb):
    """Vuelca pozos del OLTP al espejo de TSDB (pozo_id = nombre OLTP)."""
    cur_oltp = oltp.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur_oltp.execute(
        "SELECT nombre, cuenca, fecha_perforacion, estado FROM pozos ORDER BY nombre"
    )
    pozos = cur_oltp.fetchall()
    cur_oltp.close()

    cur = tsdb.cursor()
    cur.execute("SELECT nombre, cuenca_id FROM cuencas")
    cuenca_map = {nombre: cid for nombre, cid in cur.fetchall()}

    for p in pozos:
        cur.execute(
            """
            INSERT INTO pozos (pozo_id, nombre, cuenca, cuenca_id, fecha_perforacion, estado, tipo)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (pozo_id) DO UPDATE SET
                nombre = EXCLUDED.nombre,
                cuenca = EXCLUDED.cuenca,
                cuenca_id = EXCLUDED.cuenca_id,
                fecha_perforacion = EXCLUDED.fecha_perforacion,
                estado = EXCLUDED.estado,
                tipo = EXCLUDED.tipo
            """,
            (
                p["nombre"],
                p["nombre"],
                p["cuenca"],
                cuenca_map.get(p["cuenca"]),
                p["fecha_perforacion"],
                p["estado"],
                None,  # OLTP aún no tiene columna 'tipo'; queda NULL por ahora
            ),
        )
    tsdb.commit()
    log.info("Pozos sincronizados en TSDB (%d)", len(pozos))


def main():
    oltp = oltp_conn()
    tsdb = tsdb_conn()
    try:
        upsert_cuencas(oltp, tsdb)
        upsert_pozos(oltp, tsdb)
        log.info("Seed TSDB completado.")
    finally:
        oltp.close()
        tsdb.close()


if __name__ == "__main__":
    main()