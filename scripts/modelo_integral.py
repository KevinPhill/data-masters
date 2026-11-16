# AI-assisted code (Claude, Anthropic), directed and reviewed by the team. See README: "Use of artificial intelligence".
"""Integral model: each hot spot type is harmonized with its own model.

FIRMS classifies each detection into four types:
  0  vegetation       wildfires, agricultural and pasture burning
  1  volcanoes        thermal anomalies of active volcanoes
  2  industry and gas other static land sources: gas flaring at wells, refineries, steel mills
  3  offshore         detections over water, mostly oil and gas platforms

Vegetation: LightGBM with the same 28 inputs as notebook 03_modelo, but learning only type 0 VIIRS
detections. Then the regional correction of scripts/validar.py is applied.
Types 1–3: fixed, persistent sources, so they are modelled cell by cell in scripts/validar.py.

This script does the heavy part (~40 min):
  1. tipos_celdas.parquet  counts per 0.5° cell, month, satellite and type, from data/db_nasa.duckdb
  2. veg_celdas.parquet    vegetation LightGBM trained on 2012–2016 and 2018–2020, applied to 2002–2025
                           (in months without VIIRS it predicts what NOAA-20 would see)
  3. veg_loyo.parquet      vegetation LightGBM leaving one year out, 2012–2021 (validation and correction)

Usage:  python scripts/modelo_integral.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import duckdb
import lightgbm as lgb
import numpy as np
import pandas as pd

from evaluar_modelos import ENTRADAS, ENTRENAMIENTO, LightGBM, TABLA, variables

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "db_nasa.duckdb"
MODELO = ROOT / "data" / "modelo"
TIPOS = MODELO / "tipos_celdas.parquet"
VEG = MODELO / "veg_celdas.parquet"
VEG_LOYO = MODELO / "veg_loyo.parquet"
AÑOS_LOYO = range(2012, 2022)


def log(msg: str, t0: float):
    print(f"[{time.time() - t0:5.0f} s] {msg}", flush=True)


def tipos_celdas():
    """Counts per cell, month, satellite (Terra, Aqua, N = S-NPP, N20 = NOAA-20) and type."""
    con = duckdb.connect()
    con.execute("SET preserve_insertion_order = false")
    con.execute(f"ATTACH '{DB.as_posix()}' AS nasa (READ_ONLY)")
    con.execute(f"""
    COPY (
      SELECT CAST(floor(latitude / 0.5) AS INT) fila, CAST(floor(longitude / 0.5) AS INT) col,
             CAST(year(acq_date) AS SMALLINT) año, CAST(month(acq_date) AS TINYINT) mes,
             CASE WHEN sensor = 'MODIS' THEN satellite WHEN satellite = 'N' THEN 'N' ELSE 'N20' END AS sat,
             CAST(type AS TINYINT) tipo, count(*)::INT n
      FROM nasa.hotspots GROUP BY ALL
    ) TO '{TIPOS.as_posix()}' (FORMAT parquet, COMPRESSION zstd)
    """)


def cargar() -> pd.DataFrame:
    """Cell × month with complete MODIS (2002–2025), its 28 inputs and the VIIRS vegetation detections."""
    con = duckdb.connect()
    base = sorted(set(ENTRADAS) - {"frp_por_det_terra", "frp_por_det_aqua", "razon_aqua_terra", "frac_noche",
                                   "cenit_terra", "cenit_aqua", "horas_de_sol", "distancia_sol"}
                  | {"fila", "col", "año", "viirs_sat", "modis_n"})
    d = con.sql(f"""
        SELECT {", ".join("t." + c for c in base)}, v.n AS viirs_veg_bruto
        FROM read_parquet('{TABLA.as_posix()}') t
        LEFT JOIN (SELECT fila, col, año, mes, sat, n FROM read_parquet('{TIPOS.as_posix()}') WHERE tipo = 0) v
               ON v.fila = t.fila AND v.col = t.col AND v.año = t.año AND v.mes = t.mes AND v.sat = t.viirs_sat
        WHERE t.terra_ok AND t.aqua_ok
    """).df()
    num = d.columns.difference(["fila", "col", "año", "mes", "viirs_sat"])
    d[num] = d[num].astype("float32")
    d["viirs_veg"] = d.viirs_veg_bruto.fillna(0).where(d.viirs_sat.notna())  # empty where there is no VIIRS
    return variables(d.drop(columns="viirs_veg_bruto"))


class LightGBMVegetacion(LightGBM):
    def entrenar(self, d):
        self.modelo = lgb.LGBMRegressor(objective="poisson", **self.PARAMETROS).fit(self._x(d), d.viirs_veg)
        return self

    def _x(self, d):
        # which VIIRS to imitate: S-NPP in its months; NOAA-20 in the others (also before 2012)
        return d[ENTRADAS].assign(noaa20=np.where(d.viirs_sat == "N", 0, 1))


def main():
    t0 = time.time()
    if "--sin-tipos" not in sys.argv or not TIPOS.exists():
        tipos_celdas()
        log("tipos_celdas.parquet done", t0)
    d = cargar()
    log(f"{len(d):,} cell-months loaded", t0)
    con_viirs = d.viirs_veg.notna()

    final = LightGBMVegetacion().entrenar(d[con_viirs & d.año.isin(ENTRENAMIENTO)])
    log("vegetation model trained", t0)
    d[["fila", "col", "año", "mes"]].assign(pred=final.predecir(d).astype("float32")).to_parquet(VEG, index=False)
    log("veg_celdas.parquet done", t0)

    partes = []
    datos = d[con_viirs & d.año.isin(AÑOS_LOYO)]
    for año in AÑOS_LOYO:
        m = LightGBMVegetacion().entrenar(datos[datos.año != año])
        fuera = datos[datos.año == año]
        partes.append(fuera[["fila", "col", "año", "mes"]].assign(pred=m.predecir(fuera).astype("float32")))
        log(f"one year out: {año} done", t0)
    pd.concat(partes).to_parquet(VEG_LOYO, index=False)
    log("veg_loyo.parquet done", t0)


if __name__ == "__main__":
    main()
