# AI-assisted code (Claude, Anthropic), directed and reviewed by the team. See README: "Use of artificial intelligence".
"""Alzas de fuego fuera de lo normal, semana a semana o mes a mes.

Cada periodo se compara con el mismo periodo del año (la misma semana ISO, o el mismo mes) en los años anteriores
del periodo de historia elegido. Es la regla del estado del mes:
    muy alto   ≥ 2 veces la mediana, o percentil ≥ 90
    alto       ≥ 1.25 veces la mediana, o percentil ≥ 75
    bajo       ≤ la mitad de la mediana
Para no alertar por ruido, un alza tiene que superar la mediana en al menos MINIMO detecciones.

Un episodio es una seguidilla de periodos altos o muy altos. Es alerta si dura al menos RACHA periodos (un patrón de
alzas, no una semana rara) o si alguno de sus periodos es muy alto, al menos duplica la mediana y la pasa por
3 × MINIMO detecciones.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

MINIMO = {"semana": 10, "mes": 20, "pais": 50}
RACHA = {"semana": 3, "mes": 2}
VENTANA = {"semana": 26, "mes": 24}
ALTOS = ("alto", "muy_alto")


def clasificar(x: float, hist: np.ndarray, minimo: float = 0.0) -> dict:
    """Nivel de un valor frente a su historia (los mismos periodos de años anteriores)."""
    hist = np.asarray(hist, dtype=float)
    if len(hist) < 3 or not np.isfinite(x):
        return dict(x=x, n=len(hist), nivel="sin_historia")
    med = float(np.median(hist))
    mad = float(np.median(np.abs(hist - med)))
    pct = 100 * (np.sum(hist < x) + 0.5 * np.sum(hist == x)) / len(hist)
    razon = x / med if med > 0 else (np.inf if x > 0 else 1.0)
    z = (x - med) / (1.4826 * mad) if mad > 0 else 0.0
    alza = x - med >= minimo
    if alza and (razon >= 2 or pct >= 90):
        nivel = "muy_alto"
    elif alza and (razon >= 1.25 or pct >= 75):
        nivel = "alto"
    elif razon <= 0.5 and med > 0:
        nivel = "bajo"
    else:
        nivel = "normal"
    p25, p75 = (float(v) for v in np.percentile(hist, [25, 75]))
    umbral = max(min(1.25 * med, float(np.percentile(hist, 75))), med + minimo)
    return dict(x=x, med=med, p25=p25, p75=p75, umbral=umbral, pct=pct, razon=razon, z=z,
                rank=int(np.sum(hist > x)) + 1, n=len(hist), nivel=nivel)


def niveles(d: pd.DataFrame, periodo: str, año0: int) -> pd.DataFrame:
    """d: fecha (inicio del periodo) y det, en orden. Agrega año, clave (semana ISO o mes) y la comparación de cada
    periodo con los mismos periodos de [año0, año − 1]. Con la columna frac (mes en curso), la historia se escala."""
    d = d.copy()
    if periodo == "semana":
        iso = d.fecha.dt.isocalendar()
        d["año"], d["clave"] = iso.year.astype(int).to_numpy(), iso.week.clip(upper=52).astype(int).to_numpy()
    else:
        d["año"], d["clave"] = d.fecha.dt.year, d.fecha.dt.month
    frac = d["frac"] if "frac" in d else pd.Series(1.0, index=d.index)
    filas = []
    for _, g in d.groupby("clave", sort=False):
        años_g, det_g = g.año.to_numpy(), g.det.to_numpy(dtype=float)
        for i, a, x in zip(g.index, años_g, det_g):
            hist = det_g[(años_g >= año0) & (años_g < a)] * float(frac.loc[i])
            filas.append((i, clasificar(x, hist, MINIMO[periodo])))
    r = pd.DataFrame([f for _, f in filas], index=[i for i, _ in filas]).drop(columns="x")
    return d.join(r).sort_values("fecha")


def episodios(n: pd.DataFrame, periodo: str) -> pd.DataFrame:
    """Seguidillas de periodos altos o muy altos (seguidos en el calendario) y si cada una es alerta."""
    paso = pd.Timedelta(days=7) if periodo == "semana" else None
    alto = n.nivel.isin(ALTOS).to_numpy()
    fechas = n.fecha.to_numpy()
    grupos, actual = [], []
    for i in range(len(n)):
        seguido = bool(actual) and (
            (fechas[i] - fechas[actual[-1]] == paso) if paso is not None
            else (pd.Timestamp(fechas[i]) - pd.DateOffset(months=1) == pd.Timestamp(fechas[actual[-1]])))
        if alto[i] and (not actual or seguido):
            actual.append(i)
            continue
        if actual:
            grupos.append(actual)
        actual = [i] if alto[i] else []
    if actual:
        grupos.append(actual)
    filas = []
    for g in grupos:
        e = n.iloc[g]
        filas.append(dict(inicio=e.fecha.iloc[0], fin=e.fecha.iloc[-1], periodos=len(g), det=float(e.det.sum()),
                          normal=float(e.med.sum()), pico=float(e.razon.replace(np.inf, np.nan).max()),
                          fecha_pico=e.fecha.iloc[int(np.argmax(e.det.to_numpy() - e.med.to_numpy()))],
                          muy_alto=bool((e.nivel == "muy_alto").any()),
                          exceso=float((e.det - e.med).max())))
    ep = pd.DataFrame(filas, columns=["inicio", "fin", "periodos", "det", "normal", "pico", "fecha_pico", "muy_alto",
                                      "exceso"])
    ep["razon"] = ep.det / ep.normal.where(ep.normal > 0)
    ep["alerta"] = (ep.periodos >= RACHA[periodo]) | (ep.muy_alto & (ep.pico >= 2) & (ep.exceso >= 3 * MINIMO[periodo]))
    return ep


def estado(n: pd.DataFrame, ep: pd.DataFrame, periodo: str) -> dict:
    """Lo que hay que decir del final de la ventana: alerta en curso, alza que ya terminó o nada fuera de lo normal."""
    if n.empty:
        return dict(clave="sin_datos")
    ult = n.iloc[-1]
    if ult.nivel == "sin_historia":
        return dict(clave="sin_historia")
    en_curso = ep[ep.fin == ult.fecha]
    if len(en_curso):
        e = en_curso.iloc[0]
        clave = "racha" if e.periodos >= RACHA[periodo] else ("pico" if e.alerta else "subiendo")
        return dict(clave=clave, nivel="muy_alto" if e.alerta else "alto", periodos=int(e.periodos), inicio=e.inicio,
                    razon=float(e.razon), ultima=float(ult.razon), pct=float(ult.pct))
    recientes = ep[ep.alerta & (ep.fin >= n.fecha.iloc[max(0, len(n) - (8 if periodo == "semana" else 6))])]
    if len(recientes):
        e = recientes.iloc[-1]
        return dict(clave="termino", nivel="normal", periodos=int(e.periodos), inicio=e.inicio, fin=e.fin,
                    razon=float(e.razon))
    return dict(clave="normal", nivel="bajo" if ult.nivel == "bajo" else "normal", periodos=len(n))


def ranking_paises(pm: pd.DataFrame, año: int, mes: int, año0: int) -> pd.DataFrame:
    """Países cuyo mes está fuera de lo normal: pm = country, año, mes, det (meses sin fuego = sin fila)."""
    m = pm[pm.mes == mes]
    tabla = m.pivot_table(index="country", columns="año", values="det", aggfunc="sum")
    años_hist = [a for a in range(año0, año) if a in tabla.columns]
    if año not in tabla.columns or len(años_hist) < 3:
        return pd.DataFrame(columns=["country", "x", "med", "razon", "pct", "nivel"])
    filas = []
    for pais, f in tabla.iterrows():
        x = float(np.nan_to_num(f.get(año, 0.0)))
        hist = np.nan_to_num(f[años_hist].to_numpy(dtype=float))
        c = clasificar(x, hist, MINIMO["pais"])
        if c["nivel"] in ALTOS:
            filas.append(dict(country=pais, x=x, med=c["med"], razon=c["razon"], pct=c["pct"], nivel=c["nivel"]))
    r = pd.DataFrame(filas, columns=["country", "x", "med", "razon", "pct", "nivel"])
    return r.assign(exceso=r.x - r.med).sort_values(["nivel", "exceso"], ascending=[False, False])
