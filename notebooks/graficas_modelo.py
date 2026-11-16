# AI-assisted code (Claude, Anthropic), directed and reviewed by the team. See README: "Use of artificial intelligence".
"""Gráficas del notebook 03_modelo.

Cada función recibe datos ya calculados en el notebook y solo dibuja.
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, ListedColormap, Normalize, TwoSlopeNorm
from matplotlib.patches import Patch

from estilo import (COLOR_GRUPO, COLOR_MODELO, COLOR_SAT, GRID, GRIS, INK, INK2, MESES, NOMBRE_SAT,
                    eje_numeros, eje_porcentaje, titulo, titulo_figura)

NOMBRE_VARIABLE = {"detecciones": "Detecciones", "frp": "FRP total (MW)"}

# azul = se queda corto · gris = acierta · rojo = se pasa
DIVERGENTE = LinearSegmentedColormap.from_list("error", ["#184f95", "#6da7ec", "#f0efec", "#ec8a89", "#b8302f"])
# más oscuro = más error
SECUENCIAL = LinearSegmentedColormap.from_list("magnitud", ["#f6dcdb", "#ec8a89", "#d55a58", "#b8302f", "#7f2120"])

# Nombre legible de cada entrada del modelo
ETIQUETA = {
    "terra_dia": "Terra: detecciones de día",
    "terra_noche": "Terra: detecciones de noche",
    "aqua_dia": "Aqua: detecciones de día",
    "aqua_noche": "Aqua: detecciones de noche",
    "terra_frp": "Terra: FRP total",
    "aqua_frp": "Aqua: FRP total",
    "modis_frp_max": "FRP máximo",
    "modis_area_px": "tamaño del píxel",
    "modis_confianza": "confianza media",
    "modis_frac_baja_conf": "% baja confianza",
    "modis_dias": "días con fuego",
    "modis_frac_fijas": "% fuentes fijas",
    "frp_por_det_terra": "Terra: FRP por detección",
    "frp_por_det_aqua": "Aqua: FRP por detección",
    "razon_aqua_terra": "razón Aqua / Terra",
    "frac_noche": "% de noche",
    "modis_vecinos": "fuego en celdas vecinas",
    "modis_mes_anterior": "fuego el mes anterior",
    "modis_mes_siguiente": "fuego el mes siguiente",
    "modis_historico": "promedio histórico del mes",
    "hora_paso_terra": "hora de paso de Terra",
    "hora_paso_aqua": "hora de paso de Aqua",
    "cenit_terra": "ángulo del Sol (Terra)",
    "cenit_aqua": "ángulo del Sol (Aqua)",
    "horas_de_sol": "horas de luz",
    "distancia_sol": "distancia Tierra–Sol",
    "lat": "latitud",
    "lon": "longitud",
    "mes": "mes",
    "noaa20": "¿NOAA-20 o S-NPP?",
}


def prueba(totales, satelites):
    """Total global de cada mes en los años de prueba: lo observado (negro) contra cada modelo.

    totales:   tabla de totales_mensuales()
    satelites: {año: nombre del VIIRS de ese año}
    """
    modelos = [m for m in totales["detecciones"].columns if m != "Observado"]
    fig, axs = plt.subplots(2, len(satelites), figsize=(13, 7.5), sharey="row")
    for fila, variable in enumerate(("detecciones", "frp")):
        for col, (año, satelite) in enumerate(satelites.items()):
            ax, datos = axs[fila, col], totales[variable].loc[año]
            for modelo in modelos:
                ax.plot(datos.index, datos[modelo], color=COLOR_MODELO[modelo], label=modelo)
            ax.plot(datos.index, datos["Observado"], color=INK, lw=2.5, marker="o", markersize=5,
                    label="Observado (VIIRS)")
            ax.set_xticks(range(1, 13), MESES)
            titulo(ax, f"{NOMBRE_VARIABLE[variable]} · {año} ({satelite})")
        axs[fila, 0].set_ylim(bottom=0)
        eje_numeros(axs[fila, 0], "y")
    handles, labels = axs[0, 0].get_legend_handles_labels()
    fig.legend(handles[::-1], labels[::-1], loc="outside lower center", ncol=len(labels))
    titulo_figura(fig, "¿Qué tan bien predice cada modelo lo que vio VIIRS? Años que ningún modelo vio al entrenar")
    plt.show()


def importancia(tabla, grupos):
    """Barras: qué tanto usó LightGBM cada entrada, coloreadas por grupo.

    tabla:  % de importancia por entrada (columnas detecciones y FRP)
    grupos: {grupo: [entradas]}
    """
    grupo_de = {entrada: grupo for grupo, entradas in grupos.items() for entrada in entradas}
    fig, axs = plt.subplots(1, 2, figsize=(13, 8.5))
    for ax, columna in zip(axs, tabla.columns):
        datos = tabla[columna].sort_values()
        ax.barh([ETIQUETA.get(e, e) for e in datos.index], datos, height=0.7,
                color=[COLOR_GRUPO.get(grupo_de.get(e), GRIS) for e in datos.index])
        for y, valor in enumerate(datos):
            ax.text(valor + datos.max() * 0.01, y, f"{valor:.1f}%", va="center", fontsize=8.5, color=INK2)
        ax.set_xlim(0, datos.max() * 1.15)
        ax.xaxis.set_major_formatter(lambda v, _: f"{v:g}%")
        ax.grid(axis="y", visible=False)
        ax.tick_params(axis="y", length=0, labelsize=8.5)
        titulo(ax, f"Para predecir {columna}")
    fig.legend([Patch(color=COLOR_GRUPO[g]) for g in grupos], list(grupos), loc="outside lower center",
               ncol=len(grupos))
    titulo_figura(fig, "¿Qué entradas usa LightGBM? (% de la mejora total que aporta cada una)")
    plt.show()


def deriva(errores, años_prueba):
    """Error del total global de cada mes, 2012–2025, para cada modelo.

    errores: tabla de errores_mensuales() (índice = fecha, columnas = (variable, modelo))
    """
    fig, axs = plt.subplots(2, 1, figsize=(13, 7.5), sharex=True)
    for ax, variable in zip(axs, ("detecciones", "frp")):
        for año in años_prueba:
            ax.axvspan(pd.Timestamp(año, 1, 1), pd.Timestamp(año + 1, 1, 1), color=GRID, alpha=0.7, lw=0)
        ax.axvspan(pd.Timestamp(2022, 1, 1), pd.Timestamp(2026, 1, 1), color=COLOR_SAT["Terra"], alpha=0.12, lw=0)
        for modelo, serie in errores[variable].items():
            ax.plot(serie.index, serie, color=COLOR_MODELO[modelo], lw=1.6, label=modelo)
        ax.axhline(0, color=INK2, lw=1)
        eje_porcentaje(ax, signo=True)
        titulo(ax, f"{NOMBRE_VARIABLE[variable]}: error del total global de cada mes")
    tope = axs[0].get_ylim()[1] + 4  # espacio para las etiquetas
    axs[0].set_ylim(top=tope)
    etiquetas = [(pd.Timestamp(año, 7, 1), "prueba") for año in años_prueba]
    etiquetas.append((pd.Timestamp(2024, 1, 1), "órbitas MODIS corridas\n(no se usó para entrenar)"))
    for x, texto in etiquetas:
        axs[0].text(x, tope, texto, ha="center", va="top", fontsize=9, color=INK2)
    axs[0].legend(loc="lower left", ncol=len(errores["detecciones"].columns))
    titulo_figura(fig, "¿Funciona el modelo cuando las órbitas de MODIS se corren? (+ = predice de más)")
    plt.show()


def mapa_error(bloques, grado):
    """Dos mapas del error fuera de muestra (2012–2021) en bloques de grado × grado.

    bloques: tabla de error_por_bloque()
    """
    def rejilla(valores):
        mapa = np.full((int(180 / grado), int(360 / grado)), np.nan)
        mapa[((bloques.bloque_lat + 90) / grado).astype(int), ((bloques.bloque_lon + 180) / grado).astype(int)] = valores
        return mapa

    paneles = [
        ("sesgo", "Sesgo: cuánto se pasa (+) o se queda corto (−) en el total de 2012–2021",
         DIVERGENTE, TwoSlopeNorm(vcenter=0, vmin=-30, vmax=30), lambda v, _: f"{v:+.0f}%" if v else "0"),
        ("error_mensual", "Error típico de un mes en ese bloque",
         SECUENCIAL, Normalize(0, 60), lambda v, _: f"{v:.0f}%"),
    ]
    fig, axs = plt.subplots(2, 1, figsize=(13, 12))
    for ax, (columna, texto, colores, escala, formato) in zip(axs, paneles):
        extension = dict(origin="lower", extent=(-180, 180, -90, 90), interpolation="nearest")
        ax.imshow(rejilla(np.where(bloques.observado > 0, 1.0, np.nan)), cmap=ListedColormap([GRIS]), **extension)
        imagen = ax.imshow(rejilla(bloques[columna].where(bloques.confiable)), cmap=colores, norm=escala, **extension)
        ax.set_xlim(-180, 180)
        ax.set_ylim(-60, 75)
        ax.grid(False)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.spines[:].set_visible(False)
        barra = fig.colorbar(imagen, ax=ax, shrink=0.7, extend="both", pad=0.01)
        barra.ax.yaxis.set_major_formatter(formato)
        barra.outline.set_visible(False)
        titulo(ax, texto)
    titulo_figura(fig, f"¿Dónde se equivoca el modelo? Bloques de {grado}° · gris = muy poco fuego para medir")
    plt.show()


def antes_y_despues(anual, factor):
    """Promedio mensual de cada año: unir MODIS y VIIRS tal cual (izquierda) contra armonizado (derecha).

    anual:  tabla de serie_armonizada() promediada por año
    factor: {variable: cuántas veces más ve VIIRS que MODIS en los años en que coinciden}
    """
    antes, despues = anual.index <= 2011, anual.index >= 2012
    fig, axs = plt.subplots(2, 2, figsize=(13, 8), sharey="row", sharex=True)
    for fila, variable in enumerate(("detecciones", "frp")):
        sin_armonizar, armonizado = axs[fila]
        observado = anual[f"{variable}_observado"][despues]
        for ax in (sin_armonizar, armonizado):
            ax.plot(observado.index, observado, color=INK, marker="o", markersize=5, label="VIIRS observado")
            ax.axvline(2011.5, color=INK2, lw=1, ls=":")
        sin_armonizar.plot(anual.index[antes], anual[f"{variable}_modis"][antes], color=COLOR_SAT["Aqua"],
                           marker="o", markersize=5, label="MODIS tal cual")
        if abs(factor[variable] - 1) >= 0.2:  # solo se marca el salto si de verdad lo hay
            sin_armonizar.annotate(f"salto falso:\nVIIRS ve {factor[variable]:.1f}× más", xy=(2011.5, observado.iloc[0]),
                                   xytext=(2004.5, observado.max()), fontsize=9.5, color=INK2,
                                   arrowprops=dict(arrowstyle="->", color=INK2, lw=1))
        else:
            sin_armonizar.text(2004, observado.max() * 0.45, f"casi sin salto: aquí MODIS y VIIRS\nya miden parecido "
                               f"({factor[variable]:.2f}×)", fontsize=9.5, color=INK2)
        armonizado.fill_between(anual.index[antes], anual[f"{variable}_min"][antes], anual[f"{variable}_max"][antes],
                                color=COLOR_SAT["Aqua"], alpha=0.2, lw=0, label="rango del 90 %")
        armonizado.plot(anual.index[antes], anual[f"{variable}_estimado"][antes], color=COLOR_SAT["Aqua"],
                        marker="o", markersize=5, label="MODIS armonizado (unidades VIIRS)")
        sin_armonizar.set_ylim(bottom=0)
        eje_numeros(sin_armonizar, "y")
        titulo(sin_armonizar, f"{NOMBRE_VARIABLE[variable]} · sin armonizar")
        titulo(armonizado, f"{NOMBRE_VARIABLE[variable]} · armonizado")
    for ax in axs[1]:
        handles, labels = ax.get_legend_handles_labels()
        ax.legend(handles[::-1], labels[::-1], loc="lower left")
    titulo_figura(fig, "Antes y después: promedio mensual de cada año en todo el mundo")
    plt.show()


def serie(serie, satelite="N20"):
    """Serie armonizada: lo estimado desde MODIS (azul, con su rango del 90 %) y lo que VIIRS observó.

    serie: tabla de serie_armonizada()
    """
    serie = serie.sort_index().asfreq("MS")  # un renglón por mes: los meses que faltan cortan la línea
    fig, axs = plt.subplots(2, 1, figsize=(13, 7.5), sharex=True)
    for ax, variable in zip(axs, ("detecciones", "frp")):
        ax.axvspan(serie.index.min(), pd.Timestamp(2012, 1, 1), color=GRID, alpha=0.5, lw=0)
        ax.fill_between(serie.index, serie[f"{variable}_min"], serie[f"{variable}_max"],
                        color=COLOR_SAT["Aqua"], alpha=0.25, lw=0, label="rango del 90 %")
        ax.plot(serie.index, serie[f"{variable}_estimado"], color=COLOR_SAT["Aqua"], lw=1.6,
                label=f"Estimado desde MODIS (en unidades {NOMBRE_SAT[satelite]})")
        for sat in ("N", "N20"):
            observado = serie[f"{variable}_observado"].where(serie.satelite_observado == sat)
            ax.plot(serie.index, observado, color=COLOR_SAT[sat], lw=1.6, label=f"Observado {NOMBRE_SAT[sat]}")
        ax.set_ylim(bottom=0)
        eje_numeros(ax, "y")
        titulo(ax, NOMBRE_VARIABLE[variable])
    axs[0].text(pd.Timestamp(2007, 1, 1), axs[0].get_ylim()[1], "solo MODIS: aquí el modelo llena el hueco",
                ha="center", va="top", fontsize=9, color=INK2)
    handles, labels = axs[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside lower center", ncol=4)
    titulo_figura(fig, "Serie armonizada: lo que VIIRS habría visto desde 2002")
    plt.show()
