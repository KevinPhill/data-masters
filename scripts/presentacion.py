# AI-assisted code (Claude, Anthropic), directed and reviewed by the team. See README: "Use of artificial intelligence".
"""Genera la presentación del proyecto (máximo 7 filminas) en PDF y PPTX.

La fuente está en docs/presentacion/fuente/: slides.html (una <section class="slide"> por filmina, con sus notas del
orador en <aside class="notas">), estilo.css e img/: capturas de la app en inglés y las imágenes que dibuja
scripts/imagenes_presentacion.py con las detecciones de NASA FIRMS (el planeta, MODIS frente a VIIRS, Costa Rica y la
línea de tiempo de los satélites). Las tipografías son las de la app (app/static/fonts). Chrome dibuja cada filmina a
1920 × 1080:

  docs/presentacion/Data_Masters.pdf    una página por filmina, con texto seleccionable y enlaces
  docs/presentacion/Data_Masters.pptx   16:9, cada filmina como imagen a sangre, con notas del orador

Necesita:  pip install playwright python-pptx pypdf   (y Google Chrome, o `playwright install chromium`)

Uso:  python scripts/presentacion.py
      python scripts/presentacion.py --demo https://otra-url.streamlit.app
      python scripts/presentacion.py --equipo "Nombre Uno, Nombre Dos"     # integrantes en la portada
      python scripts/presentacion.py --png carpeta/                         # además guarda cada filmina como PNG

El texto y el diseño de estas filminas se hicieron con asistencia de IA (Claude, de Anthropic); las imágenes son
visualizaciones de datos y capturas de la app, no imágenes generadas. Ver la filmina 7 y la sección "Uso de
inteligencia artificial" del README.
"""

from __future__ import annotations

import argparse
import html
import io
import shutil
import tempfile
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright
from pptx import Presentation
from pptx.util import Emu
from pypdf import PdfReader, PdfWriter

ROOT = Path(__file__).resolve().parents[1]
FUENTE = ROOT / "docs" / "presentacion" / "fuente"
SALIDA = ROOT / "docs" / "presentacion"
DEMO_URL = "https://data-masters.streamlit.app"
EQUIPO = "Kevin Alexander Delgado Phillips"  # integrantes en la portada
TITULO = "Data Masters"
ASUNTO = "NASA Space Apps Challenge 2026 Costa Rica · Harmonization of MODIS and VIIRS Hot Spots"
NOTA_IA = ("Slides written and designed with AI assistance (Claude, Anthropic). Maps and charts are data visualizations "
           "drawn by code from NASA FIRMS detections; no AI-generated images. Short note on slide 7; full disclosure in the README.")
ANCHO, ALTO, MAXIMO = 1920, 1080, 7


def navegador(p):
    try:
        return p.chromium.launch(channel="chrome", headless=True)
    except Exception:
        return p.chromium.launch(headless=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--demo", default=DEMO_URL, help="URL de la demo que aparece en la portada y en el cierre")
    ap.add_argument("--equipo", default=EQUIPO, help="integrantes del equipo, para la portada")
    ap.add_argument("--png", default="", help="carpeta donde guardar además cada filmina como PNG")
    a = ap.parse_args()

    texto = (FUENTE / "slides.html").read_text(encoding="utf-8")
    nombres = [n.strip() for n in a.equipo.split(",") if n.strip()]
    equipo = (f'      <div><span>{"Member" if len(nombres) == 1 else "Members"}</span>'
              f'<a>{html.escape(", ".join(nombres))}</a></div>\n') if nombres else ""
    texto = (texto.replace("{{DEMO_URL}}", html.escape(a.demo))
             .replace("{{DEMO_TEXTO}}", html.escape(a.demo.split("://", 1)[-1].rstrip("/")))
             .replace("{{EQUIPO}}", equipo)
             .replace("{{LINEA_TIEMPO}}", (FUENTE / "img" / "linea_tiempo.svg").read_text(encoding="utf-8")))
    temporal = FUENTE / "_render.html"          # junto a estilo.css e img/, para que las rutas relativas sirvan
    temporal.write_text(texto, encoding="utf-8")
    carpeta = Path(tempfile.mkdtemp(prefix="filminas_"))
    try:
        with sync_playwright() as p:
            b = navegador(p)
            pg = b.new_context(viewport={"width": ANCHO, "height": ALTO}, device_scale_factor=2).new_page()
            pg.goto(temporal.as_uri())
            pg.evaluate("document.fonts.ready")
            pg.wait_for_timeout(500)
            filminas = pg.locator("section.slide")
            n = filminas.count()
            if n > MAXIMO:
                raise SystemExit(f"Hay {n} filminas y el máximo de Space Apps es {MAXIMO}.")
            notas, alt = [], []
            for i in range(n):
                f = filminas.nth(i)
                desborde = f.evaluate("e => e.scrollHeight > e.clientHeight + 1 || e.scrollWidth > e.clientWidth + 1")
                if desborde:
                    print(f"  ojo: el contenido de la filmina {i + 1} se sale del cuadro")
                notas.append(f.locator("aside.notas").text_content().strip())
                alt.append(" ".join(f.evaluate("e => { const c = e.cloneNode(true); c.querySelectorAll('aside').forEach(x => x.remove()); return c.innerText; }").split()))
                f.screenshot(path=str(carpeta / f"filmina_{i + 1}.png"))
                # para el PPTX, JPEG: las filminas llevan imágenes a sangre y en PNG pesarían demasiado
                Image.open(carpeta / f"filmina_{i + 1}.png").convert("RGB").save(
                    carpeta / f"filmina_{i + 1}.jpg", quality=90, subsampling=0, optimize=True)
            pdf = pg.pdf(width=f"{ANCHO}px", height=f"{ALTO}px", print_background=True, prefer_css_page_size=True)
            b.close()
    finally:
        temporal.unlink(missing_ok=True)

    # PDF: mismas páginas, con los metadatos del equipo
    lector = PdfReader(io.BytesIO(pdf))
    if len(lector.pages) != n:
        raise SystemExit(f"El PDF salió con {len(lector.pages)} páginas y hay {n} filminas: algo se desborda.")
    w = PdfWriter(clone_from=lector)
    w.add_metadata({"/Title": TITULO, "/Author": TITULO, "/Subject": ASUNTO, "/Keywords": NOTA_IA, "/Creator": TITULO,
                    "/Producer": TITULO})
    with open(SALIDA / "Data_Masters.pdf", "wb") as f:
        w.write(f)

    # PPTX: cada filmina como imagen a sangre + notas del orador
    prs = Presentation()
    prs.slide_width, prs.slide_height = Emu(12192000), Emu(6858000)
    for i in range(n):
        s = prs.slides.add_slide(prs.slide_layouts[6])
        im = s.shapes.add_picture(str(carpeta / f"filmina_{i + 1}.jpg"), 0, 0, prs.slide_width, prs.slide_height)
        im.name = f"Slide {i + 1}"
        im._element.nvPicPr.cNvPr.set("descr", alt[i])     # texto alternativo: lo que dice la filmina
        s.notes_slide.notes_text_frame.text = notas[i]
    c = prs.core_properties
    c.author = c.last_modified_by = c.title = TITULO
    c.subject, c.keywords, c.comments, c.language = ASUNTO, "NASA FIRMS, MODIS, VIIRS, hot spots, wildfire, gas flaring, volcanoes, Space Apps", NOTA_IA, "en-US"
    prs.save(SALIDA / "Data_Masters.pptx")

    if a.png:
        destino = Path(a.png)
        destino.mkdir(parents=True, exist_ok=True)
        for f in sorted(carpeta.glob("*.png")):
            shutil.copy(f, destino / f.name)
    shutil.rmtree(carpeta, ignore_errors=True)
    print(f"{n} filminas → {SALIDA / 'Data_Masters.pdf'} y {SALIDA / 'Data_Masters.pptx'} (demo: {a.demo})")


if __name__ == "__main__":
    main()
