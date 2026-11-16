# AI-assisted code (Claude, Anthropic), directed and reviewed by the team. See README: "Use of artificial intelligence".
"""Evalúa los modelos de armonización MODIS → VIIRS: qué tan bien predicen, si sobreajustan y en qué países fallan.

Años (los mismos del notebook 03_modelo):
  entrenamiento  2012–2016 y 2018–2020   el modelo aprende aquí
  prueba         2017 (S-NPP) y 2021 (NOAA-20)   años completos que el modelo no vio
  nunca vistos   2022–2025   tampoco se usan, y además las órbitas de Terra y Aqua ya están corridas

Modelos
  factor_global  VIIRS = MODIS × un solo factor mundial
  razon          VIIRS = MODIS × razón VIIRS/MODIS de su región de 10° y su mes del año
  lightgbm       28 entradas (MODIS, intensidad, vecindad, Sol, lugar y fecha) → detecciones VIIRS, pérdida Poisson
  lightgbm_corregido   LightGBM × corrección de su región de 10° y su mes: Σ VIIRS ÷ Σ predicho en la validación
                 dejando un año fuera, siempre sin el año que se predice
  integral       cada tipo FIRMS con su modelo (scripts/modelo_integral.py y validar.py): vegetación con LightGBM de
                 vegetación (mismas 28 entradas y años) × corrección regional; volcanes, industria y gas, y costa
                 afuera celda por celda, ajustado con los años de entrenamiento   ← el que usa la app

Métricas en cuatro niveles (celda de 0.5° × mes, país × mes, país × año, mundo × mes)
  R²            en escala log (log 1 + x): así cada celda o país pesa parecido sin importar su tamaño
  MSE, RMSE     error cuadrático medio y su raíz, en detecciones
  MAE           error absoluto medio, en detecciones
  error típico  mediana del |error| en %, solo donde VIIRS vio lo suficiente para que el % tenga sentido
  sesgo         cuánto se pasa (+) o se queda corto (−) el total

Sobreajuste: se compara el error en entrenamiento con el de prueba y el de nunca vistos.

Países: con predicciones que el modelo no vio (un año fuera a la vez en 2012–2021 + 2022–2025) se mide cada
país; "no funciona bien" si el error típico por año pasa de UMBRAL_MAL o el mensual de UMBRAL_MAL_MES.
También se guarda qué parte de sus detecciones MODIS son fuentes fijas (quema de gas, industria, volcanes).
  Las predicciones no vistas salen de scripts/validar.py (las mismas que muestra la app):
  · razón: recalculada sin el año que se predice
  · LightGBM + corrección: data/modelo/validacion_por_año.parquet (notebook 03) + armonizado_celdas.parquet en
    2022–2025, con la corrección regional de validar.py

Salida (data/app/)
  evaluacion.json            métricas por modelo, conjunto y nivel; resumen de sobreajuste y de países
  evaluacion_paises.parquet  una fila por país y modelo

Uso:  python scripts/evaluar_modelos.py          (~5 min: entrena LightGBM una vez)
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import duckdb
import lightgbm as lgb
import numpy as np
import pandas as pd

import validar

ROOT = Path(__file__).resolve().parents[1]
TABLA = ROOT / "data" / "modelo" / "tabla_celdas_0.5.parquet"
PAISES = ROOT / "data" / "app" / "paises.parquet"
OUT = ROOT / "data" / "app"

ENTRENAMIENTO = [2012, 2013, 2014, 2015, 2016, 2018, 2019, 2020]
PRUEBA = [2017, 2021]
NUNCA_VISTOS = [2022, 2023, 2024, 2025]

# un país se evalúa si VIIRS ve en promedio al menos esto por año (con menos, los % son ruido)
MINIMO_PAIS = 1000
UMBRAL_MAL, UMBRAL_REGULAR = 25.0, 15.0          # error típico por año (%)
UMBRAL_MAL_MES, UMBRAL_REGULAR_MES = 40.0, 25.0  # error típico por mes (%), meses con al menos 100 detecciones
NIVELES = {"celda_mes": 20, "pais_mes": 100, "pais_año": 1000, "mundo_mes": 1}  # mínimo VIIRS para el error en %

# ------------------------------------------------------------------------------------------- variables
DIA_DEL_AÑO = np.array([15, 46, 74, 105, 135, 166, 196, 227, 258, 288, 319, 349])
HORA_NOMINAL = {"terra": 10.5, "aqua": 13.5}
GRUPOS = {
    "MODIS": ["terra_dia", "terra_noche", "aqua_dia", "aqua_noche", "terra_frp", "aqua_frp",
              "modis_frp_max", "modis_area_px", "modis_confianza", "modis_frac_baja_conf",
              "modis_dias", "modis_frac_fijas"],
    "intensidad": ["frp_por_det_terra", "frp_por_det_aqua", "razon_aqua_terra", "frac_noche"],
    "vecindad y tiempo": ["modis_vecinos", "modis_mes_anterior", "modis_mes_siguiente", "modis_historico"],
    "sol": ["cenit_terra", "cenit_aqua", "horas_de_sol", "distancia_sol"],
    "lugar y fecha": ["lat", "lon", "mes"],
}
ENTRADAS = [e for g in GRUPOS.values() for e in g]


def variables(t: pd.DataFrame) -> pd.DataFrame:
    """Las mismas variables calculadas del notebook 03 (sección 3)."""
    dia = DIA_DEL_AÑO[t.mes.to_numpy() - 1]
    lat = np.radians(t.lat.to_numpy())
    declinacion = np.radians(23.44) * np.sin(2 * np.pi * (284 + dia) / 365)
    t["distancia_sol"] = 1 - 0.01672 * np.cos(2 * np.pi * (dia - 4) / 365.25)
    t["horas_de_sol"] = 24 / np.pi * np.arccos(np.clip(-np.tan(lat) * np.tan(declinacion), -1, 1))
    for sat in ("terra", "aqua"):
        angulo = np.radians(15 * (HORA_NOMINAL[sat] - 12))
        cos_cenit = np.sin(lat) * np.sin(declinacion) + np.cos(lat) * np.cos(declinacion) * np.cos(angulo)
        t[f"cenit_{sat}"] = np.degrees(np.arccos(np.clip(cos_cenit, -1, 1)))
    terra, aqua = t.terra_dia + t.terra_noche, t.aqua_dia + t.aqua_noche
    t["frp_por_det_terra"] = (t.terra_frp / terra).where(terra > 0, 0)
    t["frp_por_det_aqua"] = (t.aqua_frp / aqua).where(aqua > 0, 0)
    t["razon_aqua_terra"] = np.log1p(aqua) - np.log1p(terra)
    t["frac_noche"] = ((t.terra_noche + t.aqua_noche) / t.modis_n).where(t.modis_n > 0, 0)
    nuevas = ["distancia_sol", "horas_de_sol", "cenit_terra", "cenit_aqua", "frp_por_det_terra", "frp_por_det_aqua",
              "razon_aqua_terra", "frac_noche"]
    t[nuevas] = t[nuevas].astype("float32")
    return t


def region_10(t: pd.DataFrame) -> np.ndarray:
    return ((t.lat.to_numpy() + 90) // 10 * 36 + (t.lon.to_numpy() + 180) // 10).astype(int)


# ------------------------------------------------------------------------------------------- modelos
class FactorGlobal:
    nombre = "Un solo factor mundial"

    def entrenar(self, d):
        self.k = d.viirs_n.sum() / d.modis_n.sum()
        return self

    def predecir(self, d):
        return d.modis_n.to_numpy() * self.k


class Razon:
    """Lo mismo que scripts/preparar_app.py: razón de la región (10°) y el mes si la región tuvo fuego en
    al menos 3 años; si no, la razón mundial de ese mes."""
    nombre = "Razón VIIRS/MODIS por región y mes"

    def entrenar(self, d):
        s = d.assign(region=region_10(d)).groupby(["region", "mes", "año"])[["viirs_n", "modis_n"]].sum()
        r = s.groupby(["region", "mes"]).sum()
        r["k"] = r.viirs_n / r.modis_n.replace(0, np.nan)
        r["años"] = (s.modis_n > 0).groupby(["region", "mes"]).sum()
        self.region = r.loc[r.años >= 3, "k"]
        g = d.groupby("mes")[["viirs_n", "modis_n"]].sum()
        self.mes = g.viirs_n / g.modis_n
        self.n_factores = int(self.region.notna().sum() + self.mes.notna().sum())
        return self

    def predecir(self, d):
        llave = pd.MultiIndex.from_arrays([region_10(d), d.mes.to_numpy()])
        k = self.region.reindex(llave).to_numpy()
        k = np.where(np.isnan(k), self.mes.reindex(d.mes).to_numpy(), k)
        return d.modis_n.to_numpy() * k


class LightGBM:
    nombre = "LightGBM (notebook 03)"
    PARAMETROS = dict(n_estimators=600, learning_rate=0.05, num_leaves=127, min_child_samples=100, subsample=0.5,
                      subsample_freq=1, colsample_bytree=0.9, verbose=-1)

    def _x(self, d):
        return d[ENTRADAS].assign(noaa20=np.where(d.viirs_sat == "N20", 1, 0))

    def entrenar(self, d):
        self.modelo = lgb.LGBMRegressor(objective="poisson", **self.PARAMETROS).fit(self._x(d), d.viirs_n)
        return self

    def predecir(self, d):
        return self.modelo.predict(self._x(d))


class Integral:
    """Suma de los cuatro tipos FIRMS, cada uno con su modelo. Vegetación: LightGBM de vegetación entrenado con los
    años de entrenamiento (data/modelo/veg_celdas.parquet) × corrección regional sin el año que se predice.
    Fuentes fijas: modelo por celda de validar.modelo_fijas, con parámetros de los años de entrenamiento."""
    nombre = "Integral: un modelo por tipo de fuente (la app)"

    def __init__(self, con: duckdb.DuckDBPyConnection):
        # validar.validacion_integral ya dejó tt, nf, f_veg (corrección) y par_fijas en la conexión
        con.execute("CREATE OR REPLACE TABLE pr_fit (prueba INT, año INT)")
        con.executemany("INSERT INTO pr_fit VALUES (?, ?)", [(-2, a) for a in ENTRENAMIENTO])
        validar.ajustar_fijas(con, "par_eval")
        lo, hi = validar.CORRECCION
        self.pred = con.sql(f"""
            WITH veg AS (
              SELECT p.fila, p.col, p.año, p.mes,
                     p.pred * least(greatest(coalesce(r.k, g.k), {lo}), {hi}) pred
              FROM read_parquet('{validar.VEG_CELDAS.as_posix()}') p
              JOIN meses_sat s ON s.año = p.año AND s.mes = p.mes AND s.terra_ok AND s.aqua_ok AND s.viirs_sat IS NOT NULL
              LEFT JOIN f_veg r ON r.prueba = {validar._prueba('p.año')} AND r.region = {validar.region_fc('p')} AND r.mes = p.mes
              LEFT JOIN f_veg g ON g.prueba = {validar._prueba('p.año')} AND g.region = -1 AND g.mes = p.mes
              WHERE p.año BETWEEN 2012 AND 2025
            ),
            fijas AS (
              SELECT n.fila, n.col, n.año, n.mes, {validar._pred_fijas()} pred
              FROM nf n JOIN par_eval p ON p.prueba = -2 AND p.tipo = n.tipo AND p.etapa = {validar._etapa()}
                                        AND p.fila = n.fila AND p.col = n.col
              WHERE n.v IS NOT NULL AND n.modis_ok AND n.año BETWEEN 2012 AND 2025
            )
            SELECT fila, col, año, mes, sum(pred) pred FROM (SELECT * FROM veg UNION ALL SELECT * FROM fijas)
            GROUP BY ALL HAVING sum(pred) > 0
        """).df()
        self.n_factores = int(con.sql("SELECT count(*) FROM f_veg WHERE prueba = 0 AND region >= 0").fetchall()[0][0])
        self.n_celdas = int(con.sql("SELECT count(*) FROM (SELECT DISTINCT tipo, fila, col FROM par_eval)").fetchall()[0][0])


class LightGBMCorregido:
    """LightGBM × k de su región y mes; k sale de la validación dejando un año fuera (scripts/validar.py) y nunca
    usa el año que se predice: en 2012–2021 se calcula sin ese año, en 2022–2025 con 2012–2021."""
    nombre = "LightGBM + corrección regional"

    def __init__(self, con: duckdb.DuckDBPyConnection):
        validar.rango_lightgbm(con, "f_lgbm")
        f = con.sql("SELECT prueba, region, mes, k FROM f_lgbm").df()
        self.region = f[f.region >= 0].set_index(["prueba", "region", "mes"]).k
        self.mes = f[f.region == -1].set_index(["prueba", "mes"]).k
        self.n_factores = int(((f.prueba == 0) & (f.region >= 0)).sum())

    def predecir(self, d, pred_lightgbm):
        prueba = np.where(d.año.to_numpy() <= validar.CALIBRACION[1], d.año.to_numpy(), 0).astype("int64")
        mes = d.mes.to_numpy().astype("int64")
        k = self.region.reindex(pd.MultiIndex.from_arrays([prueba, region_10(d), mes])).to_numpy()
        k = np.where(np.isnan(k), self.mes.reindex(pd.MultiIndex.from_arrays([prueba, mes])).to_numpy(), k)
        return np.asarray(pred_lightgbm) * np.clip(k, *validar.CORRECCION)


# ------------------------------------------------------------------------------------------- métricas
def metricas(obs: np.ndarray, pred: np.ndarray, minimo: float) -> dict:
    obs, pred = np.asarray(obs, float), np.clip(np.asarray(pred, float), 0, None)
    lo, lp = np.log1p(obs), np.log1p(pred)
    r2_log = 1 - ((lo - lp) ** 2).sum() / ((lo - lo.mean()) ** 2).sum()
    r2 = 1 - ((obs - pred) ** 2).sum() / ((obs - obs.mean()) ** 2).sum()
    mse = float(((obs - pred) ** 2).mean())
    hay = obs >= minimo
    return {"r2_log": round(float(r2_log), 3), "r2": round(float(r2), 3), "mse": round(mse, 1),
            "rmse": round(mse ** 0.5, 2), "mae": round(float(np.abs(obs - pred).mean()), 2),
            "error_tipico": round(float(np.median(np.abs(pred[hay] / obs[hay] - 1)) * 100), 1) if hay.any() else None,
            "sesgo": round(float((pred.sum() / obs.sum() - 1) * 100), 1), "n": int(len(obs))}


def por_nivel(d: pd.DataFrame, col: str) -> dict:
    """d: filas celda × mes con viirs_n, la predicción `col`, país, año y mes."""
    activas = d[(d.viirs_n > 0) | (d.modis_n > 0)]
    con_pais = d[d.country.notna()]
    grupos = {
        "celda_mes": activas[["viirs_n", col]],
        "pais_mes": con_pais.groupby(["country", "año", "mes"])[["viirs_n", col]].sum(),
        "pais_año": con_pais.groupby(["country", "año"])[["viirs_n", col]].sum(),
        "mundo_mes": d.groupby(["año", "mes"])[["viirs_n", col]].sum(),
    }
    return {n: metricas(g.viirs_n, g[col], NIVELES[n]) for n, g in grupos.items()}


# ------------------------------------------------------------------------------------------- países
def tabla_paises(v: pd.DataFrame, modelo: str) -> pd.DataFrame:
    """v: celda × mes no vistos con country, año, mes, viirs, pred (y opcional pred_bajo / pred_alto)."""
    año = v.groupby(["country", "año"]).agg(viirs=("viirs", "sum"), pred=("pred", "sum"),
                                           bajo=("pred_bajo", "sum"), alto=("pred_alto", "sum"))
    mes = v.groupby(["country", "año", "mes"])[["viirs", "pred"]].sum()
    mes["err"] = (mes.pred / mes.viirs.replace(0, np.nan) - 1).abs().where(mes.viirs >= 100)
    filas = []
    for pais, a in año.groupby(level=0):
        viirs_año = float(a.viirs.mean())
        err = a.pred / a.viirs.replace(0, np.nan) - 1
        m = mes.loc[pais]
        lo, lp = np.log1p(m.viirs.to_numpy(float)), np.log1p(m.pred.clip(lower=0).to_numpy(float))
        r2 = 1 - ((lo - lp) ** 2).sum() / max(((lo - lo.mean()) ** 2).sum(), 1e-9)
        dentro = ((a.viirs >= a.bajo) & (a.viirs <= a.alto)).mean() * 100 if a.alto.sum() > 0 else np.nan
        filas.append({"country": pais, "modelo": modelo, "viirs_año": round(viirs_año), "años": int(len(a)),
                      "error_tipico": round(float(err.abs().median() * 100), 1),
                      "sesgo": round(float(err.median() * 100), 1),
                      "peor_año": int(err.abs().idxmax()[1]) if err.notna().any() else None,
                      "error_peor_año": round(float(err.loc[err.abs().idxmax()] * 100), 1) if err.notna().any() else None,
                      "error_mensual": round(float(m.err.median() * 100), 1) if m.err.notna().sum() >= 6 else np.nan,
                      "r2_mensual": round(float(r2), 3), "dentro_rango": round(float(dentro), 1) if np.isfinite(dentro) else None})
    p = pd.DataFrame(filas)
    mes_mal, mes_regular = p.error_mensual.fillna(0) > UMBRAL_MAL_MES, p.error_mensual.fillna(0) > UMBRAL_REGULAR_MES
    p["estado"] = np.select(
        [p.viirs_año < MINIMO_PAIS, (p.error_tipico > UMBRAL_MAL) | mes_mal, (p.error_tipico > UMBRAL_REGULAR) | mes_regular],
        ["pocos datos", "no funciona bien", "regular"], "bien")
    return p


# ------------------------------------------------------------------------------------------- principal
def main():
    t0 = time.time()
    con = duckdb.connect()
    columnas = ", ".join(sorted(set(ENTRADAS) - {"frp_por_det_terra", "frp_por_det_aqua", "razon_aqua_terra",
                                                 "frac_noche", "cenit_terra", "cenit_aqua", "horas_de_sol",
                                                 "distancia_sol"} | {"fila", "col", "año", "viirs_sat", "viirs_n", "modis_n"}))
    d = con.sql(f"""SELECT {columnas} FROM read_parquet('{TABLA.as_posix()}')
                    WHERE terra_ok AND aqua_ok AND viirs_sat IS NOT NULL AND año BETWEEN 2012 AND 2025""").df()
    num = d.columns.difference(["fila", "col", "año", "mes", "viirs_sat"])
    d[num] = d[num].astype("float32")
    d = variables(d)
    pais = con.sql(f"""SELECT fila, col, arg_max(country, parte) country FROM read_parquet('{PAISES.as_posix()}')
                       WHERE parte >= 0.5 GROUP BY ALL""").df()
    d = d.merge(pais, on=["fila", "col"], how="left")
    d["conjunto"] = np.select([d.año.isin(ENTRENAMIENTO), d.año.isin(PRUEBA)], ["entrenamiento", "prueba"], "nunca_vistos")
    print(f"{len(d):,} celda-mes con MODIS y VIIRS · {time.time() - t0:.0f} s")

    entrenamiento = d[d.conjunto == "entrenamiento"]
    modelos = {"factor_global": FactorGlobal(), "razon": Razon(), "lightgbm": LightGBM()}
    for clave, m in modelos.items():
        t1 = time.time()
        m.entrenar(entrenamiento)
        d[f"pred_{clave}"] = m.predecir(d).astype("float32")
        print(f"{clave}: entrenado y aplicado en {time.time() - t1:.0f} s")
    corregido = LightGBMCorregido(con)
    d["pred_lightgbm_corregido"] = corregido.predecir(d, d.pred_lightgbm).astype("float32")
    modelos["lightgbm_corregido"] = corregido
    pais_v = None
    if validar.hay_integral():
        t1 = time.time()
        validar.validacion_integral(con, "v_int")  # predicciones no vistas por tipo (también para los países)
        integral = Integral(con)
        llave = ["fila", "col", "año", "mes"]
        d = d.merge(integral.pred.rename(columns={"pred": "pred_integral"}), on=llave, how="left")
        # celdas-mes sin ninguna detección donde el modelo de fuentes fijas predice algo: cuentan como error
        fuera = integral.pred.merge(d[llave], on=llave, how="left", indicator=True)
        fuera = fuera[fuera._merge == "left_only"].drop(columns="_merge").rename(columns={"pred": "pred_integral"})
        fuera = fuera.merge(pais, on=["fila", "col"], how="left").assign(viirs_n=0.0, modis_n=0.0)
        fuera["conjunto"] = np.select([fuera.año.isin(ENTRENAMIENTO), fuera.año.isin(PRUEBA)],
                                      ["entrenamiento", "prueba"], "nunca_vistos")
        d = pd.concat([d, fuera], ignore_index=True)
        preds = [c for c in d.columns if c.startswith("pred_")]
        d[preds] = d[preds].fillna(0).astype("float32")
        modelos["integral"] = integral
        print(f"integral: {len(fuera):,} celda-mes extra sin detecciones · {time.time() - t1:.0f} s")

    resultado = {"conjuntos": {"entrenamiento": ENTRENAMIENTO, "prueba": PRUEBA, "nunca_vistos": NUNCA_VISTOS},
                 "modelos": {k: {"nombre": m.nombre} for k, m in modelos.items()}, "metricas": {}}
    resultado["modelos"]["razon"]["parametros"] = modelos["razon"].n_factores
    resultado["modelos"]["lightgbm"]["parametros"] = int(modelos["lightgbm"].modelo.booster_.num_trees() * 127)
    resultado["modelos"]["lightgbm_corregido"]["parametros"] = corregido.n_factores
    resultado["modelos"]["factor_global"]["parametros"] = 1
    if "integral" in modelos:
        resultado["modelos"]["integral"]["parametros"] = modelos["integral"].n_factores
        resultado["modelos"]["integral"]["celdas_fijas"] = modelos["integral"].n_celdas
    resultado["modelos"]["factor_global"]["factor"] = round(float(modelos["factor_global"].k), 2)
    for clave in modelos:
        resultado["metricas"][clave] = {c: por_nivel(g, f"pred_{clave}") for c, g in d.groupby("conjunto")}

    # sobreajuste: cuánto empeora de entrenamiento a prueba (y a nunca vistos)
    sobre = {}
    for clave in modelos:
        m = resultado["metricas"][clave]
        sobre[clave] = {n: {"r2_log_entrenamiento": m["entrenamiento"][n]["r2_log"],
                            "r2_log_prueba": m["prueba"][n]["r2_log"],
                            "r2_log_nunca_vistos": m["nunca_vistos"][n]["r2_log"],
                            "caida_r2": round(m["entrenamiento"][n]["r2_log"] - m["prueba"][n]["r2_log"], 3),
                            "error_entrenamiento": m["entrenamiento"][n]["error_tipico"],
                            "error_prueba": m["prueba"][n]["error_tipico"],
                            "error_nunca_vistos": m["nunca_vistos"][n]["error_tipico"]}
                        for n in ("celda_mes", "pais_año")}
        c = sobre[clave]["celda_mes"]
        sobre[clave]["veredicto"] = ("sin_sobreajuste" if c["caida_r2"] <= 0.03 and c["error_prueba"] <= 1.25 * c["error_entrenamiento"]
                                     else "leve" if c["caida_r2"] <= 0.08 else "sobreajuste")
    resultado["sobreajuste"] = sobre

    # países, con predicciones no vistas
    modelo_app = "integral" if validar.hay_integral() else "lightgbm_corregido" if validar.hay_lightgbm() else "razon"
    con.register("pais", pais)
    validar.validacion_razon(con, "v_razon")
    paises = [tabla_paises(con.sql("SELECT v.*, p.country FROM v_razon v JOIN pais p USING (fila, col)").df(), "razon")]
    if validar.hay_lightgbm():
        validar.validacion_lightgbm(con, "v_lgbm")
        paises.append(tabla_paises(con.sql("SELECT v.*, p.country FROM v_lgbm v JOIN pais p USING (fila, col)").df(),
                                   "lightgbm_corregido"))
    if modelo_app == "integral":
        paises.append(tabla_paises(con.sql("""
            SELECT v.fila, v.col, v.año, v.mes, v.prueba, p.country, sum(viirs) viirs, sum(modis) modis, sum(pred) pred,
                   sum(pred_bajo) pred_bajo, sum(pred_alto) pred_alto
            FROM v_int v JOIN pais p USING (fila, col) GROUP BY ALL""").df(), "integral"))
    paises = pd.concat(paises, ignore_index=True)
    con_pais = d[d.country.notna()]
    fijas = (con_pais.modis_frac_fijas * con_pais.modis_n).groupby(con_pais.country).sum() / con_pais.groupby("country").modis_n.sum()
    paises["fuentes_fijas"] = (100 * paises.country.map(fijas)).round(1)
    paises.to_parquet(OUT / "evaluacion_paises.parquet", index=False)
    resultado["modelo_app"] = modelo_app
    resultado["paises"] = {
        "umbrales": {"minimo_viirs_año": MINIMO_PAIS, "mal": UMBRAL_MAL, "regular": UMBRAL_REGULAR,
                     "mal_mes": UMBRAL_MAL_MES, "regular_mes": UMBRAL_REGULAR_MES},
        **{m: {e: int(n) for e, n in g.estado.value_counts().items()} for m, g in paises.groupby("modelo")},
    }
    evaluados = paises[(paises.modelo == modelo_app) & (paises.estado != "pocos datos")]
    malos_r = evaluados.estado == "no funciona bien"
    resultado["paises"]["fuentes_fijas_mediana"] = {"no_funciona": round(float(evaluados.loc[malos_r, "fuentes_fijas"].median()), 1),
                                                     "resto": round(float(evaluados.loc[~malos_r, "fuentes_fijas"].median()), 1)}
    (OUT / "evaluacion.json").write_text(json.dumps(resultado, indent=1, ensure_ascii=False))

    # ------------------------------------------------------------------ resumen en pantalla
    for nivel in NIVELES:
        print(f"\n{nivel}")
        print(f"  {'modelo':14s} {'conjunto':13s} {'R² log':>7s} {'R²':>7s} {'MSE':>14s} {'RMSE':>10s} {'MAE':>9s} {'err típ':>8s} {'sesgo':>7s}")
        for clave in modelos:
            for c in ("entrenamiento", "prueba", "nunca_vistos"):
                x = resultado["metricas"][clave][c][nivel]
                print(f"  {clave:14s} {c:13s} {x['r2_log']:7.3f} {x['r2']:7.3f} {x['mse']:14,.0f} {x['rmse']:10,.1f} "
                      f"{x['mae']:9,.1f} {x['error_tipico'] or 0:7.1f}% {x['sesgo']:6.1f}%")
    print("\nsobreajuste:", {k: v["veredicto"] for k, v in sobre.items()})
    print("países:", resultado["paises"])
    malos = paises[(paises.modelo == modelo_app) & (paises.estado == "no funciona bien")].sort_values("error_tipico", ascending=False)
    print(malos[["country", "viirs_año", "error_tipico", "error_mensual", "sesgo", "fuentes_fijas", "r2_mensual"]].to_string(index=False))
    print("fuentes fijas (mediana %):", resultado["paises"]["fuentes_fijas_mediana"])
    print(f"listo en {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
