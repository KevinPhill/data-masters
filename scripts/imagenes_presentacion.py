"""Dibuja las imágenes de la presentación a partir de las detecciones de NASA FIRMS (no son imágenes generadas con IA).

Cada imagen es un conteo de puntos de calor por píxel, en escala logarítmica, con una rampa de fuego sobre azul noche:

  portada.jpg        el planeta en proyección ortográfica: todas las detecciones VIIRS (NOAA-20) de 2025
  modis_viirs.jpg    la misma región y los mismos dos meses vistos por MODIS (izquierda) y por VIIRS (derecha)
  mundo_tipos.jpg    el mundo con las detecciones VIIRS (NOAA-20) de 2024–2025, un color por tipo de FIRMS:
                     vegetación (fuego), industria y gas (amarillo), volcanes (blanco) y sobre agua (azul)
  linea_tiempo.svg   los satélites con sus fechas y la serie mundial tal cual y armonizada (data/app/serie_mundial.csv)
  datos.json         las cifras que salen de estas consultas y que cita la presentación

Necesita data/db_nasa.duckdb (scripts/crear_db.py), que se abre en modo de solo lectura, y los mapas de app/static.
Los contornos vienen del TopoJSON público que usa la app.

Uso:  python scripts/imagenes_presentacion.py        (~1 min)   y después   python scripts/presentacion.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import duckdb
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "db_nasa.duckdb"
TOPO = ROOT / "app" / "static" / "topojson" / "world_50m.json"
SERIE = ROOT / "data" / "app" / "serie_mundial.csv"
OUT = ROOT / "docs" / "presentacion" / "fuente" / "img"

ANCHO, ALTO = 3840, 2160                       # las filminas se dibujan a 1920 × 1080 con densidad 2
NOCHE = np.array([3, 8, 24], dtype=float)      # fondo: casi negro, hacia Deep Blue
TIERRA = np.array([9, 24, 62], dtype=float)
# rampa de fuego: Martian Red → Rocket Red → ámbar → amarillo cálido
RAMPA_X = [0.0, 0.12, 0.45, 0.75, 1.0]
RAMPA = np.array([[60, 6, 0], [142, 17, 0], [228, 55, 0], [255, 168, 40], [255, 240, 170]], dtype=float)


# ---------- mapa base ----------
def topo():
    t = json.loads(TOPO.read_text())
    sx, sy = t["transform"]["scale"]
    tx, ty = t["transform"]["translate"]
    arcos = []
    for a in t["arcs"]:
        p = np.cumsum(np.array(a, dtype=float), axis=0)
        arcos.append(np.column_stack([p[:, 0] * sx + tx, p[:, 1] * sy + ty]))
    return t, arcos


def anillo(indices, arcos):
    partes = [arcos[i] if i >= 0 else arcos[~i][::-1] for i in indices]
    return np.concatenate(partes)


def poligonos(obj, arcos):
    """Lista de polígonos; cada uno es una lista de anillos (el primero es el borde, los demás son huecos)."""
    salida = []
    for g in obj["geometries"]:
        if g["type"] == "Polygon":
            salida.append([anillo(r, arcos) for r in g["arcs"]])
        elif g["type"] == "MultiPolygon":
            salida.extend([anillo(r, arcos) for r in pol] for pol in g["arcs"])
    return salida


def mascara_tierra(pols, lon0, lon1, lat0, lat1, w, h):
    im = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(im)
    for pol in pols:
        for k, r in enumerate(pol):
            if r[:, 0].max() < lon0 or r[:, 0].min() > lon1 or r[:, 1].max() < lat0 or r[:, 1].min() > lat1:
                continue
            xy = np.column_stack([(r[:, 0] - lon0) / (lon1 - lon0) * w, (lat1 - r[:, 1]) / (lat1 - lat0) * h])
            d.polygon([tuple(p) for p in xy], fill=255 if k == 0 else 0)
    return np.asarray(im, dtype=float) / 255


def bordes(pols, lon0, lon1, lat0, lat1, w, h, ancho):
    im = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(im)
    for pol in pols:
        for r in pol:
            if r[:, 0].max() < lon0 or r[:, 0].min() > lon1 or r[:, 1].max() < lat0 or r[:, 1].min() > lat1:
                continue
            xy = np.column_stack([(r[:, 0] - lon0) / (lon1 - lon0) * w, (lat1 - r[:, 1]) / (lat1 - lat0) * h])
            d.line([tuple(p) for p in xy], fill=255, width=ancho, joint="curve")
    return np.asarray(im, dtype=float) / 255


# ---------- detecciones ----------
def conteo(con, donde, lon0, lon1, lat0, lat1, w, h):
    """Detecciones por píxel de una rejilla w × h, agregadas en DuckDB."""
    x, y, n = con.execute(f"""
        SELECT CAST(floor((longitude - {lon0}) / {(lon1 - lon0) / w}) AS INTEGER) AS x,
               CAST(floor(({lat1} - latitude) / {(lat1 - lat0) / h}) AS INTEGER) AS y, count(*) AS n
        FROM hotspots
        WHERE {donde} AND longitude >= {lon0} AND longitude < {lon1} AND latitude > {lat0} AND latitude <= {lat1}
        GROUP BY 1, 2""").fetchnumpy().values()
    g = np.zeros((h, w), dtype=float)
    ok = (x >= 0) & (x < w) & (y >= 0) & (y < h)
    g[y[ok], x[ok]] = n[ok]
    return g


def brillo(g, radio, tope):
    """De conteos a 0–1: escala logarítmica más un halo (el mismo conteo, desenfocado)."""
    v = np.log1p(g) / np.log1p(tope)
    halo = np.asarray(Image.fromarray((np.clip(v, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(radio)),
                      dtype=float) / 255
    return np.clip(np.maximum(v, halo * 1.6), 0, 1)


def resplandor(g, sigma, tope):
    """Para fuentes puntuales (un volcán ocupa uno o dos píxeles): el mismo núcleo logarítmico con un resplandor
    gaussiano redondo, escalado para que un píxel aislado conserve su brillo en el centro."""
    v = np.clip(np.log1p(g) / np.log1p(tope), 0, 1)
    return np.clip(np.maximum(v, ndimage.gaussian_filter(v, sigma) * 2 * np.pi * sigma ** 2), 0, 1)


def pintar(fondo, v, rampa=RAMPA):
    """Mezcla la rampa de fuego sobre el fondo: la opacidad crece con el brillo."""
    color = np.stack([np.interp(v, RAMPA_X, rampa[:, k]) for k in range(3)], axis=-1)
    alfa = np.clip(v * 3.2, 0, 1)[..., None]
    return fondo * (1 - alfa) + color * alfa


def guardar(a, nombre, calidad=86):
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(OUT / nombre, quality=calidad, optimize=True, subsampling=0)
    print(f"  {nombre}: {(OUT / nombre).stat().st_size / 1e6:.1f} MB")


# ---------- 1 · portada: el planeta visto desde la órbita ----------
def portada(con, tierra_pols):
    gw, gh = 7200, 3600                                        # rejilla de 0.05°
    g = conteo(con, "sensor = 'VIIRS_NOAA20' AND acq_date BETWEEN '2025-01-01' AND '2025-12-31'", -180, 180, -90, 90, gw, gh)
    total = int(g.sum())
    v = brillo(g, 1.2, np.percentile(g[g > 0], 99.7))
    m = mascara_tierra(tierra_pols, -180, 180, -90, 90, gw, gh)

    radio, cx, cy = 1210, 2700, 1130                           # el globo se sale por la derecha
    lat_c, lon_c = np.radians(4.0), np.radians(-58.0)
    yy, xx = np.mgrid[0:ALTO, 0:ANCHO]
    X, Y = (xx - cx) / radio, (cy - yy) / radio
    r2 = X ** 2 + Y ** 2
    dentro = r2 <= 1
    Z = np.sqrt(np.where(dentro, 1 - r2, 0))
    lat = np.arcsin(np.clip(Y * np.cos(lat_c) + Z * np.sin(lat_c), -1, 1))
    lon = lon_c + np.arctan2(X, Z * np.cos(lat_c) - Y * np.sin(lat_c))
    col = ((np.degrees(lon) + 180) % 360 / 360 * gw).astype(int) % gw
    fil = np.clip(((90 - np.degrees(lat)) / 180 * gh).astype(int), 0, gh - 1)

    sombra = (0.35 + 0.65 * Z)[..., None]                      # el borde del disco se oscurece, como una esfera
    base = NOCHE + (TIERRA - NOCHE) * m[fil, col][..., None] * 1.25
    oceano = np.array([5, 13, 36], dtype=float)
    disco = np.where(m[fil, col][..., None] > 0.5, base, oceano) * sombra
    disco = pintar(disco, v[fil, col])
    im = np.where(dentro[..., None], disco, NOCHE)
    # limbo: una línea fina de atmósfera en el borde
    d = np.sqrt(r2)
    limbo = np.exp(-((d - 1.004) / 0.006) ** 2)[..., None]
    im = im + limbo * np.array([46, 150, 245]) * 0.55
    guardar(im, "portada.jpg")
    return {"portada_detecciones_viirs_2025": total}


# ---------- 2 · la misma región, dos sensores ----------
def modis_viirs(con, tierra_pols, paises_pols):
    lon0, lon1, lat0, lat1 = -93.0, -77.0, 5.0, 23.0           # Centroamérica y el Caribe occidental
    w, h = ANCHO // 2, ALTO
    fechas = "acq_date BETWEEN '2024-03-01' AND '2024-04-30'"
    m = mascara_tierra(tierra_pols, lon0, lon1, lat0, lat1, w, h)
    b = bordes(paises_pols, lon0, lon1, lat0, lat1, w, h, 2)
    fondo = NOCHE + (TIERRA - NOCHE) * m[..., None] + b[..., None] * np.array([18, 40, 90])
    mitades, cifras = [], {}
    for clave, sensor in (("modis", "sensor = 'MODIS'"), ("viirs", "sensor = 'VIIRS_NOAA20'")):
        g = conteo(con, f"{sensor} AND {fechas}", lon0, lon1, lat0, lat1, w, h)
        cifras[clave] = int(g.sum())
        mitades.append(pintar(fondo, brillo(g, 2.2, 6)))
    im = np.concatenate(mitades, axis=1)
    im[:, w - 2:w + 2] = [234, 254, 7]                         # la costura entre los dos sensores
    guardar(im, "modis_viirs.jpg")
    return {"region": "Central America and western Caribbean, 5–23° N, 77–93° W", "periodo": "March–April 2024",
            "modis": cifras["modis"], "viirs": cifras["viirs"], "razon": round(cifras["viirs"] / cifras["modis"], 1)}


# ---------- 4 · el mundo, por tipo de punto de calor ----------
MUNDO = (-180.0, 180.0, -56.0, 78.0)                           # sin la Antártida ni el Ártico alto
TIPOS = [  # (clave, tipo FIRMS, rampa, sigma del resplandor o None para el fuego de vegetación, tope como percentil de
           #  las celdas con puntos). Van en orden de dibujo: lo que cae sobre agua queda debajo de la vegetación.
    ("costa_afuera", 3, np.array([[20, 70, 160], [30, 105, 215], [46, 150, 245], [70, 170, 250], [110, 190, 255]], float),
     1.3, 95),
    ("vegetacion", 0, RAMPA, None, 99.9),
    ("industria_gas", 2, np.array([[70, 80, 0], [150, 165, 0], [234, 254, 7], [245, 255, 120], [250, 255, 200]], float),
     1.1, 99.5),
    ("volcanes", 1, np.array([[200, 200, 210], [235, 235, 240], [255, 255, 255], [255, 255, 255], [255, 255, 255]], float),
     4.0, 50),
]


def mascara_mundo(pols, lon0, lon1, lat0, lat1, w, h):
    """Como mascara_tierra, con dos arreglos para el mapa del mundo entero:
    - los anillos que cruzan el meridiano 180 se desenvuelven y se dibujan a los dos lados (si no, quedan franjas de
      lado a lado);
    - los huecos se resuelven por paridad dentro de cada polígono: en el TopoJSON el anillo de Afro-Eurasia viene
      después del Caspio, como si fuera su hueco."""
    def dibujar(d, r):
        lon = np.degrees(np.unwrap(np.radians(r[:, 0])))
        for dx in ((0.0, -360.0, 360.0) if np.abs(np.diff(r[:, 0])).max(initial=0) > 180 else (0.0,)):
            xy = np.column_stack([(lon + dx - lon0) / (lon1 - lon0) * w, (lat1 - r[:, 1]) / (lat1 - lat0) * h])
            d.polygon([tuple(q) for q in xy], fill=255)

    base = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(base)
    con_huecos = np.zeros((h, w), bool)
    for pol in pols:
        if len(pol) == 1:
            dibujar(d, pol[0])
            continue
        paridad = np.zeros((h, w), bool)
        for r in pol:
            capa = Image.new("L", (w, h), 0)
            dibujar(ImageDraw.Draw(capa), r)
            paridad ^= np.asarray(capa) > 0
        con_huecos |= paridad
    return np.maximum(np.asarray(base, dtype=float) / 255, con_huecos)


def mundo_tipos(con, tierra_pols):
    lon0, lon1, lat0, lat1 = MUNDO
    w = ANCHO
    h = round(w * (lat1 - lat0) / (lon1 - lon0))
    fechas = "sensor = 'VIIRS_NOAA20' AND acq_date BETWEEN '2024-01-01' AND '2025-12-31'"
    m = mascara_mundo(tierra_pols, lon0, lon1, lat0, lat1, w, h)
    im = NOCHE + (TIERRA - NOCHE) * m[..., None]
    cuentas = {}
    for clave, tipo, rampa, sigma, pct in TIPOS:
        # tipo 3 es todo lo que FIRMS ve sobre agua: plataformas en el mar, pero también costas, bahías y lagos
        g = conteo(con, f"{fechas} AND type = {tipo}", lon0, lon1, lat0, lat1, w, h)
        cuentas[clave] = int(g.sum())
        tope = np.percentile(g[g > 0], pct)
        # la vegetación cubre continentes: sin halo y con gamma, para que el centro de África no quede todo blanco
        v = np.clip(np.log1p(g) / np.log1p(tope), 0, 1) ** 1.8 if sigma is None else resplandor(g, sigma, tope)
        im = pintar(im, v, rampa)
    guardar(im, "mundo_tipos.jpg")
    return {"periodo": "2024–2025", "sensor": "VIIRS NOAA-20", "alto_px": h, "limites": list(MUNDO), **cuentas}


# ---------- 3 · línea de tiempo de los satélites y serie mundial ----------
def linea_tiempo():
    filas = list(csv.DictReader(SERIE.open()))
    años = {}
    for f in filas:
        a = int(f["mes"][:4])
        obs = float(f["detecciones_observado"]) if f["detecciones_observado"] else None
        est = float(f["detecciones_estimado"])
        años.setdefault(a, []).append((float(f["detecciones_modis"]), obs if obs is not None else est,
                                       float(f["detecciones_min"]) if obs is None else obs,
                                       float(f["detecciones_max"]) if obs is None else obs, obs is not None))
    serie = []
    for a, v in sorted(años.items()):
        if len(v) < 9:
            continue
        m = np.array([x[:4] for x in v], dtype=float).mean(axis=0)
        con_viirs = sum(x[4] for x in v) > len(v) / 2
        serie.append(dict(año=a, tal_cual=m[1] if con_viirs else m[0], armonizado=m[1], lo=m[2], hi=m[3], viirs=con_viirs))

    W, H = 1728, 720
    x0, x1, a0, a1 = 250, 1690, 2000.0, 2028.0
    X = lambda t: x0 + (t - a0) / (a1 - a0) * (x1 - x0)
    hoy = 2026 + 10.5 / 12
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" class="tiempo">']
    for a in range(2000, 2029, 4):
        s.append(f'<line x1="{X(a):.1f}" y1="20" x2="{X(a):.1f}" y2="{H - 46}" class="t-rejilla"/>'
                 f'<text x="{X(a):.1f}" y="{H - 16}" class="t-eje" text-anchor="middle">{a}</text>')
    # órbitas: una pista por satélite, de su primer dato a hoy; lo que sigue, punteado
    pistas = [("Terra", "MODIS", 2000 + 10 / 12, 2027.0, "data from Nov 2000", "modis", True),
              ("Aqua", "MODIS", 2002 + 6 / 12, 2027.0, "data from Jul 2002", "modis", True),
              ("Suomi NPP", "VIIRS", 2012 + 0.6 / 12, 2026 + 10 / 12, "Jan 2012 → 2 Nov 2026", "viirs", True),
              ("NOAA-20", "VIIRS", 2018.0, a1, "from 2018", "viirs", False),
              ("NOAA-21", "VIIRS", 2022 + 10 / 12, a1, "launched Nov 2022", "viirs", False)]
    for k, (nombre, sensor, ini, fin, nota, clase, termina) in enumerate(pistas):
        y = 52 + k * 50
        s.append(f'<text x="0" y="{y + 7}" class="t-sat">{nombre}</text><text x="150" y="{y + 6}" class="t-sensor">{sensor}</text>')
        s.append(f'<line x1="{X(ini):.1f}" y1="{y}" x2="{X(min(fin, hoy)):.1f}" y2="{y}" class="t-pista t-{clase}"/>')
        if fin > hoy:
            s.append(f'<line x1="{X(hoy):.1f}" y1="{y}" x2="{X(fin):.1f}" y2="{y}" class="t-pista t-{clase} t-futuro"/>')
        s.append(f'<circle cx="{X(ini):.1f}" cy="{y}" r="7" class="t-punto t-{clase}"/>')
        if termina:
            s.append(f'<line x1="{X(fin):.1f}" y1="{y - 12}" x2="{X(fin):.1f}" y2="{y + 12}" class="t-fin"/>')
        s.append(f'<text x="{X(ini) + 16:.1f}" y="{y - 12}" class="t-nota">{nota}</text>')
    s.append(f'<text x="{X(2027.0) - 14:.1f}" y="{52 + 25 + 6}" class="t-alerta" text-anchor="end">MODIS ends in 2027</text>')
    # serie mundial: promedio mensual de cada año
    y_base, y_tope = H - 60, 330
    vmax = max(d["hi"] for d in serie) * 1.05
    Y = lambda v: y_base - v / vmax * (y_base - y_tope)
    xs = lambda d: X(d["año"] + 0.5)
    est = [d for d in serie if not d["viirs"]] + [d for d in serie if d["viirs"]][:1]
    banda = " ".join(f'{xs(d):.1f},{Y(d["hi"]):.1f}' for d in est) + " " + " ".join(f'{xs(d):.1f},{Y(d["lo"]):.1f}' for d in est[::-1])
    s.append(f'<polygon points="{banda}" class="t-banda"/>')
    s.append('<polyline points="' + " ".join(f'{xs(d):.1f},{Y(d["tal_cual"]):.1f}' for d in serie) + '" class="t-talcual"/>')
    s.append('<polyline points="' + " ".join(f'{xs(d):.1f},{Y(d["armonizado"]):.1f}' for d in est) + '" class="t-armonizado"/>')
    for d in serie:
        s.append(f'<circle cx="{xs(d):.1f}" cy="{Y(d["tal_cual"]):.1f}" r="5" class="t-ptc"/>')
    antes = [d for d in serie if not d["viirs"]][-1]
    despues = [d for d in serie if d["viirs"]][0]
    s.append(f'<text x="{xs(antes) - 14:.1f}" y="{Y(antes["tal_cual"]) + 44:.1f}" class="t-rot t-azul" text-anchor="end">MODIS as it is</text>')
    s.append(f'<text x="{X(2003.5):.1f}" y="{Y(est[0]["hi"]) - 16:.1f}" class="t-rot t-fuego">Harmonized, with its range</text>')
    s.append(f'<text x="{xs(despues) + 22:.1f}" y="{Y(despues["tal_cual"]) - 54:.1f}" class="t-rot t-blanco">VIIRS observed</text>')
    s.append(f'<line x1="{X(2012):.1f}" y1="300" x2="{X(2012):.1f}" y2="{y_base}" class="t-2012"/>')
    s.append(f'<text x="0" y="{Y(vmax * 0.5):.1f}" class="t-sensor">World, detections</text><text x="0" y="{Y(vmax * 0.5) + 28:.1f}" class="t-sensor">per month</text>')
    s.append("</svg>")
    (OUT / "linea_tiempo.svg").write_text("\n".join(s), encoding="utf-8")
    return {"mundo_tal_cual_antes": round(antes["tal_cual"]), "mundo_tal_cual_despues": round(despues["tal_cual"]),
            "año_antes": antes["año"], "año_despues": despues["año"]}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    t, arcos = topo()
    tierra_pols = poligonos(t["objects"]["land"], arcos)
    paises_pols = poligonos(t["objects"]["countries"], arcos)
    con = duckdb.connect(str(DB), read_only=True)
    datos = {}
    datos.update(portada(con, tierra_pols))
    datos["modis_viirs"] = modis_viirs(con, tierra_pols, paises_pols)
    datos["mundo_tipos"] = mundo_tipos(con, tierra_pols)
    datos["serie_mundial"] = linea_tiempo()
    (OUT / "datos.json").write_text(json.dumps(datos, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(datos, ensure_ascii=False))


if __name__ == "__main__":
    main()
