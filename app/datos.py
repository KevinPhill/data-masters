# AI-assisted code (Claude, Anthropic), directed and reviewed by the team. See README: "Use of artificial intelligence".
"""App data access: harmonized cells (data/app) and raw detections (db_nasa.duckdb)."""

from __future__ import annotations

import calendar
import io
import json
import os
from datetime import date, timedelta
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import requests
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "data" / "app"
DB = ROOT / "data" / "db_nasa.duckdb"
# without the full database (e.g. in the online demo): Central America points (scripts/exportar_puntos.py)
PUNTOS = APP / "puntos_centroamerica.parquet"
# world total per month: from the integral model (scripts/validar.py) or, if missing, from notebook 03_modelo
SERIE_GLOBAL = next((p for p in (APP / "serie_mundial.csv", ROOT / "data" / "modelo" / "serie_armonizada.csv")
                     if p.exists()), APP / "serie_mundial.csv")
GRADO = 0.5

# FIRMS hot spot types (categoria column; "todos" if the data were harmonized together)
CATEGORIAS = ["veg", "industria", "volcan", "mar"]

FUENTES = {
    "N": "VIIRS NOAA-20 (observado)",
    "S": "VIIRS S-NPP (observado)",
    "M": "MODIS Terra+Aqua → unidades VIIRS",
    "T": "MODIS Terra → unidades VIIRS",
}

# Example regions: (lat_min, lat_max, lon_min, lon_max)
REGIONES = {
    "Guanacaste (Costa Rica)": (9.5, 11.2, -86.0, -84.7),
    "Zona Norte (Costa Rica)": (10.2, 11.2, -85.0, -83.6),
    "Centroamérica": (7.0, 18.5, -92.5, -77.0),
    "Península de Yucatán": (17.5, 22.0, -92.0, -86.5),
    "Amazonía brasileña (arco de deforestación)": (-13.0, -3.0, -63.0, -45.0),
    "Cerrado (Brasil)": (-20.0, -8.0, -55.0, -42.0),
    "Chaco (Bolivia–Paraguay–Argentina)": (-25.0, -17.0, -64.0, -57.0),
    "California (EE. UU.)": (32.5, 42.0, -124.5, -114.0),
    "Sudeste asiático continental": (10.0, 23.0, 97.0, 108.0),
    "Sahel occidental": (10.0, 17.0, -17.0, 5.0),
    "Australia septentrional": (-20.0, -11.0, 120.0, 145.0),
    "Siberia oriental": (55.0, 70.0, 110.0, 145.0),
}


# ------------------------------------------------------------------------------- connection
@st.cache_resource
def conexion() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    archivos = ", ".join(f"'{p.as_posix()}'" for p in (APP / "celdas.parquet", APP / "celdas_fijas.parquet") if p.exists())
    con.execute(f"CREATE VIEW celdas AS SELECT * FROM read_parquet([{archivos}], union_by_name = true)")
    con.execute(f"CREATE TABLE meses AS SELECT * FROM read_parquet('{(APP / 'meses.parquet').as_posix()}')")
    if (APP / "paises.parquet").exists():
        con.execute(f"CREATE TABLE paises AS SELECT * FROM read_parquet('{(APP / 'paises.parquet').as_posix()}')")
    if (APP / "semanas.parquet").exists():  # scripts/semanas.py
        con.execute(f"CREATE VIEW semanas AS SELECT * FROM read_parquet('{(APP / 'semanas.parquet').as_posix()}')")
    if (APP / "paises_mes.parquet").exists():
        con.execute(f"CREATE TABLE paises_mes AS SELECT * FROM read_parquet('{(APP / 'paises_mes.parquet').as_posix()}')")
    if (APP / "validacion.parquet").exists():
        con.execute(f"CREATE VIEW validacion AS SELECT * FROM read_parquet('{(APP / 'validacion.parquet').as_posix()}')")
        con.execute("CREATE TABLE meses_val AS SELECT DISTINCT año, mes, prueba FROM validacion")
    return con


def _cat(cats: tuple[str, ...] | None, alias: str = "c") -> str:
    """Filter by hot spot type; None = all."""
    if not cats:
        return ""
    return f" AND {alias}.categoria IN ({', '.join(repr(str(c)) for c in cats)})"


@st.cache_data
def categorias_disponibles() -> list[str]:
    hay = {r[0] for r in conexion().sql("SELECT DISTINCT categoria FROM celdas").fetchall()}
    return [c for c in CATEGORIAS if c in hay]


def datos_listos() -> bool:
    return (APP / "celdas.parquet").exists() and (APP / "meses.parquet").exists()


@st.cache_data
def meta() -> dict:
    p = APP / "meta.json"
    return json.loads(p.read_text()) if p.exists() else {}


@st.cache_data
def meses() -> pd.DataFrame:
    return conexion().sql("SELECT año, mes, fuente FROM meses ORDER BY año, mes").df()


@st.cache_data
def lista_paises() -> list[str]:
    con = conexion()
    if "paises" not in [r[0] for r in con.sql("SHOW TABLES").fetchall()]:
        return []
    return [r[0] for r in con.sql(
        "SELECT country FROM paises WHERE parte >= 0.5 GROUP BY country HAVING sum(n) >= 50 ORDER BY country"
    ).fetchall()]


@st.cache_data
def resumen_paises(cats: tuple[str, ...] | None = None) -> pd.DataFrame:
    """One row per country for the globe: harmonized detections per year (average over the whole period)."""
    validos = lista_paises()
    if not validos:
        return pd.DataFrame(columns=["pais", "det", "por_año"])
    n_años = len(meses()) / 12
    df = conexion().sql(f"""
        SELECT p.country AS pais, sum(c.det) AS det
        FROM celdas c JOIN (SELECT fila, col, country FROM paises WHERE parte >= 0.5) p USING (fila, col)
        WHERE TRUE {_cat(cats)}
        GROUP BY ALL
    """).df()
    df = df[df.pais.isin(validos)].copy()
    df["por_año"] = df.det / n_años
    return df.reset_index(drop=True)


@st.cache_data
def todas_las_celdas() -> pd.DataFrame:
    """fila, col, lat, lon of every cell that ever had fire."""
    return conexion().sql("SELECT DISTINCT fila, col, lat, lon FROM celdas").df()


# ------------------------------------------------------------------------------- area of interest
def celdas_pais(pais: str) -> pd.DataFrame:
    sel = conexion().sql(
        "SELECT fila, col FROM paises WHERE country = ? AND parte >= 0.5", params=[pais]).df()
    if sel.empty:  # small countries: any cell with detections from the country
        sel = conexion().sql("SELECT DISTINCT fila, col FROM paises WHERE country = ?", params=[pais]).df()
    return sel.merge(todas_las_celdas(), on=["fila", "col"])


def celdas_caja(lat0, lat1, lon0, lon1) -> pd.DataFrame:
    c = todas_las_celdas()
    return c[c.lat.between(lat0, lat1) & c.lon.between(lon0, lon1)]


def celdas_circulo(lat, lon, radio_km) -> pd.DataFrame:
    c = todas_las_celdas()
    la1, lo1, la2, lo2 = map(np.radians, (lat, lon, c.lat.to_numpy(), c.lon.to_numpy()))
    h = np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2
    dist = 2 * 6371 * np.arcsin(np.sqrt(h))
    # includes the cell if its centre falls inside, or if the circle is smaller than a cell
    cerca = dist <= max(radio_km, 40)
    return c[cerca]


# ------------------------------------------------------------------------------- series
def _registrar(sel: pd.DataFrame):
    con = conexion()
    con.register("sel", sel[["fila", "col"]])
    return con


def serie_mensual(sel: pd.DataFrame, cats: tuple[str, ...] | None = None) -> pd.DataFrame:
    """Monthly series of the area: harmonized (with range) and raw, with zeros in valid months without fire."""
    con = _registrar(sel)
    s = con.sql(f"""
        SELECT m.año, m.mes, m.fuente,
               coalesce(sum(c.det), 0)      AS det,
               coalesce(sum(c.det_bajo), 0) AS det_bajo,
               coalesce(sum(c.det_alto), 0) AS det_alto,
               coalesce(sum(c.modis_n), 0)  AS modis_n,
               sum(c.viirs_n)               AS viirs_n
        FROM meses m
        LEFT JOIN (SELECT c.* FROM celdas c JOIN sel USING (fila, col) WHERE TRUE {_cat(cats)}) c USING (año, mes)
        GROUP BY ALL ORDER BY m.año, m.mes
    """).df()
    s.loc[s.fuente.isin(["N", "S"]) & s.viirs_n.isna(), "viirs_n"] = 0
    s["fecha"] = pd.to_datetime(dict(year=s.año, month=s.mes, day=1))
    # "sin armonizar" (not harmonized): MODIS as is until VIIRS exists, then VIIRS (what happens if they are simply joined)
    s["sin_armonizar"] = np.where(s.fuente.isin(["N", "S"]), s.viirs_n, s.modis_n)
    return s


@st.cache_data
def semanas_completas() -> pd.DatetimeIndex:
    """Monday of each ISO week whose seven days fall inside months with data."""
    return pd.DatetimeIndex(conexion().sql("SELECT DISTINCT semana FROM semanas ORDER BY 1").df().semana)


@st.cache_data(show_spinner=False)
def serie_semanal(area: str, cats: tuple[str, ...] | None = None) -> pd.DataFrame | None:
    """Harmonized detections per week for a country ("pais:<country>") or example region ("region:<region>"), with
    zeros in weeks without fire. None if the area has no weekly series (by coordinates)."""
    if not (APP / "semanas.parquet").exists() or not area.startswith(("pais:", "region:")):
        return None
    d = conexion().sql(f"SELECT semana, sum(det) det FROM semanas s WHERE s.area = ? {_cat(cats, 's')} GROUP BY 1",
                       params=[area]).df()
    hay = conexion().sql("SELECT count(*) FROM semanas WHERE area = ?", params=[area]).fetchall()[0][0]
    if not hay:
        return None
    d["semana"] = pd.to_datetime(d.semana)
    d = d.set_index("semana").reindex(semanas_completas(), fill_value=0.0).rename_axis("fecha").reset_index()
    return d.astype({"det": float})


@st.cache_data(show_spinner=False)
def paises_mes(cats: tuple[str, ...] | None = None) -> pd.DataFrame:
    """Harmonized detections per country and month (to see which countries are out of the ordinary)."""
    if not (APP / "paises_mes.parquet").exists():
        return pd.DataFrame(columns=["country", "año", "mes", "det"])
    return conexion().sql(f"SELECT country, año, mes, sum(det) det FROM paises_mes p WHERE TRUE {_cat(cats, 'p')} "
                          "GROUP BY ALL").df()


def mapa_celdas(sel: pd.DataFrame, año0: int, año1: int, cats: tuple[str, ...] | None = None) -> pd.DataFrame:
    con = _registrar(sel)
    return con.sql(f"""
        SELECT c.fila, c.col, any_value(c.lat) lat, any_value(c.lon) lon, sum(c.det) det
        FROM celdas c JOIN sel USING (fila, col)
        WHERE c.año BETWEEN {int(año0)} AND {int(año1)} {_cat(cats)}
        GROUP BY ALL HAVING sum(c.det) > 0
    """).df()


def mapa_anomalia_mes(sel: pd.DataFrame, año: int, mes: int, año0: int,
                      cats: tuple[str, ...] | None = None) -> pd.DataFrame:
    """Per cell: detections of the chosen month vs the median of the same month in previous years."""
    con = _registrar(sel)
    return con.sql(f"""
        WITH a AS (  -- one value per cell and year (sum of the chosen types)
            SELECT c.fila, c.col, c.año, any_value(c.lat) lat, any_value(c.lon) lon, sum(c.det) det
            FROM celdas c JOIN sel USING (fila, col)
            WHERE c.mes = {int(mes)} {_cat(cats)}
            GROUP BY ALL
        ),
        h AS (
            SELECT fila, col, any_value(lat) lat, any_value(lon) lon,
                   sum(det) FILTER (WHERE año = {int(año)}) AS actual,
                   median(det) FILTER (WHERE año BETWEEN {int(año0)} AND {int(año) - 1}) AS mediana
            FROM a GROUP BY ALL
        )
        SELECT *, coalesce(actual, 0) - coalesce(mediana, 0) AS diferencia FROM h
        WHERE coalesce(actual, 0) > 0 OR coalesce(mediana, 0) > 0
    """).df()


def composicion(sel: pd.DataFrame) -> pd.DataFrame:
    """Harmonized detections per year and hot spot type in the area."""
    con = _registrar(sel)
    return con.sql("""
        SELECT c.año, c.categoria, sum(c.det) det, count(DISTINCT c.mes) meses
        FROM celdas c JOIN sel USING (fila, col) GROUP BY ALL ORDER BY c.año
    """).df()


@st.cache_data
def serie_global() -> pd.DataFrame | None:
    if not SERIE_GLOBAL.exists():
        return None
    s = pd.read_csv(SERIE_GLOBAL, parse_dates=["mes"])
    return s


# ------------------------------------------------------------------------------- validation (scripts/validar.py)
@st.cache_data
def validacion_resumen() -> dict:
    p = APP / "validacion.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


# ------------------------------------------------------------------------------- evaluation (scripts/evaluar_modelos.py)
@st.cache_data
def evaluacion() -> tuple[dict, pd.DataFrame]:
    """Metrics of the three models (R², MSE, error, overfitting) and the per-country diagnosis."""
    j, p = APP / "evaluacion.json", APP / "evaluacion_paises.parquet"
    if not (j.exists() and p.exists()):
        return {}, pd.DataFrame()
    return json.loads(j.read_text(encoding="utf-8")), pd.read_parquet(p)


def validacion_area(sel: pd.DataFrame, cats: tuple[str, ...] | None = None) -> pd.DataFrame:
    """Per month (2012–2025): observed VIIRS, raw MODIS and the prediction from MODIS with the year held out
    (2012–2021) or with ratios that never saw that year (2022–2025)."""
    if not (APP / "validacion.parquet").exists():
        return pd.DataFrame()
    con = _registrar(sel)
    v = con.sql(f"""
        SELECT m.año, m.mes, m.prueba,
               coalesce(sum(v.viirs), 0) viirs, coalesce(sum(v.modis), 0) modis, coalesce(sum(v.pred), 0) pred,
               coalesce(sum(v.pred_bajo), 0) pred_bajo, coalesce(sum(v.pred_alto), 0) pred_alto
        FROM meses_val m
        LEFT JOIN (SELECT v.* FROM validacion v JOIN sel USING (fila, col) WHERE TRUE {_cat(cats, "v")}) v USING (año, mes)
        GROUP BY ALL ORDER BY m.año, m.mes
    """).df()
    v["fecha"] = pd.to_datetime(dict(year=v.año, month=v.mes, day=1))
    return v


def errores_validacion(v: pd.DataFrame) -> dict:
    """Typical error (median |error|) per year and per month, coverage of the range and error of non-harmonized MODIS."""
    if v.empty:
        return {}
    a = v.groupby("año").agg(viirs=("viirs", "sum"), modis=("modis", "sum"), pred=("pred", "sum"),
                             lo=("pred_bajo", "sum"), hi=("pred_alto", "sum"))
    a = a[a.viirs >= 30]
    m = v[v.viirs >= 20]
    if a.empty:
        return {}
    return dict(
        anual=float(100 * np.median(np.abs(a.pred / a.viirs - 1))),
        mensual=float(100 * np.median(np.abs(m.pred / m.viirs - 1))) if len(m) else np.nan,
        modis=float(100 * np.median(np.abs(a.modis / a.viirs - 1))),
        dentro=float(100 * np.mean((a.viirs >= a.lo) & (a.viirs <= a.hi))),
        años=int(len(a)),
    )


# ------------------------------------------------------------------------------- raw detections
def db_disponible() -> bool:
    return DB.exists() or PUNTOS.exists()


def puntos_solo_centroamerica() -> bool:
    return not DB.exists() and PUNTOS.exists()


def detecciones_crudas(sel: pd.DataFrame, desde: date, hasta: date, limite: int = 1_000_000) -> pd.DataFrame:
    """Original hot spots (all sensors) inside the cells of the area, between two dates."""
    lat0, lat1 = sel.lat.min() - GRADO, sel.lat.max() + GRADO
    lon0, lon1 = sel.lon.min() - GRADO, sel.lon.max() + GRADO
    completa = DB.exists()
    con = duckdb.connect(str(DB), read_only=True) if completa else duckdb.connect()
    origen = "hotspots" if completa else f"read_parquet('{PUNTOS.as_posix()}')"
    try:
        con.register("sel", sel[["fila", "col"]])
        return con.sql(f"""
            SELECT h.sensor, h.satellite, h.country, h.latitude, h.longitude, h.acq_date, h.acq_time,
                   h.confidence, h.frp, h.daynight, h.type
            FROM {origen} h
            JOIN sel ON sel.fila = CAST(floor(h.latitude / {GRADO}) AS INT)
                    AND sel.col  = CAST(floor(h.longitude / {GRADO}) AS INT)
            WHERE h.latitude BETWEEN {lat0} AND {lat1} AND h.longitude BETWEEN {lon0} AND {lon1}
              AND h.acq_date BETWEEN DATE '{desde.isoformat()}' AND DATE '{hasta.isoformat()}'
            ORDER BY h.acq_date
            LIMIT {int(limite)}
        """).df()
    finally:
        con.close()


# ------------------------------------------------------------------------------- near real time
FIRMS = os.environ.get("FIRMS_URL", "https://firms.modaps.eosdis.nasa.gov")  # FIRMS_URL: mirror or tests
FIRMS_AREA = FIRMS + "/api/area/csv/{key}/{src}/{w},{s},{e},{n}/{dias}"
FIRMS_DISPONIBLE = FIRMS + "/api/data_availability/csv/{key}/all"
# public files of the last 7 days (no key needed). S-NPP stopped delivering data on 2 Nov 2026.
FIRMS_7D = {"NOAA-20": FIRMS + "/data/active_fire/noaa-20-viirs-c2/csv/J1_VIIRS_C2_Global_7d.csv",
            "NOAA-21": FIRMS + "/data/active_fire/noaa-21-viirs-c2/csv/J2_VIIRS_C2_Global_7d.csv"}
COLUMNAS_NRT = ["latitude", "longitude", "acq_date", "acq_time", "satellite", "confidence", "frp", "daynight"]


def _caja(sel: pd.DataFrame) -> tuple[float, float, float, float]:
    return (float(sel.lon.min() - GRADO / 2), float(sel.lat.min() - GRADO / 2),
            float(sel.lon.max() + GRADO / 2), float(sel.lat.max() + GRADO / 2))


def _en_area(df: pd.DataFrame, sel: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df["fila"] = np.floor(df.latitude / GRADO).astype(int)
    df["col"] = np.floor(df.longitude / GRADO).astype(int)
    return df.merge(sel[["fila", "col"]], on=["fila", "col"])


def _leer_firms(txt: str) -> pd.DataFrame:
    if not txt.strip() or txt.lower().startswith(("invalid", "error", "<")):
        raise ValueError(txt[:200] or "Respuesta vacía de FIRMS")
    df = pd.read_csv(io.StringIO(txt))
    return df[[c for c in COLUMNAS_NRT if c in df.columns]]


@st.cache_data(ttl=3600, show_spinner=False)
def firms_7d_global(satelite: str) -> pd.DataFrame:
    """Public global FIRMS file with the last 7 days (cached for one hour)."""
    r = requests.get(FIRMS_7D[satelite], timeout=180)
    r.raise_for_status()
    return _leer_firms(r.text)


def firms_7d(sel: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Last 7 days in the area without a MAP_KEY: VIIRS NOAA-20 and, if it does not respond, NOAA-21."""
    error = None
    for satelite in FIRMS_7D:
        try:
            return _en_area(firms_7d_global(satelite), sel), satelite
        except Exception as e:  # noqa: BLE001
            error = e
    raise RuntimeError(error)


def firms_area(map_key: str, sel: pd.DataFrame, dias: int = 10, fuente: str = "VIIRS_NOAA20_NRT",
               desde: date | None = None) -> pd.DataFrame:
    """FIRMS area API (needs a MAP_KEY): up to 10 days, the latest ones or starting at `desde`."""
    w, s, e, n = _caja(sel)
    url = FIRMS_AREA.format(key=map_key.strip(), src=fuente, w=round(w, 3), s=round(s, 3),
                            e=round(e, 3), n=round(n, 3), dias=int(dias))
    if desde:
        url += f"/{desde.isoformat()}"
    r = requests.get(url, timeout=90)
    r.raise_for_status()
    return _en_area(_leer_firms(r.text), sel)


def firms_nrt(map_key: str, sel: pd.DataFrame, dias: int = 10) -> tuple[pd.DataFrame, str]:
    """Last `dias` days with a MAP_KEY: NOAA-20 and, if it fails, NOAA-21."""
    error = None
    for fuente, nombre in (("VIIRS_NOAA20_NRT", "NOAA-20"), ("VIIRS_NOAA21_NRT", "NOAA-21")):
        try:
            return firms_area(map_key, sel, dias, fuente), nombre
        except Exception as e:  # noqa: BLE001
            error = e
    raise RuntimeError(error)


def firms_disponibilidad(map_key: str) -> dict[str, tuple[date, date]]:
    r = requests.get(FIRMS_DISPONIBLE.format(key=map_key.strip()), timeout=60)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    return {f: (date.fromisoformat(str(a)[:10]), date.fromisoformat(str(b)[:10]))
            for f, a, b in zip(df.data_id, df.min_date, df.max_date)}


def firms_meses_recientes(map_key: str, sel: pd.DataFrame, desde: date, hasta: date,
                          avance=None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """VIIRS NOAA-20 detections per month between `desde` and `hasta` (10-day windows of the area API).
    Uses standard processing (SP) where it exists and near real time (NRT) for the most recent days,
    so the new months are comparable with the history (also NOAA-20 since 2018).
    Returns (months, points): count per month with the days covered, and the individual detections."""
    disp = firms_disponibilidad(map_key)
    fin_sp = disp.get("VIIRS_NOAA20_SP", (None, date.min))[1]
    ventanas, d = [], desde
    while d <= hasta:
        fin = min(d + timedelta(days=9), hasta)
        if d <= fin_sp < fin:  # the window crosses the end of SP: split it in two
            ventanas += [(d, fin_sp, "VIIRS_NOAA20_SP"), (fin_sp + timedelta(days=1), fin, "VIIRS_NOAA20_NRT")]
        else:
            ventanas.append((d, fin, "VIIRS_NOAA20_SP" if fin <= fin_sp else "VIIRS_NOAA20_NRT"))
        d = fin + timedelta(days=1)
    partes = []
    for k, (a, b, fuente) in enumerate(ventanas):
        if avance:
            avance((k + 1) / len(ventanas))
        df = firms_area(map_key, sel, (b - a).days + 1, fuente, desde=a)
        if len(df):
            partes.append(df.assign(procesamiento=fuente[-3:].strip("_")))
    puntos = pd.concat(partes, ignore_index=True) if partes else pd.DataFrame(columns=["acq_date"])
    fechas = pd.to_datetime(puntos.acq_date) if len(puntos) else pd.Series(dtype="datetime64[ns]")
    filas = []
    a, m = desde.year, desde.month
    while (a, m) <= (hasta.year, hasta.month):
        en_mes = (fechas.dt.year == a) & (fechas.dt.month == m) if len(fechas) else []
        ultimo = calendar.monthrange(a, m)[1]
        dia1 = desde.day if (a, m) == (desde.year, desde.month) else 1
        diaN = hasta.day if (a, m) == (hasta.year, hasta.month) else ultimo
        filas.append(dict(año=a, mes=m, det=float(np.sum(en_mes)) if len(fechas) else 0.0,
                          dias=diaN - dia1 + 1, dias_mes=ultimo))
        a, m = (a + 1, 1) if m == 12 else (a, m + 1)
    return pd.DataFrame(filas), puntos
