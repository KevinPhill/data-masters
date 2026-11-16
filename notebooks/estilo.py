# AI-assisted code (Claude, Anthropic), directed and reviewed by the team. See README: "Use of artificial intelligence".
"""Estilo común de las gráficas de Data Masters: colores, tipografía y ayudas para los ejes.

Al importarlo se aplica el estilo a matplotlib.
"""

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# Tinta y fondo
SURFACE, INK, INK2, MUTED, GRID, EJE = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
GRIS = "#c9c7bf"

# Un color fijo por satélite (igual que en el EDA)
NOMBRE_SAT = {"Terra": "MODIS Terra", "Aqua": "MODIS Aqua", "N": "VIIRS S-NPP", "N20": "VIIRS NOAA-20"}
COLOR_SAT = {"Terra": "#eda100", "Aqua": "#2a78d6", "N": "#eb6834", "N20": "#1baf7a"}

# Un color fijo por modelo y por grupo de entradas
COLOR_MODELO = {"Referencia": MUTED, "LightGBM": "#2a78d6", "Red neuronal": "#eb6834"}
COLOR_GRUPO = {
    "MODIS": "#2a78d6",
    "intensidad": "#eb6834",
    "vecindad y tiempo": "#1baf7a",
    "sol": "#eda100",
    "lugar y fecha": MUTED,
}

MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

plt.rcParams.update({
    "figure.figsize": (11, 4),
    "figure.dpi": 110,
    "figure.constrained_layout.use": True,
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "font.family": ["Arial", "DejaVu Sans"],
    "font.size": 10,
    "text.color": INK,
    "axes.edgecolor": EJE,
    "axes.linewidth": 0.8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 0.6,
    "axes.axisbelow": True,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "axes.titlelocation": "left",
    "axes.titlepad": 10,
    "axes.labelcolor": INK2,
    "axes.labelsize": 9.5,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "xtick.labelcolor": INK2,
    "ytick.labelcolor": INK2,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "lines.linewidth": 2,
    "lines.solid_capstyle": "round",
    "lines.solid_joinstyle": "round",
    "lines.markersize": 6,
    "lines.markeredgewidth": 1.5,
    "lines.markeredgecolor": SURFACE,
    "legend.frameon": False,
    "legend.fontsize": 9,
    "legend.labelcolor": INK2,
})


def _comp(x, d, s):
    return f"{x / d:,.1f}".removesuffix(".0") + s


def compacto(x):
    """1234 -> '1,234' · 12900 -> '12.9K' · 4.2e6 -> '4.2M'."""
    a = abs(x)
    if a >= 1e9:
        return _comp(x, 1e9, "B")
    if a >= 1e6:
        return _comp(x, 1e6, "M")
    if a >= 1e4:
        return _comp(x, 1e3, "K")
    return f"{x:,.0f}"


def _tick(x, d, s):
    """Como _comp pero con hasta 2 decimales, para que 0.25M no se lea como 0.2M."""
    return f"{x / d:,.2f}".rstrip("0").rstrip(".") + s


def eje_numeros(ax, eje="y"):
    """Ticks limpios: completos bajo 10,000; compactos (10K, 2M) si el eje llega más arriba."""
    axis = ax.yaxis if eje == "y" else ax.xaxis
    tope = max(abs(v) for v in (ax.get_ylim() if eje == "y" else ax.get_xlim()))
    if tope >= 1e6:
        f = lambda x, _: _tick(x, 1e6, "M") if x else "0"
    elif tope >= 1e4:
        f = lambda x, _: _tick(x, 1e3, "K") if x else "0"
    else:
        f = lambda x, _: f"{x:,.0f}"
    axis.set_major_formatter(mticker.FuncFormatter(f))


def eje_porcentaje(ax, signo=False):
    """Ticks del eje y como porcentaje: 5% o, con signo, +5% / −5%."""
    formato = (lambda v, _: f"{v:+.0f}%" if v else "0") if signo else (lambda v, _: f"{v:g}%")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(formato))


def titulo(ax, texto, sub=None):
    """Título a la izquierda y, opcional, un subtítulo gris debajo."""
    ax.set_title(texto, pad=22 if sub else 10)
    if sub:
        ax.text(0, 1.015, sub, transform=ax.transAxes, color=INK2, fontsize=9.5, va="bottom")


def titulo_figura(fig, texto):
    fig.suptitle(texto, x=0.01, ha="left", fontweight="bold", fontsize=13)
