# AI-assisted code (Claude, Anthropic), directed and reviewed by the team. See README: "Use of artificial intelligence".
"""Informe descargable del área: analíticas y gráficas en un solo archivo HTML.

Plotly va incluido una sola vez dentro del archivo, así que el informe se abre y se puede explorar sin internet.
"""

from __future__ import annotations

import html

import plotly.graph_objects as go

esc = html.escape

ESTILO = """
:root { color-scheme: light; }
body { margin: 0; background: #FFFFFF; color: #07173F; font: 16px/1.55 "Overpass", system-ui, -apple-system,
  "Segoe UI", sans-serif; }
h1, h2, h3 { font-family: "Fira Sans", "Overpass", system-ui, sans-serif; }
main { max-width: 1040px; margin: 0 auto; padding: 40px 24px 56px; }
.evento { margin: 0 0 6px; font-size: .9rem; color: #5A6680; }
h1 { margin: 0; font-size: 2.2rem; line-height: 1.1; }
.generado { margin: 6px 0 28px; color: #5A6680; font-size: .92rem; }
.estado { padding: 22px 24px; background: #F3F6FB; border-left: 4px solid #E43700; border-radius: 8px; margin: 0 0 30px; }
.estado h2 { margin: 0 0 8px; font-size: 1.5rem; line-height: 1.25; }
.estado p { margin: 0; color: #3D4B66; }
h2.sec { margin: 34px 0 10px; font-size: 1.3rem; }
h3 { margin: 26px 0 4px; font-size: 1.08rem; }
table { width: 100%; border-collapse: collapse; font-size: .95rem; }
th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid #E3E8F1; vertical-align: top; }
th { color: #5A6680; font-weight: 600; border-bottom-color: #C9D2E1; }
td.v { font-variant-numeric: tabular-nums; font-weight: 600; }
.hechos p { margin: 0 0 10px; color: #3D4B66; }
.pie { margin-top: 40px; padding-top: 14px; border-top: 1px solid #E3E8F1; font-size: .85rem; color: #5A6680; }
@media (max-width: 640px) { main { padding: 24px 16px 40px; } h1 { font-size: 1.7rem; } }
"""


def construir(*, idioma: str, titulo: str, evento: str, generado: str, frase: str, detalle: str,
              metricas: list[tuple[str, str]], hechos: list[str], figuras: list[tuple[str, go.Figure]],
              etiquetas: dict[str, str], metodo: str, credito: str) -> str:
    """`detalle` y `hechos` llegan como HTML ya escapado; el resto es texto plano."""
    filas = "".join(f'<tr><td>{esc(k)}</td><td class="v">{esc(v)}</td></tr>' for k, v in metricas)
    graficas = []
    for i, (nombre, fig) in enumerate(figuras):
        fig = go.Figure(fig)
        fig.update_layout(height=max(int(fig.layout.height or 380), 360))
        graficas.append(f"<h3>{esc(nombre)}</h3>" + fig.to_html(
            full_html=False, include_plotlyjs=(i == 0), config={"displaylogo": False, "responsive": True}))
    return f"""<!doctype html>
<html lang="{idioma}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(titulo)}</title>
<style>{ESTILO}</style>
</head>
<body><main>
<p class="evento">{esc(evento)}</p>
<h1>{esc(titulo)}</h1>
<p class="generado">{esc(generado)}</p>
<section class="estado"><h2>{esc(frase)}</h2><p>{detalle}</p></section>
<h2 class="sec">{esc(etiquetas["cifras"])}</h2>
<table><thead><tr><th>{esc(etiquetas["metrica"])}</th><th>{esc(etiquetas["valor"])}</th></tr></thead>
<tbody>{filas}</tbody></table>
<h2 class="sec">{esc(etiquetas["hechos"])}</h2>
<div class="hechos">{"".join(f"<p>{h}</p>" for h in hechos)}</div>
<h2 class="sec">{esc(etiquetas["graficas"])}</h2>
{"".join(graficas)}
<h2 class="sec">{esc(etiquetas["metodo"])}</h2>
<p>{esc(metodo)}</p>
<p class="pie">{esc(credito)}</p>
</main></body></html>"""
