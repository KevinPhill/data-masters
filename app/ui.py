"""Componentes visuales de Data Masters (HTML): estilos, encabezado, estado del mes, cifras y piezas de contenido.

Las funciones devuelven HTML como texto; la app lo muestra con st.html. Todo texto dinámico pasa por esc().
"""

from __future__ import annotations

import html
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

STATIC = Path(__file__).resolve().parent / "static"
MARCA = STATIC / "marca"
URL_STATIC = "app/static"
RETO = "Harmonization of MODIS and VIIRS Hot Spots"
NIVELES = ("bajo", "normal", "alto", "muy_alto")

esc = html.escape


# =============================================================================== estilos
@lru_cache(maxsize=4)
def _css(_version: float) -> str:
    return (STATIC / "estilo.css").read_text(encoding="utf-8")


def estilos(modo: str, presentacion: bool) -> None:
    """Hoja de estilos global + marcas de modo (noche / presentación) que el CSS lee con :root:has(...).
    Van en el primer elemento de la página para que el tema correcto se aplique desde el primer pintado."""
    marcas = " ".join(c for c, activo in (("dm-modo-noche", modo == "noche"),
                                           ("dm-presentacion", presentacion)) if activo)
    st.html(f"<style>{_css((STATIC / 'estilo.css').stat().st_mtime)}</style>"
            f'<span class="dm-marca-modo {marcas}" aria-hidden="true"></span>')


# =============================================================================== marca
def space_apps_logo() -> str:
    for ext in ("svg", "png"):
        if (MARCA / f"space_apps.{ext}").exists():
            return (f'<img class="dm-pie-logo" src="{URL_STATIC}/marca/space_apps.{ext}" '
                    'alt="NASA Space Apps Challenge" height="40">')
    return ""


# =============================================================================== encabezado
def encabezado(T) -> str:
    """Evento, nombre del proyecto, reto y una frase de qué hace la app (lo primero de la banda del globo)."""
    return f"""
<header class="dm-cab">
  <div class="dm-cab-nombre">
    <p class="dm-cab-evento">{esc(T("app_evento"))}</p>
    <h1>{esc(T("app_nombre"))}</h1>
  </div>
  <div class="dm-cab-texto">
    <p class="dm-cab-reto">{esc(T("app_reto", reto="")).strip()} <b>{RETO}</b></p>
    <p class="dm-cab-lead">{esc(T("app_lead"))}</p>
  </div>
</header>"""


def contexto(T, datos: list[tuple[str, str]]) -> str:
    """Una línea con el área que se está analizando (encima del estado del mes)."""
    filas = "".join(f"<div><dt>{esc(k)}</dt><dd>{esc(v)}</dd></div>" for k, v in datos)
    return f'<dl class="dm-contexto" aria-label="{esc(T("tel_area"))}">{filas}</dl>'


def ficha_pais(nombre: str, sub: str, frase: str) -> str:
    """Cabeza del panel del país junto al globo: nombre, periodo y una frase en lenguaje llano."""
    frase_html = f'<p class="dm-ficha-frase">{esc(frase)}</p>' if frase else ""
    return f'<div class="dm-ficha"><h2>{esc(nombre)}</h2><p class="dm-ficha-sub">{esc(sub)}</p>{frase_html}</div>'


def escala_fuego(titulo: str, rampa: list, marcas: list[tuple[float, str]]) -> str:
    """Escala de color del globo en HTML: barra con la rampa y marcas en su posición (0–1)."""
    degradado = ", ".join(f"{c} {100 * float(x):.0f}%" for x, c in rampa)
    etiquetas = "".join(f'<span style="left:{100 * x:.1f}%">{esc(e)}</span>' for x, e in marcas)
    return (f'<figure class="dm-escala-fuego" aria-label="{esc(titulo)}"><figcaption>{esc(titulo)}</figcaption>'
            f'<i style="background: linear-gradient(90deg, {degradado})"></i><div>{etiquetas}</div></figure>')


def por_que_importa(T, cifras: list[tuple[str, str, str]]) -> str:
    """Franja de cuatro cifras bajo el encabezado: (valor, texto, fuente)."""
    items = "".join(
        f'<li><b class="dm-importa-n">{esc(v)}</b><span>{esc(txt)}</span>'
        + (f"<small>{esc(f)}</small>" if f else "") + "</li>"
        for v, txt, f in cifras)
    return (f'<section class="dm-importa" aria-labelledby="dm-importa-t"><h2 id="dm-importa-t">{esc(T("imp_franja_t"))}</h2>'
            f"<ul>{items}</ul></section>")


def hechos(items: list[tuple[str, str]]) -> str:
    """Tarjetas de texto (título, cuerpo en HTML ya escapado) para los datos del área."""
    return '<div class="dm-hechos">' + "".join(
        f'<div class="dm-hecho"><h4>{esc(t)}</h4><p>{c}</p></div>' for t, c in items) + "</div>"


def lista(items: list[str], clase: str = "") -> str:
    return f'<ul class="dm-lista {clase}">' + "".join(f"<li>{esc(i)}</li>" for i in items) + "</ul>"


def fuentes(items: list[tuple[str, str]]) -> str:
    return '<ol class="dm-fuentes">' + "".join(
        f'<li>{esc(t)} <a href="{esc(u)}" target="_blank" rel="noopener">{esc(u.split("//")[1].split("/")[0])}</a></li>'
        for t, u in items) + "</ol>"


def pitch(T) -> str:
    partes = "".join(f'<p><b>{esc(T(clave + "_t"))}</b>{esc(T(clave))}</p>'
                     for clave in ("pitch_problema", "pitch_solucion", "pitch_impacto"))
    return f'<section class="dm-pitch" aria-label="Pitch">{partes}</section>'


# =============================================================================== panel de estado y cifras
def kpi(etiqueta: str, valor: str, nota: str = "", clase: str = "", extra: str = "") -> str:
    """Una cifra con su etiqueta; `extra` (p. ej. un medidor) va entre el valor y la nota."""
    return (f'<div class="dm-kpi {clase}"><div class="dm-kpi-etq">{esc(etiqueta)}</div>'
            f'<div class="dm-kpi-valor">{esc(valor)}</div>{extra}<div class="dm-kpi-nota">{nota}</div></div>')


def kpis(tarjetas: list[str], clase: str = "") -> str:
    return f'<div class="dm-kpis {clase}">{"".join(tarjetas)}</div>'


def delta(v: float, texto: str) -> str:
    """Cambio con flecha + signo + texto, nunca solo color."""
    if not np.isfinite(v):
        return ""
    clase, flecha = ("dm-delta-sube", "▲") if v > 0 else (("dm-delta-baja", "▼") if v < 0 else ("dm-delta-igual", "■"))
    return f'<span class="dm-delta {clase}">{flecha} {esc(texto)}</span>'


def medidor(pos: float, tipo: str, etiquetas: tuple[str, ...], nombre: str, valor: float,
            vmin: float, vmax: float) -> str:
    """Pista por zonas con una aguja (role="meter"). pos ∈ [0, 1]; tipo elige las zonas: 'pct' o 'z'."""
    if not np.isfinite(pos):
        return ""
    izq = f"{100 * min(max(pos, 0.0), 1.0):.1f}%"
    v = min(max(valor, vmin), vmax)
    ejes = "".join(f"<span>{esc(e)}</span>" for e in etiquetas)
    return (f'<div class="dm-medidor" role="meter" aria-label="{esc(nombre)}" aria-valuenow="{v:.1f}" '
            f'aria-valuemin="{vmin:g}" aria-valuemax="{vmax:g}">'
            f'<div class="dm-medidor-pista dm-medidor-{tipo}"><span class="dm-medidor-marca" style="left:{izq}"></span></div>'
            f'<div class="dm-medidor-ejes" aria-hidden="true">{ejes}</div></div>')


def alerta(T, nivel: str, frase: str, titulo: str, detalle_html: str, tarjetas: list[str]) -> str:
    """Estado del mes: frase, escala de 4 niveles (texto + color) y las cifras."""
    etiqueta = T("escala_lbl", nivel=T(f"nivel_{nivel}"))
    sello = T("escala_lbl", nivel=T(f"esc_{nivel}") if nivel in NIVELES else T(f"nivel_{nivel}"))
    actual = ' class="activo" aria-current="true"'
    escala = "".join(f'<li data-nivel="{n}"{actual if n == nivel else ""}>{esc(T("esc_" + n))}</li>' for n in NIVELES)
    return f"""
<section class="dm-alerta dm-nivel-{nivel}" aria-live="polite">
  <div class="dm-alerta-cab">
    <p class="dm-eyebrow">{esc(titulo)}</p>
    <h2>{esc(frase)}</h2>
    <p class="dm-alerta-detalle">{detalle_html}</p>
  </div>
  <div class="dm-alerta-nivel">
    <p class="dm-sello" aria-hidden="true"><i></i>{esc(sello)}</p>
    <ol class="dm-escala" aria-label="{esc(etiqueta)}">{escala}</ol>
  </div>
  {kpis(tarjetas)}
</section>"""


# =============================================================================== piezas de contenido
def seccion(titulo: str, sub: str | None = None, nivel: int = 3) -> str:
    sub_html = f"<p>{esc(sub)}</p>" if sub else ""
    return f'<div class="dm-seccion"><h{nivel}>{esc(titulo)}</h{nivel}>{sub_html}</div>'


def paso(titulo: str) -> str:
    return f'<p class="dm-paso">{esc(titulo)}</p>'


def marca_lateral(nombre: str, sub: str) -> str:
    return f'<div class="dm-marca-lateral"><strong>{esc(nombre)}</strong><span>{esc(sub)}</span></div>'


def nota(titulo: str | None, texto_html: str, clase: str = "") -> str:
    t = f"<b>{esc(titulo)}:</b> " if titulo else ""
    return f'<p class="dm-nota {clase}">{t}{texto_html}</p>'


GLIFOS = {"estrella": "★", "punto": "●", "anillo": "○", "cursor": "↖"}


def leyenda(items: list[tuple[str, str]]) -> str:
    return '<div class="dm-leyenda">' + "".join(
        f'<span><i class="dm-glifo dm-glifo-{g}" aria-hidden="true">{GLIFOS.get(g, "·")}</i>{esc(txt)}</span>'
        for g, txt in items) + "</div>"


def tabla(df: pd.DataFrame, formatos: dict | None = None, alto: int | None = None, texto: bool = False) -> str:
    """texto=True: celdas con saltos de línea (tablas de frases, no de cifras)."""
    formatos = formatos or {}
    cab = "".join(f'<th scope="col">{esc(str(c))}</th>' for c in df.columns)
    filas = []
    for fila in df.itertuples(index=False):
        celdas = []
        for c, v in zip(df.columns, fila):
            num = isinstance(v, (int, float, np.integer, np.floating)) and not isinstance(v, bool)
            if v is None or (num and not np.isfinite(v)) or (not num and pd.isna(v) is True):
                txt = "—"
            elif c in formatos:
                txt = formatos[c].format(v)
            elif isinstance(v, (float, np.floating)):
                txt = f"{v:,.0f}" if float(v).is_integer() else f"{v:,.2f}"
            else:
                txt = str(v)
            celdas.append(f'<td class="{"num" if num else ""}">{esc(txt)}</td>')
        filas.append("<tr>" + "".join(celdas) + "</tr>")
    estilo = f' style="max-height:{alto}px"' if alto else ""
    clase = "dm-tabla dm-tabla-texto" if texto else "dm-tabla"
    return (f'<div class="dm-tabla-caja" tabindex="0"{estilo}><table class="{clase}"><thead><tr>{cab}</tr></thead>'
            f'<tbody>{"".join(filas)}</tbody></table></div>')


def ranking(filas: list[tuple]) -> str:
    """filas = [(periodo, valor, fuente[, fracción del máximo])] ordenadas de mayor a menor."""
    items = []
    for i, (p, v, f, *resto) in enumerate(filas):
        barra = ""
        if resto and np.isfinite(resto[0]):
            ancho = f"{100 * min(max(resto[0], 0.0), 1.0):.1f}%"
            barra = f'<i class="dm-rank-barra" aria-hidden="true"><i style="width:{ancho}"></i></i>'
        items.append(
            f'<li><b class="dm-rank">{i + 1}</b>'
            f'<span class="dm-rank-periodo"><span>{esc(p)}</span>{barra}</span>'
            f'<span class="dm-rank-valor">{esc(v)}</span><span class="dm-rank-fuente">{esc(f)}</span></li>')
    return f'<ol class="dm-ranking">{"".join(items)}</ol>'


def sensores(T) -> str:
    def bloque(clase, titulo, det):
        return f'<div class="dm-sensor {clase}"><i aria-hidden="true"></i><b>{esc(titulo)}</b><span>{esc(det)}</span></div>'
    return ('<div class="dm-sensores">'
            + bloque("dm-sensor-modis", T("arm_modis"), T("arm_modis_det"))
            + '<div class="dm-sensor-op" aria-hidden="true">+</div>'
            + bloque("dm-sensor-viirs", T("arm_viirs"), T("arm_viirs_det"))
            + '<div class="dm-sensor-op" aria-hidden="true">=</div>'
            + bloque("dm-sensor-final", T("arm_resultado"), T("arm_resultado_det"))
            + "</div>")


def metodo(pasos: list[tuple[str, str]], pie: str) -> str:
    """pasos = [(título, cuerpo_html)]."""
    items = "".join(f'<li class="dm-metodo-paso"><h4><span class="dm-metodo-n">{i + 1}.</span>{esc(t)}</h4><p>{c}</p></li>'
                    for i, (t, c) in enumerate(pasos))
    return f'<ol class="dm-metodo">{items}</ol><p class="dm-nota">{esc(pie)}</p>'


def paso_tour(i: int, n: int, titulo: str, texto: str, mirar: str, T) -> str:
    return f"""
<div class="dm-tour">
  <span class="dm-tour-n">{esc(T("tour_paso", i=i + 1, n=n))}</span>
  <h3>{esc(titulo)}</h3>
  <p>{esc(texto)}</p>
  <p class="dm-tour-mirar"><b>{esc(T("tour_mirar"))}:</b> {esc(mirar)}</p>
</div>"""


def pie(T) -> str:
    return f'<footer class="dm-pie"><p>{esc(T("pie_credito"))}</p>{space_apps_logo()}</footer>'
