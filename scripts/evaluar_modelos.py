# AI-assisted code (Claude, Anthropic), directed and reviewed by the team. See README: "Use of artificial intelligence".
"""Evaluates the MODIS → VIIRS harmonization models: how well they predict, whether they overfit and where they fail.

Years (the same as in notebook 03_modelo):
  training       2012–2016 and 2018–2020   the model learns here
  test           2017 (S-NPP) and 2021 (NOAA-20)   complete years the model did not see
  never seen     2022–2025   not used either, and the Terra and Aqua orbits have already drifted

Models
  factor_global  VIIRS = MODIS × a single worldwide factor
  razon          VIIRS = MODIS × VIIRS/MODIS ratio of its 10° region and its month of the year
  lightgbm       28 inputs (MODIS, intensity, neighbourhood, Sun, place and date) → VIIRS detections, Poisson loss
  lightgbm_corregido   LightGBM × correction of its 10° region and month: Σ VIIRS ÷ Σ predicted in the validation
                 leaving one year out, always without the year being predicted
  integral       each FIRMS type with its own model (scripts/modelo_integral.py and validar.py): vegetation with the
                 vegetation LightGBM (same 28 inputs and years) × regional correction; volcanoes, industry and gas,
                 and offshore cell by cell, fitted with the training years   ← the one the app uses

Metrics at four levels (0.5° cell × month, country × month, country × year, world × month)
  R²            on a log scale (log 1 + x): so each cell or country weighs about the same whatever its size
  MSE, RMSE     mean squared error and its root, in detections
  MAE           mean absolute error, in detections
  typical error median |error| in %, only where VIIRS saw enough for the % to make sense
  bias          how much the total overshoots (+) or falls short (−)

Overfitting: the training error is compared with the test and never-seen errors.

Countries: each country is measured with predictions the model did not see (one year out at a time in 2012–2021
+ 2022–2025); "does not work well" if the typical error per year goes above UMBRAL_MAL or the monthly one above
UMBRAL_MAL_MES. It also stores what share of its MODIS detections are fixed sources (gas flaring, industry, volcanoes).
  The unseen predictions come from scripts/validar.py (the same ones the app shows):
  · razon: recomputed without the year being predicted
  · LightGBM + correction: data/modelo/validacion_por_año.parquet (notebook 03) + armonizado_celdas.parquet in
    2022–2025, with the regional correction of validar.py

Output (data/app/)
  evaluacion.json            metrics per model, set and level; overfitting and country summary
  evaluacion_paises.parquet  one row per country and model

Usage:  python scripts/evaluar_modelos.py          (~5 min: trains LightGBM once)
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

# a country is evaluated if VIIRS sees at least this many per year on average (with fewer, the % are noise)
MINIMO_PAIS = 1000
UMBRAL_MAL, UMBRAL_REGULAR = 25.0, 15.0          # typical error per year (%)
UMBRAL_MAL_MES, UMBRAL_REGULAR_MES = 40.0, 25.0  # typical error per month (%), months with at least 100 detections
NIVELES = {"celda_mes": 20, "pais_mes": 100, "pais_año": 1000, "mundo_mes": 1}  # minimum VIIRS for the error in %

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
    """The same calculated variables as notebook 03 (section 3)."""
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


# ------------------------------------------------------------------------------------------- models
class FactorGlobal:
    nombre = "Un solo factor mundial"

    def entrenar(self, d):
        self.k = d.viirs_n.sum() / d.modis_n.sum()
        return self

    def predecir(self, d):
        return d.modis_n.to_numpy() * self.k


class Razon:
    """Same as scripts/preparar_app.py: ratio of the region (10°) and month if the region had fire in
    at least 3 years; otherwise, the world ratio for that month."""
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
    """Sum of the four FIRMS types, each with its own model. Vegetation: vegetation LightGBM trained on the
    training years (data/modelo/veg_celdas.parquet) × regional correction without the year being predicted.
    Fixed sources: per-cell model from validar.modelo_fijas, with parameters from the training years."""
    nombre = "Integral: un modelo por tipo de fuente (la app)"

    def __init__(self, con: duckdb.DuckDBPyConnection):
        # validar.validacion_integral already left tt, nf, f_veg (correction) and par_fijas in the connection
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
    """LightGBM × k of its region and month; k comes from the leave-one-year-out validation (scripts/validar.py) and
    never uses the year being predicted: in 2012–2021 it is computed without that year, in 2022–2025 with 2012–2021."""
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


# ------------------------------------------------------------------------------------------- metrics
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
    """d: cell × month rows with viirs_n, the prediction `col`, country, year and month."""
    activas = d[(d.viirs_n > 0) | (d.modis_n > 0)]
    con_pais = d[d.country.notna()]
    grupos = {
        "celda_mes": activas[["viirs_n", col]],
        "pais_mes": con_pais.groupby(["country", "año", "mes"])[["viirs_n", col]].sum(),
        "pais_año": con_pais.groupby(["country", "año"])[["viirs_n", col]].sum(),
        "mundo_mes": d.groupby(["año", "mes"])[["viirs_n", col]].sum(),
    }
    return {n: metricas(g.viirs_n, g[col], NIVELES[n]) for n, g in grupos.items()}


# ------------------------------------------------------------------------------------------- countries
def tabla_paises(v: pd.DataFrame, modelo: str) -> pd.DataFrame:
    """v: unseen cell × month with country, year, month, viirs, pred (and optional pred_bajo / pred_alto)."""
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


# ------------------------------------------------------------------------------------------- main
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
    print(f"{len(d):,} cell-months with MODIS and VIIRS · {time.time() - t0:.0f} s")

    entrenamiento = d[d.conjunto == "entrenamiento"]
    modelos = {"factor_global": FactorGlobal(), "razon": Razon(), "lightgbm": LightGBM()}
    for clave, m in modelos.items():
        t1 = time.time()
        m.entrenar(entrenamiento)
        d[f"pred_{clave}"] = m.predecir(d).astype("float32")
        print(f"{clave}: trained and applied in {time.time() - t1:.0f} s")
    corregido = LightGBMCorregido(con)
    d["pred_lightgbm_corregido"] = corregido.predecir(d, d.pred_lightgbm).astype("float32")
    modelos["lightgbm_corregido"] = corregido
    pais_v = None
    if validar.hay_integral():
        t1 = time.time()
        validar.validacion_integral(con, "v_int")  # unseen predictions per type (also for the countries)
        integral = Integral(con)
        llave = ["fila", "col", "año", "mes"]
        d = d.merge(integral.pred.rename(columns={"pred": "pred_integral"}), on=llave, how="left")
        # cell-months with no detection where the fixed-source model predicts something: they count as error
        fuera = integral.pred.merge(d[llave], on=llave, how="left", indicator=True)
        fuera = fuera[fuera._merge == "left_only"].drop(columns="_merge").rename(columns={"pred": "pred_integral"})
        fuera = fuera.merge(pais, on=["fila", "col"], how="left").assign(viirs_n=0.0, modis_n=0.0)
        fuera["conjunto"] = np.select([fuera.año.isin(ENTRENAMIENTO), fuera.año.isin(PRUEBA)],
                                      ["entrenamiento", "prueba"], "nunca_vistos")
        d = pd.concat([d, fuera], ignore_index=True)
        preds = [c for c in d.columns if c.startswith("pred_")]
        d[preds] = d[preds].fillna(0).astype("float32")
        modelos["integral"] = integral
        print(f"integral: {len(fuera):,} extra cell-months without detections · {time.time() - t1:.0f} s")

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

    # overfitting: how much worse it gets from training to test (and to never seen)
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

    # countries, with unseen predictions
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

    # ------------------------------------------------------------------ on-screen summary
    for nivel in NIVELES:
        print(f"\n{nivel}")
        print(f"  {'model':14s} {'set':13s} {'R² log':>7s} {'R²':>7s} {'MSE':>14s} {'RMSE':>10s} {'MAE':>9s} {'typ err':>8s} {'bias':>7s}")
        for clave in modelos:
            for c in ("entrenamiento", "prueba", "nunca_vistos"):
                x = resultado["metricas"][clave][c][nivel]
                print(f"  {clave:14s} {c:13s} {x['r2_log']:7.3f} {x['r2']:7.3f} {x['mse']:14,.0f} {x['rmse']:10,.1f} "
                      f"{x['mae']:9,.1f} {x['error_tipico'] or 0:7.1f}% {x['sesgo']:6.1f}%")
    print("\noverfitting:", {k: v["veredicto"] for k, v in sobre.items()})
    print("countries:", resultado["paises"])
    malos = paises[(paises.modelo == modelo_app) & (paises.estado == "no funciona bien")].sort_values("error_tipico", ascending=False)
    print(malos[["country", "viirs_año", "error_tipico", "error_mensual", "sesgo", "fuentes_fijas", "r2_mensual"]].to_string(index=False))
    print("fixed sources (median %):", resultado["paises"]["fuentes_fijas_mediana"])
    print(f"done in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
