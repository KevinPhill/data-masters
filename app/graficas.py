# AI-assisted code (Claude, Anthropic), directed and reviewed by the team. See README: "Use of artificial intelligence".
"""Plotly charts for Data Masters.

Templates "datamasters_claro", "datamasters_noche" and "datamasters_banda" (the blue band of the globe, the same in both
modes): same background as what is behind, faint grid, Overpass for text and Fira Sans for labels, and
names directly on the lines instead of legends. Colours from the NASA Space Apps palette (blues, Rocket Red,
Martian Red, Neon Yellow). The calendar and the map use Cividis (perceptually uniform).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

import textos as X

FUENTE = "'Overpass', system-ui, -apple-system, 'Segoe UI', sans-serif"
TITULAR = "'Fira Sans', 'Overpass', system-ui, sans-serif"  # labels on the chart and titles

# NASA Space Apps palette: Electric Blue #0042A6, Neon Blue #0960E1, Blue Yonder #2E96F5, Deep Blue #07173F,
# Rocket Red #E43700, Martian Red #8E1100, Neon Yellow #EAFE07
NARANJA, AMARILLO, AZUL, VERDE, ROJO, LILA = "#E43700", "#FFB31F", "#0960E1", "#2F9E72", "#8E1100", "#8C7BD6"

PALETA = {
    "claro": dict(fondo="#FFFFFF", tinta="#07173F", tinta2="#3D4B66", tenue="#5A6680", rejilla="rgba(7,23,63,0.07)",
                  linea="rgba(7,23,63,0.28)", tierra="#E9EDF4", oceano="#DCE6F3", fronteras="#FFFFFF",
                  banda=(228, 55, 0), acento="#E43700", acento_txt="#C42F00", azul="#0960E1", azul_txt="#0042A6",
                  verde_txt="#1F7A55"),
    "noche": dict(fondo="#07173F", tinta="#FFFFFF", tinta2="#C8D3E8", tenue="#93A4C4", rejilla="rgba(255,255,255,0.07)",
                  linea="rgba(255,255,255,0.25)", tierra="#14275A", oceano="#050F2C", fronteras="#07173F",
                  banda=(255, 106, 61), acento="#FF6A3D", acento_txt="#FF7A45", azul="#2E96F5", azul_txt="#6FB1FF",
                  verde_txt="#5CC8A0"),
    # blue band of the globe (Electric Blue → Deep Blue gradient): transparent paper so the gradient shows
    "banda": dict(fondo="#062060", papel="rgba(0,0,0,0)", tinta="#FFFFFF", tinta2="#C8D3E8", tenue="#A9B8D6",
                  rejilla="rgba(255,255,255,0.08)", linea="rgba(255,255,255,0.3)", tierra="#1C2B55", oceano="#061338",
                  fronteras="#0A1A45", banda=(255, 106, 61), acento="#FF6A3D", acento_txt="#FF8A5C", azul="#6FB1FF",
                  azul_txt="#8EC3FF", verde_txt="#5CC8A0", seleccion="#EAFE07", atmosfera="rgba(46,150,245,0.7)"),
}
PLANTILLA = {"claro": "datamasters_claro", "noche": "datamasters_noche", "banda": "datamasters_banda"}

# Compatibility with the previous version
SURFACE, INK, INK2, MUTED, GRID = (PALETA["claro"][k] for k in ("fondo", "tinta", "tinta2", "tenue", "rejilla"))
COLOR_FUENTE = {"M": AZUL, "T": AMARILLO, "S": NARANJA, "N": VERDE, "R": LILA}
NOMBRE_FUENTE = {"M": "MODIS → VIIRS", "T": "MODIS Terra → VIIRS", "S": "VIIRS S-NPP", "N": "VIIRS NOAA-20",
                 "R": "VIIRS NOAA-20 · casi real"}  # R: months fetched from the FIRMS API (provisional)
MESES = X.MESES_CORTO["es"]

RAMPAS = {  # all colour-blind safe and readable in greyscale
    "Cividis (recomendada)": "Cividis",
    "Viridis": "Viridis",
    "Inferno": "Inferno",
    "Magma": "Magma",
}
# globe ramps (monotonic lightness): on light, more fire = darker; on dark blue, more fire = more
# luminous, from Martian Red to Rocket Red and on to yellow
_FUEGO_OSCURO = [[0, "#8E1100"], [0.3, "#D42F00"], [0.55, "#FF6A1F"], [0.78, "#FFA92E"], [1, "#FFE45C"]]
FUEGO = {"claro": [[0, "#FDE7D6"], [0.3, "#F9AE80"], [0.55, "#F06A35"], [0.8, "#C42F00"], [1, "#8E1100"]],
         "noche": _FUEGO_OSCURO, "banda": _FUEGO_OSCURO}
TOPOJSON = Path(__file__).resolve().parent / "static" / "topojson" / "world_110m.json"
DIVERGENTE = [[0, "#184f95"], [0.25, "#6da7ec"], [0.5, "#f0efec"], [0.75, "#ec8a89"], [1, "#b8302f"]]


# =============================================================================== template
def _plantilla(modo: str) -> go.layout.Template:
    p = PALETA[modo]
    eje = dict(automargin=True, gridcolor=p["rejilla"], gridwidth=1, zeroline=False, linecolor=p["linea"], linewidth=1,
               showline=True, ticks="outside", tickcolor=p["linea"], ticklen=4,
               tickfont=dict(family=FUENTE, size=12, color=p["tenue"]),
               title=dict(font=dict(family=FUENTE, size=12.5, color=p["tenue"])))
    return go.layout.Template(
        layout=dict(
            paper_bgcolor=p.get("papel", p["fondo"]), plot_bgcolor=p.get("papel", p["fondo"]),
            font=dict(family=FUENTE, size=13, color=p["tinta2"]),
            title=dict(font=dict(family=TITULAR, size=17, color=p["tinta"], weight=700), x=0, xanchor="left"),
            colorway=[p["acento"], p["azul"], VERDE, AMARILLO, LILA, ROJO],
            xaxis=eje, yaxis={**eje, "showline": False, "ticks": ""},
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, bgcolor="rgba(0,0,0,0)",
                        font=dict(family=FUENTE, size=12.5, color=p["tinta2"])),
            hoverlabel=dict(bgcolor=p["fondo"], bordercolor=p["linea"], font=dict(family=FUENTE, size=12.5, color=p["tinta"])),
            margin=dict(l=10, r=10, t=44, b=10),
            barcornerradius=0,
            geo=dict(bgcolor=p.get("papel", p["fondo"])),
        ),
        data=dict(scatter=[go.Scatter(line=dict(width=2.2), marker=dict(size=6, line=dict(width=0)))]),
    )


for _modo, _nombre in PLANTILLA.items():
    pio.templates[_nombre] = _plantilla(_modo)


def _layout(fig, alto=380, modo="claro", titulo=None):
    fig.update_layout(template=PLANTILLA.get(modo, PLANTILLA["claro"]), height=alto)
    if titulo:
        fig.update_layout(title_text=titulo, margin_t=60)
    return fig


def _colorbar(p: dict, **kw) -> dict:
    return {**dict(outlinecolor=p["linea"], outlinewidth=1, thickness=12, len=0.92,
                   tickfont=dict(family=FUENTE, size=11, color=p["tenue"]),
                   title=dict(font=dict(family=FUENTE, size=11, color=p["tinta2"]))), **kw}


# =============================================================================== year × month calendar
def calendario(s: pd.DataFrame, vista: str, rampa: str, escala_log: bool, ref: tuple[int, int] | None,
               idioma: str = "en", modo: str = "claro"):
    """Year × month heat map. vista: 'armonizado' | 'sin_armonizar' | 'anomalia'."""
    t = lambda k, **kw: X.t(k, idioma, **kw)  # noqa: E731
    p = PALETA[modo]
    tabla = s.pivot(index="año", columns="mes", values="det" if vista != "sin_armonizar" else "sin_armonizar")
    tabla = tabla.reindex(columns=range(1, 13))
    fuente = s.pivot(index="año", columns="mes", values="fuente").reindex(columns=range(1, 13))
    lo = s.pivot(index="año", columns="mes", values="det_bajo").reindex(columns=range(1, 13))
    hi = s.pivot(index="año", columns="mes", values="det_alto").reindex(columns=range(1, 13))

    sin_datos = t("g_sin_datos")
    texto_fuente = fuente.map(lambda f: NOMBRE_FUENTE.get(f, sin_datos) if isinstance(f, str) else sin_datos)
    custom = np.dstack([texto_fuente.to_numpy(), lo.round().to_numpy(), hi.round().to_numpy()])

    if vista == "anomalia":
        mediana = tabla.median(axis=0)
        z = 100 * (tabla / mediana.replace(0, np.nan) - 1)
        z = z.clip(-100, 300)
        colorscale, zmid = DIVERGENTE, 0
        hover = (f"<b>%{{y}} · %{{x}}</b><br>%{{customdata[3]:,.0f}} {t('g_detecciones')}<br>"
                 f"%{{z:+.0f}}% {t('g_vs_mediana')}<br>{t('g_fuente')}: %{{customdata[0]}}<extra></extra>")
        custom = np.dstack([custom, tabla.to_numpy()])
        colorbar = _colorbar(p, ticksuffix="%")
        colorbar["title"]["text"] = t("g_pct_mediana")
        zmin, zmax = -100, 200
        zplot = z
    else:
        colorscale, zmid = RAMPAS.get(rampa, rampa), None
        zplot = np.log10(tabla + 1) if escala_log else tabla
        custom = np.dstack([custom, tabla.to_numpy()])
        hover = (f"<b>%{{y}} · %{{x}}</b><br>%{{customdata[3]:,.0f}} {t('g_det_viirs')}"
                 f"<br>{t('g_rango')}: %{{customdata[1]:,.0f}} – %{{customdata[2]:,.0f}}"
                 f"<br>{t('g_fuente')}: %{{customdata[0]}}<extra></extra>")
        if vista == "sin_armonizar":
            hover = (f"<b>%{{y}} · %{{x}}</b><br>%{{customdata[3]:,.0f}} {t('g_det_crudas')}"
                     f"<br>{t('g_sensor')}: %{{customdata[0]}}<extra></extra>")
        maxv = float(np.nanmax(tabla.to_numpy())) if np.isfinite(np.nanmax(tabla.to_numpy())) else 1
        if escala_log:
            ticks = [v for v in (0, 1, 10, 100, 1_000, 10_000, 100_000, 1_000_000) if v <= max(maxv, 1)]
            colorbar = _colorbar(p, tickvals=[np.log10(v + 1) for v in ticks], ticktext=[f"{v:,}" for v in ticks])
        else:
            colorbar = _colorbar(p)
        colorbar["title"]["text"] = t("g_detecciones")
        zmin = zmax = None

    años = tabla.index.to_numpy()
    meses = X.MESES_CORTO.get(idioma, MESES)
    fig = go.Figure(go.Heatmap(
        z=zplot.to_numpy(), x=list(range(1, 13)), y=años, customdata=custom,
        colorscale=colorscale, zmid=zmid, zmin=zmin, zmax=zmax, xgap=2, ygap=2,
        hovertemplate=hover.replace("%{x}", "%{customdata[4]}"), colorbar=colorbar, hoverongaps=False,
    ))
    # month name for the hover
    mes_txt = np.tile(np.array(meses, dtype=object), (len(años), 1))
    fig.data[0].customdata = np.dstack([custom, mes_txt])
    # mark months calibrated from MODIS (more uncertainty)
    if vista != "sin_armonizar":
        pts = [(m, a) for a in años for m in range(1, 13) if fuente.loc[a, m] in ("M", "T")]
        if pts:
            fig.add_trace(go.Scatter(x=[q[0] + 0.3 for q in pts], y=[q[1] - 0.22 for q in pts], mode="markers",
                                     marker=dict(symbol="circle", size=4, color="#FFFFFF", opacity=0.9,
                                                 line=dict(width=0.8, color="#07173F")),
                                     hoverinfo="skip", showlegend=False))
        recientes = [(m, a) for a in años for m in range(1, 13) if fuente.loc[a, m] == "R"]
        if recientes:  # near-real-time months: ring
            fig.add_trace(go.Scatter(x=[q[0] + 0.3 for q in recientes], y=[q[1] - 0.22 for q in recientes],
                                     mode="markers", marker=dict(symbol="circle-open", size=7, color=p["tinta"],
                                                                 line=dict(width=1.6)),
                                     hoverinfo="skip", showlegend=False))
    # evaluated month: double frame (contrasts with any colour of the ramp) + star
    if ref and ref[0] in años:
        x0, y0 = ref[1], ref[0]
        fig.add_shape(type="rect", x0=x0 - 0.5, x1=x0 + 0.5, y0=y0 - 0.5, y1=y0 + 0.5, line=dict(color=p["tinta"], width=3))
        fig.add_shape(type="rect", x0=x0 - 0.42, x1=x0 + 0.42, y0=y0 - 0.4, y1=y0 + 0.4,
                      line=dict(color=p["fondo"], width=1.2))
        fig.add_trace(go.Scatter(x=[x0 + 0.42], y=[y0 - 0.42], mode="markers", cliponaxis=False,
                                 marker=dict(symbol="star", size=15, color=AMARILLO, line=dict(width=1.2, color="#07173F")),
                                 hoverinfo="skip", showlegend=False))
    fig.update_yaxes(range=[años.max() + 0.5, años.min() - 0.5], showgrid=False, showline=False, ticks="",
                     dtick=1 if len(años) <= 30 else 2, tickformat="d")
    fig.update_xaxes(side="top", showgrid=False, showline=False, ticks="", tickvals=list(range(1, 13)), ticktext=meses,
                     range=[0.5, 12.5])
    fig = _layout(fig, alto=max(380, 25 * len(tabla) + 90), modo=modo)
    fig.update_layout(margin=dict(t=30))
    return fig


# =============================================================================== trends
def perfil_estacional(s: pd.DataFrame, año_ref: int, años_hist: tuple[int, int], idioma: str = "en",
                      modo: str = "claro"):
    t = lambda k, **kw: X.t(k, idioma, **kw)  # noqa: E731
    p = PALETA[modo]
    r, g_, b = p["banda"]
    meses = X.MESES_CORTO.get(idioma, MESES)
    h = s[s.año.between(*años_hist) & (s.año != año_ref)]
    q = h.groupby("mes").det.quantile([0.1, 0.25, 0.5, 0.75, 0.9]).unstack()
    actual = s[s.año == año_ref].set_index("mes").det
    fig = go.Figure()
    x = [meses[m - 1] for m in q.index]
    fig.add_trace(go.Scatter(x=x, y=q[0.9], mode="lines", line=dict(width=0), hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(x=x, y=q[0.1], mode="lines", fill="tonexty", fillcolor=f"rgba({r},{g_},{b},0.13)",
                             line=dict(width=0), name="10–90 %", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=x, y=q[0.75], mode="lines", line=dict(width=0), hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(x=x, y=q[0.25], mode="lines", fill="tonexty", fillcolor=f"rgba({r},{g_},{b},0.30)",
                             line=dict(width=0), name="25–75 %", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=x, y=q[0.5], mode="lines", line=dict(color=p["acento"], width=3, shape="spline", smoothing=0.6),
                             name=t("g_mediana_rango", a0=años_hist[0], a1=años_hist[1]),
                             hovertemplate=f"%{{x}}: %{{y:,.0f}}<extra>{t('g_mediana')}</extra>"))
    fig.add_trace(go.Scatter(x=[meses[m - 1] for m in actual.index], y=actual, mode="lines+markers",
                             line=dict(color=p["tinta"], width=2, dash="dot"),
                             marker=dict(size=7, color=p["tinta"], line=dict(width=0)),
                             name=str(año_ref), hovertemplate="%{x}: %{y:,.0f}<extra>" + str(año_ref) + "</extra>"))
    fig.update_yaxes(title=t("g_det_mes"), rangemode="tozero")
    return _layout(fig, alto=380, modo=modo)


def anual(s: pd.DataFrame, años: tuple[int, int], idioma: str = "en", modo: str = "claro"):
    t = lambda k, **kw: X.t(k, idioma, **kw)  # noqa: E731
    p = PALETA[modo]
    d = s[s.año.between(*años)]
    g = d.groupby("año").agg(det=("det", "sum"), lo=("det_bajo", "sum"), hi=("det_alto", "sum"),
                             meses=("mes", "count"),
                             fuente=("fuente", lambda f: f.value_counts().index[0]))
    completos = g[g.meses == 12]
    fig = go.Figure()
    for f, sub in g.groupby("fuente"):
        fig.add_trace(go.Bar(
            x=sub.index, y=sub.det, name=NOMBRE_FUENTE.get(f, f),
            marker=dict(color=COLOR_FUENTE.get(f, p["tenue"]), opacity=[1 if m == 12 else 0.45 for m in sub.meses],
                        line=dict(width=0)),
            error_y=dict(type="data", symmetric=False, array=(sub.hi - sub.det).clip(lower=0),
                         arrayminus=(sub.det - sub.lo).clip(lower=0), color=p["tenue"], thickness=1, width=2),
            customdata=np.column_stack([sub.lo, sub.hi, sub.meses]),
            hovertemplate=f"<b>%{{x}}</b>: %{{y:,.0f}}<br>{t('g_rango')} %{{customdata[0]:,.0f}}–%{{customdata[1]:,.0f}}"
                          f"<br>%{{customdata[2]}} {t('g_meses_datos')}<extra></extra>"))
    if len(completos) >= 5:  # linear trend over complete years
        b, a = np.polyfit(completos.index, completos.det, 1)
        xs = np.array([completos.index.min(), completos.index.max()])
        fig.add_trace(go.Scatter(x=xs, y=a + b * xs, mode="lines", line=dict(color=p["tinta"], dash="dash", width=1.6),
                                 name=t("g_tendencia", v=100 * b / completos.det.mean()), hoverinfo="skip"))
    fig.update_layout(barmode="overlay", bargap=0.18)
    fig.update_yaxes(title=t("g_det_año"), rangemode="tozero")
    return _layout(fig, alto=380, modo=modo)


# =============================================================================== alerts by week or by month
COLOR_NIVEL = {"muy_alto": "#E43700", "alto": "#FFA51F", "normal": "#3FA37F", "bajo": "#2E96F5"}


def _fecha_corta(f: pd.Timestamp, idioma: str, dia: bool = True) -> str:
    m = X.MESES_CORTO.get(idioma, MESES)[f.month - 1]
    m = m.lower() if idioma == "es" else m  # in Spanish, month names are lowercase inside a sentence
    return f"{f.day} {m} {f.year}" if dia else f"{m} {f.year}"


def alertas(n: pd.DataFrame, periodo: str, año0: int, idioma: str = "en", modo: str = "claro"):
    """Bars for each week (or month) coloured by level, over the normal range (percentiles 25–75 of the same period
    in previous years), the median and the alert threshold."""
    t = lambda k, **kw: X.t(k, idioma, **kw)  # noqa: E731
    p = PALETA[modo]
    semana = periodo == "semana"
    medio = pd.Timedelta(days=3.5) if semana else pd.Timedelta(days=15)
    x = n.fecha + medio
    ancho = (6 if semana else 26) * 24 * 3600 * 1000
    r, g_, b = (9, 96, 225) if modo == "claro" else (111, 177, 255)
    fig = go.Figure()
    h = n[n.nivel != "sin_historia"]
    if len(h):
        xh = h.fecha + medio
        fig.add_trace(go.Scatter(x=xh, y=h.p75, mode="lines", line=dict(width=0, shape="hvh"), hoverinfo="skip",
                                 showlegend=False))
        fig.add_trace(go.Scatter(x=xh, y=h.p25, mode="lines", fill="tonexty", fillcolor=f"rgba({r},{g_},{b},0.14)",
                                 line=dict(width=0, shape="hvh"), name=t("g_al_normal"), hoverinfo="skip"))
    nivel_txt = n.nivel.map(lambda v: t(f"esc_{v}") if v in COLOR_NIVEL else t("nivel_sin_historia"))
    etiqueta = [t("g_al_semana", f=_fecha_corta(f, idioma)) if semana else _fecha_corta(f, idioma, dia=False)
                for f in n.fecha]
    razon = n.razon.where(np.isfinite(n.razon)) if "razon" in n else pd.Series(np.nan, index=n.index)
    fig.add_trace(go.Bar(
        x=x, y=n.det, width=ancho, name=t("g_al_det"), showlegend=False,
        marker=dict(color=[COLOR_NIVEL.get(v, p["tenue"]) for v in n.nivel], line=dict(width=0)),
        customdata=np.column_stack([etiqueta, n.get("med", pd.Series(np.nan, index=n.index)).round(), razon.round(1),
                                    nivel_txt]),
        hovertemplate=(f"<b>%{{customdata[0]}}</b><br>%{{y:,.0f}} {t('g_det_viirs')}"
                       f"<br>{t('g_al_lo_normal')}: %{{customdata[1]:,.0f}} (%{{customdata[2]}}×)"
                       f"<br>%{{customdata[3]}}<extra></extra>")))
    if len(h):
        fig.add_trace(go.Scatter(x=xh, y=h.med, mode="lines", line=dict(color=p["azul"], width=1.8, shape="hvh"),
                                 name=t("g_al_mediana", a0=año0), hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=xh, y=h.umbral, mode="lines", line=dict(color=p["acento"], width=1.6, dash="dot",
                                                                           shape="hvh"),
                                 name=t("g_al_umbral"), hoverinfo="skip"))
    for nv in ("muy_alto", "alto", "normal", "bajo"):  # bar colour legend (text, not just colour)
        if (n.nivel == nv).any():
            fig.add_trace(go.Bar(x=[None], y=[None], marker_color=COLOR_NIVEL[nv], name=t(f"esc_{nv}"),
                                 hoverinfo="skip"))
    meses = X.MESES_CORTO.get(idioma, MESES)
    inicios = pd.date_range(n.fecha.min(), n.fecha.max() + medio, freq="MS")
    paso = 1 if semana else 3
    ticks = [f for f in inicios[::paso]]
    fig.update_xaxes(tickvals=ticks, ticktext=[f"{meses[f.month - 1]}<br>{f.year}" if f.month == 1 or i == 0
                                               else meses[f.month - 1] for i, f in enumerate(ticks)],
                     range=[n.fecha.min() - medio / 2, n.fecha.max() + 2 * medio])
    fig.update_yaxes(title=t("g_al_det_semana" if semana else "g_det_mes"), rangemode="tozero")
    fig.update_layout(bargap=0.15, barmode="overlay", hovermode="closest",
                      legend=dict(traceorder="normal"))
    return _layout(fig, alto=400, modo=modo)


# hot spot type colours: vegetation in fire red, volcanoes in yellow, industry and offshore
# in two blues of different lightness
COLOR_TIPO = {"veg": NARANJA, "industria": AZUL, "volcan": AMARILLO, "mar": "#2E96F5"}


def composicion(c: pd.DataFrame, años: tuple[int, int], idioma: str = "en", modo: str = "claro"):
    """Stacked bars per year: how much of what was detected is vegetation, industry and gas, volcanoes or offshore."""
    t = lambda k, **kw: X.t(k, idioma, **kw)  # noqa: E731
    p = PALETA[modo]
    d = c[c.año.between(*años)]
    tabla = d.pivot_table(index="año", columns="categoria", values="det", aggfunc="sum").fillna(0)
    meses = d.groupby("año").meses.max()
    fig = go.Figure()
    colores = dict(COLOR_TIPO, mar=p["azul"] if modo != "claro" else "#2E96F5")
    for cat in [k for k in COLOR_TIPO if k in tabla.columns]:
        y = tabla[cat]
        parte = 100 * y / tabla.sum(axis=1).replace(0, np.nan)
        fig.add_trace(go.Bar(
            x=tabla.index, y=y, name=t(f"tipo_{cat}"),
            marker=dict(color=colores[cat], opacity=[1 if meses.get(a, 12) == 12 else 0.45 for a in tabla.index],
                        line=dict(width=0)),
            customdata=parte.to_numpy(),
            hovertemplate=f"<b>%{{x}}</b> · {t(f'tipo_{cat}')}: %{{y:,.0f}} (%{{customdata:.1f}} %)<extra></extra>"))
    fig.update_layout(barmode="stack", bargap=0.18, showlegend=True,
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, traceorder="normal",
                                  font=dict(color=p["tinta2"])))
    fig.update_yaxes(title=t("g_det_año"), rangemode="tozero")
    return _layout(fig, alto=380, modo=modo)


# =============================================================================== harmonization
def factor_viirs_modis(s: pd.DataFrame) -> float:
    """How many times more VIIRS sees than MODIS in the months when both fly."""
    ambos = s[s.fuente.isin(["N", "S"]) & (s.modis_n > 0)]
    return float(ambos.viirs_n.sum() / ambos.modis_n.sum()) if len(ambos) else np.nan


def viirs_puro(d: pd.DataFrame, minimo: int = 9) -> pd.Series:
    """Monthly average of observed VIIRS, only in years where every valid month is VIIRS: if a year has
    months filled in with MODIS (e.g. 2012 or 2018) and one of them is in the high season, averaging only the VIIRS
    months would drag it down."""
    g = d.groupby("año").agg(v=("viirs_n", "mean"), n=("mes", "count"),
                             nv=("fuente", lambda f: int(f.isin(["N", "S"]).sum())))
    return g.loc[(g.n == g.nv) & (g.n >= minimo), "v"]


def antes_despues(s: pd.DataFrame, años: tuple[int, int], idioma: str = "en", modo: str = "claro"):
    """Two panels with the same axis and the same colours: on the left MODIS and VIIRS joined as they are (false jump),
    on the right harmonized MODIS (with its range) next to VIIRS. The only thing that moves is the blue line.
    Each point is the monthly average of a year with at least 9 valid months (as in notebook 03)."""
    t = lambda k, **kw: X.t(k, idioma, **kw)  # noqa: E731
    p = PALETA[modo]
    minimo = 9
    d = s[s.año.between(*años)]
    años_viirs = s.loc[s.fuente.isin(["N", "S"]), "año"]
    año_viirs = int(años_viirs.min()) if len(años_viirs) else 10_000
    era_modis = d.año < año_viirs
    rango = list(range(años[0], años[1] + 1))

    def promedio(filas, columna):
        g = d[filas].groupby("año")[columna].agg(["mean", "count"])
        return g.loc[g["count"] >= minimo, "mean"].reindex(rango)

    modis_crudo = promedio(era_modis, "modis_n")
    viirs = viirs_puro(d, minimo).reindex(rango)
    arm = d.groupby("año").agg(det=("det", "mean"), lo=("det_bajo", "mean"), hi=("det_alto", "mean"), n=("mes", "count"))
    arm = arm[arm.n >= minimo].reindex(rango)
    arm_modis, arm_viirs = arm.copy(), arm.copy()
    arm_modis.loc[arm.index >= año_viirs] = np.nan
    arm_viirs.loc[arm.index < año_viirs] = np.nan
    factor = factor_viirs_modis(s)

    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.045,
                        subplot_titles=(t("g_antes"), t("g_despues")))
    azul = p["azul"]
    r, g_, b = (int(azul[i:i + 2], 16) for i in (1, 3, 5))
    linea = dict(mode="lines+markers", connectgaps=False, showlegend=False,
                 hovertemplate="<b>%{x}</b> · %{y:,.0f}<extra>%{fullData.name}</extra>")
    fig.add_trace(go.Scatter(x=rango, y=modis_crudo, name=t("g_modis_tal_cual"), line=dict(color=azul, width=2.4),
                             marker=dict(size=6, color=azul), **linea), row=1, col=1)
    # VIIRS only has points in 100 % VIIRS years; the line joins them (the points mark the real years)
    fig.add_trace(go.Scatter(x=rango, y=viirs, name=t("g_viirs_c"), line=dict(color=p["tinta"], width=2.4),
                             marker=dict(size=6, color=p["tinta"]), **{**linea, "connectgaps": True}), row=1, col=1)
    fig.add_trace(go.Scatter(x=rango, y=arm_modis.hi, mode="lines", line=dict(width=0), hoverinfo="skip",
                             showlegend=False, connectgaps=False), row=1, col=2)
    fig.add_trace(go.Scatter(x=rango, y=arm_modis.lo, mode="lines", line=dict(width=0), fill="tonexty",
                             fillcolor=f"rgba({r},{g_},{b},0.22)", hoverinfo="skip", showlegend=False, connectgaps=False),
                  row=1, col=2)
    fig.add_trace(go.Scatter(x=rango, y=arm_modis.det, name=t("g_modis_arm"), line=dict(color=azul, width=2.4),
                             marker=dict(size=6, color=azul), **linea), row=1, col=2)
    fig.add_trace(go.Scatter(x=rango, y=arm_viirs.det, name=t("g_viirs_c"), line=dict(color=p["tinta"], width=2.4),
                             marker=dict(size=6, color=p["tinta"]), **linea), row=1, col=2)

    def etiqueta(serie, techo, texto, color, col):
        """Line name above its segment (no legend, as in the EDA)."""
        v = serie.dropna()
        if v.empty:
            return
        fig.add_annotation(x=int(v.index[len(v) // 2]), y=float(np.nanmax(techo)), xref="x" if col == 1 else "x2",
                           yref="y", text=texto, showarrow=False, yanchor="bottom", yshift=8, bgcolor=p["fondo"],
                           borderpad=2, font=dict(family=TITULAR, size=13.5, color=color, weight=600))

    etiqueta(modis_crudo, modis_crudo, t("g_modis_tal_cual"), p["azul_txt"], 1)
    etiqueta(viirs, viirs, t("g_viirs_c"), p["tinta"], 1)
    etiqueta(arm_modis.det, arm_modis.hi, t("g_modis_arm"), p["azul_txt"], 2)
    etiqueta(arm_viirs.det, arm_viirs.det, t("g_viirs_c"), p["tinta"], 2)

    # the jump: arrow from the last MODIS year to the first VIIRS year, and each panel's label
    m, v = modis_crudo.dropna(), viirs.dropna()
    if len(m) and len(v):
        fig.add_annotation(x=int(v.index[0]), y=float(v.iloc[0]), ax=int(m.index[-1]), ay=float(m.iloc[-1]),
                           xref="x", yref="y", axref="x", ayref="y", text="", showarrow=True, arrowhead=2,
                           arrowsize=1.1, arrowwidth=1.8, arrowcolor=p["acento"], standoff=6, startstandoff=6)
    if np.isfinite(factor):
        salto = t("g_salto", f=factor) if factor >= 1.2 else t("g_casi_sin_salto", f=factor)
        for eje, texto, color in (("x", salto, p["acento_txt"]), ("x2", t("g_sin_salto"), p["verde_txt"])):
            fig.add_annotation(x=0.02, y=0.98, xref=f"{eje} domain", yref="y domain", text=texto, showarrow=False,
                               xanchor="left", yanchor="top", bgcolor=p["fondo"], borderpad=2,
                               font=dict(family=TITULAR, size=14.5, color=color, weight=700))
    if años[0] < año_viirs <= años[1]:
        for col in (1, 2):
            fig.add_vline(x=año_viirs - 0.5, line=dict(color=p["linea"], dash="dot", width=1), row=1, col=col)

    techo = max([float(np.nanmax(x)) for x in (modis_crudo, viirs, arm.hi) if x.notna().any()] or [1.0])
    fig.update_yaxes(range=[0, techo * 1.34])
    fig.update_yaxes(title=t("g_det_mes_prom"), row=1, col=1)
    fig.update_xaxes(range=[años[0] - 0.7, años[1] + 0.7], tickformat="d", dtick=5 if años[1] - años[0] > 12 else 2)
    for ann, eje in zip(fig.layout.annotations[:2], ("xaxis", "xaxis2")):  # panel titles aligned to the left
        ann.update(x=fig.layout[eje].domain[0], xanchor="left", yshift=6,
                   font=dict(family=TITULAR, size=15, color=p["tinta"], weight=700))
    fig = _layout(fig, alto=430, modo=modo)
    fig.update_layout(margin=dict(t=58))
    return fig


# =============================================================================== globe + country history
@lru_cache(maxsize=1)
def centroides() -> dict[str, tuple[float, float]]:
    """ISO3 → (lon, lat) of the centre of each country, taken from the same topojson that draws the globe."""
    geoms = json.loads(TOPOJSON.read_text())["objects"]["countries"]["geometries"]
    return {g["id"]: tuple(g["properties"]["ct"]) for g in geoms if g.get("id") and "ct" in g.get("properties", {})}


def _etiqueta_log(v: int) -> str:
    return f"{v // 1_000_000} M" if v >= 1e6 else f"{v // 1000} k" if v >= 1000 else str(v)


def escala_globo(df: pd.DataFrame, modo: str = "banda") -> tuple[list, list[tuple[float, str]]]:
    """Globe ramp and its ticks [(position 0–1, text)], to draw the scale outside the chart."""
    maxv = max(float(df.por_año.max()), 10.0)
    tope = np.log10(maxv + 1)
    marcas = [(float(np.log10(v + 1) / tope), _etiqueta_log(v)) for v in (10, 100, 1_000, 10_000, 100_000, 1_000_000)
              if v <= maxv]
    return FUEGO[modo], marcas


def globo(df: pd.DataFrame, seleccionado: str | None, idioma: str = "en", modo: str = "claro", alto: int = 560,
          barra: bool = True):
    """Orthographic globe with every country, colour = harmonized detections per year (log scale).
    It rotates by dragging; the chosen country stays centred and outlined. customdata = [FIRMS name, value, name].
    barra=False: no colour bar (the app draws it in HTML below, with escala_globo) and no bottom margin."""
    t = lambda k, **kw: X.t(k, idioma, **kw)  # noqa: E731
    p = PALETA[modo]
    d = df.assign(iso=df.pais.map(X.iso3), nombre=df.pais.map(lambda n: X.pais(n, idioma))).dropna(subset=["iso"])
    d = d[d.iso != "ATA"]  # Antarctica has almost no fire: its points are volcanoes and reflections
    maxv = max(float(d.por_año.max()), 10.0)
    ticks = [v for v in (10, 100, 1_000, 10_000, 100_000, 1_000_000) if v <= maxv]
    hover = f"<b>%{{customdata[2]}}</b><br>%{{customdata[1]:,.0f}} {t('globo_hover')}<extra></extra>"
    sin_atenuar = dict(selected=dict(marker=dict(opacity=1)), unselected=dict(marker=dict(opacity=1)))

    def datos(filas):
        return np.column_stack([filas.pais.to_numpy(object), filas.por_año.to_numpy(float), filas.nombre.to_numpy(object)])

    fig = go.Figure(go.Choropleth(
        locations=d.iso, locationmode="ISO-3", z=np.log10(d.por_año + 1), zmin=0, zmax=np.log10(maxv + 1),
        colorscale=FUEGO[modo], marker_line_color=p["fronteras"], marker_line_width=0.5, customdata=datos(d),
        hovertemplate=hover, **sin_atenuar, showscale=barra,
        colorbar=_colorbar(p, orientation="h", x=0.5, xanchor="center", y=0, yanchor="top", len=0.8, thickness=8,
                           tickvals=[np.log10(v + 1) for v in ticks],
                           ticktext=[_etiqueta_log(v) for v in ticks],
                           title=dict(text=t("globo_hover"), side="top",
                                      font=dict(family=FUENTE, size=12, color=p["tinta2"]))),
    ))
    elegido = d[d.pais == seleccionado]
    if len(elegido):  # border of the chosen country: dark halo with the light stroke on top, readable over any colour
        for color, ancho in ((p["oceano"], 5.0), (p.get("seleccion", p["tinta"]), 2.2)):
            fig.add_trace(go.Choropleth(
                locations=elegido.iso, locationmode="ISO-3", z=[0],
                colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]], showscale=False, marker_line_color=color,
                marker_line_width=ancho, customdata=datos(elegido), hovertemplate=hover, **sin_atenuar))
    lon, lat = centroides().get(elegido.iso.iloc[0] if len(elegido) else "", (-60.0, 5.0))
    # whole degrees: with a decimal tilt (e.g. 9.97°) Plotly clips the globe into a band
    reticula = dict(showgrid=True, gridcolor=p["rejilla"], gridwidth=1, dtick=15)
    fig.update_geos(
        projection_type="orthographic", projection_rotation=dict(lon=round(lon), lat=int(np.clip(round(lat), -35, 35)), roll=0),
        showocean=True, oceancolor=p["oceano"], showland=True, landcolor=p["tierra"], showlakes=False,
        showcountries=True, countrycolor=p["fronteras"], countrywidth=0.4,
        showcoastlines=True, coastlinecolor=p["fronteras"], coastlinewidth=0.6,
        showframe=True, framecolor=p.get("atmosfera", p["linea"]), framewidth=1.5 if "atmosfera" in p else 1,
        lataxis=reticula, lonaxis=reticula,
        resolution=110, bgcolor="rgba(0,0,0,0)",
    )
    fig = _layout(fig, alto=alto, modo=modo)
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=72 if barra else 0), dragmode="pan", uirevision=seleccionado or "globo",
                      clickmode="event+select")
    return fig


def historia_pais(s: pd.DataFrame, años: tuple[int, int], idioma: str = "en", modo: str = "claro"):
    """Yearly history of the country, EDA style: the harmonized series (filled dot = year observed by VIIRS, hollow =
    estimated from MODIS, with its band) against MODIS as is. Names at the end of each line, no legend."""
    t = lambda k, **kw: X.t(k, idioma, **kw)  # noqa: E731
    p = PALETA[modo]
    minimo = 9
    d = s[s.año.between(*años)]
    rango = list(range(años[0], años[1] + 1))
    arm = d.groupby("año").agg(det=("det", "mean"), lo=("det_bajo", "mean"), hi=("det_alto", "mean"),
                               n=("mes", "count"), nv=("fuente", lambda f: int(f.isin(["N", "S"]).sum())))
    arm = arm[arm.n >= minimo].reindex(rango)
    mo = d.groupby("año").modis_n.agg(["mean", "count"])
    modis = mo.loc[mo["count"] >= minimo, "mean"].reindex(rango)
    observado = (arm.nv >= arm.n / 2).fillna(False).to_numpy()
    r, g_, b = p["banda"]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=rango, y=arm.hi, mode="lines", line=dict(width=0), hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(x=rango, y=arm.lo, mode="lines", line=dict(width=0), fill="tonexty",
                             fillcolor=f"rgba({r},{g_},{b},0.26)", hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(
        x=rango, y=modis, name=t("hist_modis"), mode="lines+markers", line=dict(color=p["azul"], width=2),
        marker=dict(size=5, color=p["azul"]), showlegend=False, connectgaps=False,
        hovertemplate=f"<b>%{{x}}</b> · %{{y:,.0f}}<extra>{t('hist_modis')}</extra>"))
    origen = np.where(observado, t("hist_viirs"), t("hist_estimado"))
    fig.add_trace(go.Scatter(
        x=rango, y=arm.det, name=t("hist_arm"), mode="lines+markers", line=dict(color=p["acento"], width=3),
        marker=dict(size=8, color=np.where(observado, p["acento"], p["fondo"]), symbol="circle",
                    line=dict(color=p["acento"], width=2)),
        showlegend=False, connectgaps=False, customdata=np.column_stack([origen, arm.lo, arm.hi]),
        hovertemplate=(f"<b>%{{x}}</b> · %{{y:,.0f}} {t('g_det_mes')}<br>%{{customdata[0]}}"
                       f"<br>{t('g_rango')}: %{{customdata[1]:,.0f}}–%{{customdata[2]:,.0f}}"
                       f"<extra>{t('hist_arm')}</extra>")))

    # names at the end of each line (spread apart if they overlap)
    finales = []
    for serie, texto, color in ((arm.det, t("hist_arm"), p["acento_txt"]), (modis, t("hist_modis"), p["azul_txt"])):
        v = serie.dropna()
        if len(v):
            finales.append([int(v.index[-1]), float(v.iloc[-1]), texto, color])
    techo = max([float(np.nanmax(x)) for x in (arm.hi, modis) if x.notna().any()] or [1.0])
    if len(finales) == 2 and abs(finales[0][1] - finales[1][1]) < 0.09 * techo:
        alto_, bajo_ = sorted(finales, key=lambda f: -f[1])
        alto_.append(9), bajo_.append(-9)
    for f in finales:
        fig.add_annotation(x=f[0], y=f[1], text=f"<b>{f[2]}</b>", showarrow=False, xanchor="left", xshift=9,
                           yshift=f[4] if len(f) > 4 else 0, font=dict(family=TITULAR, size=13.5, color=f[3], weight=600))

    años_viirs = d.loc[d.fuente.isin(["N", "S"]), "año"]
    if len(años_viirs) and años[0] < int(años_viirs.min()) <= años[1]:
        x0 = int(años_viirs.min()) - 0.5
        fig.add_vline(x=x0, line=dict(color=p["linea"], dash="dot", width=1))
        fig.add_annotation(x=x0, y=1, yref="paper", text=t("hist_entra_viirs"), showarrow=False, xanchor="left",
                           yanchor="top", xshift=6, font=dict(family=FUENTE, size=12.5, color=p["tenue"]))
    fig.update_yaxes(title=t("g_det_mes_prom"), rangemode="tozero", range=[0, techo * 1.12])
    fig.update_xaxes(range=[años[0] - 0.6, años[1] + 0.6], tickformat="d", dtick=5 if años[1] - años[0] > 12 else 2)
    fig = _layout(fig, alto=360, modo=modo)
    fig.update_layout(margin=dict(t=14, r=128), hovermode="closest")
    return fig


def validacion(v: pd.DataFrame, idioma: str = "en", modo: str = "claro"):
    """Validation per year in the area: observed VIIRS against what was predicted from MODIS without having seen that year
    (2012–2021 leaving one year out; 2022–2025 never used for calibration), and MODIS as is."""
    t = lambda k, **kw: X.t(k, idioma, **kw)  # noqa: E731
    p = PALETA[modo]
    a = v.groupby("año").agg(viirs=("viirs", "sum"), modis=("modis", "sum"), pred=("pred", "sum"),
                             lo=("pred_bajo", "sum"), hi=("pred_alto", "sum"))
    x = a.index.to_numpy()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=a.modis, mode="lines+markers", line=dict(color=p["azul"], width=2),
                             marker=dict(size=5, color=p["azul"]), showlegend=False,
                             hovertemplate=f"<b>%{{x}}</b> · %{{y:,.0f}}<extra>{t('g_modis_tal_cual')}</extra>"))
    fig.add_trace(go.Scatter(x=x, y=a.viirs, mode="lines+markers", line=dict(color=p["tinta"], width=2.4),
                             marker=dict(size=6, color=p["tinta"]), showlegend=False,
                             hovertemplate=f"<b>%{{x}}</b> · %{{y:,.0f}}<extra>{t('g_viirs_obs')}</extra>"))
    error = 100 * (a.pred / a.viirs.replace(0, np.nan) - 1)
    fig.add_trace(go.Scatter(
        x=x, y=a.pred, mode="markers", showlegend=False,
        marker=dict(size=12, color="rgba(0,0,0,0)", symbol="circle", line=dict(color=p["acento"], width=2.6)),
        error_y=dict(type="data", symmetric=False, array=(a.hi - a.pred).clip(lower=0),
                     arrayminus=(a.pred - a.lo).clip(lower=0), color=p["acento"], thickness=1.4, width=4),
        customdata=np.column_stack([a.lo, a.hi, a.viirs, error.fillna(0)]),
        hovertemplate=(f"<b>%{{x}}</b> · %{{y:,.0f}}<br>{t('g_rango')}: %{{customdata[0]:,.0f}}–%{{customdata[1]:,.0f}}"
                       f"<br>{t('g_viirs_obs')}: %{{customdata[2]:,.0f}} (%{{customdata[3]:+.0f}} %)"
                       f"<extra>{t('g_val_pred')}</extra>")))
    techo = float(np.nanmax([a.viirs.max(), a.hi.max(), a.modis.max(), 1]))
    finales = sorted([[float(a.viirs.iloc[-1]), t("g_viirs_obs"), p["tinta"]],
                      [float(a.pred.iloc[-1]), t("g_val_pred"), p["acento_txt"]],
                      [float(a.modis.iloc[-1]), t("g_modis_tal_cual"), p["azul_txt"]]], key=lambda f: -f[0])
    y_prev = None
    for f in finales:  # names at the end, spread apart if they overlap
        y = f[0] if y_prev is None else min(f[0], y_prev - 0.08 * techo)
        fig.add_annotation(x=int(x[-1]), y=y, text=f[1], showarrow=False, xanchor="left", xshift=12,
                           font=dict(family=TITULAR, size=13, color=f[2], weight=600))
        y_prev = y
    corte = 2021.5
    if x.min() < corte < x.max():
        fig.add_vline(x=corte, line=dict(color=p["linea"], dash="dot", width=1))
        for xx, texto, ancla in ((corte, t("g_val_fuera"), "left"), (corte, t("g_val_loyo"), "right")):
            fig.add_annotation(x=xx, y=1, yref="paper", text=texto, showarrow=False, xanchor=ancla, yanchor="top",
                               xshift=6 if ancla == "left" else -6, font=dict(family=FUENTE, size=12.5, color=p["tenue"]))
    fig.update_yaxes(title=t("g_det_año_corto"), rangemode="tozero", range=[0, techo * 1.15])
    fig.update_xaxes(tickformat="d", dtick=1 if len(x) <= 16 else 2, range=[x.min() - 0.6, x.max() + 0.6])
    fig = _layout(fig, alto=380, modo=modo)
    fig.update_layout(margin=dict(t=30, r=170), hovermode="closest")
    return fig


def serie_global(g: pd.DataFrame, idioma: str = "en", modo: str = "claro"):
    t = lambda k, **kw: X.t(k, idioma, **kw)  # noqa: E731
    p = PALETA[modo]
    fig = go.Figure()
    if "detecciones_modis" in g:
        fig.add_trace(go.Scatter(x=g.mes, y=g.detecciones_modis, name=t("g_modis_crudo"),
                                 line=dict(color=p["tenue"], width=2)))
    if {"detecciones_min", "detecciones_max"} <= set(g.columns):
        fig.add_trace(go.Scatter(x=g.mes, y=g.detecciones_max, mode="lines", line=dict(width=0), hoverinfo="skip",
                                 showlegend=False))
        fig.add_trace(go.Scatter(x=g.mes, y=g.detecciones_min, mode="lines", fill="tonexty", line=dict(width=0),
                                 fillcolor="rgba(9,96,225,0.2)", name=t("g_rango90"), hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=g.mes, y=g.detecciones_estimado, name=t("g_lgbm"), line=dict(color=p["azul"], width=3)))
    fig.add_trace(go.Scatter(x=g.mes, y=g.detecciones_observado, name=t("g_viirs_obs"),
                             line=dict(color=p["tinta"], width=2.5)))
    fig.update_yaxes(title=t("g_det_mundo"), rangemode="tozero")
    return _layout(fig, alto=400, modo=modo)


# =============================================================================== map
def mapa(df: pd.DataFrame, columna: str, titulo_color: str, divergente=False, rampa="Cividis", modo: str = "claro"):
    """0.5° cells on a vector map (works offline)."""
    p = PALETA[modo]
    v = df[columna].to_numpy(dtype=float)
    if divergente:
        lim = float(np.nanpercentile(np.abs(v), 98)) or 1.0
        marker = dict(color=v, colorscale=DIVERGENTE, cmin=-lim, cmax=lim, colorbar=_colorbar(p))
    else:
        maxv = max(float(np.nanmax(v)), 1.0)
        ticks = [t for t in (1, 10, 100, 1_000, 10_000, 100_000, 1_000_000) if t <= maxv * 1.01]
        marker = dict(color=np.log10(v + 1), colorscale=RAMPAS.get(rampa, rampa),
                      cmin=0, cmax=np.log10(maxv + 1),
                      colorbar=_colorbar(p, tickvals=[np.log10(t + 1) for t in ticks], ticktext=[f"{t:,}" for t in ticks]))
    marker["colorbar"]["title"]["text"] = titulo_color
    extension = max(df.lat.max() - df.lat.min(), df.lon.max() - df.lon.min(), 1)
    h = 0.25  # half a cell
    ids = [f"{a:.2f}_{o:.2f}" for a, o in zip(df.lat, df.lon)]
    geojson = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "id": i, "properties": {},
         "geometry": {"type": "Polygon", "coordinates": [[[o - h, a - h], [o - h, a + h], [o + h, a + h],
                                                          [o + h, a - h], [o - h, a - h]]]}}
        for i, a, o in zip(ids, df.lat, df.lon)]}
    z = marker.pop("color")
    fig = go.Figure(go.Choropleth(
        geojson=geojson, locations=ids, z=z, marker_line_width=0, marker_opacity=0.78,
        colorscale=marker["colorscale"], zmin=marker["cmin"], zmax=marker["cmax"], colorbar=marker["colorbar"],
        customdata=np.column_stack([v, df.lat, df.lon]),
        hovertemplate="%{customdata[1]:.2f}°, %{customdata[2]:.2f}°<br><b>%{customdata[0]:,.0f}</b><extra></extra>",
    ))
    pad = max(0.6, extension * 0.08)
    fig.update_geos(
        projection_type="mercator", showcountries=True, countrycolor=p["fronteras"], countrywidth=0.8,
        showcoastlines=True, coastlinecolor=p["fronteras"], coastlinewidth=0.8, showland=True, landcolor=p["tierra"],
        showocean=True, oceancolor=p["oceano"], showlakes=True, lakecolor=p["oceano"], resolution=50,
        showframe=True, framecolor=p["linea"], framewidth=1,
        lataxis_range=[df.lat.min() - pad, df.lat.max() + pad],
        lonaxis_range=[df.lon.min() - pad, df.lon.max() + pad], bgcolor=p["fondo"],
    )
    fig = _layout(fig, alto=540, modo=modo)
    fig.update_layout(margin=dict(t=10, b=10))
    return fig
