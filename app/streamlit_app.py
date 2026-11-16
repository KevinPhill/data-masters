# AI-assisted code (Claude, Anthropic), directed and reviewed by the team. See README: "Use of artificial intelligence".
"""Data Masters — Every hot spot on Earth, on one calendar (MODIS + VIIRS harmonized).

NASA Space Apps Challenge 2026 · Costa Rica · Challenge "Harmonization of MODIS and VIIRS Hot Spots".
Data in datos.py, charts in graficas.py, visual components in ui.py and texts (ES/EN) in textos.py.

    streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import html
import os
import sys
import unicodedata
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import alertas as A  # noqa: E402
import datos as D  # noqa: E402
import graficas as G  # noqa: E402
import informe as INF  # noqa: E402
import textos as X  # noqa: E402
import ui  # noqa: E402

# =============================================================================== interface state
ss = st.session_state
for _clave, _valor in {"idioma": "en", "modo": "claro", "presentacion": False, "vista": "armonizado",
                       "capa": "total", "tour_paso": 0}.items():
    ss.setdefault(_clave, _valor)
IDI = ss.idioma if ss.idioma in X.IDIOMAS else "en"
MODO = ss.modo if ss.modo in ("claro", "noche") else "claro"
PRES = bool(ss.presentacion)
MESES_LARGO = X.MESES_LARGO[IDI]
esc = html.escape
st.set_page_config(page_title=X.t("pagina_titulo", IDI), page_icon="🔥", layout="wide", initial_sidebar_state="auto")

# click on the globe: applied before the sidebar widgets are created (afterwards they can no longer change).
# The globe key changes after each click so the selection clears and the same country can be chosen again.
ss.setdefault("globo_n", 0)
_puntos = ((ss.get(f"globo_{ss.globo_n}") or {}).get("selection") or {}).get("points") or []
if _puntos:
    _dato = _puntos[0].get("customdata")
    _nombre = _dato[0] if isinstance(_dato, (list, tuple)) else _dato
    if isinstance(_nombre, str):
        ss.modo_area = "pais"
        ss[f"pais_{IDI}"] = _nombre
        ss.pais_globo = _nombre
    ss.globo_n += 1


def T(clave: str, **kw) -> str:
    return X.t(clave, IDI, **kw)


def ir_a_pais() -> None:
    """Choose a country from the alerts list: applied before the sidebar is created, like the click on the globe."""
    nombre = ss.get("al_ver")
    if nombre:
        ss.modo_area = "pais"
        ss[f"pais_{IDI}"] = nombre
        ss.pais_globo = nombre
    ss.al_ver = None


def mes_nombre(m: int, mayuscula: bool = True) -> str:
    n = MESES_LARGO[m - 1]
    return n.capitalize() if mayuscula else n


def clave_idioma(base: str) -> str:
    """Widget key per language: comboboxes do not re-translate their visible text when the language changes,
    so each language has its own widget and inherits the option chosen in the other."""
    clave = f"{base}_{IDI}"
    if clave not in ss:
        for otro in X.IDIOMAS:
            if ss.get(f"{base}_{otro}") is not None:
                ss[clave] = ss[f"{base}_{otro}"]
                break
    return clave


def orden_alfabetico(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto.casefold()) if not unicodedata.combining(c))


def porcentaje(v: float) -> str:
    if not np.isfinite(v):
        return "—"
    return f"{v:+.0f} %".replace("-", "−")


SUPERINDICE = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")


def cientifica(v: float) -> str:
    """Very large numbers (MSE) as 5.6 × 10⁶; small ones with thousands separators."""
    if not np.isfinite(v):
        return "—"
    if v < 1e5:
        return f"{v:,.0f}"
    exp = int(np.floor(np.log10(v)))
    return f"{v / 10 ** exp:.1f} × 10{str(exp).translate(SUPERINDICE)}"


def compacto(v: float) -> str:
    if not np.isfinite(v):
        return "—"
    if v >= 1e6:
        return f"{v / 1e6:.1f} M"
    if v >= 1e5:
        return f"{v / 1e3:.0f} k"
    return f"{v:,.0f}"


def grafica(fig, **config) -> None:
    """Shows a figure with our own template (not Streamlit's); larger in presentation mode."""
    if PRES:
        fig.update_layout(height=int((fig.layout.height or 380) * 1.3), font_size=16, legend_font_size=16)
    st.plotly_chart(fig, theme=None, width="stretch",
                    config={"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"], **config})


ui.estilos(MODO, PRES)


# =============================================================================== tour for judges
def _ir_paso(n: int) -> None:
    ss.tour_paso = n


def tour() -> None:
    pasos = X.pasos_tour(IDI)

    def cuerpo():
        i = max(0, min(int(ss.tour_paso), len(pasos) - 1))
        st.html(ui.paso_tour(i, len(pasos), pasos[i]["titulo"], pasos[i]["texto"], pasos[i]["mirar"], T))
        c1, _, c3 = st.columns([1, 1, 1])
        c1.button(T("tour_anterior"), icon=":material/arrow_back:", disabled=i == 0, key="tour_ant", width="stretch",
                  on_click=_ir_paso, args=(i - 1,))
        if i < len(pasos) - 1:
            c3.button(T("tour_siguiente"), icon=":material/arrow_forward:", icon_position="right", type="primary",
                      key="tour_sig", width="stretch", on_click=_ir_paso, args=(i + 1,))
        elif c3.button(T("tour_listo"), icon=":material/check:", type="primary", key="tour_fin", width="stretch"):
            st.rerun()

    st.dialog(T("tour_titulo"), width="large")(cuerpo)()


# =============================================================================== top bar
with st.container(horizontal=True, horizontal_alignment="right", vertical_alignment="center", key="barra"):
    if st.button(T("tour_boton"), icon=":material/explore:", key="btn_tour"):
        ss.tour_paso = 0
        tour()
    st.toggle(T("presentacion"), key="presentacion", help=T("presentacion_ayuda"))
    st.segmented_control(T("idioma"), list(X.IDIOMAS), key="idioma", required=True, label_visibility="collapsed",
                         format_func=lambda i: i.upper())
    st.segmented_control(T("modo"), ["claro", "noche"], key="modo", required=True, label_visibility="collapsed",
                         format_func=lambda m: T(f"modo_{m}"))

# First comes the blue band: title, globe and the chosen country's history. The globe is added further down, once
# the sidebar controls exist; everything written after this line goes below the band.
banda = st.container(key="banda")
banda.html(ui.encabezado(T))
contexto_ph = None  # its place is created below the globe
if PRES:
    st.html(ui.pitch(T))


def coordenadas(lat: float, lon: float) -> str:
    oeste = "O" if IDI == "es" else "W"
    return f"{abs(lat):.1f}°{'N' if lat >= 0 else 'S'} {abs(lon):.1f}°{'E' if lon >= 0 else oeste}"


def mostrar_contexto(area: str | None = None, n_celdas: int | None = None, años_sel: tuple | None = None,
                     centro: str | None = None) -> None:
    tel = [(T("tel_area"), area or T("chip_sin_area"))]
    if n_celdas:
        tel.append((T("tel_celdas"), f"{n_celdas:,}"))
    if años_sel:
        tel.append((T("tel_periodo"), f"{años_sel[0]}–{años_sel[1]}"))
    if centro:
        tel.append((T("tel_centro"), centro))
    tel.append((T("tel_sensores"), "MODIS + VIIRS (NASA FIRMS)"))
    if contexto_ph is not None:
        contexto_ph.html(ui.contexto(T, tel))


# =============================================================================== data ready?
if not D.datos_listos():
    st.error(T("faltan_datos"))
    st.markdown(T("faltan_pasos"))
    st.stop()

META = D.meta()
VAL = D.validacion_resumen()
EV, EV_P = D.evaluacion()  # scripts/evaluar_modelos.py
MODELO_APP = EV.get("modelo_app", "lightgbm_corregido")
MODELO_ALT = "razon"
MESES_DF = D.meses()
AÑO_MIN, AÑO_MAX = int(MESES_DF.año.min()), int(MESES_DF.año.max())
N_PAISES = len(D.lista_paises())

_cifras = [("1.5 M", T("imp_n1_t"), T("imp_n1_f"))]
if VAL.get("factor_viirs_modis"):
    _cifras.append((f"{VAL['factor_viirs_modis']:.1f}×", T("imp_n2_t"), T("imp_n2_f")))
_cifras += [(T("imp_n3"), T("imp_n3_t"), T("imp_n3_f")), (f"{N_PAISES}", T("imp_n4_t"), "")]
st.html(ui.por_que_importa(T, _cifras))

# =============================================================================== sidebar
with st.sidebar:
    st.html(ui.marca_lateral(T("app_nombre"), T("lateral_sub")))

    st.html(ui.paso(T("area_titulo")))
    modos = ["pais", "region", "coords"]
    paises = D.lista_paises()
    if not paises:
        modos.remove("pais")
    if ss.get("modo_area") not in modos:
        ss.pop("modo_area", None)
    modo_area = st.radio(T("area_como"), modos, key="modo_area", format_func=lambda m: T(f"area_{m}"),
                         label_visibility="collapsed")

    if modo_area == "pais":
        clave_pais = clave_idioma("pais")
        if ss.get(clave_pais) not in paises:
            ss[clave_pais] = (ss.get("pais_globo") if ss.get("pais_globo") in paises
                              else "Costa Rica" if "Costa Rica" in paises else paises[0])
        pais = st.selectbox(T("pais"), sorted(paises, key=lambda n: orden_alfabetico(X.pais(n, IDI))), key=clave_pais,
                            format_func=lambda n: X.pais(n, IDI))
        ss.pais_globo = pais
    elif modo_area == "region":
        region = st.selectbox(T("region"), list(D.REGIONES), key=clave_idioma("region"),
                              format_func=lambda r: X.region(r, IDI))
    else:
        c1, c2 = st.columns(2)
        lat = c1.number_input(T("latitud"), -90.0, 90.0, 10.5, 0.1, format="%.3f", key="lat")
        lon = c2.number_input(T("longitud"), -180.0, 180.0, -85.4, 0.1, format="%.3f", key="lon")
        radio = st.slider(T("radio_km"), 25, 500, 100, 25, key="radio")

    # hot spot type (FIRMS): vegetation, industry and gas, volcanoes, offshore; "todos" = the sum
    CATS = D.categorias_disponibles()
    if len(CATS) > 1:
        st.html(ui.paso(T("tipo_titulo")))
        tipo = st.radio(T("tipo_titulo"), ["todos", *CATS], key="tipo", format_func=lambda c: T(f"tipo_{c}"),
                        label_visibility="collapsed", help=T("tipo_ayuda"))
    else:
        tipo = "todos"
    CATS_SEL = None if tipo == "todos" else (tipo,)

    # months fetched from FIRMS for this area ("Last few days" tab): extend the period up to today
    id_previo = {"pais": lambda: f"pais:{pais}", "region": lambda: f"region:{region}",
                 "coords": lambda: f"coords:{lat},{lon},{radio}"}[modo_area]()
    ss.setdefault("recientes", {})
    ss.setdefault("recientes_pts", {})
    recientes = ss.recientes.get(id_previo) if not CATS_SEL else None  # near-real-time FIRMS does not include the type
    AÑO_TOPE = max(AÑO_MAX, int(recientes.año.max())) if recientes is not None and len(recientes) else AÑO_MAX
    _ir = ss.pop("_ir_a_mes", None)
    if _ir:
        ss["años"] = (ss.get("años", (AÑO_MIN, AÑO_TOPE))[0], AÑO_TOPE)
        for _i in X.IDIOMAS:
            ss[f"mes_eval_{_i}"] = f"{_ir[0]}-{_ir[1]:02d}"
    if "años" in ss and ss["años"][1] > AÑO_TOPE:  # another area without recent months
        ss["años"] = (min(ss["años"][0], AÑO_TOPE), AÑO_TOPE)

    st.html(ui.paso(T("periodo_titulo")))
    # 2003: first complete year with Terra and Aqua (2000–2002 Terra only, more uncertainty; they can be chosen)
    años = st.slider(T("años_historia"), AÑO_MIN, AÑO_TOPE, (max(AÑO_MIN, 2003), AÑO_TOPE), key="años")
    opciones = MESES_DF[MESES_DF.año.between(*años)]
    claves_mes = [f"{a}-{m:02d}" for a, m in zip(opciones.año, opciones.mes)]
    if recientes is not None:
        claves_mes += [f"{a}-{m:02d}" for a, m in zip(recientes.año, recientes.mes) if años[0] <= a <= años[1]]
    clave_mes = clave_idioma("mes_eval")
    if ss.get(clave_mes) not in claves_mes:
        ss[clave_mes] = claves_mes[-1]
    mes_sel = st.selectbox(T("mes_evaluar"), claves_mes, key=clave_mes,
                           format_func=lambda k: f"{mes_nombre(int(k[5:]))} {k[:4]}")
    año_ref, mes_ref = int(mes_sel[:4]), int(mes_sel[5:])

    st.html(ui.nota(T("nota_armonizacion"), esc(X.metodo(META.get("metodo", "—"), IDI))))
    st.html(ui.nota(None, esc(T("nota_datos", a0=AÑO_MIN, a1=AÑO_MAX))))



RAMPA = "Cividis"  # calendar and map: perceptually uniform and readable with colour blindness


@st.cache_data(show_spinner=False)
def serie_cache(clave: str, filas: tuple, cols: tuple, cats: tuple | None = None) -> pd.DataFrame:
    return D.serie_mensual(pd.DataFrame({"fila": filas, "col": cols}), cats)


@st.cache_data(show_spinner=False)
def composicion_cache(clave: str, filas: tuple, cols: tuple) -> pd.DataFrame:
    return D.composicion(pd.DataFrame({"fila": filas, "col": cols}))


def reparto(c: pd.DataFrame, años: tuple[int, int]) -> str:
    """"96 % vegetation · 3 % industry and gas · …" over the period (only if there is more than one type)."""
    d = c[c.año.between(*años)].groupby("categoria").det.sum()
    if len(d) < 2 or d.sum() <= 0:
        return ""
    d = (100 * d / d.sum()).sort_values(ascending=False)
    return " · ".join(f"{'<1' if v < 1 else f'{v:.0f}'} % {T(f'tipo_{k}').lower()}" for k, v in d.items() if v > 0)


# =============================================================================== model evaluation ("How do we harmonize?" tab)
def comparacion() -> dict:
    """Figures to compare the app's model with LightGBM + correction (all types together), on the test years."""
    m, otro = EV["metricas"][MODELO_APP]["prueba"], EV["metricas"].get("lightgbm_corregido", {}).get("prueba")
    if not otro:
        return {}
    falla = lambda k: int(EV["paises"].get(k, {}).get("no funciona bien", 0))  # noqa: E731
    bien_ = lambda k: int(EV["paises"].get(k, {}).get("bien", 0))  # noqa: E731
    p_app = set(EV_P[(EV_P.modelo == MODELO_APP) & (EV_P.estado == "no funciona bien")].country)
    p_otro = set(EV_P[(EV_P.modelo == "lightgbm_corregido") & (EV_P.estado == "no funciona bien")].country)
    nombres = lambda c: [X.pais(n, IDI) for n in sorted(c, key=lambda n: X.pais(n, IDI))]  # noqa: E731
    # where LightGBM with correction does better (only if the difference shows with one decimal)
    ventajas = [T(f"cmp_err_{n}", a=otro[n]["error_tipico"], b=m[n]["error_tipico"]) for n in ("pais_mes", "pais_año")
                if round(otro[n]["error_tipico"], 1) < round(m[n]["error_tipico"], 1)]
    mse = [T(f"cmp_nivel_{n}") for n in ("celda_mes", "pais_mes", "pais_año") if otro[n]["mse"] < m[n]["mse"]]
    if mse:
        ventajas.append(T("cmp_mse", niveles=unir(mse)))
    nuevos = nombres(p_app - p_otro)
    return dict(r2i=m["celda_mes"]["r2_log"], r2c=otro["celda_mes"]["r2_log"], ei=m["pais_año"]["error_tipico"],
                ec=otro["pais_año"]["error_tipico"], gi=m["mundo_mes"]["error_tipico"], gc=otro["mundo_mes"]["error_tipico"],
                fi=falla(MODELO_APP), fc=falla("lightgbm_corregido"), bi=bien_(MODELO_APP), bc=bien_("lightgbm_corregido"),
                arregla=len(p_otro - p_app), arreglados=unir(nombres(p_otro - p_app)) if p_otro - p_app else "—",
                ventaja=" " + T("cmp_ventaja", donde=unir(ventajas)) if ventajas else "",
                empeora=" " + T("cmp_empeora", paises=unir(nuevos)) if nuevos else "")


def metricas_modelo() -> None:
    """R², MSE and error of the app's model (LightGBM); overfitting of the three models; countries where it does not work well."""
    mr = EV["metricas"][MODELO_APP]
    with st.container(key="tarjeta_metricas"):
        st.html(ui.seccion(T("ev_titulo"), T("ev_sub")))
        filas = []
        for n in ("celda_mes", "pais_mes", "pais_año", "mundo_mes"):
            x = mr["prueba"][n]
            filas.append({T("ev_col_nivel"): T(f"ev_nivel_{n}"), T("ev_col_r2"): f"{x['r2']:.3f}",
                          T("ev_col_r2log"): f"{x['r2_log']:.3f}", T("ev_col_mse"): cientifica(x["mse"]),
                          T("ev_col_rmse"): f"{x['rmse']:,.0f}" if x["rmse"] >= 100 else f"{x['rmse']:.1f}",
                          T("ev_col_err"): f"{x['error_tipico']:.1f} %", T("ev_col_sesgo"): f"{x['sesgo']:+.1f} %"})
        st.html(ui.tabla(pd.DataFrame(filas)))
        st.html(f'<p class="dm-texto dm-texto-tabla">{esc(T("ev_celda", r2=mr["prueba"]["celda_mes"]["r2_log"], r2p=mr["prueba"]["pais_mes"]["r2_log"], r2r=EV["metricas"][MODELO_ALT]["prueba"]["celda_mes"]["r2_log"]))}</p>'
                + ui.nota(None, esc(T("ev_nota"))))

    paises_ev = EV_P[EV_P.modelo == MODELO_APP].set_index("country")
    alt = EV_P[EV_P.modelo == MODELO_ALT].set_index("country")
    with st.container(key="tarjeta_sobreajuste"):
        st.html(ui.seccion(T("sob_titulo"), T("sob_sub")))
        filas, caida, sube = [], 0.0, 0.0
        for clave, s in EV["sobreajuste"].items():
            c, pa = s["celda_mes"], s["pais_año"]
            caida, sube = max(caida, c["caida_r2"]), max(sube, pa["error_prueba"] - pa["error_entrenamiento"])
            filas.append({
                T("sob_col_modelo"): T(f"sob_modelo_{clave}"),
                T("sob_col_param"): T(f"sob_param_{clave}", n=EV["modelos"][clave]["parametros"],
                                      c=EV["modelos"][clave].get("celdas_fijas", 0)),
                T("sob_col_r2"): f"{c['r2_log_entrenamiento']:.3f} → {c['r2_log_prueba']:.3f} → {c['r2_log_nunca_vistos']:.3f}",
                T("sob_col_err"): (f"{pa['error_entrenamiento']:.1f} → {pa['error_prueba']:.1f} → "
                                   f"{pa['error_nunca_vistos']:.1f} %"),
                T("sob_col_ver"): T(f"sob_{s['veredicto']}")})
        st.html(ui.tabla(pd.DataFrame(filas), texto=True))
        if all(s["veredicto"] == "sin_sobreajuste" for s in EV["sobreajuste"].values()):
            crl, cr = paises_ev.error_tipico.get("Costa Rica", np.nan), alt.error_tipico.get("Costa Rica", np.nan)
            extra = f' {T("sob_cr", cr=cr, crl=crl)}' if cr < crl else ""
            st.html(f'<p class="dm-texto dm-texto-tabla">{esc(T("sob_conclusion", caida=caida, sube=sube, **comparacion()) + extra)}</p>')

    with st.container(key="tarjeta_paises"):
        st.html(ui.seccion(T("pai_titulo"), T("pai_sub")))
        cuenta = paises_ev.estado.value_counts()
        if modo_area == "pais" and pais in paises_ev.index:
            f = paises_ev.loc[pais]
            em = T("pai_area_mes", v=f.error_mensual) if np.isfinite(f.error_mensual) else ""
            tend = T("pai_sube" if f.sesgo > 0 else "pai_baja", v=abs(f.sesgo))
            st.html(f'<p class="dm-texto dm-pais-estado dm-estado-{f.estado.replace(" ", "_")}"><b>'
                    + esc(T("pai_area", pais=X.pais(pais, IDI), estado=T(f"pai_estado_{f.estado}"), e=f.error_tipico,
                            em=em, tendencia=tend)) + "</b></p>")
        malos = paises_ev[paises_ev.estado == "no funciona bien"].sort_values("error_tipico", ascending=False)
        bien = paises_ev[paises_ev.estado == "bien"]
        st.html(f'<p class="dm-texto">{esc(T("pai_resumen", n=int(cuenta.drop("pocos datos", errors="ignore").sum()), bien=int(cuenta.get("bien", 0)), regular=int(cuenta.get("regular", 0)), mal=len(malos), pocos=int(cuenta.get("pocos datos", 0))))}</p>'
                + f'<p class="dm-texto dm-texto-tabla">{esc(T("pai_por_que", nf=int((malos.fuentes_fijas >= 10).sum()), mal=len(malos), fr=float(bien.fuentes_fijas.median()), mr=int((alt.estado == "no funciona bien").sum()), **comparacion()))}</p>')

        def pct(v):
            return f"{v:.0f} %" if np.isfinite(v) else "—"
        tabla_malos = pd.DataFrame({
            T("pai_col_pais"): [X.pais(n, IDI) for n in malos.index],
            T("pai_col_año"): [pct(v) for v in malos.error_tipico],
            T("pai_col_mes"): [pct(v) for v in malos.error_mensual],
            T("pai_col_tend"): [T("pai_tend_sube" if v > 0 else "pai_tend_baja", v=abs(v)) for v in malos.sesgo],
            T("pai_col_fijas"): [pct(v) for v in malos.fuentes_fijas],
            T("pai_col_alt"): [pct(alt.error_tipico.get(n, np.nan)) for n in malos.index],
        })
        st.html(ui.tabla(tabla_malos, alto=440))


# =============================================================================== globe + country history (first thing)
def seccion_globo() -> None:
    pais_g = ss.get("pais_globo")
    if pais_g not in paises:
        pais_g = "Costa Rica" if "Costa Rica" in paises else paises[0]
    with banda:
        c1, c2 = st.columns([1.38, 1], gap="large")
        with c1:
            resumen = D.resumen_paises(CATS_SEL)
            st.plotly_chart(G.globo(resumen, pais_g, idioma=IDI, modo="banda", alto=830 if PRES else 680, barra=False),
                            theme=None, width="stretch", key=f"globo_{ss.globo_n}", on_select="rerun",
                            selection_mode="points",
                            config={"displaylogo": False, "displayModeBar": False, "scrollZoom": False,
                                    "topojsonURL": "app/static/topojson/"})
            st.html(ui.escala_fuego(T("globo_hover"), *G.escala_globo(resumen))
                    + f'<p class="dm-pista"><b>{esc(T("globo_pista"))}</b> '
                    f'{esc(T("globo_sub", a0=AÑO_MIN, a1=AÑO_MAX))}</p>')
        with c2:
            celdas_g = D.celdas_pais(pais_g)
            s_g = serie_cache(f"pais:{pais_g}", tuple(celdas_g.fila), tuple(celdas_g.col), CATS_SEL)
            rep_g = reparto(composicion_cache(f"pais:{pais_g}", tuple(celdas_g.fila), tuple(celdas_g.col)), años)
            r = s_g[s_g.año.between(*años)]
            prom = r.det.sum() / (len(r) / 12) if len(r) else np.nan
            por_año = r.groupby("año").agg(det=("det", "mean"), n=("mes", "count"))
            por_año = por_año[por_año.n >= 9]
            cifras, frase = [ui.kpi(T("hist_promedio"), compacto(prom), esc(T("hist_promedio_nota")))], ""
            if CATS_SEL and not prom > 0:
                frase = T("hist_sin_tipo", tipo=T(f"tipo_{tipo}").lower())
            if len(por_año):
                pico, ultimo = int(por_año.det.idxmax()), int(por_año.index[-1])
                cambio = 100 * (por_año.det.iloc[-1] * 12 / prom - 1) if prom > 0 else np.nan
                cifras.append(ui.kpi(T("hist_ultimo", a=ultimo), compacto(por_año.det.iloc[-1] * 12),
                                     ui.delta(cambio, f"{cambio:+.0f} % {T('hist_ultimo_nota')}")))
                if np.isfinite(cambio):
                    clave = ("hist_frase_pico" if ultimo == pico else "hist_frase_igual" if abs(cambio) < 10
                             else "hist_frase_mas" if cambio > 0 else "hist_frase_menos")
                    frase = T(clave, a=ultimo, p=f"{abs(cambio):.0f}", pico=pico)
            factor = G.factor_viirs_modis(s_g)
            cifras.append(ui.kpi(T("hist_factor"), f"{factor:.1f}×" if np.isfinite(factor) else "—",
                                 esc(T("hist_factor_nota"))))
            sub_g = T("hist_sub", a0=años[0], a1=años[1]) + (f" · {T(f'tipo_{tipo}')}" if CATS_SEL else "")
            st.html(ui.ficha_pais(X.pais(pais_g, IDI), sub_g, frase)
                    + ui.kpis(cifras, "dm-kpis-mini")
                    + (f'<p class="dm-reparto">{esc(T("hist_reparto"))} {esc(rep_g)}</p>' if rep_g else ""))
            if prom > 0:  # without points of that type there is no history to draw (the sentence already says so)
                grafica(G.historia_pais(s_g, años, idioma=IDI, modo="banda"))
            st.html(ui.nota(None, esc(T("hist_nota"))))


if paises:
    seccion_globo()
contexto_ph = st.empty()

# =============================================================================== selected area
if modo_area == "pais":
    sel, nombre_area, id_area = D.celdas_pais(pais), X.pais(pais, IDI), f"pais:{pais}"
elif modo_area == "region":
    sel, nombre_area, id_area = D.celdas_caja(*D.REGIONES[region]), X.region(region, IDI), f"region:{region}"
else:
    sel = D.celdas_circulo(lat, lon, radio)
    nombre_area, id_area = T("area_circulo", r=radio, lat=lat, lon=lon), f"coords:{lat},{lon},{radio}"

if sel.empty:
    mostrar_contexto(nombre_area, 0, años)
    st.warning(T("area_vacia"), icon=":material/travel_explore:")
    st.html(ui.pie(T))
    st.stop()
mostrar_contexto(nombre_area, len(sel), años, coordenadas(float(sel.lat.mean()), float(sel.lon.mean())))


if CATS_SEL:  # the area name carries the chosen type (titles, report, downloads)
    nombre_area = f"{nombre_area} · {T(f'tipo_{tipo}')}"
with st.spinner(T("calculando")):
    s = serie_cache(id_area, tuple(sel.fila), tuple(sel.col), CATS_SEL)
    s_todos = serie_cache(id_area, tuple(sel.fila), tuple(sel.col)) if CATS_SEL else s
    comp = composicion_cache(id_area, tuple(sel.fila), tuple(sel.col))
rec = ss.recientes.get(id_area)
if rec is not None and len(rec) and not CATS_SEL:  # FIRMS near-real-time months (source "R"); they have no type
    _n = rec.assign(fuente="R", det_bajo=rec.det, det_alto=rec.det, modis_n=0.0, viirs_n=rec.det,
                    fecha=pd.to_datetime(dict(year=rec.año, month=rec.mes, day=1)), sin_armonizar=rec.det)
    s = pd.concat([s, _n[[*s.columns, "dias", "dias_mes"]]], ignore_index=True)
s_rango = s[s.año.between(*años)]
if CATS_SEL and not (s.det > 0).any():  # no hot spot of this type in the area
    st.info(T("tipo_vacio", tipo=T(f"tipo_{tipo}"), area=nombre_area.split(" · ")[0], a0=AÑO_MIN, a1=AÑO_MAX),
            icon=":material/travel_explore:")
    st.html(ui.pie(T))
    st.stop()


# =============================================================================== status panel
def evaluar_mes(s, año, mes, año0):
    """Same rule as always; returns the level key instead of the text (the texts are in textos.py).
    If the month is in progress (FIRMS near-real-time months), the history is scaled to the days elapsed."""
    fila = s[(s.año == año) & (s.mes == mes)]
    x = float(fila.det.iloc[0]) if len(fila) else np.nan
    frac = 1.0
    if len(fila) and "dias" in s.columns and pd.notna(fila.dias.iloc[0]):
        frac = float(fila.dias.iloc[0]) / float(fila.dias_mes.iloc[0])
    hist = s[(s.mes == mes) & s.año.between(año0, año - 1) & (s.fuente != "R")].det.to_numpy() * frac
    return {**A.clasificar(x, hist, A.MINIMO["mes"]), "frac": frac}  # the same rule as the Alerts tab


ev = evaluar_mes(s, año_ref, mes_ref, años[0])
mes_txt = mes_nombre(mes_ref, mayuscula=False)
Mes_txt = mes_nombre(mes_ref)
fila_ref = s[(s.año == año_ref) & (s.mes == mes_ref)]
fuente_ref = G.NOMBRE_FUENTE.get(fila_ref.fuente.iloc[0], "") if len(fila_ref) else ""
hay_historia = ev["n"] >= 3 and ev["nivel"] != "sin_historia"

if hay_historia:
    razon_txt = (T("alerta_razon", r=ev["razon"]) if np.isfinite(ev["razon"]) else T("alerta_sin_fuego_previo"))
    detalle = T("alerta_detalle", x=f"{ev['x']:,.0f}", razon=esc(razon_txt), mes=esc(mes_txt), a0=años[0],
                a1=año_ref - 1, rank=ev["rank"], n=ev["n"] + 1, fuente=esc(fuente_ref))
    if ev["frac"] < 1:
        detalle += esc(T("alerta_parcial", d=int(fila_ref.dias.iloc[0]), n=int(fila_ref.dias_mes.iloc[0])))
    var_pct = 100 * (ev["x"] / ev["med"] - 1) if ev["med"] > 0 else np.nan
    tarjetas = [
        ui.kpi(T("kpi_este_mes", mes=Mes_txt, año=año_ref), f"{ev['x']:,.0f}",
               ui.delta(var_pct, T("kpi_vs_mediana", v=var_pct)) if np.isfinite(var_pct) else esc(T("kpi_det_viirs"))),
        ui.kpi(T("kpi_mediana"), f"{ev['med']:,.0f}",
               esc(T("kpi_mediana_nota", mes=mes_txt, a0=años[0], a1=año_ref - 1))),
        ui.kpi(T("kpi_percentil"), f"{ev['pct']:.0f}", esc(T("kpi_percentil_nota")),
               extra=ui.medidor(ev["pct"] / 100, "pct", ("0", "50", "100"), T("kpi_percentil"), ev["pct"], 0, 100)),
        ui.kpi(T("kpi_z"), f"{ev['z']:+.1f}", esc(T("kpi_z_nota")),
               extra=ui.medidor((ev["z"] + 4) / 8, "z", ("−4", "0", "+4"), T("kpi_z"), ev["z"], -4, 4)),
    ]
else:
    detalle = esc(T("alerta_sin_historia"))
    valor = f"{ev['x']:,.0f}" if np.isfinite(ev["x"]) else "—"
    tarjetas = [ui.kpi(T("kpi_este_mes", mes=Mes_txt, año=año_ref), valor, esc(T("kpi_det_viirs"))),
                ui.kpi(T("kpi_mediana"), "—"), ui.kpi(T("kpi_percentil"), "—"), ui.kpi(T("kpi_z"), "—")]

def hechos_area(s: pd.DataFrame, años: tuple[int, int]) -> dict:
    """Area facts that show what the analysis is for: the false conclusion it avoids, the season and the
    extreme year. Only complete years with no provisional months."""
    d = s[s.año.between(*años) & (s.fuente != "R")]
    h = {}
    # trend: monthly average of each year with at least 9 valid months (same rule as the country history)
    prom = d.groupby("año").agg(det=("det", "mean"), ing=("sin_armonizar", "mean"), n=("mes", "count"))
    prom = prom[prom.n >= 9]
    antes, despues = prom[prom.index < 2012].head(5), prom[prom.index >= 2013].tail(5)
    full = d.groupby("año").agg(det=("det", "sum"), n=("mes", "count"))
    full = full[full.n == 12]
    if len(antes) >= 3 and len(despues) >= 3 and antes.det.mean() > 0 and antes.ing.mean() > 0:
        h["p0"] = f"{antes.index.min()}–{antes.index.max()}"
        h["p1"] = f"{despues.index.min()}–{despues.index.max()}"
        h["real"] = 100 * (despues.det.mean() / antes.det.mean() - 1)
        h["ingenuo"] = 100 * (despues.ing.mean() / antes.ing.mean() - 1)
    est = d.groupby("mes").det.median()
    if est.sum() > 0:
        top = set(est.sort_values(ascending=False).index[:3])
        pico = int(est.idxmax())
        inicio = pico
        while (inicio - 2) % 12 + 1 in top and (inicio - 2) % 12 + 1 != pico:
            inicio = (inicio - 2) % 12 + 1
        orden = [(inicio - 1 + k) % 12 + 1 for k in range(12)]
        h["temporada"] = [m for m in orden if m in top]
        h["pct"] = float(100 * est[list(top)].sum() / est.sum())
        h["pico"], h["prep"] = pico, (inicio - 2) % 12 + 1
    if len(full) >= 3 and full.det.median() > 0:
        h["año_pico"], h["v_pico"] = int(full.det.idxmax()), float(full.det.max())
        h["r_pico"] = float(full.det.max() / full.det.median())
    return h


def mayuscula(texto: str) -> str:
    return texto[:1].upper() + texto[1:]


def unir(nombres: list[str]) -> str:
    y = " y " if IDI == "es" else " and "
    return nombres[0] if len(nombres) == 1 else ", ".join(nombres[:-1]) + y + nombres[-1]


H = hechos_area(s, años)
hechos_html = []
if "real" in H:
    hechos_html.append((T("imp_tend_t"), T("imp_tend", p0=H["p0"], p1=H["p1"], ni=porcentaje(H["ingenuo"]),
                                           nr=porcentaje(H["real"]))))
else:
    hechos_html.append((T("imp_tend_t"), esc(T("imp_tend_sin"))))
if "temporada" in H:
    hechos_html.append((T("imp_temp_t"), T("imp_temp", meses=esc(mayuscula(unir([mes_nombre(m, False) for m in H["temporada"]]))),
                                           pct=H["pct"], pico=esc(mes_nombre(H["pico"], False)),
                                           prep=esc(mes_nombre(H["prep"], False)))))
if "año_pico" in H:
    hechos_html.append((T("imp_pico_t"), T("imp_pico", año=H["año_pico"], v=f"{H['v_pico']:,.0f}", r=H["r_pico"])))

nivel = ev["nivel"]
frase = T(f"frase_{nivel}", mes=Mes_txt if nivel != "sin_historia" else mes_txt, año=año_ref)
st.html(ui.alerta(T, nivel, frase, T("alerta_titulo", mes=Mes_txt, año=año_ref, area=nombre_area), detalle, tarjetas))

# =============================================================================== tabs
t_al, t_cal, t_imp, t_tend, t_mapa, t_arm, t_nrt, t_datos, t_met = st.tabs(
    [T("tab_alertas"), T("tab_calendario"), T("tab_impacto"), T("tab_tendencias"), T("tab_mapa"), T("tab_armonizacion"),
     T("tab_nrt"), T("tab_descargas"), T("tab_metodo")], key="pestanas")

# =============================================================================== alerts by week or by month
sem = D.serie_semanal(id_area, CATS_SEL)
sem_todos = D.serie_semanal(id_area) if CATS_SEL else sem


def unidades(periodo: str, n: int = 2) -> str:
    return T(f"al_u_{periodo}" + ("" if n == 1 else ("s" if periodo == "semana" else "es")))


def fecha_periodo(f: pd.Timestamp, periodo: str, dia: bool = True) -> str:
    if periodo == "semana":
        return G._fecha_corta(f, IDI) if dia else T("al_la_semana", f=G._fecha_corta(f, IDI))
    return f"{mes_nombre(f.month, False)} {f.year}"


def aviso_alerta(e: dict, periodo: str) -> tuple[str, str]:
    """(level for the colour, sentence) for the end of the window."""
    mes_ = periodo == "mes"
    k = e.get("clave")
    if k == "racha":
        return e["nivel"], T("al_racha_mes" if mes_ else "al_racha", n=e["periodos"], u=unidades(periodo),
                             inicio=fecha_periodo(e["inicio"], periodo), r=e["razon"])
    if k == "pico":
        return "muy_alto", T("al_pico", periodo=fecha_periodo(ultimo.fecha, periodo, dia=False),
                             r=e["ultima"], pct=e["pct"])
    if k == "subiendo":
        return "alto", T("al_subiendo_mes" if mes_ else "al_subiendo",
                         periodo=fecha_periodo(ultimo.fecha, periodo, dia=False), r=e["ultima"],
                         k=A.RACHA[periodo], u=unidades(periodo))
    if k == "termino":
        fin_ep = e["fin"] + pd.Timedelta(days=6) if periodo == "semana" else e["fin"]  # last day of the run
        return "normal", T("al_termino", n=e["periodos"], u=unidades(periodo, e["periodos"]),
                           inicio=fecha_periodo(e["inicio"], periodo), fin=fecha_periodo(fin_ep, periodo))
    if k == "normal":
        if e["nivel"] == "bajo":
            return "bajo", T("al_normal_bajo")
        return "normal", T(f"al_normal_{periodo}", u=f"{min(e['periodos'], A.VENTANA[periodo])} {unidades(periodo)}")
    if k == "sin_historia":
        return "sin_historia", T("al_sin_historia", u=unidades(periodo, 1))
    return "sin_historia", T("al_sin_datos")


with t_al:
    with st.container(key="tarjeta_alertas"):
        st.html(ui.seccion(T("al_titulo")))
        opciones_al = ["semana", "mes"] if sem is not None else ["mes"]
        if len(opciones_al) == 1:  # area without a weekly series: by month, keeping what had been chosen
            ss._al_forzado = ss.get("_al_forzado") or ss.get("al_periodo") != "mes"
            ss.al_periodo = "mes"
        elif ss.pop("_al_forzado", False) or ss.get("al_periodo") not in opciones_al:
            ss.al_periodo = "semana"
        periodo = st.segmented_control(T("al_titulo"), opciones_al, key="al_periodo", required=True,
                                       label_visibility="collapsed", format_func=lambda v: T(f"al_por_{v}"))
        fin_mes = pd.Timestamp(año_ref, mes_ref, 1) + pd.offsets.MonthEnd(0)
        if periodo == "semana":
            base = sem[(sem.fecha >= pd.Timestamp(años[0], 1, 1)) & (sem.fecha <= fin_mes)]
        else:
            base = s[(s.año >= años[0]) & (s.fecha <= fin_mes)].copy()
            if "dias" in base:  # current month fetched from FIRMS: the history is scaled to the days so far
                base["frac"] = (base.dias / base.dias_mes).fillna(1.0)
            base = base[["fecha", "det", *(["frac"] if "frac" in base else [])]]
        n_al = A.niveles(base.reset_index(drop=True), periodo, años[0]) if len(base) else base.assign(nivel=[])
        ep_al = A.episodios(n_al, periodo) if len(n_al) else pd.DataFrame(columns=["alerta"])
        ultimo = n_al.iloc[-1] if len(n_al) else None
        nivel_al, frase_al = aviso_alerta(A.estado(n_al, ep_al, periodo), periodo)
        st.html(f'<p class="dm-aviso dm-nivel-{nivel_al}" aria-live="polite"><i aria-hidden="true"></i>'
                f'{esc(frase_al)}</p>'
                + f'<p class="dm-texto">{esc(T(f"al_sub_{periodo}", area=nombre_area, a0=años[0], mes=mes_txt, año=año_ref))}</p>')
        if sem is None:
            st.html(ui.nota(None, esc(T("al_sin_semanas"))))
        ventana = n_al.tail(A.VENTANA[periodo])
        if len(ventana):
            grafica(G.alertas(ventana, periodo, años[0], idioma=IDI, modo=MODO))
        st.html(ui.nota(None, esc(T("al_regla_mes" if periodo == "mes" else "al_regla", m=A.MINIMO[periodo],
                                    k=A.RACHA[periodo], u=unidades(periodo), m3=3 * A.MINIMO[periodo]))))

    c1, c2 = st.columns([1.15, 1], gap="large")
    with c1, st.container(key="tarjeta_rachas"):
        a_ini = int(n_al[n_al.nivel != "sin_historia"].año.min()) if (n_al.nivel != "sin_historia").any() else años[0]
        st.html(ui.seccion(T("al_ep_titulo", a0=a_ini, a1=año_ref), T("al_ep_sub", u=unidades(periodo))))
        rachas = ep_al[ep_al.alerta].sort_values("inicio", ascending=False).head(10) if len(ep_al) else ep_al
        if len(rachas):
            fin_txt = (lambda f: G._fecha_corta(f + pd.Timedelta(days=6), IDI)) if periodo == "semana" \
                else (lambda f: fecha_periodo(f, "mes"))
            tabla_r = pd.DataFrame({
                T("al_col_desde"): [fecha_periodo(f, periodo) for f in rachas.inicio],
                T("al_col_hasta"): [fin_txt(f) for f in rachas.fin],
                T("al_col_dura"): [f"{int(k)} {unidades(periodo, int(k))}" for k in rachas.periodos],
                T("al_col_det"): rachas.det.round(), T("al_col_normal"): rachas.normal.round(),
                T("al_col_veces"): [f"{r:.1f}×" if np.isfinite(r) else "—" for r in rachas.razon]})
            st.html(ui.tabla(tabla_r))
        else:
            st.info(T("al_ep_ninguna"), icon=":material/check_circle:")
    pm = D.paises_mes(CATS_SEL)
    if len(pm):
        with c2, st.container(key="tarjeta_paises_alerta"):
            st.html(ui.seccion(T("al_pa_titulo", mes=mes_txt, año=año_ref),
                               T("al_pa_sub", m=A.MINIMO["pais"], mes=mes_txt, a0=años[0], a1=año_ref - 1)))
            rk = A.ranking_paises(pm, año_ref, mes_ref, años[0])
            if len(rk):
                st.html(f'<p class="dm-texto">{esc(T("al_pa_n", n=len(rk), k=int((rk.nivel == "muy_alto").sum())))}</p>')
                top_rk = rk.head(12)
                st.html(ui.tabla(pd.DataFrame({
                    T("al_col_pais"): [X.pais(c, IDI) for c in top_rk.country],
                    T("al_col_nivel"): [T(f"esc_{v}") for v in top_rk.nivel],
                    T("al_col_det"): top_rk.x.round(), T("al_col_normal"): top_rk.med.round(),
                    T("al_col_veces"): [f"{r:.1f}×" if np.isfinite(r) else "—" for r in top_rk.razon]})))
                st.selectbox(T("al_pa_ver"), list(rk.country), index=None, key="al_ver", on_change=ir_a_pais,
                             format_func=lambda c: X.pais(c, IDI), placeholder=T("al_pa_ver_ph"))
            else:
                st.info(T("al_pa_ninguno", mes=mes_txt, año=año_ref), icon=":material/check_circle:")

with t_cal:
    with st.container(key="tarjeta_calendario"):
        st.html(ui.seccion(T("cal_titulo"), T("cal_sub", area=nombre_area, a0=años[0], a1=años[1])))
        with st.container(horizontal=True, vertical_alignment="center", gap="medium"):
            vista = st.segmented_control(T("vista"), ["armonizado", "anomalia", "sin_armonizar"], key="vista",
                                         required=True, label_visibility="collapsed",
                                         format_func=lambda v: T(f"vista_{v}"))
            escala_log = st.toggle(T("cal_escala_log"), value=True, key="escala_log", help=T("escala_log_ayuda"),
                                   disabled=vista == "anomalia")
        grafica(G.calendario(s_rango, vista, RAMPA, escala_log, (año_ref, mes_ref), idioma=IDI, modo=MODO))
        _ley = [("estrella", T("cal_leyenda_estrella")), ("punto", T("cal_leyenda_punto"))]
        if (s_rango.fuente == "R").any():
            _ley.append(("anillo", T("cal_leyenda_reciente")))
        st.html(ui.leyenda(_ley + [("cursor", T("cal_leyenda_cursor"))]))

    c1, c2 = st.columns(2, gap="large")
    with c1, st.container(key="tarjeta_criticos"):
        st.html(ui.seccion(T("criticos_titulo"), T("criticos_sub")))
        top = s_rango.nlargest(10, "det")[["año", "mes", "det", "fuente"]]
        tope = float(top.det.max()) if len(top) else 0.0
        st.html(ui.ranking([(f"{mes_nombre(int(m), False)} {int(a)}", f"{d:,.0f}", G.NOMBRE_FUENTE.get(f, f),
                             d / tope if tope > 0 else np.nan)
                            for a, m, d, f in top.itertuples(index=False)]))
    with c2, st.container(key="tarjeta_concentra"):
        st.html(ui.seccion(T("concentra_titulo"), T("concentra_sub")))
        est = s_rango.groupby("mes").det.median()
        parte = (100 * est / est.sum()).round(1)
        temporada = [mes_nombre(m, False) for m in parte.sort_values(ascending=False).index[:3]]
        tarjetas_c = [ui.kpi(T("temporada_pico"), ", ".join(temporada),
                             esc(T("temporada_nota", v=parte.sort_values(ascending=False).iloc[:3].sum())),
                             clase="dm-kpi-texto")]
        años_tot = s_rango.groupby("año").agg(det=("det", "sum"), n=("mes", "count"))
        años_tot = años_tot[años_tot.n == 12]
        if len(años_tot):
            tarjetas_c += [
                ui.kpi(T("año_mas"), str(int(años_tot.det.idxmax())),
                       esc(T("n_detecciones", v=f"{años_tot.det.max():,.0f}"))),
                ui.kpi(T("año_menos"), str(int(años_tot.det.idxmin())),
                       esc(T("n_detecciones", v=f"{años_tot.det.min():,.0f}"))),
            ]
        st.html(ui.kpis(tarjetas_c))

with t_imp:
    with st.container(key="tarjeta_impacto"):
        st.html(ui.seccion(T("imp_titulo")) + f'<p class="dm-texto">{esc(T("imp_intro"))}</p>')
    with st.container(key="tarjeta_imp_area"):
        st.html(ui.seccion(T("imp_area_t", area=nombre_area)) + ui.hechos(hechos_html))
    c1, c2 = st.columns([1.4, 1], gap="large")
    with c1, st.container(key="tarjeta_imp_quien"):
        quien = pd.DataFrame([(T(f"imp_q{i}"), T(f"imp_d{i}"), T(f"imp_w{i}")) for i in range(1, 9)],
                             columns=[T("imp_col_quien"), T("imp_col_decide"), T("imp_col_donde")])
        st.html(ui.seccion(T("imp_quien_t")) + ui.tabla(quien, texto=True))
    with c2, st.container(key="tarjeta_imp_ahora"):
        st.html(ui.seccion(T("imp_ahora_t")) + ui.lista([T(f"imp_ahora_{i}") for i in (1, 2, 3)]))
        st.html(ui.seccion(T("imp_alcance_t"))
                + f'<p class="dm-texto">{esc(T("imp_alcance", n=N_PAISES, a0=AÑO_MIN, a1=AÑO_TOPE))}</p>')
    c1, c2 = st.columns([1.4, 1], gap="large")
    with c1, st.container(key="tarjeta_imp_limites"):
        _e = VAL.get("pais_anual", {}).get("loyo", {}).get("error_tipico", np.nan)
        st.html(ui.seccion(T("imp_limites_t"))
                + ui.lista([T("imp_lim_1"), T("imp_lim_2"), T("imp_lim_3", e=_e), T("imp_lim_4")]))
    with c2, st.container(key="tarjeta_imp_fuentes"):
        st.html(ui.seccion(T("imp_fuentes_t")) + ui.fuentes(X.FUENTES_IMPACTO))

with t_tend:
    c1, c2 = st.columns(2, gap="large")
    with c1, st.container(key="tarjeta_perfil"):
        st.html(ui.seccion(T("perfil_titulo"), T("perfil_sub", año=año_ref)))
        grafica(G.perfil_estacional(s, año_ref, años, idioma=IDI, modo=MODO))
    with c2, st.container(key="tarjeta_anual"):
        st.html(ui.seccion(T("anual_titulo"), T("anual_sub")))
        grafica(G.anual(s, años, idioma=IDI, modo=MODO))
    if comp.categoria.nunique() > 1:
        with st.container(key="tarjeta_composicion"):
            st.html(ui.seccion(T("comp_titulo"), T("comp_sub", area=nombre_area.split(" · ")[0]))
                    + (f'<p class="dm-texto">{esc(T("comp_reparto", a0=años[0], a1=años[1]))} {esc(reparto(comp, años))}</p>'))
            grafica(G.composicion(comp, años, idioma=IDI, modo=MODO))
            st.html(ui.nota(None, esc(T("comp_nota"))))

with t_mapa:
    c1, c2 = st.columns([1, 3], gap="large")
    with c1, st.container(key="tarjeta_mapa_opciones"):
        st.html(ui.seccion(T("mapa_titulo")))
        capa = st.radio(T("mapa_mostrar"), ["total", "anomalia"], key="capa",
                        format_func=lambda c: T("capa_total", a0=años[0], a1=años[1]) if c == "total"
                        else T("capa_anomalia", mes=mes_txt, año=año_ref))
    if capa == "total":
        md = D.mapa_celdas(sel, *años, CATS_SEL)
        fig = G.mapa(md, "det", T("mapa_color_total"), rampa=RAMPA, modo=MODO) if len(md) else None
        nota_mapa = T("mapa_nota_total")
    else:
        md = D.mapa_anomalia_mes(sel, año_ref, mes_ref, años[0], CATS_SEL)
        fig = G.mapa(md, "diferencia", T("mapa_color_anomalia"), divergente=True, modo=MODO) if len(md) else None
        nota_mapa = T("mapa_nota_anomalia", mes=mes_txt, a0=años[0], a1=año_ref - 1)
    with c1:
        st.html(ui.nota(None, esc(nota_mapa)))
    with c2, st.container(key="tarjeta_mapa"):
        if fig:  # borders served from app/static: the map works offline
            grafica(fig, topojsonURL="app/static/topojson/")
        else:
            st.info(T("mapa_vacio"), icon=":material/map:")

with t_arm:
    with st.container(key="tarjeta_arm_intro"):
        st.html(ui.seccion(T("arm_titulo")))
        st.html(f'<p class="dm-texto">{T("arm_texto")}</p>' + ui.sensores(T))
    if EV:
        with st.container(key="tarjeta_modelo"):
            st.html(ui.seccion(T("mod_titulo"))
                    + f'<p class="dm-texto">{esc(T("mod_texto", n=EV["modelos"]["lightgbm"]["parametros"]))}</p>'
                    + '<ol class="dm-lista dm-pasos">' + "".join(
                        f"<li>{esc(T(f'mod_{i}', k=EV['modelos']['factor_global'].get('factor', 4.5), nr=EV['modelos']['razon']['parametros'], c=EV['modelos'].get(MODELO_APP, {}).get('celdas_fijas', 0)))}</li>"
                        for i in range(1, 9)) + "</ol>")
    with st.container(key="tarjeta_antes"):
        st.html(ui.seccion(T("antes_titulo"), T("antes_sub")))
        grafica(G.antes_despues(s, años, idioma=IDI, modo=MODO))
    v_area = D.validacion_area(sel, CATS_SEL)
    err = D.errores_validacion(v_area)
    with st.container(key="tarjeta_validacion"):
        st.html(ui.seccion(T("val_titulo"), T("val_sub")))
        if err:
            def pct(v):
                return "—" if not np.isfinite(v) else (f"{v:.1f} %" if v < 10 else f"{v:.0f} %")
            st.html(ui.kpis([
                ui.kpi(T("val_anual"), pct(err["anual"]), esc(T("val_anual_nota", n=err["años"]))),
                ui.kpi(T("val_mensual"), pct(err["mensual"]), esc(T("val_mensual_nota"))),
                ui.kpi(T("val_modis"), pct(err["modis"]), esc(T("val_modis_nota"))),
                ui.kpi(T("val_dentro"), pct(err["dentro"]), esc(T("val_dentro_nota"))),
            ], "dm-kpis-val"))
            grafica(G.validacion(v_area, idioma=IDI, modo=MODO))
        else:
            st.info(T("val_sin_datos"), icon=":material/query_stats:")
        if VAL:
            st.html(ui.nota(None, esc(T("val_global", paises=VAL["paises"],
                                        pa=VAL["pais_anual"]["loyo"]["error_tipico"],
                                        g=VAL["global_mensual"]["loyo"]["error_tipico"],
                                        pm=VAL["pais_anual"]["loyo"]["error_modis_crudo"],
                                        fa=VAL["pais_anual"]["fuera"]["error_tipico"]))))

    if EV:
        metricas_modelo()

with t_nrt:
    with st.container(key="tarjeta_nrt"):
        st.html(ui.seccion(T("nrt_titulo"), T("nrt_sub")))
        st.html(f'<p class="dm-texto">{esc(T("nrt_texto"))}</p>')
        clave_env = os.environ.get("FIRMS_MAP_KEY", "")
        c1, c2 = st.columns([2, 1])
        map_key = c1.text_input("FIRMS MAP_KEY", value=clave_env, type="password", key="map_key",
                                help=T("nrt_key_ayuda"))
        dias = c2.slider(T("nrt_dias"), 1, 10, 7, key="nrt_dias", disabled=not map_key)
        consultar = st.button(T("nrt_boton") if map_key else T("nrt_boton_publico"), type="primary",
                              icon=":material/satellite_alt:", key="btn_nrt")
    if consultar:
        try:
            with st.spinner(T("nrt_consultando")):
                if map_key:
                    nrt, satelite = D.firms_nrt(map_key, sel, dias)
                else:
                    (nrt, satelite), dias = D.firms_7d(sel), 7
            hoy = date.today()
            # near-real-time FIRMS does not include the source type: it is compared with all hot spots. Normal
            # is the median of the same week of the year (countries and regions) or of the same month, scaled to the days
            if sem_todos is not None:
                _w = sem_todos.fecha.dt.isocalendar().week.clip(upper=52)
                hist = sem_todos[_w == min(hoy.isocalendar().week, 52)].det
                esperado = float(np.median(hist)) / 7 * dias if len(hist) else np.nan
            else:
                hist = s_todos[(s_todos.mes == hoy.month) & (s_todos.fuente.isin(["N", "S", "M"]))].det
                esperado = float(np.median(hist)) / 30.4 * dias if len(hist) else np.nan
            n = len(nrt)
            tarjetas_n = [ui.kpi(T("nrt_det", d=dias), f"{n:,}"),
                          ui.kpi(T("nrt_normal", d=dias, mes=mes_nombre(hoy.month, False)), f"{esperado:,.0f}"
                                 if np.isfinite(esperado) else "—")]
            if esperado and np.isfinite(esperado) and esperado > 0:
                arriba = n > 1.25 * esperado
                tarjetas_n.append(ui.kpi(T("nrt_relacion"), f"{n / esperado:.1f}×",
                                         ui.delta(1 if arriba else 0, T("nrt_arriba") if arriba else T("nrt_normal_bajo"))))
            st.html(ui.kpis(tarjetas_n) + ui.nota(None, esc(T("nrt_satelite", s=satelite))
                                                  + (" " + esc(T("nrt_sin_tipo")) if CATS_SEL else "")))
            if n:
                st.map(nrt.rename(columns={"latitude": "lat", "longitude": "lon"})[["lat", "lon"]], size=800,
                       color="#FF5A1F")
                st.download_button(T("nrt_csv"), nrt.drop(columns=["fila", "col"], errors="ignore").to_csv(index=False)
                                   .encode(), f"datamasters_nrt_{dias}d.csv", "text/csv", icon=":material/download:",
                                   key="dl_nrt")
        except Exception as e:  # noqa: BLE001
            st.error(T("nrt_error", e=e), icon=":material/error:")

    with st.container(key="tarjeta_recientes"):
        st.html(ui.seccion(T("nrt_recientes_t"))
                + f'<p class="dm-texto">{esc(T("nrt_recientes", a=AÑO_MAX, b=AÑO_MAX + 1))}</p>')
        if ss.get("_rec_ok"):
            st.success(ss.pop("_rec_ok"), icon=":material/check_circle:")
        traer = st.button(T("nrt_recientes_boton"), icon=":material/calendar_month:", disabled=not map_key,
                          key="btn_recientes")
        if traer:
            barra = st.progress(0.0, text=T("nrt_trayendo"))
            try:
                meses_r, puntos_r = D.firms_meses_recientes(
                    map_key, sel, date(AÑO_MAX + 1, 1, 1), date.today(),
                    avance=lambda f: barra.progress(min(f, 1.0), text=T("nrt_trayendo")))
                ss.recientes[id_area], ss.recientes_pts[id_area] = meses_r, puntos_r
                ss["_ir_a_mes"] = (int(meses_r.año.iloc[-1]), int(meses_r.mes.iloc[-1]))
                ss["_rec_ok"] = T("nrt_recientes_ok", n=len(meses_r), d=f"{meses_r.det.sum():,.0f}")
                st.rerun()
            except Exception as e:  # noqa: BLE001
                barra.empty()
                st.error(T("nrt_error", e=e), icon=":material/error:")
        elif not map_key:
            st.info(T("nrt_falta_key"), icon=":material/key:")

def metricas_area() -> list[tuple[str, str]]:
    m = [(T("tel_area"), nombre_area), (T("tel_periodo"), f"{años[0]}–{años[1]}"), (T("tel_celdas"), f"{len(sel):,}"),
         (T("tipo_titulo"), T(f"tipo_{tipo}"))]
    if not CATS_SEL and (rep := reparto(comp, años)):
        m.append((T("hist_reparto").rstrip(":"), rep))
    m.append((T("inf_nivel"), f"{Mes_txt} {año_ref}: {T(f'nivel_{nivel}')}"))
    if hay_historia:
        m += [(T("kpi_este_mes", mes=Mes_txt, año=año_ref), f"{ev['x']:,.0f}"),
              (T("kpi_mediana"), f"{ev['med']:,.0f}"), (T("kpi_percentil"), f"{ev['pct']:.0f}"),
              (T("kpi_z"), f"{ev['z']:+.1f}")]
    if "temporada" in H:
        m.append((T("inf_temporada"), f"{unir([mes_nombre(x, False) for x in H['temporada']])} ({H['pct']:.0f} %)"))
    if "real" in H:
        m += [(T("inf_tend_arm"), f"{porcentaje(H['real'])} ({H['p0']} → {H['p1']})"),
              (T("inf_tend_ing"), f"{porcentaje(H['ingenuo'])} ({H['p0']} → {H['p1']})")]
    if "año_pico" in H:
        m.append((T("año_mas"), f"{H['año_pico']} ({H['v_pico']:,.0f})"))
    factor = G.factor_viirs_modis(s)
    if np.isfinite(factor):
        m.append((T("inf_factor"), f"{factor:.1f}×"))
    if err:
        m.append((T("inf_val"), f"{err['anual']:.1f} %"))
    return m


def informe_html() -> str:
    figs = [(T("cal_titulo"), G.calendario(s_rango, "armonizado", RAMPA, escala_log, (año_ref, mes_ref), idioma=IDI)),
            (T("perfil_titulo"), G.perfil_estacional(s, año_ref, años, idioma=IDI)),
            (T("anual_titulo"), G.anual(s, años, idioma=IDI)),
            (T("antes_titulo"), G.antes_despues(s, años, idioma=IDI))]
    if err:
        figs.append((T("val_titulo"), G.validacion(v_area, idioma=IDI)))
    return INF.construir(
        idioma=IDI, titulo=T("inf_titulo", area=nombre_area), evento=f"{T('app_nombre')} · {T('app_evento')}",
        generado=T("inf_generado", f=datetime.now().strftime("%Y-%m-%d %H:%M"), a0=años[0], a1=años[1]),
        frase=frase, detalle=detalle, metricas=metricas_area(), hechos=[f"<b>{esc(t)}:</b> {c}" for t, c in hechos_html],
        figuras=figs, etiquetas=dict(cifras=T("inf_cifras"), metrica=T("inf_metrica"), valor=T("inf_valor"),
                                     hechos=T("imp_area_t", area=nombre_area), graficas=T("inf_graficas"),
                                     metodo=T("met_titulo")),
        metodo=f"{X.metodo(META.get('metodo', ''), IDI)}. {T('met_4')}", credito=T("pie_credito"))


with t_datos:
    st.html(ui.seccion(T("desc_titulo"), nivel=3))
    nombre_archivo = "".join(c if c.isalnum() else "_" for c in orden_alfabetico(nombre_area))[:40].strip("_")
    with st.container(key="tarjeta_desc_informe"):
        st.html(ui.seccion(T("desc_informe"), T("desc_informe_sub")))
        c1, c2 = st.columns(2, gap="large")
        c1.download_button(T("desc_informe_boton"), informe_html, f"datamasters_informe_{nombre_archivo}.html",
                           "text/html", width="stretch", type="primary", icon=":material/description:", key="dl_informe")
        resumen = pd.DataFrame(metricas_area(), columns=[T("inf_metrica"), T("inf_valor")])
        c2.download_button(T("desc_resumen_boton"), resumen.to_csv(index=False).encode(),
                           f"datamasters_resumen_{nombre_archivo}.csv", "text/csv", width="stretch",
                           icon=":material/table_chart:", key="dl_resumen")
        st.html(ui.nota(None, esc(T("desc_png"))))
    c1, c2 = st.columns(2, gap="large")
    with c1, st.container(key="tarjeta_desc_cal"):
        st.html(ui.seccion(T("desc_cal"), T("desc_cal_sub")))
        out = s_rango[["año", "mes", "fuente", "det", "det_bajo", "det_alto", "modis_n", "viirs_n"]].rename(
            columns={"det": "detecciones_armonizadas", "det_bajo": "rango_bajo", "det_alto": "rango_alto",
                     "modis_n": "modis_crudo", "viirs_n": "viirs_crudo"})
        out["fuente"] = out.fuente.map(G.NOMBRE_FUENTE)
        out.insert(3, "tipo", T(f"tipo_{tipo}"))
        st.download_button(T("desc_cal_boton"), out.to_csv(index=False).encode(),
                           f"datamasters_calendario_{tipo}_{años[0]}-{años[1]}.csv", "text/csv", width="stretch",
                           type="primary", icon=":material/download:", key="dl_cal")
        st.html(ui.nota(None, esc(T("desc_ultimos"))) + ui.tabla(out.tail(12), formatos={"año": "{}", "mes": "{}"}))
    with c2, st.container(key="tarjeta_desc_puntos"):
        st.html(ui.seccion(T("desc_puntos"), T("desc_puntos_sub_ca" if D.puntos_solo_centroamerica() else "desc_puntos_sub")))
        if D.db_disponible():
            _hoy = date.today()
            fechas = st.date_input(T("desc_fechas"), (date(años[0], 1, 1), min(date(años[1], 12, 31), _hoy)),
                                   min_value=date(AÑO_MIN, 1, 1), max_value=_hoy, key="desc_rango_fechas")
            f0, f1 = (fechas[0], fechas[-1]) if isinstance(fechas, (list, tuple)) and len(fechas) else (fechas, fechas)
            limite = st.number_input(T("desc_max"), 10_000, 2_000_000, 500_000, 50_000, key="limite")
            if st.button(T("desc_preparar"), width="stretch", icon=":material/database:", key="btn_puntos"):
                with st.spinner(T("desc_consultando")):
                    crudo = D.detecciones_crudas(sel, f0, f1, limite=int(limite))
                    pts = ss.recientes_pts.get(id_area)
                    if pts is not None and len(pts):  # months fetched from FIRMS in near real time
                        pts = pts.assign(acq_date=pd.to_datetime(pts.acq_date).dt.date, sensor="VIIRS")
                        pts = pts[(pts.acq_date >= f0) & (pts.acq_date <= f1)]
                        crudo = pd.concat([crudo, pts[[c for c in crudo.columns if c in pts.columns]]],
                                          ignore_index=True).head(int(limite))
                st.success(T("desc_n", n=f"{len(crudo):,}") + (T("desc_max_alcanzado") if len(crudo) == limite else ""),
                           icon=":material/check_circle:")
                st.download_button(T("desc_puntos_boton"), crudo.to_csv(index=False).encode(),
                                   f"datamasters_puntos_{f0}_{f1}.csv", "text/csv", width="stretch",
                                   type="primary", icon=":material/download:", key="dl_puntos")
                st.html(ui.nota(None, esc(T("desc_primeras")))
                        + ui.tabla(crudo.head(200), formatos={"latitude": "{:.4f}", "longitude": "{:.4f}",
                                                              "frp": "{:.1f}"}, alto=420))
        else:
            st.info(T("desc_sin_db"), icon=":material/database_off:")

with t_met:
    st.html(ui.seccion(T("met_titulo"), nivel=3))
    metodo_txt = esc(X.metodo(META.get("metodo", ""), IDI))
    pasos_met = [(T(f"met_{i}_t"), T(f"met_{i}", metodo=metodo_txt) if i == 3 else T(f"met_{i}")) for i in range(1, 7)]
    st.html(ui.metodo(pasos_met, T("met_pie", generado=META.get("generado", "—"), celdas=f"{META.get('celdas', 0):,}",
                                   filas=f"{META.get('filas', 0):,}")))
    with st.container(key="tarjeta_cobertura"):
        cob = pd.DataFrame([(T(f"cob_{i}"), T(f"cob_{i}_d", b=AÑO_MAX + 1)) for i in range(1, 14)],
                           columns=[T("cob_col_pide"), T("cob_col_donde")])
        st.html(ui.seccion(T("cob_titulo")) + ui.tabla(cob, texto=True))
    g = D.serie_global()
    if g is not None:
        with st.container(key="tarjeta_global"):
            st.html(ui.seccion(T("global_titulo")))
            grafica(G.serie_global(g, idioma=IDI, modo=MODO))
            st.html(ui.nota(None, esc(T("global_nota"))))

st.html(ui.pie(T))
