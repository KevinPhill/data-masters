"""Crea data/db_nasa.duckdb: UNA base con todas las detecciones FIRMS (todos los países, sensores y años).

Pasos (reanudable: si se corta, vuelve a correrlo y sigue donde quedó):
  1. Consolida los ZIP de data/raw a Parquet (scripts/consolidar.py), solo los que falten.
  2. Carga cada Parquet en la tabla `hotspots` de DuckDB.
  3. Crea la tabla resumen `resumen_mensual` y vistas útiles.

Uso:
    python scripts/crear_db.py
    python scripts/crear_db.py --workers 6
    python scripts/crear_db.py --borrar-parquet     # libera espacio al final (el .duckdb ya tiene todo)

Consultar:
    import duckdb
    con = duckdb.connect("data/db_nasa.duckdb", read_only=True)
    con.sql("SELECT sensor, year(acq_date) y, count(*) FROM hotspots WHERE country='Costa Rica' GROUP BY ALL ORDER BY y").df()
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import time
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent))
import consolidar  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "db_nasa.duckdb"

DDL = """
CREATE TABLE IF NOT EXISTS hotspots (
    sensor      VARCHAR,   -- MODIS | VIIRS_SNPP | VIIRS_NOAA20 | VIIRS_NOAA21
    satellite   VARCHAR,   -- Terra/Aqua (MODIS), N (S-NPP), 1 (NOAA-20)
    country     VARCHAR,
    latitude    DOUBLE,
    longitude   DOUBLE,
    acq_date    DATE,
    acq_time    SMALLINT,  -- HHMM UTC
    confidence  VARCHAR,   -- MODIS 0-100 | VIIRS l/n/h
    bright_mir  FLOAT,     -- MODIS brightness / VIIRS bright_ti4 (K)
    bright_tir  FLOAT,     -- MODIS bright_t31 / VIIRS bright_ti5 (K)
    scan        FLOAT,
    track       FLOAT,
    frp         FLOAT,     -- MW
    daynight    VARCHAR,
    type        TINYINT,   -- 0 vegetación, 1 volcán, 2 estática/industria, 3 costa afuera
    version     VARCHAR
);
CREATE TABLE IF NOT EXISTS _cargados (archivo VARCHAR PRIMARY KEY, filas BIGINT, cargado_en TIMESTAMP);
CREATE TABLE IF NOT EXISTS resumen_mensual (
    sensor VARCHAR, country VARCHAR, year INTEGER, month INTEGER,
    detecciones BIGINT, detecciones_vegetacion BIGINT, frp_total DOUBLE
);
"""

RESUMEN_ARCHIVO = """
INSERT INTO resumen_mensual
SELECT sensor, country, year(acq_date), month(acq_date),
       count(*), count(*) FILTER (WHERE type = 0), sum(frp)
FROM read_parquet('{f}')
GROUP BY ALL
"""

POST = """
CREATE OR REPLACE VIEW modis        AS SELECT * FROM hotspots WHERE sensor = 'MODIS';
CREATE OR REPLACE VIEW viirs_snpp   AS SELECT * FROM hotspots WHERE sensor = 'VIIRS_SNPP';
CREATE OR REPLACE VIEW viirs_noaa20 AS SELECT * FROM hotspots WHERE sensor = 'VIIRS_NOAA20';
CREATE OR REPLACE VIEW paises AS
SELECT country, sum(detecciones) AS detecciones, min(year) AS desde, max(year) AS hasta
FROM resumen_mensual GROUP BY country;
"""


def paso_consolidar(workers: int):
    zips = [p for p in sorted(consolidar.RAW.glob("*.zip")) if consolidar.parse_name(p)]
    todo = [p for p in zips if not consolidar.out_path(*consolidar.parse_name(p)).exists()]
    print(f"[1/3] Consolidar: {len(zips)} ZIP, {len(todo)} por convertir a Parquet")
    if not todo:
        return
    from concurrent.futures import ProcessPoolExecutor, as_completed
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(consolidar.consolidate_zip, str(p), None): p for p in todo}
        for i, fut in enumerate(as_completed(futs), 1):
            r = fut.result()
            print(f"    [{i}/{len(todo)}] {r['archivo']}: {r['filas']:,} filas ({r['seg']} s)", flush=True)


def run_sql(con, script: str):
    for stmt in (x.strip() for x in script.split(";")):
        if stmt:
            con.execute(stmt).fetchall()


def paso_cargar(con):
    run_sql(con, DDL)
    files = sorted(consolidar.OUT.rglob("*.parquet"))
    done = {r[0] for r in con.execute("SELECT archivo FROM _cargados").fetchall()}
    todo = [f for f in files if f.name not in done]
    print(f"[2/3] Cargar a DuckDB: {len(files)} Parquet, {len(todo)} por cargar")
    for i, f in enumerate(todo, 1):
        t0 = time.time()
        con.execute("BEGIN")
        n = con.execute(f"INSERT INTO hotspots SELECT * FROM read_parquet('{f.as_posix()}')").fetchall()[0][0]
        con.execute(RESUMEN_ARCHIVO.format(f=f.as_posix())).fetchall()
        con.execute("INSERT INTO _cargados VALUES (?, ?, now())", [f.name, n]).fetchall()
        con.execute("COMMIT")
        print(f"    [{i}/{len(todo)}] {f.name}: {n:,} filas ({time.time() - t0:.0f} s)", flush=True)


def paso_resumen(con):
    print("[3/3] Vistas y resumen…", flush=True)
    run_sql(con, POST)
    total = con.execute("SELECT sum(detecciones) FROM resumen_mensual").fetchall()[0][0]
    print(con.sql("SELECT sensor, min(year) desde, max(year) hasta, sum(detecciones) filas, "
                  "count(DISTINCT country) paises FROM resumen_mensual GROUP BY sensor ORDER BY sensor"))
    con.execute("CHECKPOINT").fetchall()
    print(f"Total: {total:,} detecciones · {DB.stat().st_size / 1e9:.1f} GB en {DB.relative_to(ROOT)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--solo", choices=["consolidar", "cargar", "resumen"], help="correr un solo paso")
    ap.add_argument("--borrar-parquet", action="store_true", help="borra data/consolidado al terminar")
    args = ap.parse_args()

    if args.solo in (None, "consolidar"):
        paso_consolidar(args.workers)
    if args.solo in (None, "cargar", "resumen"):
        DB.parent.mkdir(parents=True, exist_ok=True)
        con = duckdb.connect(str(DB))
        if args.solo in (None, "cargar"):
            paso_cargar(con)
        if args.solo in (None, "resumen"):
            paso_resumen(con)
        con.close()
    if args.borrar_parquet and args.solo is None:
        shutil.rmtree(consolidar.OUT, ignore_errors=True)
        print("data/consolidado borrado.")


if __name__ == "__main__":
    main()
