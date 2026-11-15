"""Modelo integral: cada tipo de punto de calor se armoniza con su propio modelo.

FIRMS clasifica cada detección en cuatro tipos:
  0  vegetación      incendios forestales, quemas agrícolas y de pastos
  1  volcanes        anomalías térmicas de volcanes activos
  2  industria y gas otras fuentes fijas en tierra: quema de gas en pozos, refinerías, siderúrgicas
  3  costa afuera    detecciones en el mar, casi todas plataformas de petróleo y gas

Vegetación: LightGBM con las mismas 28 entradas del notebook 03_modelo, pero aprendiendo solo las detecciones
VIIRS de tipo 0. Después se le aplica la corrección regional de scripts/validar.py.
Tipos 1–3: fuentes fijas y persistentes, por eso se modelan celda por celda en scripts/validar.py.

Este script hace la parte pesada (~40 min):
  1. tipos_celdas.parquet  conteos por celda de 0.5°, mes, satélite y tipo, desde data/db_nasa.duckdb
  2. veg_celdas.parquet    LightGBM de vegetación entrenado con 2012–2016 y 2018–2020, aplicado a 2002–2025
                           (en meses sin VIIRS predice lo que vería NOAA-20)
  3. veg_loyo.parquet      LightGBM de vegetación dejando un año fuera, 2012–2021 (validación y corrección)

Uso:  python scripts/modelo_integral.py
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
    """Conteos por celda, mes, satélite (Terra, Aqua, N = S-NPP, N20 = NOAA-20) y tipo."""
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
    """Celda × mes con MODIS completo (2002–2025), sus 28 entradas y las detecciones VIIRS de vegetación."""
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
    d["viirs_veg"] = d.viirs_veg_bruto.fillna(0).where(d.viirs_sat.notna())  # vacío donde no hay VIIRS
    return variables(d.drop(columns="viirs_veg_bruto"))


class LightGBMVegetacion(LightGBM):
    def entrenar(self, d):
        self.modelo = lgb.LGBMRegressor(objective="poisson", **self.PARAMETROS).fit(self._x(d), d.viirs_veg)
        return self

    def _x(self, d):
        # qué VIIRS imitar: S-NPP en sus meses; NOAA-20 en los demás (también antes de 2012)
        return d[ENTRADAS].assign(noaa20=np.where(d.viirs_sat == "N", 0, 1))


def main():
    t0 = time.time()
    if "--sin-tipos" not in sys.argv or not TIPOS.exists():
        tipos_celdas()
        log("tipos_celdas.parquet listo", t0)
    d = cargar()
    log(f"{len(d):,} celda-mes cargadas", t0)
    con_viirs = d.viirs_veg.notna()

    final = LightGBMVegetacion().entrenar(d[con_viirs & d.año.isin(ENTRENAMIENTO)])
    log("modelo de vegetación entrenado", t0)
    d[["fila", "col", "año", "mes"]].assign(pred=final.predecir(d).astype("float32")).to_parquet(VEG, index=False)
    log("veg_celdas.parquet listo", t0)

    partes = []
    datos = d[con_viirs & d.año.isin(AÑOS_LOYO)]
    for año in AÑOS_LOYO:
        m = LightGBMVegetacion().entrenar(datos[datos.año != año])
        fuera = datos[datos.año == año]
        partes.append(fuera[["fila", "col", "año", "mes"]].assign(pred=m.predecir(fuera).astype("float32")))
        log(f"un año fuera: {año} listo", t0)
    pd.concat(partes).to_parquet(VEG_LOYO, index=False)
    log("veg_loyo.parquet listo", t0)


if __name__ == "__main__":
    main()
