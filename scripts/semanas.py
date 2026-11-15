"""Series semanales armonizadas por país y región de ejemplo, y serie mensual de cada país (alertas de la app).

La armonización es mensual (celda × mes, scripts/preparar_app.py). Para ver semana a semana, cada mes armonizado se
reparte entre sus días según lo que vio el sensor de ese mes: VIIRS S-NPP o NOAA-20 donde es lo observado, MODIS
(Terra + Aqua, o solo Terra) donde el mes viene del modelo. Así la suma de las semanas de un mes da el mes de la app.
Si el sensor no vio nada ese mes pero el modelo estima algo (fuentes fijas), se reparte parejo entre los días.

Semanas ISO (de lunes a domingo). Solo quedan las semanas con los siete días dentro de meses con datos.

  data/app/semanas.parquet     area ("pais:<país>" o "region:<región>"), categoria, semana (lunes), det
  data/app/paises_mes.parquet  country, categoria, año, mes, det   (para ver qué países están fuera de lo normal)

Necesita data/db_nasa.duckdb (scripts/crear_db.py) y data/app (scripts/preparar_app.py).

Uso:  python scripts/semanas.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "data" / "app"
DB = ROOT / "data" / "db_nasa.duckdb"
sys.path.insert(0, str(ROOT / "app"))
from datos import GRADO, REGIONES  # noqa: E402


def main():
    t0 = time.time()
    con = duckdb.connect()
    con.execute("SET preserve_insertion_order = false")
    con.execute(f"ATTACH '{DB.as_posix()}' AS nasa (READ_ONLY)")
    celdas = ", ".join(f"'{(APP / f).as_posix()}'" for f in ("celdas.parquet", "celdas_fijas.parquet"))
    con.execute(f"CREATE VIEW celdas AS SELECT * FROM read_parquet([{celdas}], union_by_name = true)")
    con.execute(f"CREATE TABLE meses AS SELECT * FROM '{(APP / 'meses.parquet').as_posix()}'")

    # celdas de cada área, con la misma regla que la app (datos.celdas_pais y datos.celdas_caja)
    con.execute(f"""
    CREATE TABLE areas AS
    WITH p AS (SELECT * FROM '{(APP / 'paises.parquet').as_posix()}'),
         grandes AS (SELECT country, fila, col FROM p WHERE parte >= 0.5),
         chicos AS (SELECT DISTINCT country, fila, col FROM p WHERE country NOT IN (SELECT country FROM grandes))
    SELECT 'pais:' || country AS area, fila, col FROM (SELECT * FROM grandes UNION ALL SELECT * FROM chicos)
    """)
    con.execute("CREATE TABLE todas AS SELECT DISTINCT fila, col, lat, lon FROM celdas")
    for nombre, (la0, la1, lo0, lo1) in REGIONES.items():
        con.execute(f"""INSERT INTO areas SELECT 'region:' || ?, fila, col FROM todas
                        WHERE lat BETWEEN {la0} AND {la1} AND lon BETWEEN {lo0} AND {lo1}""", [nombre])
    print(f"[{time.time() - t0:4.0f} s] {con.sql('SELECT count(DISTINCT area) FROM areas').fetchall()[0][0]} áreas")

    # mes armonizado de cada área (lo que muestra la app)
    con.execute("""
    CREATE TABLE mes_area AS
    SELECT a.area, c.categoria, c.año, c.mes, sum(c.det) det
    FROM celdas c JOIN areas a USING (fila, col) GROUP BY ALL
    """)
    # detecciones por día, área, tipo y sensor (Terra, Aqua, N = S-NPP, N20 = NOAA-20)
    con.execute(f"""
    CREATE TABLE dia AS
    WITH h AS (
      SELECT CAST(floor(latitude / {GRADO}) AS INT) fila, CAST(floor(longitude / {GRADO}) AS INT) col, acq_date,
             CASE type WHEN 0 THEN 'veg' WHEN 1 THEN 'volcan' WHEN 2 THEN 'industria' ELSE 'mar' END categoria,
             CASE WHEN sensor = 'MODIS' THEN satellite WHEN satellite = 'N' THEN 'N' ELSE 'N20' END sat
      FROM nasa.hotspots
    )
    SELECT a.area, h.categoria, h.acq_date fecha, h.sat, count(*)::INT n
    FROM h JOIN areas a USING (fila, col) GROUP BY ALL
    """)
    print(f"[{time.time() - t0:4.0f} s] {con.sql('SELECT count(*) FROM dia').fetchall()[0][0]:,} área-día")

    # el sensor que cuenta en cada mes, según la fuente del mes en la app
    con.execute("""
    CREATE TABLE peso AS
    WITH d AS (
      SELECT d.area, d.categoria, d.fecha, year(d.fecha) año, month(d.fecha) mes, m.fuente,
             sum(d.n) FILTER (WHERE (m.fuente = 'S' AND d.sat = 'N') OR (m.fuente = 'N' AND d.sat = 'N20')
                                 OR (m.fuente = 'M' AND d.sat IN ('Terra', 'Aqua')) OR (m.fuente = 'T' AND d.sat = 'Terra')) n
      FROM dia d JOIN meses m ON m.año = year(d.fecha) AND m.mes = month(d.fecha) GROUP BY ALL
    )
    SELECT *, sum(n) OVER (PARTITION BY area, categoria, año, mes) n_mes FROM d
    """)
    con.execute("""
    CREATE TABLE dias AS
    SELECT CAST(d AS DATE) fecha, year(d) año, month(d) mes
    FROM range(DATE '2000-11-01', DATE '2026-01-01', INTERVAL 1 DAY) t(d)
    JOIN meses m ON m.año = year(d) AND m.mes = month(d)
    """)
    # cada día se lleva su parte del mes; los días sin detecciones también existen (dias), así que el total del mes
    # (n_mes) va aparte, en pm
    con.execute("""
    CREATE TABLE sem AS
    WITH x AS (
      SELECT ma.area, ma.categoria, ds.fecha,
             CASE WHEN coalesce(pm.n_mes, 0) > 0 THEN ma.det * coalesce(p.n, 0) / pm.n_mes
                  ELSE ma.det / day(last_day(ds.fecha)) END det
      FROM mes_area ma
      JOIN dias ds USING (año, mes)
      LEFT JOIN (SELECT DISTINCT area, categoria, año, mes, n_mes FROM peso WHERE n_mes > 0) pm
             USING (area, categoria, año, mes)
      LEFT JOIN (SELECT area, categoria, fecha, n FROM peso) p USING (area, categoria, fecha)
    )
    SELECT area, categoria, date_trunc('week', fecha)::DATE semana, CAST(sum(det) AS FLOAT) det FROM x GROUP BY ALL
    """)
    # solo semanas completas: sus siete días caen en meses con datos
    con.execute("""
    CREATE TABLE completas AS
    SELECT date_trunc('week', fecha)::DATE semana FROM dias GROUP BY 1 HAVING count(*) = 7
    """)
    con.execute(f"""
    COPY (SELECT s.* FROM sem s JOIN completas USING (semana) WHERE s.det > 0 ORDER BY area, categoria, semana)
    TO '{(APP / 'semanas.parquet').as_posix()}' (FORMAT parquet, COMPRESSION zstd)
    """)
    con.execute(f"""
    COPY (SELECT substr(area, 6) country, categoria, CAST(año AS SMALLINT) año, CAST(mes AS TINYINT) mes,
                 CAST(det AS FLOAT) det
          FROM mes_area WHERE area LIKE 'pais:%' AND det > 0 ORDER BY country, categoria, año, mes)
    TO '{(APP / 'paises_mes.parquet').as_posix()}' (FORMAT parquet, COMPRESSION zstd)
    """)
    # control: las semanas suman lo mismo que los meses (en los meses de semanas completas, aprox.)
    tot = con.sql("SELECT (SELECT sum(det) FROM sem) s, (SELECT sum(det) FROM mes_area) m").fetchall()[0]
    print(f"[{time.time() - t0:4.0f} s] listo · suma semanas {tot[0]:,.0f} · suma meses {tot[1]:,.0f}")


if __name__ == "__main__":
    main()
