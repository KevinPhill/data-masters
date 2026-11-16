# AI-assisted code (Claude, Anthropic), directed and reviewed by the team. See README: "Use of artificial intelligence".
"""Validates the harmonization model the app uses, always against what VIIRS really saw.

Two tests:
  · leaving one year out (2012–2021): each year Y is predicted with a model that did not see Y.
  · never-seen years (2022–2025): the final model did not use them, and the Terra and Aqua orbits have already drifted.

Models
  lightgbm  (the app's) predictions from notebook 03_modelo:
              2012–2021  data/modelo/validacion_por_año.parquet   (one year out at a time)
              2022–2025  data/modelo/armonizado_celdas.parquet     (model trained without those years)
            with regional correction: each prediction is multiplied by k = Σ VIIRS ÷ Σ predicted of its 10°
            region and month in the validation, without the year being predicted (capped at CORRECCION)
  razon     MODIS × VIIRS/MODIS ratio per 10° region and month, recomputed without the year being predicted.
            Used if the LightGBM files are missing; scripts/evaluar_modelos.py uses it for comparison.

Range of each prediction: percentiles 5 and 95, year by year, of observed ÷ predicted in its 10° region and
month (without the year being predicted). If the region has fewer than 3 years, the world's for that month.

Output (data/app/)
  validacion.parquet  cell × month: observed VIIRS, raw MODIS, prediction and its range (p5–p95)
  validacion.json     global and per-country metrics

Usage:  python scripts/validar.py
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
CELDAS = ROOT / "data" / "modelo" / "celdas_0.5.parquet"
LOYO_LGBM = ROOT / "data" / "modelo" / "validacion_por_año.parquet"
MODELO_LGBM = ROOT / "data" / "modelo" / "armonizado_celdas.parquet"
PAISES = ROOT / "data" / "app" / "paises.parquet"
OUT = ROOT / "data" / "app"
CALIBRACION = (2012, 2021)
FUERA = (2022, 2025)
GRADO = 0.5
CORRECCION = (0.5, 2.0)  # limits of the LightGBM regional correction factor
MINIMO_FIJAS = 100        # fixed sources: the range uses the region only if it predicts at least this much per year (otherwise the world)
TOPE_FIJAS = 3            # fixed sources: the range goes from a third to three times the estimate, at most
ETAPA_NOAA20 = 2018       # fixed sources: in 2018 the reference VIIRS changes and MODIS flags ~6 times more volcanoes
REGION = "CAST(floor((lat + 90) / 10) * 36 + floor((lon + 180) / 10) AS INT)"
# integral model (scripts/modelo_integral.py): counts per FIRMS type and vegetation LightGBM
TIPOS = ROOT / "data" / "modelo" / "tipos_celdas.parquet"
VEG_CELDAS = ROOT / "data" / "modelo" / "veg_celdas.parquet"
VEG_LOYO = ROOT / "data" / "modelo" / "veg_loyo.parquet"
CATEGORIAS = {0: "veg", 1: "volcan", 2: "industria", 3: "mar"}  # FIRMS type → app category


def region_fc(t: str = "") -> str:
    """10° region from fila and col (cell centre)."""
    p = f"{t}." if t else ""
    return (f"CAST(floor(({p}fila * {GRADO} + {GRADO / 2} + 90) / 10) * 36 + "
            f"floor(({p}col * {GRADO} + {GRADO / 2} + 180) / 10) AS INT)")


def hay_lightgbm() -> bool:
    return LOYO_LGBM.exists() and MODELO_LGBM.exists()


def tabla_base(con: duckdb.DuckDBPyConnection):
    """c: cell × month with complete MODIS and VIIRS, 2012–2025."""
    con.execute(f"""
    CREATE OR REPLACE TABLE c AS
    SELECT fila, col, año, mes,
           terra_dia + terra_noche + aqua_dia + aqua_noche AS modis_n, viirs_n, {REGION} AS region
    FROM read_parquet('{CELDAS.as_posix()}')
    WHERE terra_ok AND aqua_ok AND viirs_sat IS NOT NULL AND año BETWEEN {CALIBRACION[0]} AND {FUERA[1]}
    """)


def factores(con: duckdb.DuckDBPyConnection, anual: str, nombre: str, minimo: float = 0, minimo_año: float = 0):
    """For each held-out year (prueba; 0 = all years) and region × month: k = Σv / Σm and percentiles 5–95 of
    v / m year by year, without the held-out year. anual: table with region, mes, año, v (observed), m (base).
    The region is used if it has at least 3 years with m > 0 and a mean m ≥ minimo; otherwise, the world for that month.
    The percentiles only use years with m ≥ minimo_año (the ratio between two small numbers says nothing)."""
    a0, a1 = CALIBRACION
    con.execute(f"""
    CREATE OR REPLACE TABLE {nombre} AS
    WITH cal AS (
        SELECT p.prueba, a.* FROM {anual} a,
               (SELECT unnest(range({a0}, {a1} + 1)) AS prueba UNION ALL SELECT 0) p
        WHERE a.año <> p.prueba
    ),
    reg AS (
        SELECT prueba, region, mes, sum(v) / nullif(sum(m), 0) k,
               quantile_cont(v / nullif(m, 0), 0.05) FILTER (WHERE m >= {minimo_año}) k_lo,
               quantile_cont(v / nullif(m, 0), 0.95) FILTER (WHERE m >= {minimo_año}) k_hi,
               count(*) FILTER (WHERE m > 0) años, avg(m) m_medio
        FROM cal GROUP BY ALL
    ),
    glb AS (
        SELECT prueba, mes, sum(v) / sum(m) k, quantile_cont(v / m, 0.05) k_lo, quantile_cont(v / m, 0.95) k_hi
        FROM (SELECT prueba, mes, año, sum(v) v, sum(m) m FROM cal GROUP BY ALL) GROUP BY ALL
    )
    SELECT g.prueba, r.region, g.mes,
           coalesce(CASE WHEN r.años >= 3 AND r.m_medio >= {minimo} THEN r.k END, g.k) k,
           coalesce(CASE WHEN r.años >= 3 AND r.m_medio >= {minimo} THEN r.k_lo END, g.k_lo) k_lo,
           coalesce(CASE WHEN r.años >= 3 AND r.m_medio >= {minimo} THEN r.k_hi END, g.k_hi) k_hi
    FROM glb g LEFT JOIN reg r ON r.prueba = g.prueba AND r.mes = g.mes
    UNION ALL
    SELECT prueba, -1, mes, k, k_lo, k_hi FROM glb
    """)


def _etapa(año: str = "n.año") -> str:
    """1 = MODIS alongside S-NPP (until 2017, and backwards); 2 = alongside NOAA-20 (from 2018)."""
    return f"CASE WHEN {año} < {ETAPA_NOAA20} THEN 1 ELSE 2 END"


def _prueba(año: str = "c.año") -> str:
    return f"CASE WHEN {año} <= {CALIBRACION[1]} THEN {año} ELSE 0 END"


def validacion_razon(con: duckdb.DuckDBPyConnection, nombre: str = "v_razon"):
    """Ratio model: the ratio of each held-out year is computed without that year (same rules as preparar_app)."""
    tabla_base(con)
    a0, a1 = CALIBRACION
    con.execute(f"""CREATE OR REPLACE TABLE anual_razon AS
                    SELECT region, mes, año, sum(viirs_n) v, sum(modis_n) m FROM c
                    WHERE año BETWEEN {a0} AND {a1} GROUP BY ALL""")
    factores(con, "anual_razon", "f_razon")
    con.execute(f"""
    CREATE OR REPLACE TABLE {nombre} AS
    SELECT c.fila, c.col, CAST(c.año AS SMALLINT) año, CAST(c.mes AS TINYINT) mes,
           CASE WHEN c.año <= {a1} THEN 'loyo' ELSE 'fuera' END AS prueba,
           CAST(c.viirs_n AS INT) viirs, CAST(c.modis_n AS INT) modis,
           CAST(c.modis_n * coalesce(r.k, g.k) AS FLOAT) pred,
           CAST(c.modis_n * coalesce(r.k_lo, g.k_lo) AS FLOAT) pred_bajo,
           CAST(c.modis_n * coalesce(r.k_hi, g.k_hi) AS FLOAT) pred_alto
    FROM c
    LEFT JOIN f_razon r ON r.prueba = {_prueba()} AND r.region = c.region AND r.mes = c.mes
    LEFT JOIN f_razon g ON g.prueba = {_prueba()} AND g.region = -1 AND g.mes = c.mes
    WHERE coalesce(c.viirs_n, 0) > 0 OR coalesce(c.modis_n, 0) > 0
    """)


def predicciones_lightgbm(con: duckdb.DuckDBPyConnection):
    """p: unseen LightGBM prediction for each cell × month (one year out in 2012–2021; final model in 2022–2025)."""
    con.execute(f"""
    CREATE OR REPLACE TABLE p AS
    SELECT CAST(floor(lat / {GRADO}) AS INT) fila, CAST(floor(lon / {GRADO}) AS INT) col, año, mes, detecciones pred
    FROM read_parquet('{LOYO_LGBM.as_posix()}')
    UNION ALL
    SELECT fila, col, año, mes, detecciones FROM read_parquet('{MODELO_LGBM.as_posix()}')
    WHERE año BETWEEN {FUERA[0]} AND {FUERA[1]}
    """)


def rango_lightgbm(con: duckdb.DuckDBPyConnection, nombre: str = "f_lgbm"):
    """LightGBM regional correction: per region × month and held-out year, k = Σ observed ÷ Σ predicted (one year
    out) and percentiles 5–95 of observed ÷ predicted year by year, without the held-out year."""
    a0, a1 = CALIBRACION
    con.execute(f"""
    CREATE OR REPLACE TABLE anual_lgbm AS
    SELECT {REGION} region, mes, año, sum(viirs_n) v, sum(detecciones) m
    FROM read_parquet('{LOYO_LGBM.as_posix()}') WHERE año BETWEEN {a0} AND {a1} GROUP BY ALL
    """)
    factores(con, "anual_lgbm", nombre)


def validacion_lightgbm(con: duckdb.DuckDBPyConnection, nombre: str = "v_lgbm"):
    tabla_base(con)
    predicciones_lightgbm(con)
    rango_lightgbm(con)
    a1 = CALIBRACION[1]
    con.execute(f"""
    CREATE OR REPLACE TABLE {nombre} AS
    SELECT c.fila, c.col, CAST(c.año AS SMALLINT) año, CAST(c.mes AS TINYINT) mes,
           CASE WHEN c.año <= {a1} THEN 'loyo' ELSE 'fuera' END AS prueba,
           CAST(c.viirs_n AS INT) viirs, CAST(c.modis_n AS INT) modis,
           CAST(coalesce(p.pred, 0) * least(greatest(coalesce(r.k, g.k), {CORRECCION[0]}), {CORRECCION[1]}) AS FLOAT) pred,
           CAST(coalesce(p.pred, 0) * least(greatest(coalesce(r.k, g.k), {CORRECCION[0]}), {CORRECCION[1]})
                * coalesce(r.k_lo, g.k_lo) / nullif(coalesce(r.k, g.k), 0) AS FLOAT) pred_bajo,
           CAST(coalesce(p.pred, 0) * least(greatest(coalesce(r.k, g.k), {CORRECCION[0]}), {CORRECCION[1]})
                * coalesce(r.k_hi, g.k_hi) / nullif(coalesce(r.k, g.k), 0) AS FLOAT) pred_alto
    FROM c
    LEFT JOIN p USING (fila, col, año, mes)
    LEFT JOIN f_lgbm r ON r.prueba = {_prueba()} AND r.region = c.region AND r.mes = c.mes
    LEFT JOIN f_lgbm g ON g.prueba = {_prueba()} AND g.region = -1 AND g.mes = c.mes
    WHERE coalesce(c.viirs_n, 0) > 0 OR coalesce(c.modis_n, 0) > 0 OR coalesce(p.pred, 0) >= 0.5
    """)


# ===================================================================================== integral model
def hay_integral() -> bool:
    return TIPOS.exists() and VEG_CELDAS.exists() and VEG_LOYO.exists()


def _categoria(tipo: str = "tipo") -> str:
    return "CASE {} {} END".format(tipo, " ".join(f"WHEN {t} THEN '{c}'" for t, c in CATEGORIAS.items()))


def conteos_tipo(con: duckdb.DuckDBPyConnection):
    """meses_sat: which satellites count in each month. tt: detections per cell, month and FIRMS type: m (Terra + Aqua),
    t (Terra) and v (that month's VIIRS, S-NPP or NOAA-20)."""
    con.execute(f"""CREATE OR REPLACE TABLE meses_sat AS
                    SELECT DISTINCT año, mes, terra_ok, aqua_ok, viirs_sat FROM read_parquet('{CELDAS.as_posix()}')""")
    con.execute(f"""
    CREATE OR REPLACE TABLE tt AS
    SELECT x.fila, x.col, x.tipo, x.año, x.mes,
           coalesce(sum(x.n) FILTER (WHERE x.sat IN ('Terra', 'Aqua')), 0) m,
           coalesce(sum(x.n) FILTER (WHERE x.sat = 'Terra'), 0) t,
           coalesce(sum(x.n) FILTER (WHERE x.sat = s.viirs_sat), 0) v
    FROM read_parquet('{TIPOS.as_posix()}') x JOIN meses_sat s USING (año, mes) GROUP BY ALL
    """)


def modelo_vegetacion(con: duckdb.DuckDBPyConnection):
    """p_veg: vegetation LightGBM without seeing the year (one year out in 2012–2021, final model afterwards).
    f_veg: its regional correction (Σ VIIRS ÷ Σ predicted per 10° region and month, without the year being predicted)
    and the p5–p95 range. Needs tt (conteos_tipo)."""
    a0, a1 = CALIBRACION
    con.execute(f"""
    CREATE OR REPLACE TABLE p_veg AS
    SELECT fila, col, año, mes, pred FROM read_parquet('{VEG_LOYO.as_posix()}')
    UNION ALL
    SELECT fila, col, año, mes, pred FROM read_parquet('{VEG_CELDAS.as_posix()}') WHERE año BETWEEN {FUERA[0]} AND {FUERA[1]}
    """)
    con.execute(f"""
    CREATE OR REPLACE TABLE anual_veg AS
    SELECT {region_fc()} region, mes, año, sum(coalesce(o.v, 0)) v, sum(coalesce(l.pred, 0)) m
    FROM read_parquet('{VEG_LOYO.as_posix()}') l
    FULL JOIN (SELECT x.fila, x.col, x.año, x.mes, x.v FROM tt x JOIN meses_sat s USING (año, mes)
               WHERE x.tipo = 0 AND s.terra_ok AND s.aqua_ok AND s.viirs_sat IS NOT NULL
                 AND x.año BETWEEN {a0} AND {a1}) o
         USING (fila, col, año, mes)  -- only months with complete MODIS and VIIRS: where the model predicts and is compared
    WHERE año BETWEEN {a0} AND {a1} GROUP BY ALL
    """)
    factores(con, "anual_veg", "f_veg")


def modelo_fijas(con: duckdb.DuckDBPyConnection):
    """Fixed sources (types 1–3: volcanoes, industry and gas, offshore), cell by cell.

    These sources do not move: the same stack, the same well, the same volcano. So each cell has its
    own relation between MODIS and VIIRS. For a cell and a month:
        pred = MODIS × k_celda     + b_act    if MODIS did not see it that month but did in other months of the year
                                   + b_inact  if MODIS did not see it all year
    k_celda = Σ VIIRS ÷ Σ MODIS in the months when MODIS saw it (with fewer than 3 months, that of its 10° region or
    of the world). b_act and b_inact = average VIIRS in those months: VIIRS sees small sources MODIS cannot reach
    (assumption: that base holds going back in time). With Terra only, MODIS = Terra × (Σ MODIS ÷ Σ Terra).
    The parameters go by stage (_etapa): in 2018 the relation changes abruptly (VIIRS moves from S-NPP to NOAA-20 and
    MODIS flags many more fixed sources, ~6 times more volcanoes), so 2018–2025 uses what was learned from 2018 on and
    2000–2017 what was learned with 2012–2017.

    nf        every cell that ever had that type × every month (2000–2025)
    par_fijas parameters without the year being predicted (prueba = year; 0 = with all years 2012–2021)
    pf        unseen prediction 2012–2025 (one year out; 2022–2025 with all)
    f_fijas   p5–p95 range of VIIRS ÷ predicted year by year, per 10° region and type (without the year being predicted)
    Needs tt (conteos_tipo)."""
    a0, a1 = CALIBRACION
    con.execute(f"""
    CREATE OR REPLACE TABLE nf AS
    WITH ct AS (SELECT DISTINCT fila, col, tipo FROM tt WHERE tipo > 0),
         g AS (SELECT ct.*, s.año, s.mes, s.terra_ok, s.aqua_ok, s.viirs_sat FROM ct, meses_sat s)
    SELECT g.fila, g.col, CAST(g.tipo AS INT) tipo, g.año, g.mes, g.terra_ok AND g.aqua_ok AS modis_ok, g.terra_ok, g.viirs_sat, {region_fc('g')} region,
           coalesce(x.m, 0) AS m_obs, coalesce(x.t, 0) t,
           CASE WHEN g.viirs_sat IS NOT NULL THEN coalesce(x.v, 0) END AS v
    FROM g LEFT JOIN tt x USING (fila, col, tipo, año, mes)
    """)
    con.execute(f"""
    CREATE OR REPLACE TABLE nf AS
    WITH r AS (SELECT tipo, sum(m_obs) / sum(t) r FROM nf WHERE modis_ok AND año BETWEEN {a0} AND {a1} GROUP BY tipo),
         x AS (SELECT n.*, CASE WHEN n.terra_ok AND NOT n.modis_ok THEN n.t * r.r ELSE n.m_obs END AS m
               FROM nf n JOIN r USING (tipo))
    SELECT *, sum(m) OVER (PARTITION BY fila, col, tipo, año) AS m_año FROM x
    """)
    años = range(a0, a1 + 1)
    con.execute("CREATE OR REPLACE TABLE pr_fit (prueba INT, año INT)")
    con.executemany("INSERT INTO pr_fit VALUES (?, ?)", [(p, a) for p in (0, *años) for a in años if a != p])
    ajustar_fijas(con)
    con.execute(f"""
    CREATE OR REPLACE TABLE pf AS
    SELECT n.fila, n.col, n.tipo, n.año, n.mes, n.region, n.v, n.m_obs, {_pred_fijas()} AS pred
    FROM nf n JOIN par_fijas p ON p.prueba = {_prueba('n.año')} AND p.tipo = n.tipo AND p.etapa = {_etapa()}
                                AND p.fila = n.fila AND p.col = n.col
    WHERE n.v IS NOT NULL AND n.modis_ok AND n.año BETWEEN {a0} AND {FUERA[1]}
    """)
    # the type goes in the "mes" column of factores(): that way the world fallback is per type
    con.execute(f"""CREATE OR REPLACE TABLE anual_fijas AS
                    SELECT region, tipo AS mes, año, sum(v) v, sum(pred) m FROM pf WHERE año <= {a1} GROUP BY ALL""")
    factores(con, "anual_fijas", "f_fijas", minimo=MINIMO_FIJAS, minimo_año=20)
    # a source MODIS never saw can make VIIRS see hundreds of times the prediction in a year: the range is
    # capped between a third and three times the estimate
    con.execute(f"""UPDATE f_fijas SET k_lo = greatest(coalesce(k_lo, k), k / {TOPE_FIJAS}),
                                       k_hi = least(coalesce(k_hi, k), k * {TOPE_FIJAS})""")


def ajustar_fijas(con: duckdb.DuckDBPyConnection, nombre: str = "par_fijas"):
    """Parameters per cell and type for each test in pr_fit (test, year used for fitting)."""
    con.execute(f"""
    CREATE OR REPLACE TABLE {nombre} AS
    WITH par AS (
      SELECT f.prueba, n.tipo, {_etapa()} etapa, n.fila, n.col, any_value(n.region) region,
             sum(n.v) FILTER (WHERE n.m > 0) sv, sum(n.m) FILTER (WHERE n.m > 0) sm, count(*) FILTER (WHERE n.m > 0) nm,
             avg(n.v) FILTER (WHERE n.m = 0 AND n.m_año > 0) b_act, avg(n.v) FILTER (WHERE n.m_año = 0) b_inact
      FROM nf n JOIN pr_fit f USING (año) WHERE n.v IS NOT NULL AND n.modis_ok GROUP BY ALL
    ),
    reg AS (SELECT prueba, tipo, etapa, region, sum(sv) / nullif(sum(sm), 0) k FROM par GROUP BY ALL),
    glb AS (SELECT prueba, tipo, etapa, sum(sv) / sum(sm) k FROM par GROUP BY ALL)
    SELECT p.prueba, p.tipo, p.etapa, p.fila, p.col, coalesce(CASE WHEN p.nm >= 3 THEN p.sv / p.sm END, r.k, g.k) k,
           coalesce(p.b_act, 0) b_act, coalesce(p.b_inact, 0) b_inact
    FROM par p JOIN glb g USING (prueba, tipo, etapa) LEFT JOIN reg r USING (prueba, tipo, etapa, region)
    """)


def _pred_fijas(n: str = "n", p: str = "p") -> str:
    return (f"{n}.m * {p}.k + CASE WHEN {n}.m = 0 AND {n}.m_año > 0 THEN {p}.b_act "
            f"WHEN {n}.m_año = 0 THEN {p}.b_inact ELSE 0 END")


def validacion_integral(con: duckdb.DuckDBPyConnection, nombre: str = "v_integral"):
    """Cell × month × category, 2012–2025, with predictions that did not see the year: vegetation (LightGBM +
    correction) and the three fixed sources (per-cell model)."""
    tabla_base(con)
    conteos_tipo(con)
    modelo_vegetacion(con)
    modelo_fijas(con)
    a1 = CALIBRACION[1]
    con.execute(f"""
    CREATE OR REPLACE TABLE {nombre} AS
    WITH veg AS (
      SELECT c.fila, c.col, c.año, c.mes, 'veg' AS categoria, coalesce(o.v, 0) viirs, coalesce(o.m, 0) modis,
             coalesce(p.pred, 0) * least(greatest(coalesce(r.k, g.k), {CORRECCION[0]}), {CORRECCION[1]}) pred,
             pred * coalesce(r.k_lo, g.k_lo) / nullif(coalesce(r.k, g.k), 0) pred_bajo,
             pred * coalesce(r.k_hi, g.k_hi) / nullif(coalesce(r.k, g.k), 0) pred_alto
      FROM c
      LEFT JOIN p_veg p USING (fila, col, año, mes)
      LEFT JOIN (SELECT * FROM tt WHERE tipo = 0) o USING (fila, col, año, mes)
      LEFT JOIN f_veg r ON r.prueba = {_prueba()} AND r.region = c.region AND r.mes = c.mes
      LEFT JOIN f_veg g ON g.prueba = {_prueba()} AND g.region = -1 AND g.mes = c.mes
    ),
    fijas AS (
      SELECT f.fila, f.col, f.año, f.mes, {_categoria('f.tipo')} AS categoria, f.v viirs, f.m_obs modis, f.pred,
             f.pred * coalesce(r.k_lo, g.k_lo) / nullif(coalesce(r.k, g.k), 0) pred_bajo,
             f.pred * coalesce(r.k_hi, g.k_hi) / nullif(coalesce(r.k, g.k), 0) pred_alto
      FROM pf f
      LEFT JOIN f_fijas r ON r.prueba = {_prueba('f.año')} AND r.region = f.region AND r.mes = f.tipo
      LEFT JOIN f_fijas g ON g.prueba = {_prueba('f.año')} AND g.region = -1 AND g.mes = f.tipo
    )
    SELECT fila, col, CAST(año AS SMALLINT) año, CAST(mes AS TINYINT) mes, categoria,
           CASE WHEN año <= {a1} THEN 'loyo' ELSE 'fuera' END AS prueba,
           CAST(viirs AS INT) viirs, CAST(modis AS INT) modis, CAST(pred AS FLOAT) pred,
           CAST(pred_bajo AS FLOAT) pred_bajo, CAST(pred_alto AS FLOAT) pred_alto
    FROM (SELECT * FROM veg UNION ALL SELECT * FROM fijas)
    WHERE viirs > 0 OR modis > 0 OR pred >= 0.05  -- the same threshold as data/app: fixed sources add up many small values
    """)


def serie_mundial(con: duckdb.DuckDBPyConnection):
    """data/app/serie_mundial.csv: world total of each month. MODIS as is; the estimate from MODIS (2002–2011 from
    data/app, 2012–2025 the unseen prediction from the validation) with its range; and what VIIRS observed.
    Needs v (validation) and tt, and preparar_app.py must already have written data/app."""
    archivos = ", ".join(f"'{p.as_posix()}'" for p in (OUT / "celdas.parquet", OUT / "celdas_fijas.parquet") if p.exists())
    con.execute(f"""
    COPY (
      WITH modis AS (SELECT año, mes, sum(m) m FROM tt JOIN meses_sat USING (año, mes) WHERE terra_ok AND aqua_ok GROUP BY ALL),
      antes AS (SELECT año, mes, sum(det) est, sum(det_bajo) lo, sum(det_alto) hi
                FROM read_parquet([{archivos}], union_by_name = true) WHERE fuente = 'M' GROUP BY ALL),
      val AS (SELECT año, mes, sum(pred) est, sum(pred_bajo) lo, sum(pred_alto) hi, sum(viirs) obs FROM v GROUP BY ALL),
      sat AS (SELECT año, mes, viirs_sat FROM meses_sat)
      SELECT make_date(m.año, m.mes, 1) AS mes, m.m AS detecciones_modis,
             round(coalesce(v.est, a.est), 1) AS detecciones_estimado, v.obs AS detecciones_observado,
             s.viirs_sat AS satelite_observado,
             round(coalesce(v.lo, a.lo), 1) AS detecciones_min, round(coalesce(v.hi, a.hi), 1) AS detecciones_max
      FROM modis m LEFT JOIN antes a USING (año, mes) LEFT JOIN val v USING (año, mes) LEFT JOIN sat s USING (año, mes)
      WHERE coalesce(v.est, a.est) IS NOT NULL
      ORDER BY 1
    ) TO '{(OUT / "serie_mundial.csv").as_posix()}' (HEADER, DELIMITER ',')
    """)


def main():
    t0 = time.time()
    con = duckdb.connect()
    con.execute("SET preserve_insertion_order = false")
    modelo = "integral" if hay_integral() else "lightgbm" if hay_lightgbm() else "razon"
    if modelo == "integral":
        validacion_integral(con, "v")
    else:  # a single model for all types
        (validacion_lightgbm if modelo == "lightgbm" else validacion_razon)(con, "v0")
        con.execute("CREATE TABLE v AS SELECT fila, col, año, mes, 'todos' AS categoria, * EXCLUDE (fila, col, año, mes) FROM v0")
    # a tenth of a detection is enough and halves the file size
    con.execute(f"""COPY (SELECT * REPLACE (CAST(round(pred, 1) AS FLOAT) AS pred, CAST(round(pred_bajo, 1) AS FLOAT) AS pred_bajo,
                                            CAST(round(pred_alto, 1) AS FLOAT) AS pred_alto)
                          FROM v ORDER BY fila, col, año, mes)
                    TO '{(OUT / 'validacion.parquet').as_posix()}' (FORMAT parquet, COMPRESSION zstd, ROW_GROUP_SIZE 100000)""")

    # ---------------------------------------------------------------- metrics
    def mediana_error(tabla: str, minimo: int) -> dict:
        """Typical error (median |error| %) of the prediction and of raw MODIS, and coverage of the range."""
        fila = con.sql(f"""
            SELECT prueba,
                   median(abs(pred / viirs - 1)) * 100,
                   median(abs(modis / viirs - 1)) * 100,
                   avg(CASE WHEN viirs BETWEEN pred_bajo AND pred_alto THEN 1 ELSE 0 END) * 100,
                   median(pred / viirs - 1) * 100,
                   count(*)
            FROM {tabla} WHERE viirs >= {minimo} GROUP BY prueba
        """).fetchall()
        return {p: {"error_tipico": round(e, 1), "error_modis_crudo": round(em, 1), "dentro_del_rango": round(cob, 1),
                    "sesgo": round(s, 1), "n": n} for p, e, em, cob, s, n in fila}

    con.execute(f"""
    CREATE TABLE pais AS
    SELECT fila, col, arg_max(country, parte) country FROM read_parquet('{PAISES.as_posix()}')
    WHERE parte >= 0.5 GROUP BY ALL
    """)
    # with category; the total is the sum of the categories
    con.execute("""
    CREATE TABLE global_mes_c AS
    SELECT prueba, categoria, año, mes, sum(viirs) viirs, sum(modis) modis, sum(pred) pred, sum(pred_bajo) pred_bajo,
           sum(pred_alto) pred_alto FROM v GROUP BY ALL
    """)
    for nivel, grupo in (("pais_año_c", "v.año"), ("pais_mes_c", "v.año, v.mes")):
        con.execute(f"""
        CREATE TABLE {nivel} AS
        SELECT v.prueba, v.categoria, p.country, {grupo}, sum(viirs) viirs, sum(modis) modis, sum(pred) pred,
               sum(pred_bajo) pred_bajo, sum(pred_alto) pred_alto
        FROM v JOIN pais p USING (fila, col) GROUP BY ALL
        """)
    for nivel in ("global_mes", "pais_año", "pais_mes"):
        con.execute(f"""CREATE TABLE {nivel} AS SELECT * EXCLUDE (categoria, viirs, modis, pred, pred_bajo, pred_alto),
                               sum(viirs) viirs, sum(modis) modis, sum(pred) pred, sum(pred_bajo) pred_bajo, sum(pred_alto) pred_alto
                        FROM {nivel}_c GROUP BY ALL""")
    nombres = {"integral": "Integral: vegetación con LightGBM (28 entradas) + corrección regional; volcanes, industria y gas, "
                           "y costa afuera con un modelo por celda",
               "lightgbm": "LightGBM (28 entradas de MODIS, vecindad, Sol, lugar y fecha) + corrección regional",
               "razon": "MODIS × razón VIIRS/MODIS por región de 10° y mes"}
    resumen = {
        "modelo": nombres[modelo],
        "clave_modelo": modelo,
        "calibracion": list(CALIBRACION), "fuera": list(FUERA),
        "global_mensual": mediana_error("global_mes", 1),
        "pais_anual": mediana_error("pais_año", 1000),
        "pais_mensual": mediana_error("pais_mes", 100),
        "paises": con.sql("SELECT count(DISTINCT country) FROM pais_año WHERE viirs >= 1000").fetchall()[0][0],
        # how many times more fires VIIRS sees than MODIS worldwide when both fly (2012–2021)
        "factor_viirs_modis": round(con.sql("SELECT sum(viirs) / sum(modis) FROM v WHERE prueba = 'loyo'")
                                    .fetchall()[0][0], 2),
    }
    if modelo == "integral":
        cats, total = {}, con.sql("SELECT sum(viirs) FROM v WHERE prueba = 'loyo'").fetchall()[0][0]
        for cat in CATEGORIAS.values():
            for nivel in ("global_mes", "pais_año"):
                con.execute(f"CREATE OR REPLACE VIEW {nivel}_x AS SELECT * FROM {nivel}_c WHERE categoria = '{cat}'")
            viirs, modis = con.sql(f"SELECT sum(viirs), sum(modis) FROM v WHERE prueba = 'loyo' AND categoria = '{cat}'").fetchall()[0]
            cats[cat] = {"global_mensual": mediana_error("global_mes_x", 1),
                         "pais_anual": mediana_error("pais_año_x", 200),  # fixed sources: countries with ≥ 200 per year
                         "factor_viirs_modis": round(viirs / modis, 2),
                         "parte_viirs": round(100 * viirs / total, 2)}
        resumen["categorias"] = cats
        serie_mundial(con)
    (OUT / "validacion.json").write_text(json.dumps(resumen, indent=2, ensure_ascii=False))
    print(json.dumps(resumen, indent=2, ensure_ascii=False))
    n = con.sql(f"SELECT count(*) FROM '{(OUT / 'validacion.parquet').as_posix()}'").fetchall()[0][0]
    print(f"{n:,} cell-months · done in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
