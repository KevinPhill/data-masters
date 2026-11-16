# AI-assisted code (Claude, Anthropic), directed and reviewed by the team. See README: "Use of artificial intelligence".
"""Prepara los datos que usa la app de Streamlit (data/app/).

Entrada
  data/modelo/celdas_0.5.parquet         tabla celda (0.5°) × mes del notebook 03_modelo
  data/modelo/armonizado_celdas.parquet  (opcional) predicciones LightGBM por celda y mes
  data/db_nasa.duckdb                    (opcional) para saber a qué país pertenece cada celda

Salida (data/app/)
  celdas.parquet   celda × mes con detecciones armonizadas en unidades VIIRS, su rango y la fuente
                   (con el modelo integral: solo vegetación)
  celdas_fijas.parquet  (modelo integral) lo mismo para volcanes, industria y gas, y costa afuera
  meses.parquet    qué fuente se usó en cada mes (y por lo tanto qué meses son válidos)
  paises.parquet   país mayoritario de cada celda
  meta.json        método usado y fecha

Armonización (columna categoria: veg, volcan, industria, mar; "todos" si se armonizan juntos)
  · modelo integral (si existen los archivos de scripts/modelo_integral.py): cada tipo FIRMS por separado
        - vegetación: LightGBM de vegetación × corrección regional; solo Terra: Terra × razón VIIRS/Terra
        - volcanes, industria y gas, costa afuera: modelo por celda de scripts/validar.py (modelo_fijas)
  · si no, todos los tipos juntos:
  · 2012 en adelante, meses con VIIRS completo  -> VIIRS observado (S-NPP o NOAA-20)
  · meses solo con MODIS                       -> MODIS convertido a "unidades VIIRS":
        - con el modelo LightGBM (notebook 03_modelo) si existe armonizado_celdas.parquet, multiplicado por su
          corrección regional: Σ VIIRS ÷ Σ predicho en la validación, por región de 10° y mes (scripts/validar.py)
        - si no, con el modelo Referencia: MODIS × razón VIIRS/MODIS de su región (10°) y mes,
          aprendida en 2012–2021 (antes de la deriva de órbitas de Terra y Aqua)
        - meses con solo Terra (2000–2002): Terra × razón VIIRS/Terra de la región y mes
  · rango de incertidumbre (percentiles 5 y 95, año a año, en la región de 10° y el mes):
        - LightGBM: de observado ÷ predicho en la validación dejando un año fuera (validacion_por_año.parquet)
        - Referencia: de la razón VIIRS/MODIS

Uso:  python scripts/preparar_app.py
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

import duckdb

import validar
from validar import CORRECCION, LOYO_LGBM, rango_lightgbm

ROOT = Path(__file__).resolve().parents[1]
CELDAS = ROOT / "data" / "modelo" / "celdas_0.5.parquet"
MODELO = ROOT / "data" / "modelo" / "armonizado_celdas.parquet"
DB = ROOT / "data" / "db_nasa.duckdb"
OUT = ROOT / "data" / "app"

AÑOS_CALIBRACION = (2012, 2021)  # traslape MODIS–VIIRS con órbitas normales


def celdas_integral(con: duckdb.DuckDBPyConnection):
    """Modelo integral: celdas.parquet (vegetación) y celdas_fijas.parquet (volcanes, industria y gas, costa afuera).
    Necesita las tablas c y meses de main()."""
    validar.conteos_tipo(con)
    validar.modelo_vegetacion(con)
    validar.modelo_fijas(con)
    a0, a1 = AÑOS_CALIBRACION
    # razones VIIRS/MODIS y VIIRS/Terra de vegetación por región y mes: respaldo sin predicción y meses con solo Terra
    for nombre, base in (("veg_m", "m"), ("veg_t", "t")):
        con.execute(f"""
        CREATE TABLE anual_{nombre} AS
        SELECT {validar.region_fc('x')} region, x.mes, x.año, sum(x.v) v, sum(x.{base}) m
        FROM tt x JOIN meses_sat s USING (año, mes)
        WHERE x.tipo = 0 AND s.terra_ok AND s.aqua_ok AND s.viirs_sat IS NOT NULL AND x.año BETWEEN {a0} AND {a1}
        GROUP BY ALL
        """)
        validar.factores(con, f"anual_{nombre}", f"f_{nombre}")
    lo, hi = CORRECCION
    con.execute(f"""
    COPY (
      WITH x AS (
        SELECT c.fila, c.col, c.lat, c.lon, c.año, c.mes, ms.fuente, coalesce(o.m, 0) modis_n, coalesce(o.t, 0) terra_n,
               coalesce(o.v, 0) viirs_n, p.pred,
               least(greatest(coalesce(q.k, qg.k), {lo}), {hi}) q, coalesce(q.k, qg.k) qk,
               coalesce(q.k_lo, qg.k_lo) q_lo, coalesce(q.k_hi, qg.k_hi) q_hi,
               coalesce(r.k, rg.k) k, coalesce(r.k_lo, rg.k_lo) k_lo, coalesce(r.k_hi, rg.k_hi) k_hi,
               coalesce(t.k, tg.k) kt, coalesce(t.k_lo, tg.k_lo) kt_lo, coalesce(t.k_hi, tg.k_hi) kt_hi
        FROM c
        JOIN meses ms USING (año, mes)
        LEFT JOIN (SELECT * FROM tt WHERE tipo = 0) o USING (fila, col, año, mes)
        LEFT JOIN read_parquet('{validar.VEG_CELDAS.as_posix()}') p USING (fila, col, año, mes)
        LEFT JOIN f_veg q ON q.prueba = 0 AND q.region = c.region AND q.mes = c.mes
        LEFT JOIN f_veg qg ON qg.prueba = 0 AND qg.region = -1 AND qg.mes = c.mes
        LEFT JOIN f_veg_m r ON r.prueba = 0 AND r.region = c.region AND r.mes = c.mes
        LEFT JOIN f_veg_m rg ON rg.prueba = 0 AND rg.region = -1 AND rg.mes = c.mes
        LEFT JOIN f_veg_t t ON t.prueba = 0 AND t.region = c.region AND t.mes = c.mes
        LEFT JOIN f_veg_t tg ON tg.prueba = 0 AND tg.region = -1 AND tg.mes = c.mes
      ),
      y AS (
        SELECT *,
          CASE WHEN fuente IN ('N', 'S') THEN viirs_n
               WHEN fuente = 'M' THEN coalesce(pred * q, modis_n * k)
               WHEN fuente = 'T' THEN terra_n * kt END AS det,
          CASE WHEN fuente IN ('N', 'S') THEN viirs_n
               WHEN fuente = 'M' AND pred IS NOT NULL THEN pred * q * q_lo / nullif(qk, 0)
               WHEN fuente = 'M' THEN modis_n * k_lo ELSE terra_n * kt_lo END AS det_bajo,
          CASE WHEN fuente IN ('N', 'S') THEN viirs_n
               WHEN fuente = 'M' AND pred IS NOT NULL THEN pred * q * q_hi / nullif(qk, 0)
               WHEN fuente = 'M' THEN modis_n * k_hi ELSE terra_n * kt_hi END AS det_alto
        FROM x
      )
      SELECT fila, col, lat, lon, CAST(año AS SMALLINT) año, CAST(mes AS TINYINT) mes, fuente, 'veg' AS categoria,
             CAST(round(det, 1) AS FLOAT) det, CAST(round(least(det_bajo, det), 1) AS FLOAT) det_bajo,
             CAST(round(greatest(det_alto, det), 1) AS FLOAT) det_alto, CAST(modis_n AS INT) modis_n,
             CAST(CASE WHEN fuente IN ('N', 'S') THEN viirs_n END AS INT) viirs_n
      FROM y
      WHERE coalesce(det, 0) >= 0.05 OR modis_n > 0 OR viirs_n > 0
      ORDER BY fila, col, año, mes
    ) TO '{(OUT / "celdas.parquet").as_posix()}' (FORMAT parquet, COMPRESSION zstd, ROW_GROUP_SIZE 100000)
    """)
    con.execute(f"""
    COPY (
      WITH y AS (
        SELECT n.fila, n.col, n.tipo, n.año, n.mes, ms.fuente, n.m_obs, n.v, n.region,
               CASE WHEN ms.fuente IN ('N', 'S') THEN n.v ELSE {validar._pred_fijas()} END AS det,
               coalesce(r.k_lo, g.k_lo) / nullif(coalesce(r.k, g.k), 0) k_lo,
               coalesce(r.k_hi, g.k_hi) / nullif(coalesce(r.k, g.k), 0) k_hi
        FROM nf n
        JOIN meses ms USING (año, mes)
        JOIN par_fijas p ON p.prueba = 0 AND p.tipo = n.tipo AND p.etapa = {validar._etapa()} AND p.fila = n.fila AND p.col = n.col
        LEFT JOIN f_fijas r ON r.prueba = 0 AND r.region = n.region AND r.mes = n.tipo
        LEFT JOIN f_fijas g ON g.prueba = 0 AND g.region = -1 AND g.mes = n.tipo
      )
      SELECT fila, col, CAST(fila * {validar.GRADO} + {validar.GRADO / 2} AS FLOAT) lat,
             CAST(col * {validar.GRADO} + {validar.GRADO / 2} AS FLOAT) lon,
             CAST(año AS SMALLINT) año, CAST(mes AS TINYINT) mes, fuente, {validar._categoria()} AS categoria,
             CAST(round(det, 1) AS FLOAT) det,
             CAST(round(CASE WHEN fuente IN ('N', 'S') THEN det ELSE det * least(k_lo, 1) END, 1) AS FLOAT) det_bajo,
             CAST(round(CASE WHEN fuente IN ('N', 'S') THEN det ELSE det * greatest(k_hi, 1) END, 1) AS FLOAT) det_alto,
             CAST(m_obs AS INT) modis_n, CAST(CASE WHEN fuente IN ('N', 'S') THEN v END AS INT) viirs_n
      FROM y
      WHERE det >= 0.05 OR m_obs > 0 OR v > 0
      ORDER BY categoria, fila, col, año, mes
    ) TO '{(OUT / "celdas_fijas.parquet").as_posix()}' (FORMAT parquet, COMPRESSION zstd, ROW_GROUP_SIZE 100000)
    """)


def main():
    t0 = time.time()
    if not CELDAS.exists():
        raise SystemExit(f"Falta {CELDAS}. Corre primero la sección 2 del notebook 03_modelo.")
    OUT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("SET preserve_insertion_order = false")

    con.execute(f"""
    CREATE TABLE c AS
    SELECT fila, col, lat, lon, año, mes, terra_ok, aqua_ok, viirs_sat,
           terra_dia + terra_noche + aqua_dia + aqua_noche AS modis_n,
           terra_dia + terra_noche                         AS terra_n,
           viirs_n,
           CAST(floor((lat + 90) / 10) * 36 + floor((lon + 180) / 10) AS INT) AS region
    FROM read_parquet('{CELDAS.as_posix()}')
    """)

    # ---- razones VIIRS/MODIS (modelo Referencia) por región y mes, año a año -------------
    a0, a1 = AÑOS_CALIBRACION
    con.execute(f"""
    CREATE TABLE anual AS
    SELECT region, mes, año,
           sum(viirs_n) AS v, sum(modis_n) AS m, sum(terra_n) AS t
    FROM c
    WHERE terra_ok AND aqua_ok AND viirs_sat IS NOT NULL AND año BETWEEN {a0} AND {a1}
    GROUP BY ALL
    """)
    con.execute("""
    CREATE TABLE razon AS
    WITH reg AS (
        SELECT region, mes,
               sum(v) / nullif(sum(m), 0) AS k,  sum(v) / nullif(sum(t), 0) AS k_terra,
               quantile_cont(v / nullif(m, 0), 0.05) AS k_lo,
               quantile_cont(v / nullif(m, 0), 0.95) AS k_hi,
               count(*) FILTER (WHERE m > 0) AS años
        FROM anual GROUP BY ALL
    ),
    glb AS (
        SELECT mes, sum(v) / sum(m) AS k, sum(v) / sum(t) AS k_terra,
               quantile_cont(v / m, 0.05) AS k_lo, quantile_cont(v / m, 0.95) AS k_hi
        FROM (SELECT mes, año, sum(v) v, sum(m) m, sum(t) t FROM anual GROUP BY ALL) GROUP BY mes
    )
    SELECT r.region, g.mes,
           coalesce(CASE WHEN r.años >= 3 THEN r.k END, g.k)             AS k,
           coalesce(CASE WHEN r.años >= 3 THEN r.k_terra END, g.k_terra) AS k_terra,
           coalesce(CASE WHEN r.años >= 3 THEN r.k_lo END, g.k_lo)       AS k_lo,
           coalesce(CASE WHEN r.años >= 3 THEN r.k_hi END, g.k_hi)       AS k_hi
    FROM glb g LEFT JOIN reg r USING (mes)
    UNION ALL   -- respaldo global para regiones sin datos de calibración
    SELECT -1, mes, k, k_terra, k_lo, k_hi FROM glb
    """)

    # ---- fuente por mes ----------------------------------------------------------------
    con.execute("""
    CREATE TABLE meses AS
    SELECT año, mes,
           CASE WHEN any_value(viirs_sat) = 'N20' THEN 'N'          -- VIIRS NOAA-20 observado
                WHEN any_value(viirs_sat) = 'N'   THEN 'S'          -- VIIRS S-NPP observado
                WHEN bool_or(terra_ok AND aqua_ok) THEN 'M'         -- MODIS Terra+Aqua -> VIIRS
                WHEN bool_or(terra_ok)            THEN 'T'          -- solo Terra -> VIIRS
           END AS fuente
    FROM (SELECT DISTINCT año, mes, viirs_sat, terra_ok, aqua_ok FROM c)
    GROUP BY año, mes
    HAVING fuente IS NOT NULL
    ORDER BY año, mes
    """)

    usar_integral = validar.hay_integral()
    usar_modelo = usar_integral or (MODELO.exists() and LOYO_LGBM.exists())
    if usar_integral:
        celdas_integral(con)
    else:
        (OUT / "celdas_fijas.parquet").unlink(missing_ok=True)
        if usar_modelo:
            con.execute(f"""
            CREATE TABLE modelo AS
            SELECT fila, col, año, mes, detecciones AS det_modelo FROM read_parquet('{MODELO.as_posix()}')
            """)
            rango_lightgbm(con, "f_lgbm")  # prueba = 0: con todos los años 2012–2021
            con.execute(f"""CREATE TABLE rango AS
                            SELECT region, mes, least(greatest(k, {CORRECCION[0]}), {CORRECCION[1]}) AS q, k_lo AS q_lo, k_hi AS q_hi
                            FROM f_lgbm WHERE prueba = 0""")
        else:
            con.execute("CREATE TABLE modelo (fila INT, col INT, año BIGINT, mes BIGINT, det_modelo DOUBLE)")
            con.execute("CREATE TABLE rango (region INT, mes BIGINT, q DOUBLE, q_lo DOUBLE, q_hi DOUBLE)")

        # ---- celda × mes armonizada ----------------------------------------------------------
        con.execute(f"""
        COPY (
          WITH x AS (
            SELECT c.fila, c.col, c.lat, c.lon, c.año, c.mes, ms.fuente, c.modis_n, c.viirs_n,
                   coalesce(r.k, g.k) k, coalesce(r.k_terra, g.k_terra) k_terra,
                   coalesce(r.k_lo, g.k_lo) k_lo, coalesce(r.k_hi, g.k_hi) k_hi,
                   md.det_modelo, c.terra_n,
                   coalesce(qr.q, qg.q) q, coalesce(qr.q_lo, qg.q_lo) q_lo, coalesce(qr.q_hi, qg.q_hi) q_hi
            FROM c
            JOIN meses ms USING (año, mes)
            LEFT JOIN razon r ON r.region = c.region AND r.mes = c.mes
            LEFT JOIN razon g ON g.region = -1 AND g.mes = c.mes
            LEFT JOIN modelo md USING (fila, col, año, mes)
            LEFT JOIN rango qr ON qr.region = c.region AND qr.mes = c.mes
            LEFT JOIN rango qg ON qg.region = -1 AND qg.mes = c.mes
          ),
          y AS (
            SELECT *,
              CASE fuente
                WHEN 'N' THEN viirs_n WHEN 'S' THEN viirs_n
                WHEN 'M' THEN coalesce(det_modelo * q, modis_n * k)
                WHEN 'T' THEN terra_n * k_terra
              END AS det
            FROM x
          )
          -- con LightGBM el rango sale de su error en la validación; sin él (o con solo Terra), de la razón
          SELECT fila, col, lat, lon, CAST(año AS SMALLINT) año, CAST(mes AS TINYINT) mes, fuente, 'todos' AS categoria,
                 CAST(round(det, 1) AS FLOAT) det,
                 CAST(round(CASE WHEN fuente IN ('N','S') THEN det
                                 WHEN fuente = 'M' AND det_modelo IS NOT NULL THEN det_modelo * q_lo
                                 ELSE det * k_lo / nullif(k, 0) END, 1) AS FLOAT) det_bajo,
                 CAST(round(CASE WHEN fuente IN ('N','S') THEN det
                                 WHEN fuente = 'M' AND det_modelo IS NOT NULL THEN det_modelo * q_hi
                                 ELSE det * k_hi / nullif(k, 0) END, 1) AS FLOAT) det_alto,
                 CAST(modis_n AS INT) modis_n, CAST(viirs_n AS INT) viirs_n
          FROM y
          WHERE coalesce(det, 0) >= 0.05 OR coalesce(modis_n, 0) > 0 OR coalesce(viirs_n, 0) > 0
          ORDER BY fila, col, año, mes
        ) TO '{(OUT / "celdas.parquet").as_posix()}' (FORMAT parquet, COMPRESSION zstd, ROW_GROUP_SIZE 100000)
        """)
    con.execute(f"COPY meses TO '{(OUT / 'meses.parquet').as_posix()}' (FORMAT parquet)")

    # ---- país de cada celda --------------------------------------------------------------
    if DB.exists():
        print("Asignando país a cada celda (lee db_nasa.duckdb, ~1 min)…", flush=True)
        con.execute(f"ATTACH '{DB.as_posix()}' AS nasa (READ_ONLY)")
        con.execute(f"""
        COPY (
          WITH n AS (
            SELECT CAST(floor(latitude / 0.5) AS INT) fila, CAST(floor(longitude / 0.5) AS INT) col,
                   country, count(*) n
            FROM nasa.hotspots GROUP BY ALL
          )
          SELECT fila, col, country, n, n / sum(n) OVER (PARTITION BY fila, col) AS parte
          FROM n
        ) TO '{(OUT / "paises.parquet").as_posix()}' (FORMAT parquet)
        """)
    else:
        print("Aviso: no está data/db_nasa.duckdb; la app no tendrá selección por país.")

    archivos = [f"'{p.as_posix()}'" for p in (OUT / "celdas.parquet", OUT / "celdas_fijas.parquet") if p.exists()]
    resumen = con.sql(f"""
        SELECT count(*) filas, count(DISTINCT (fila, col)) celdas, min(año) desde, max(año) hasta
        FROM read_parquet([{", ".join(archivos)}])""").fetchall()[0]
    fuentes = dict(con.sql("SELECT fuente, count(*) FROM meses GROUP BY 1").fetchall())
    meta = {
        "metodo": ("Integral: vegetación con LightGBM + corrección regional; volcanes, industria y gas, y costa afuera "
                   "con un modelo por celda → detecciones VIIRS" if usar_integral else
                   "LightGBM (notebook 03_modelo) + corrección regional: 28 entradas → detecciones VIIRS NOAA-20" if usar_modelo else
                   "Referencia: MODIS × razón VIIRS/MODIS por región de 10° y mes (2012–2021)"),
        "integral": usar_integral,
        "usa_modelo": usar_modelo,
        "años_calibracion": list(AÑOS_CALIBRACION),
        "generado": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "filas": resumen[0], "celdas": resumen[1], "desde": resumen[2], "hasta": resumen[3],
        "meses_por_fuente": fuentes,
    }
    (OUT / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    print(json.dumps(meta, indent=2, ensure_ascii=False))
    print(f"Listo en {time.time() - t0:.0f} s -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
