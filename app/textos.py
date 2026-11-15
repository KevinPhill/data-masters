"""Textos de la interfaz en español e inglés.

Uso: t("clave", "es", **valores). Si una clave falta en un idioma se usa el español.
"""

from __future__ import annotations

import json
from pathlib import Path

IDIOMAS = ("es", "en")

MESES_LARGO = {
    "es": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
           "noviembre", "diciembre"],
    "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
           "November", "December"],
}
MESES_CORTO = {
    "es": ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"],
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
}

REGIONES_EN = {
    "Guanacaste (Costa Rica)": "Guanacaste (Costa Rica)",
    "Zona Norte (Costa Rica)": "Northern Zone (Costa Rica)",
    "Centroamérica": "Central America",
    "Península de Yucatán": "Yucatán Peninsula",
    "Amazonía brasileña (arco de deforestación)": "Brazilian Amazon (arc of deforestation)",
    "Cerrado (Brasil)": "Cerrado (Brazil)",
    "Chaco (Bolivia–Paraguay–Argentina)": "Chaco (Bolivia–Paraguay–Argentina)",
    "California (EE. UU.)": "California (USA)",
    "Sudeste asiático continental": "Mainland Southeast Asia",
    "Sahel occidental": "Western Sahel",
    "Australia septentrional": "Northern Australia",
    "Siberia oriental": "Eastern Siberia",
}

METODOS_EN = {
    "Integral: vegetación con LightGBM + corrección regional; volcanes, industria y gas, y costa afuera con un modelo "
    "por celda → detecciones VIIRS":
        "Integral: vegetation with LightGBM + regional correction; volcanoes, industry and gas, and offshore with a "
        "per-cell model → VIIRS detections",
    "LightGBM (notebook 03_modelo) + corrección regional: 28 entradas → detecciones VIIRS NOAA-20":
        "LightGBM (notebook 03_modelo) + regional correction: 28 inputs → VIIRS NOAA-20 detections",
    "LightGBM (notebook 03_modelo): 28 entradas → detecciones VIIRS NOAA-20":
        "LightGBM (notebook 03_modelo): 28 inputs → VIIRS NOAA-20 detections",
    "Referencia: MODIS × razón VIIRS/MODIS por región de 10° y mes (2012–2021)":
        "Reference: MODIS × VIIRS/MODIS ratio by 10° region and month (2012–2021)",
}

ES = {
    # ---------------------------------------------------------------- marca y encabezado
    "app_nombre": "Data Masters",
    "app_lead": "MODIS (desde 2000) y VIIRS (desde 2012) cuentan el fuego de forma distinta. Los unimos en una "
                "sola serie de 25 años, comparable en todo el mundo, para saber si este mes hubo más fuego de lo "
                "normal.",
    "app_evento": "NASA Space Apps Challenge 2026 · Costa Rica",
    "app_reto": "Reto: {reto}",
    "chip_sin_area": "Elige un área",
    "tel_area": "Área",
    "tel_celdas": "Celdas 0.5°",
    "tel_periodo": "Periodo",
    "tel_sensores": "Sensores",
    "tel_centro": "Centro",
    "esc_bajo": "Bajo",
    "esc_normal": "Normal",
    "esc_alto": "Alto",
    "esc_muy_alto": "Muy alto",
    "escala_lbl": "Nivel: {nivel}",
    # ---------------------------------------------------------------- barra superior
    "tour_boton": "Tour para jueces",
    "presentacion": "Modo presentación",
    "presentacion_ayuda": "Oculta la barra lateral, agranda textos y gráficas y muestra el pitch.",
    "idioma": "Idioma",
    "modo": "Apariencia",
    "modo_claro": ":material/light_mode: Claro",
    "modo_noche": ":material/dark_mode: Noche",
    # ---------------------------------------------------------------- pitch
    "pitch_problema_t": "El problema",
    "pitch_problema": "Unir MODIS (desde 2000) y VIIRS (desde 2012) tal cual crea un salto falso: "
                      "parece que el fuego aumentó de golpe en 2012, pero solo cambió el satélite.",
    "pitch_solucion_t": "Nuestra solución",
    "pitch_solucion": "Armonizamos 25 años de puntos de calor en una sola unidad (detecciones equivalentes "
                      "a VIIRS), con su rango de incertidumbre, en celdas de 0.5° para todo el mundo.",
    "pitch_impacto_t": "El impacto",
    "pitch_impacto": "Bomberos, salud pública y gestores de territorio saben en 5 segundos si este mes es normal "
                     "en su zona, cuándo prepararse y si la prevención funciona. El humo de estos fuegos se asocia a "
                     "1.5 millones de muertes al año en el mundo (The Lancet, 2024).",
    # ---------------------------------------------------------------- barra lateral
    "lateral_sub": "MODIS + VIIRS armonizados · NASA FIRMS",
    "area_titulo": "Área de interés",
    "area_como": "¿Cómo eliges el área?",
    "area_pais": "País",
    "area_region": "Región de ejemplo",
    "area_dibujar": "Dibujar en el mapa",
    "area_coords": "Coordenadas",
    "pais": "País",
    "region": "Región",
    "latitud": "Latitud",
    "longitud": "Longitud",
    "radio_km": "Radio (km)",
    "dibuja_info": "Dibuja un rectángulo o polígono en el mapa de la derecha.",
    "periodo_titulo": "Periodo",
    "tipo_titulo": "Tipo de punto de calor",
    "tipo_ayuda": "FIRMS clasifica cada detección: vegetación (incendios y quemas), industria y gas (quema de gas "
                  "en pozos, refinerías, siderúrgicas), volcanes y costa afuera (plataformas en el mar). Todos = la "
                  "suma.",
    "tipo_todos": "Todos",
    "tipo_veg": "Vegetación",
    "tipo_industria": "Industria y gas",
    "tipo_volcan": "Volcanes",
    "tipo_mar": "Costa afuera",
    "tipo_vacio": "En {area} no hay puntos de calor de tipo «{tipo}» entre {a0} y {a1}. Elige otro tipo o «Todos» "
                  "en el panel lateral.",
    "años_historia": "Años de historia",
    "mes_evaluar": "Mes a evaluar",
    "visual_titulo": "Visualización",
    "rampa": "Rampa de color (apta para daltonismo; se recomienda Cividis)",
    "escala_log": "Escala logarítmica",
    "escala_log_ayuda": "Hace visibles los meses con poco fuego junto a los picos.",
    "nota_armonizacion": "Armonización",
    "nota_datos": "Datos: NASA FIRMS · MODIS C6.1, VIIRS S-NPP y NOAA-20 · celdas de 0.5° · {a0}–{a1}",
    # ---------------------------------------------------------------- área
    "area_circulo": "{r} km alrededor de {lat:.2f}, {lon:.2f}",
    "area_dibujada": "Área dibujada",
    "dibuja_titulo": "Dibuja tu área de interés",
    # ---------------------------------------------------------------- globo
    "globo_sub": "Promedio anual {a0}–{a1}, en detecciones equivalentes a VIIRS.",
    "globo_hover": "detecciones / año",
    "globo_pista": "Toca un país para ver su historia · arrastra para girar el globo.",
    "hist_sub": "Historia del fuego, {a0}–{a1}",
    "hist_reparto": "Qué se detecta:",
    "hist_sin_tipo": "Aquí no hay puntos de calor de {tipo} en el periodo.",
    "hist_frase_mas": "En {a} hubo {p} % más fuego que en un año típico. Su peor año fue {pico}.",
    "hist_frase_menos": "En {a} hubo {p} % menos fuego que en un año típico. Su peor año fue {pico}.",
    "hist_frase_igual": "{a} fue un año típico. Su peor año fue {pico}.",
    "hist_frase_pico": "{a} fue su peor año: {p} % más fuego que en un año típico.",
    "hist_promedio": "Promedio anual",
    "hist_pico": "Año pico",
    "hist_ultimo": "En {a}",
    "hist_promedio_nota": "detecciones armonizadas",
    "hist_pico_nota": "{v} detecciones / mes",
    "hist_ultimo_nota": "vs. promedio",
    "hist_factor": "VIIRS ÷ MODIS",
    "hist_factor_nota": "meses con los dos sensores",
    "hist_arm": "Armonizado",
    "hist_modis": "MODIS tal cual",
    "hist_viirs": "VIIRS observado",
    "hist_estimado": "estimado desde MODIS",
    "hist_entra_viirs": "entra VIIRS",
    "hist_nota": "Promedio mensual de cada año (mínimo 9 meses). Punto lleno: visto por VIIRS. Punto hueco: "
                 "estimado desde MODIS; la banda es su rango.",
    "dibuja_usa": "Usa las herramientas ▭ o ⬠ del mapa para dibujar. El análisis aparecerá abajo.",
    "area_vacia": "En esta área no hay celdas con detecciones de fuego. Prueba con un área más grande.",
    "faltan_datos": "Faltan los datos de la app (carpeta `data/app`).",
    "faltan_pasos": "1. Corre el notebook `notebooks/03_modelo.ipynb` hasta la sección 2 "
                    "(crea `data/modelo/celdas_0.5.parquet`).\n2. En la terminal: `python scripts/preparar_app.py`\n"
                    "3. Recarga esta página.",
    "calculando": "Calculando la serie del área…",
    # ---------------------------------------------------------------- alerta
    "nivel_muy_alto": "Muy por encima de lo normal",
    "nivel_alto": "Por encima de lo normal",
    "nivel_normal": "Dentro de lo normal",
    "nivel_bajo": "Por debajo de lo normal",
    "nivel_sin_historia": "Sin historia suficiente",
    "frase_muy_alto": "{mes} {año} está muy por encima de lo normal en esta zona.",
    "frase_alto": "{mes} {año} está por encima de lo normal.",
    "frase_normal": "{mes} {año} está dentro de lo normal.",
    "frase_bajo": "{mes} {año} está por debajo de lo normal: hubo menos fuego que de costumbre.",
    "frase_sin_historia": "Sin comparación todavía: hacen falta al menos 3 años anteriores de {mes}.",
    "tab_alertas": "Alertas",
    "al_titulo": "¿Hay alzas de fuego fuera de lo normal?",
    "al_sub_semana": "Cada semana de {area} contra la misma semana del año en los años anteriores (desde {a0}). La "
                     "banda es lo normal (la mitad central de los años), la línea azul la mediana y la punteada el "
                     "umbral de alerta. Termina en {mes} {año}, el mes que se evalúa.",
    "al_sub_mes": "Cada mes de {area} contra el mismo mes en los años anteriores (desde {a0}). La banda es lo "
                  "normal (la mitad central de los años), la línea azul la mediana y la punteada el umbral de "
                  "alerta. Termina en {mes} {año}, el mes que se evalúa.",
    "al_por_semana": "Por semana",
    "al_por_mes": "Por mes",
    "al_sin_semanas": "La vista por semana está para países y regiones de ejemplo. Para un área dibujada o por "
                      "coordenadas se compara mes a mes.",
    "al_u_semana": "semana",
    "al_u_semanas": "semanas",
    "al_u_mes": "mes",
    "al_u_meses": "meses",
    "al_racha": "Alerta: {n} {u} seguidas por encima de lo normal, desde {inicio}. En total, {r:.1f} veces lo "
                "normal.",
    "al_racha_mes": "Alerta: {n} {u} seguidos por encima de lo normal, desde {inicio}. En total, {r:.1f} veces lo "
                    "normal.",
    "al_pico": "Alerta: {periodo} muy por encima de lo normal: {r:.1f} veces la mediana, más que el {pct:.0f} % de "
               "los años anteriores.",
    "al_subiendo": "Atención: {periodo} por encima de lo normal ({r:.1f} veces). Si se repite {k} {u} seguidas, es "
                   "alerta.",
    "al_subiendo_mes": "Atención: {periodo} por encima de lo normal ({r:.1f} veces). Si se repite {k} {u} seguidos, "
                       "es alerta.",
    "al_termino": "Ya volvió a lo normal. Hubo una racha de {n} {u} por encima de lo normal, de {inicio} a {fin}.",
    "al_normal_semana": "Sin alzas fuera de lo normal en las últimas {u}.",
    "al_normal_mes": "Sin alzas fuera de lo normal en los últimos {u}.",
    "al_normal_bajo": "Sin alzas: el último periodo está por debajo de lo normal.",
    "al_sin_historia": "Sin comparación todavía: hacen falta al menos 3 años anteriores con la misma {u}.",
    "al_sin_datos": "No hay datos para este periodo.",
    "al_la_semana": "la semana del {f}",
    "al_el_mes": "{f}",
    "al_regla": "Regla: alto si pasa 1.25 veces la mediana o el percentil 75; muy alto si pasa 2 veces la mediana o "
                "el percentil 90. Para no alertar por ruido, el alza tiene que ser de al menos {m} detecciones. Es "
                "alerta una racha de {k} {u} altas seguidas, o una sola muy alta que duplique la mediana y la pase "
                "por {m3} detecciones.",
    "al_regla_mes": "Regla: alto si pasa 1.25 veces la mediana o el percentil 75; muy alto si pasa 2 veces la "
                    "mediana o el percentil 90. Para no alertar por ruido, el alza tiene que ser de al menos {m} "
                    "detecciones. Es alerta una racha de {k} {u} altos seguidos, o uno solo muy alto que duplique "
                    "la mediana y la pase por {m3} detecciones.",
    "al_ep_titulo": "Rachas de alzas, {a0}–{a1}",
    "al_ep_sub": "Seguidillas de {u} por encima de lo normal. Las más recientes primero.",
    "al_ep_ninguna": "No hubo alzas fuera de lo normal en este periodo.",
    "al_col_desde": "Desde",
    "al_col_hasta": "Hasta",
    "al_col_dura": "Duración",
    "al_col_det": "Detecciones",
    "al_col_normal": "Lo normal",
    "al_col_veces": "× normal",
    "al_col_alerta": "Alerta",
    "al_si": "Sí",
    "al_pa_titulo": "Países fuera de lo normal en {mes} {año}",
    "al_pa_sub": "Países con un alza de al menos {m} detecciones sobre su mediana de {mes} ({a0}–{a1}). Toca uno "
                 "para verlo.",
    "al_pa_ninguno": "Ningún país está fuera de lo normal en {mes} {año}.",
    "al_pa_n": "{n} países por encima de lo normal; {k} muy por encima.",
    "al_col_pais": "País",
    "al_col_nivel": "Nivel",
    "al_pa_ver": "Ver un país de la lista",
    "al_pa_ver_ph": "Elige un país…",
    "g_al_normal": "Rango normal",
    "g_al_mediana": "Mediana desde {a0}",
    "g_al_umbral": "Umbral de alerta",
    "g_al_det": "Detecciones",
    "g_al_semana": "Semana del {f}",
    "g_al_lo_normal": "Lo normal",
    "g_al_det_semana": "detecciones / semana",
    "cal_escala_log": "Escala logarítmica",
    "alerta_titulo": "{mes} {año} · {area}",
    "alerta_razon": "{r:.1f}× la mediana",
    "alerta_sin_fuego_previo": "sin fuego en años anteriores",
    "alerta_detalle": "<b>{x}</b> detecciones: {razon} de {mes} ({a0}–{a1}). Es el <b>{rank}.º {mes} más activo</b> "
                      "de {n} años. Fuente: {fuente}.",
    "alerta_sin_historia": "Se necesitan al menos 3 años anteriores del mismo mes para comparar.",
    "kpi_este_mes": "{mes} {año}",
    "kpi_vs_mediana": "{v:+.0f}% vs. mediana",
    "kpi_mediana": "Mediana histórica del mes",
    "kpi_mediana_nota": "{mes}, {a0}–{a1}",
    "kpi_percentil": "Percentil",
    "kpi_percentil_nota": "% de años anteriores con menos fuego ese mes",
    "kpi_z": "Anomalía (z robusto)",
    "kpi_z_nota": "desviaciones (MAD) respecto a la mediana",
    "kpi_det_viirs": "detecciones equivalentes a VIIRS",
    # ---------------------------------------------------------------- pestañas
    "tab_calendario": "Calendario",
    "tab_tendencias": "Tendencias",
    "tab_mapa": "Mapa",
    "tab_armonizacion": "¿Cómo armonizamos?",
    "tab_nrt": "Últimos días",
    "tab_descargas": "Descargas",
    "tab_metodo": "Método",
    # ---------------------------------------------------------------- calendario
    "cal_titulo": "El calendario del fuego",
    "cal_sub": "Cada casilla es un mes de {area}, {a0}–{a1}.",
    "vista": "Vista",
    "vista_armonizado": "Armonizado",
    "vista_anomalia": "Anomalía vs. mediana del mes",
    "vista_sin_armonizar": "Sin armonizar (MODIS y luego VIIRS)",
    "cal_leyenda_estrella": "mes evaluado",
    "cal_leyenda_punto": "mes estimado desde MODIS (más incertidumbre)",
    "cal_leyenda_cursor": "Pasa el cursor para ver el valor, su rango y el sensor de origen.",
    "criticos_titulo": "Periodos críticos",
    "criticos_sub": "Los 10 meses con más fuego del periodo",
    "concentra_titulo": "Temporada de fuego",
    "concentra_sub": "Mediana de cada mes en el periodo elegido",
    "temporada_pico": "Temporada pico (mediana)",
    "temporada_nota": "{v:.0f}% del fuego anual",
    "año_mas": "Año más activo",
    "año_menos": "Año menos activo",
    "n_detecciones": "{v} detecciones",
    "col_año": "año",
    "col_mes": "mes",
    "col_detecciones": "detecciones",
    "col_fuente": "fuente",
    # ---------------------------------------------------------------- tendencias
    "perfil_titulo": "Perfil estacional",
    "perfil_sub": "{año} contra la historia del área",
    "anual_titulo": "Actividad anual",
    "anual_sub": "Color = sensor de origen · barras claras = año incompleto",
    "comp_titulo": "Qué produce el calor",
    "comp_sub": "Puntos de calor armonizados por año y tipo en {area} · barras claras = año incompleto",
    "comp_reparto": "En {a0}–{a1}:",
    "comp_nota": "Tipos de FIRMS. Cada uno se armoniza con su propio modelo, porque VIIRS no ve lo mismo de más en "
                 "todos: unas 4 veces más detecciones que MODIS en la vegetación, 7 en volcanes, 8 en industria y "
                 "gas, y 50 en las plataformas del mar.",
    # ---------------------------------------------------------------- mapa
    "mapa_titulo": "Mapa de detecciones",
    "mapa_mostrar": "Mostrar",
    "capa_total": "Total {a0}–{a1}",
    "capa_anomalia": "Anomalía de {mes} {año}",
    "mapa_nota_total": "Detecciones armonizadas acumuladas en cada celda de 0.5° (~55 km).",
    "mapa_nota_anomalia": "Rojo: más detecciones que la mediana de {mes} ({a0}–{a1}); azul: menos. "
                          "Muestra dónde se concentra la anomalía.",
    "mapa_vacio": "No hay detecciones para mostrar en este periodo.",
    "mapa_color_total": "detecciones",
    "mapa_color_anomalia": "diferencia vs.<br>mediana",
    # ---------------------------------------------------------------- armonización
    "arm_titulo": "Qué corrige la armonización",
    "arm_texto": "MODIS (1 km, desde 2000) ve muchos menos fuegos pequeños que VIIRS (375 m, desde 2012). Si se "
                 "unen los registros tal cual, aparece un <b>salto falso en 2012</b>: no hubo más fuego, solo "
                 "cambió el sensor. Armonizado, todo queda en <i>detecciones equivalentes a VIIRS</i> y la serie es "
                 "comparable de punta a punta. Se hace <b>por tipo de fuente</b>, porque la diferencia no es la "
                 "misma: VIIRS ve unas 4 veces más que MODIS en los incendios de vegetación, 8 en la quema de gas e "
                 "industria y 50 en las plataformas del mar.",
    "arm_modis": "MODIS · Terra y Aqua",
    "arm_modis_det": "Píxel de 1 km · desde nov-2000 · ve menos fuegos pequeños",
    "arm_viirs": "VIIRS · S-NPP, NOAA-20 y NOAA-21",
    "arm_viirs_det": "Píxel de 375 m · desde 2012 · ve muchos más fuegos. S-NPP se apagó el 2-nov-2026; siguen "
                     "NOAA-20 y NOAA-21",
    "arm_resultado": "Una sola serie",
    "arm_resultado_det": "Todo en detecciones equivalentes a VIIRS, con rango de incertidumbre",
    "antes_titulo": "Antes y después de armonizar",
    "antes_sub": "Promedio mensual de cada año, mismo eje en los dos paneles: lo único que cambia es MODIS",
    "global_titulo": "Serie mundial armonizada",
    "global_nota": "Total mundial de cada mes, con los cuatro tipos de punto de calor: MODIS tal cual, MODIS "
                   "armonizado con el modelo integral (con su rango) y lo que VIIRS observó. En 2012–2025 la "
                   "estimación es la de la validación: cada año se predijo sin verlo. El detalle está en “¿Cómo "
                   "armonizamos?”.",
    # ---------------------------------------------------------------- tiempo casi real
    "nrt_titulo": "Alerta temprana: últimos días",
    "nrt_sub": "NASA FIRMS en tiempo casi real",
    "nrt_texto": "Compara las detecciones VIIRS de los últimos días en esta área con lo que es normal para este mes "
                 "según la serie armonizada. Sin llave usa los archivos públicos de FIRMS (últimos 7 días); con una "
                 "MAP_KEY gratuita eliges de 1 a 10 días y completas el calendario hasta hoy.",
    "nrt_key_ayuda": "Llave gratuita: https://firms.modaps.eosdis.nasa.gov/api/map_key/",
    "nrt_dias": "Días hacia atrás",
    "nrt_boton": "Consultar FIRMS",
    "nrt_consultando": "Consultando FIRMS…",
    "nrt_det": "Detecciones últimos {d} días",
    "nrt_normal": "Lo normal en {d} días de {mes}",
    "nrt_relacion": "Relación",
    "nrt_arriba": "por encima de lo normal",
    "nrt_normal_bajo": "dentro o bajo lo normal",
    "nrt_csv": "CSV de detecciones recientes",
    "nrt_error": "No se pudo consultar FIRMS: {e}",
    "nrt_falta_key": "Ingresa tu MAP_KEY (o define la variable de entorno `FIRMS_MAP_KEY`).",
    # ---------------------------------------------------------------- descargas
    "desc_titulo": "Descargas del área y periodo seleccionados",
    "desc_cal": "Calendario mensual armonizado",
    "desc_cal_sub": "Un registro por mes, con rango y conteos crudos",
    "desc_cal_boton": "CSV calendario",
    "desc_ultimos": "Últimos 12 meses",
    "desc_puntos": "Puntos de calor originales (todos los sensores)",
    "desc_puntos_sub": "Desde data/db_nasa.duckdb",
    "desc_puntos_sub_ca": "En la demo en línea: Centroamérica (Belice, Costa Rica, El Salvador, Guatemala, Honduras, "
                          "Nicaragua y Panamá). El resto del mundo, corriendo la app con la base completa.",
    "desc_max": "Máximo de filas",
    "desc_preparar": "Preparar CSV de puntos de calor",
    "desc_consultando": "Consultando db_nasa.duckdb…",
    "desc_n": "{n} detecciones",
    "desc_max_alcanzado": " (se alcanzó el máximo)",
    "desc_puntos_boton": "CSV puntos de calor",
    "desc_sin_db": "No se encontró `data/db_nasa.duckdb`.",
    "desc_primeras": "Primeras 200 filas",
    # ---------------------------------------------------------------- método
    "met_titulo": "Método",
    "met_1_t": "Datos",
    "met_1": "Todos los puntos de calor de NASA FIRMS desde noviembre de 2000: MODIS C6.1 (Terra y Aqua), "
             "VIIRS S-NPP (2012–2017) y VIIRS NOAA-20 (2018–hoy). S-NPP dejó de entregar datos el 2-nov-2026, "
             "así que NOAA-20 es la referencia operativa y NOAA-21 el respaldo en tiempo casi real.",
    "met_2_t": "Unidad común",
    "met_2": "El mundo se divide en celdas de 0.5° (~55 km) y se cuentan las detecciones por celda, mes y tipo de "
             "fuente de FIRMS: vegetación, volcanes, otras fuentes fijas en tierra (gas, refinerías, industria) y "
             "costa afuera. Se usan solo meses completos de cada satélite (se descartan meses con días sin datos o "
             "con fallas).",
    "met_3_t": "Armonización",
    "met_3": "{metodo}. El objetivo es expresar todo en <i>detecciones que habría visto VIIRS</i>: en los meses "
             "con VIIRS se usa lo observado; en los meses solo con MODIS se estima. La calibración usa 2012–2021, "
             "antes de que las órbitas de Terra y Aqua se corrieran (2022 en adelante).",
    "met_4_t": "Incertidumbre",
    "met_4": "El rango de cada mes estimado sale del error del propio modelo: en la validación dejando un año fuera "
             "se mide, año a año, cuánto se pasó o se quedó corto en esa región de 10° y ese mes (percentiles "
             "5–95). Validación dejando un año fuera (2012–2021) y con años nunca vistos (2022–2025): el detalle "
             "está en “¿Cómo armonizamos?”.",
    "met_5_t": "Anomalías",
    "met_5": "Cada mes se compara con la mediana del mismo mes en los años anteriores del periodo elegido: razón, "
             "percentil y z robusto (MAD). Semáforo: rojo ≥ 2× la mediana o percentil ≥ 90; amarillo ≥ 1.25× o "
             "percentil ≥ 75; azul ≤ 0.5×.",
    "met_6_t": "Accesibilidad",
    "met_6": "Calendario y mapa en Cividis (perceptualmente uniforme y legible para daltonismo), escala logarítmica "
             "opcional, semáforo siempre con texto e ícono, y todos los valores disponibles al pasar el cursor y en "
             "CSV.",
    "met_pie": "Datos generados: {generado} · {celdas} celdas · {filas} celda-mes.",
    # ---------------------------------------------------------------- tour
    "tour_titulo": "Tour para jueces",
    "tour_paso": "Paso {i} de {n}",
    "tour_mirar": "Qué mirar",
    "tour_anterior": "Anterior",
    "tour_siguiente": "Siguiente",
    "tour_listo": "¡Listo!",
    "tour_0_t": "Empieza por el globo",
    "tour_0": "Cada país tiene el color de su fuego promedio por año. Gira el globo, haz clic en un país y a la "
              "derecha aparece su historia completa en una sola serie.",
    "tour_0_m": "La línea naranja (armonizada) es continua de punta a punta; la azul es MODIS tal cual, muy por "
                "debajo. Esa distancia es lo que corrige el modelo. El clic también cambia el análisis de abajo.",
    "tour_1_t": "La respuesta en 5 segundos",
    "tour_1": "El panel de estado responde “¿este mes es normal en mi zona?” con una frase, una escala de 4 "
              "niveles y cuatro cifras.",
    "tour_1_m": "La escala de nivel (texto + color) y los 4 números: este mes, la mediana histórica, el percentil "
                "y la anomalía (z robusto), con sus medidores.",
    "tour_2_t": "El calendario del fuego",
    "tour_2": "Cada casilla es un mes y cada fila un año: se ven las temporadas de quema y los años raros de un "
              "vistazo.",
    "tour_2_m": "La estrella marca el mes evaluado; los puntitos, los meses estimados desde MODIS. Cambia la vista "
                "a “Anomalía” para ver qué meses se salieron de lo normal.",
    "tour_3_t": "¿Cómo armonizamos?",
    "tour_3": "La pestaña de armonización muestra el antes y el después: unidos tal cual, MODIS y VIIRS crean un "
              "salto falso en 2012; armonizados, la serie es continua.",
    "tour_3_m": "Los dos paneles de “Antes y después”: a la izquierda, el salto falso de 2012; a la derecha, la misma "
                "serie sin salto. Debajo, la validación: cada año se esconde al calibrar y se predice desde MODIS.",
    "tour_4_t": "De la historia a la acción",
    "tour_4": "“Últimos días” compara los fuegos de los últimos días con lo normal de esa semana del año, sin "
              "llave. Con una MAP_KEY gratuita se completa el calendario hasta hoy. “Descargas” entrega un informe "
              "HTML, el resumen y los CSV.",
    "tour_4_m": "Prueba el modo presentación (arriba a la derecha) y cambia el área a “Amazonía brasileña” para ver "
                "otra región del mundo.",
    # ---------------------------------------------------------------- pie
    "pie_credito": "Datos: NASA FIRMS · Proyecto para NASA Space Apps Challenge 2026 Costa Rica. No es un producto "
                   "oficial de la NASA. Sensores: MODIS C6.1 (Terra y Aqua), VIIRS S-NPP, NOAA-20 y NOAA-21.",
    # ---------------------------------------------------------------- por qué importa
    "imp_franja_t": "Por qué importa",
    "imp_n1_t": "muertes al año se asocian al humo de incendios de vegetación, más del 90 % en países de ingreso "
                "bajo y medio",
    "imp_n1_f": "The Lancet, 2024",
    "imp_n2_t": "más fuegos ve VIIRS que MODIS. Sin armonizar, 2012 parece una ola de incendios que nunca existió",
    "imp_n2_f": "NASA FIRMS 2012–2021, cálculo propio",
    "imp_n3": "25 años",
    "imp_n3_t": "de historia del fuego en una sola serie, justo cuando MODIS se apaga (2027) y S-NPP ya dejó de "
                "enviar datos (2-nov-2026)",
    "imp_n3_f": "NASA Earthdata",
    "imp_n4_t": "países y territorios. Gratis, con datos abiertos de la NASA, en español e inglés",
    "tab_impacto": "Para qué sirve",
    "imp_titulo": "Para qué sirve",
    "imp_intro": "El fuego de vegetación no es solo un problema del bosque. Su humo se asocia a unos 1.5 millones "
                 "de muertes al año en el mundo, sobre todo en países de ingreso bajo y medio, y cada temporada "
                 "pone en riesgo cosechas, agua, casas y biodiversidad. Y no todo punto de calor es un incendio: la "
                 "quema de gas en pozos petroleros, las refinerías, las siderúrgicas y los volcanes también se ven "
                 "desde el espacio. Para prevenir y vigilar hay que saber cuándo y dónde el calor está fuera de lo "
                 "normal, y eso solo se responde con una historia larga y comparable. Data Masters la reconstruye "
                 "para cualquier lugar del planeta y cada tipo de fuente, y se la entrega a quien tiene que "
                 "decidir.",
    "imp_area_t": "Lo que dicen los datos de {area}",
    "imp_tend_t": "Una conclusión falsa que se evita",
    "imp_tend": "Si se unen los sensores tal cual, entre {p0} y {p1} el fuego parece cambiar <b>{ni}</b>. "
                "Armonizado, el cambio real es <b>{nr}</b>.",
    "imp_tend_sin": "Para ver este efecto, el periodo tiene que incluir años completos antes y después de 2012.",
    "imp_temp_t": "Cuándo prepararse",
    "imp_temp": "{meses} concentran el <b>{pct:.0f} %</b> del fuego del año y el mes más activo suele ser {pico}. "
                "Brigadas, campañas y permisos de quema se preparan desde <b>{prep}</b>.",
    "imp_pico_t": "El año para recordar",
    "imp_pico": "<b>{año}</b> fue el año con más fuego del periodo: {v} detecciones, <b>{r:.1f} veces</b> un año típico.",
    "imp_quien_t": "Quién lo usa y qué decide",
    "imp_col_quien": "Quién",
    "imp_col_decide": "Qué decide con esto",
    "imp_col_donde": "Dónde mirar",
    "imp_q1": "Bomberos forestales y comités de emergencia",
    "imp_d1": "Adelantar brigadas, vigilancia y cierres cuando el mes viene por encima de lo normal.",
    "imp_w1": "Estado del mes · Últimos días",
    "imp_q2": "Salud pública",
    "imp_d2": "Avisar a escuelas, centros de salud y personas con asma antes de las semanas con más humo.",
    "imp_w2": "Temporada de fuego · Calendario",
    "imp_q3": "Áreas protegidas y gestores de territorio",
    "imp_d3": "Medir si la prevención funciona año contra año, sin el salto falso de 2012.",
    "imp_w3": "Tendencias · Antes y después",
    "imp_q4": "Agricultura y municipios",
    "imp_d4": "Ordenar los permisos de quema según el calendario real de cada zona.",
    "imp_w4": "Calendario · Mapa",
    "imp_q5": "Ciencia y clima",
    "imp_d5": "Estudiar 25 años de fuego, El Niño o la deforestación con una sola unidad y su incertidumbre.",
    "imp_w5": "Descargas · Método",
    "imp_q6": "Periodismo y ciudadanía",
    "imp_d6": "Comprobar con datos si “este año hay más incendios” es cierto.",
    "imp_w6": "Globo · Informe descargable",
    "imp_q7": "Ministerios de ambiente y energía",
    "imp_d7": "Seguir la quema de gas en pozos, refinerías y plataformas: en 2024 se quemaron en el mundo 151 000 "
              "millones de m³ de gas, el nivel más alto desde 2007, con unos 389 millones de toneladas de CO₂ "
              "equivalente.",
    "imp_w7": "Tipo: Industria y gas · Costa afuera · Globo",
    "imp_q8": "Observatorios de volcanes",
    "imp_d8": "Ver si un volcán está más caliente que en sus 25 años de historia. En Costa Rica FIRMS registra el "
              "Arenal (con calor hasta 2010), el Turrialba y el Poás.",
    "imp_w8": "Tipo: Volcanes · Mapa · Calendario",
    "imp_ahora_t": "Por qué ahora",
    "imp_ahora_1": "Suomi NPP dejó de entregar datos el 2 de noviembre de 2026. La continuidad son NOAA-20 y NOAA-21.",
    "imp_ahora_2": "NASA prevé dejar de recolectar datos de MODIS en 2027. Sin un puente entre sensores, 25 años de "
                   "registro no se pueden comparar con lo que viene.",
    "imp_ahora_3": "En Costa Rica, al cierre de mayo de 2026 Bomberos contaba 233 incendios forestales y 30 868 "
                   "hectáreas afectadas: 264 % más incendios que en 2025. Saber si una temporada es extraordinaria "
                   "ya no es una pregunta académica.",
    "imp_alcance_t": "Alcance",
    "imp_alcance": "{n} países y territorios, celdas de 0.5° en todo el planeta, de {a0} a {a1}. Gratis y con datos "
                   "abiertos de la NASA; corre en una laptop y funciona sin internet, salvo la consulta en tiempo casi "
                   "real. En español e inglés, con colores aptos para daltonismo y un modo presentación para salas "
                   "de crisis.",
    "imp_limites_t": "Lo que no hace",
    "imp_lim_1": "Cuenta detecciones de calor, no hectáreas quemadas ni daños.",
    "imp_lim_2": "Nubes, humo denso y fuegos muy pequeños o breves pueden no verse desde el espacio.",
    "imp_lim_3": "Antes de 2012 la serie es una estimación desde MODIS: su error típico por país y año es de "
                 "{e:.0f} % (validación dejando un año fuera).",
    "imp_lim_4": "Los datos en tiempo casi real son provisionales hasta que la NASA publica el procesamiento estándar.",
    "imp_fuentes_t": "Fuentes",
    # ---------------------------------------------------------------- validación
    "val_titulo": "Validación: escondemos un año y lo predecimos",
    "val_sub": "Cada año de 2012 a 2021 se dejó fuera al calibrar y se predijo desde MODIS; 2022–2025 nunca se "
               "usaron para calibrar. Círculos: lo predicho, con su rango; línea negra: lo que VIIRS vio.",
    "val_anual": "Error típico por año",
    "val_anual_nota": "{n} años en esta área",
    "val_mensual": "Error típico por mes",
    "val_mensual_nota": "meses con al menos 20 detecciones",
    "val_modis": "Sin armonizar",
    "val_modis_nota": "error de unir MODIS tal cual",
    "val_dentro": "Años dentro del rango",
    "val_dentro_nota": "rango p5–p95 del error del modelo en la región",
    "val_global": "En el mundo ({paises} países), el error típico es de {pa:.1f} % por país y año y de {g:.1f} % en "
                  "el total mensual global; unir MODIS tal cual se equivoca un {pm:.0f} %. En años que el modelo "
                  "nunca vio (2022–2025), {fa:.1f} % por país y año. El rango sale del error del modelo en la "
                  "región y el mes; no incluye el ruido local de cada celda, por eso cubre menos años de lo que su "
                  "nombre sugiere.",
    "val_sin_datos": "No hay suficientes detecciones en esta área para validar año por año.",
    # ---------------------------------------------------------------- el modelo y su evaluación
    "mod_titulo": "Cómo armonizamos: el modelo que usa la app",
    "mod_texto": "Es un modelo integral: cada tipo de punto de calor se armoniza con el modelo que le corresponde. "
                 "La vegetación, más del 90 % de lo que ve VIIRS, con LightGBM (600 árboles, unas {n:,} hojas) y "
                 "una corrección regional. Los volcanes, la industria y el gas, y las plataformas costa afuera, "
                 "celda por celda, porque son fuentes que no se mueven. De los cinco modelos que probamos es el de "
                 "mejor R² (log) por celda y por país, y el que falla en menos países.",
    "mod_1": "Se cuentan las detecciones de MODIS y de VIIRS en cada celda de 0.5° (~55 km), cada mes y cada tipo "
             "de fuente de FIRMS (vegetación, volcanes, industria y gas, costa afuera), en 2012–2021, los años en "
             "que vuelan los dos con órbitas normales.",
    "mod_2": "Vegetación: para cada celda y mes, LightGBM recibe 28 datos: lo que vio MODIS (Terra y Aqua, de día y "
             "de noche, potencia del fuego, confianza y qué parte son fuentes fijas), la vecindad (celdas de "
             "alrededor, mes anterior y siguiente, historia de la celda), la posición del Sol a la hora de paso, el "
             "lugar y la fecha.",
    "mod_3": "Aprende con 2012–2016 y 2018–2020 a predecir cuántas detecciones de vegetación vio VIIRS, con pérdida "
             "de Poisson, la adecuada para conteos. 2017 y 2021 se guardan para la prueba y 2022–2025 nunca se "
             "usan.",
    "mod_4": "Corrección regional: en la validación dejando un año fuera se mide cuánto se pasa o se queda corto en "
             "cada región de 10° y mes (Σ VIIRS ÷ Σ predicho), y la predicción se multiplica por ese factor, "
             "acotado entre 0.5 y 2. El año que se predice nunca entra en su propio factor.",
    "mod_5": "Volcanes, industria y gas, costa afuera ({c:,} celdas): cada celda tiene su propia relación entre "
             "MODIS y VIIRS, porque es siempre la misma chimenea, el mismo pozo o el mismo volcán. VIIRS = MODIS × "
             "el factor de la celda, más una base para lo que VIIRS ve y MODIS no alcanza (pozos y plataformas "
             "chicas). En 2018 esa relación cambia de golpe (VIIRS pasa de S-NPP a NOAA-20 y MODIS empieza a marcar "
             "unas 6 veces más volcanes), así que se aprende por separado antes y después de 2018. Supuesto: la "
             "base se mantiene hacia atrás en el tiempo.",
    "mod_6": "En los meses sin VIIRS (2002–2011) se predicen las detecciones que habría visto VIIRS: en vegetación, "
             "NOAA-20; en las fuentes fijas, con la relación aprendida en 2012–2017. Donde hay VIIRS se usa lo "
             "observado. De noviembre de 2000 a junio de 2002 solo volaba Terra: ahí la vegetación usa la razón "
             "VIIRS/Terra de la región y el mes.",
    "mod_7": "El rango de incertidumbre sale del error de cada modelo en la misma validación: cuánto se pasó o se "
             "quedó corto año a año en cada región (percentiles 5 y 95). En las fuentes fijas se acota entre un "
             "tercio y el triple de lo estimado.",
    "mod_8": "Se comparó con cuatro modelos que tratan todos los tipos juntos, en los mismos años: un solo factor "
             "mundial (×{k:.1f}), una razón VIIRS/MODIS por región de 10° y mes ({nr:,} factores), LightGBM y "
             "LightGBM con corrección regional. Las cifras están abajo.",
    "ev_titulo": "Métricas: R², MSE y error",
    "ev_sub": "El modelo integral, el de la app, en los años de prueba 2017 y 2021, que no vio al entrenar, contra "
              "todos los puntos de calor que VIIRS observó de verdad (los cuatro tipos).",
    "ev_col_nivel": "Nivel",
    "ev_col_r2": "R²",
    "ev_col_r2log": "R² (log)",
    "ev_col_mse": "MSE",
    "ev_col_rmse": "RMSE",
    "ev_col_err": "Error típico",
    "ev_col_sesgo": "Sesgo",
    "ev_nivel_celda_mes": "Celda de 0.5° × mes",
    "ev_nivel_pais_mes": "País × mes",
    "ev_nivel_pais_año": "País × año",
    "ev_nivel_mundo_mes": "Mundo × mes",
    "ev_nota": "R²: 1 es perfecto y 0 es lo mismo que adivinar el promedio. R² (log) se calcula sobre "
               "log(1 + detecciones), para que cada celda o país pese parecido sin importar su tamaño. MSE es el "
               "promedio del error al cuadrado (en detecciones²) y RMSE su raíz, en detecciones. Error típico: "
               "mediana del error en %, donde VIIRS vio al menos 20 (celda), 100 (país-mes) o 1,000 (país-año) "
               "detecciones. Sesgo: cuánto se pasa (+) o se queda corto (−) el total.",
    "ev_celda": "Celda por celda es donde más cuesta (R² log {r2:.2f}): en una celda de 55 km muchos meses tienen "
                "pocos fuegos y el azar pesa. Al sumar un país o una región esos errores se compensan (R² log "
                "{r2p:.2f} por país y mes). La razón por región, el modelo simple, se queda en R² log {r2r:.2f} por "
                "celda: si MODIS no vio nada predice cero, aunque VIIRS haya visto fuegos pequeños.",
    "sob_titulo": "¿Sobreajusta?",
    "sob_sub": "Sobreajustar es aprenderse los años de entrenamiento y fallar en los nuevos. Si el error casi no "
               "cambia de entrenamiento a prueba y a años nunca vistos, el modelo generaliza. Cada casilla va "
               "entrenamiento → prueba → nunca vistos.",
    "sob_col_modelo": "Modelo",
    "sob_col_param": "Tamaño",
    "sob_col_r2": "R² (log) por celda",
    "sob_col_err": "Error típico país-año",
    "sob_col_ver": "Veredicto",
    "sob_param_factor_global": "1 factor",
    "sob_param_razon": "{n:,} factores",
    "sob_param_lightgbm": "600 árboles · {n:,} hojas",
    "sob_param_lightgbm_corregido": "600 árboles + {n:,} factores",
    "sob_param_integral": "600 árboles + {n:,} factores + {c:,} celdas",
    "sob_modelo_factor_global": "Un solo factor mundial",
    "sob_modelo_razon": "Razón por región y mes",
    "sob_modelo_lightgbm": "LightGBM sin corrección",
    "sob_modelo_lightgbm_corregido": "LightGBM + corrección regional",
    "sob_modelo_integral": "Integral: un modelo por tipo (la app)",
    "sob_sin_sobreajuste": "No sobreajusta",
    "sob_leve": "Sobreajuste leve",
    "sob_sobreajuste": "Sobreajusta",
    "sob_conclusion": "Ninguno de los cinco sobreajusta: de entrenamiento a prueba el R² por celda baja como mucho "
                      "{caida:.3f} y el error por país y año sube como mucho {sube:.1f} puntos. En 2022–2025 sube "
                      "algo más, lo esperable en años nuevos y con las órbitas de Terra y Aqua ya corridas. El "
                      "modelo integral tiene el mejor R² (log) por celda, por país y mes y por país y año "
                      "({r2i:.3f} por celda contra {r2c:.3f} de LightGBM con corrección), menos error que LightGBM "
                      "con corrección en el total mundial ({gi:.1f} % contra {gc:.1f} %) y falla en menos países "
                      "({fi} contra {fc}); por eso es el que usa la app.{ventaja}",
    "cmp_ventaja": "LightGBM con corrección, que trata todos los tipos juntos, queda un poco mejor en {donde}.",
    "cmp_err_pais_mes": "el error por país y mes ({a:.1f} % contra {b:.1f} %)",
    "cmp_err_pais_año": "el error por país y año ({a:.1f} % contra {b:.1f} %)",
    "cmp_mse": "el MSE por {niveles}",
    "cmp_nivel_celda_mes": "celda",
    "cmp_nivel_pais_mes": "país y mes",
    "cmp_nivel_pais_año": "país y año",
    "cmp_empeora": "En cambio, {paises} pasan a no funcionar bien.",
    "sob_cr": "La excepción que más nos toca es Costa Rica, donde la razón simple se equivoca menos ({cr:.1f} % "
              "contra {crl:.1f} % por año).",
    "pai_titulo": "Dónde no funciona bien",
    "pai_sub": "Cada país medido con predicciones que el modelo no vio: un año fuera a la vez en 2012–2021, más "
               "2022–2025.",
    "pai_resumen": "De {n} países con al menos 1,000 detecciones al año, el modelo de la app funciona bien en "
                   "{bien} (error típico por año < 15 %), regular en {regular} y no funciona bien en {mal} (> 25 % "
                   "por año o > 40 % por mes). Otros {pocos} tienen muy poco fuego para medirlo.",
    "pai_por_que": "{nf} de los {mal} tienen mucha quema que no es de vegetación (más del 10 % de sus detecciones "
                   "de MODIS; en los países donde funciona, la mediana es {fr:.1f} %): volcanes que entran en "
                   "erupción algunos años o pozos de gas que se abren y se cierran. El modelo por celda aprende "
                   "cómo es cada fuente, pero no puede adivinar una erupción o un pozo nuevo que MODIS no vio. "
                   "Separar los tipos arregló {arregla} de los {fc} países donde fallaba LightGBM con corrección "
                   "({arreglados}).{empeora} Con la razón por región, el modelo simple, no funcionan bien {mr}.",
    "pai_area": "{pais}: {estado}. Error típico {e:.1f} % por año{em}; {tendencia}.",
    "pai_area_mes": " y {v:.1f} % por mes",
    "pai_estado_bien": "funciona bien",
    "pai_estado_regular": "funciona regular",
    "pai_estado_no funciona bien": "no funciona bien",
    "pai_estado_pocos datos": "tiene muy poco fuego para medir el modelo",
    "pai_sube": "en general se pasa {v:.0f} %",
    "pai_baja": "en general se queda corto {v:.0f} %",
    "pai_col_pais": "País",
    "pai_col_año": "Error por año",
    "pai_col_mes": "Error por mes",
    "pai_col_tend": "Tendencia",
    "pai_col_fijas": "Fuentes fijas",
    "pai_col_alt": "Con la razón",
    "pai_tend_sube": "se pasa {v:.0f} %",
    "pai_tend_baja": "se queda corto {v:.0f} %",
    "g_val_pred": "Predicho desde MODIS",
    "g_val_fuera": "nunca vistos →",
    "g_val_loyo": "← año escondido al calibrar",
    # ---------------------------------------------------------------- tiempo casi real y meses recientes
    "nrt_boton_publico": "Consultar los últimos 7 días",
    "nrt_satelite": "Satélite: VIIRS {s} · tiempo casi real",
    "nrt_sin_tipo": "FIRMS en tiempo casi real no trae el tipo de fuente: esta comparación usa todos los puntos de "
                    "calor.",
    "nrt_recientes_t": "Completar el calendario hasta hoy",
    "nrt_recientes": "Los datos locales llegan a diciembre de {a}. Con la MAP_KEY se traen los meses desde enero de "
                     "{b} hasta hoy (VIIRS NOAA-20, la misma fuente de la historia desde 2018) y se suman al "
                     "calendario, al estado del mes y a las descargas.",
    "nrt_recientes_boton": "Traer los meses hasta hoy",
    "nrt_recientes_ok": "Listo: {n} meses agregados ({d} detecciones). Ya aparecen en el panel lateral.",
    "nrt_trayendo": "Consultando FIRMS…",
    "cal_leyenda_reciente": "mes en tiempo casi real (provisional)",
    "alerta_parcial": " Mes en curso: {d} de {n} días, comparado con lo esperado a la fecha.",
    # ---------------------------------------------------------------- informe y descargas
    "desc_informe": "Informe del área",
    "desc_informe_sub": "Analíticas y gráficas en un solo archivo HTML que se abre sin internet",
    "desc_informe_boton": "Informe HTML",
    "desc_resumen_boton": "Resumen analítico (CSV)",
    "desc_png": "Cada gráfica también se descarga como PNG con el ícono de cámara que aparece al pasar el cursor.",
    "desc_fechas": "Desde – hasta",
    "inf_titulo": "Informe de {area}",
    "inf_generado": "Generado el {f} con Data Masters · periodo {a0}–{a1}",
    "inf_cifras": "Analíticas",
    "inf_metrica": "Métrica",
    "inf_valor": "Valor",
    "inf_graficas": "Gráficas",
    "inf_nivel": "Nivel del mes",
    "inf_factor": "VIIRS ÷ MODIS en el área",
    "inf_val": "Error típico por año (validación)",
    "inf_temporada": "Temporada de fuego",
    "inf_tend_arm": "Cambio real (armonizado)",
    "inf_tend_ing": "Cambio aparente sin armonizar",
    # ---------------------------------------------------------------- cobertura del reto
    "cob_titulo": "Lo que pide el reto y dónde está",
    "cob_col_pide": "El reto pide",
    "cob_col_donde": "Dónde está en la app",
    "cob_1": "Armonizar MODIS y VIIRS en una sola serie",
    "cob_1_d": "¿Cómo armonizamos? · Método",
    "cob_2": "Elegir una región: dibujarla en el mapa o con latitud/longitud",
    "cob_2_d": "Panel lateral: País, Región de ejemplo, Dibujar en el mapa, Coordenadas",
    "cob_3": "Elegir un rango de fechas",
    "cob_3_d": "Panel lateral (años y mes) · Descargas (fechas exactas)",
    "cob_4": "Calendario de quemas desde inicios de los 2000 hasta hoy",
    "cob_4_d": "Calendario, desde nov-2000; los meses de {b} hasta hoy, con MAP_KEY en Últimos días",
    "cob_5": "Periodos del año con más fuego y años más activos",
    "cob_5_d": "Calendario · Temporada de fuego · Periodos críticos · Tendencias",
    "cob_6": "Comparar un fuego actual con los anteriores",
    "cob_6_d": "Alertas: cada semana o mes contra los mismos de años anteriores · Estado del mes · Últimos días",
    "cob_7": "Comparar el mes actual con la mediana histórica",
    "cob_7_d": "Estado del mes: razón, percentil y z robusto · Alertas por semana y por mes · Mapa de anomalía",
    "cob_8": "Descargar analíticas, visualizaciones y CSV de los focos",
    "cob_8_d": "Descargas: informe HTML, resumen CSV, calendario CSV, puntos CSV por fechas · PNG en cada gráfica",
    "cob_9": "Rampas de color accesibles",
    "cob_9_d": "Calendario y mapa en Cividis (legible para daltonismo) · texto junto a todo color",
    "cob_10": "Anomalías frente a promedios multianuales",
    "cob_10_d": "Calendario, vista Anomalía · Mapa de anomalía",
    "cob_11": "Mostrar método, validación e incertidumbre",
    "cob_11_d": "¿Cómo armonizamos?: validación dejando un año fuera, R² y MSE, sobreajuste y países donde falla · rango en cada mes estimado · Método",
    "cob_12": "Alerta temprana en tiempo casi real",
    "cob_12_d": "Alertas (rachas de alzas, países fuera de lo normal) · Últimos días (FIRMS, NOAA-20 y NOAA-21)",
    "cob_13": "Todos los tipos de punto de calor, no solo incendios",
    "cob_13_d": "Panel lateral: Tipo de punto de calor (vegetación, industria y gas, volcanes, costa afuera) · "
                "Tendencias: qué produce el calor · cada tipo con su modelo y su validación",
    "tour_5_t": "Por qué importa",
    "tour_5": "“Para qué sirve” traduce el análisis en decisiones: quién usa cada parte, qué conclusión falsa evita "
              "y cuándo prepararse en el área elegida.",
    "tour_5_m": "La conclusión falsa que se evita: sin armonizar, el fuego parece multiplicarse desde 2012; "
                "armonizado, se ve el cambio real.",
    "tour_6_t": "Alertas: ¿hay un patrón de alzas?",
    "tour_6": "La pestaña Alertas compara cada semana (o cada mes) con la misma semana de los años anteriores y "
              "avisa cuando hay una racha de alzas fuera de lo normal, no solo un mes raro. También dice qué países "
              "del mundo están por encima de lo normal ese mes.",
    "tour_6_m": "Elige Estados Unidos y septiembre de 2020: 7 semanas seguidas por encima de lo normal. Las barras "
                "rojas pasan el umbral de alerta (línea punteada); la banda es lo normal.",
    # ---------------------------------------------------------------- gráficas
    "g_sin_datos": "sin datos",
    "g_det_viirs": "detecciones (unidades VIIRS)",
    "g_det_crudas": "detecciones crudas",
    "g_detecciones": "detecciones",
    "g_rango": "rango",
    "g_fuente": "Fuente",
    "g_sensor": "Sensor",
    "g_vs_mediana": "vs. mediana del mes",
    "g_pct_mediana": "% vs.<br>mediana",
    "g_det_mes": "detecciones / mes",
    "g_det_año": "detecciones / año (unidades VIIRS)",
    "g_det_año_corto": "detecciones / año",
    "g_meses_datos": "meses con datos",
    "g_tendencia": "tendencia ({v:+.1f} %/año)",
    "g_antes": "Antes: unidos tal cual",
    "g_despues": "Después: armonizados",
    "g_modis_tal_cual": "MODIS tal cual",
    "g_modis_arm": "MODIS armonizado",
    "g_viirs_c": "VIIRS",
    "g_salto": "Salto falso: VIIRS ve {f:.1f}× más",
    "g_casi_sin_salto": "Casi sin salto ({f:.2f}×)",
    "g_sin_salto": "Sin salto: una sola serie",
    "g_det_mes_prom": "detecciones / mes (promedio del año)",
    "g_modis_crudo": "MODIS crudo",
    "g_rango90": "rango 90 %",
    "g_lgbm": "MODIS → VIIRS (modelo integral)",
    "g_viirs_obs": "VIIRS observado",
    "g_det_mundo": "detecciones / mes (mundo)",
    "g_mediana": "mediana",
    "g_mediana_rango": "mediana {a0}–{a1}",
}

EN = {
    "app_nombre": "Data Masters",
    "app_lead": "MODIS (since 2000) and VIIRS (since 2012) count fire differently. We join them into a single "
                "25-year series, comparable worldwide, to tell whether this month had more fire than usual.",
    "app_evento": "NASA Space Apps Challenge 2026 · Costa Rica",
    "app_reto": "Challenge: {reto}",
    "chip_sin_area": "Choose an area",
    "tel_area": "Area",
    "tel_celdas": "0.5° cells",
    "tel_periodo": "Period",
    "tel_sensores": "Sensors",
    "tel_centro": "Center",
    "esc_bajo": "Low",
    "esc_normal": "Normal",
    "esc_alto": "High",
    "esc_muy_alto": "Very high",
    "escala_lbl": "Level: {nivel}",
    "tour_boton": "Judges' tour",
    "presentacion": "Presentation mode",
    "presentacion_ayuda": "Hides the sidebar, enlarges text and charts, and shows the pitch.",
    "idioma": "Language",
    "modo": "Appearance",
    "modo_claro": ":material/light_mode: Light",
    "modo_noche": ":material/dark_mode: Night",
    "pitch_problema_t": "The problem",
    "pitch_problema": "Merging MODIS (since 2000) and VIIRS (since 2012) as-is creates a false jump: fire seems "
                      "to surge in 2012, but only the satellite changed.",
    "pitch_solucion_t": "Our solution",
    "pitch_solucion": "We harmonize 25 years of hot spots into a single unit (VIIRS-equivalent detections), with "
                      "an uncertainty range, on 0.5° cells for the whole world.",
    "pitch_impacto_t": "The impact",
    "pitch_impacto": "Firefighters, public health and land managers know in 5 seconds whether this month is normal "
                     "in their area, when to get ready and whether prevention works. Smoke from these fires is linked "
                     "to 1.5 million deaths a year worldwide (The Lancet, 2024).",
    "lateral_sub": "Harmonized MODIS + VIIRS · NASA FIRMS",
    "area_titulo": "Area of interest",
    "area_como": "How do you choose the area?",
    "area_pais": "Country",
    "area_region": "Example region",
    "area_dibujar": "Draw on the map",
    "area_coords": "Coordinates",
    "pais": "Country",
    "region": "Region",
    "latitud": "Latitude",
    "longitud": "Longitude",
    "radio_km": "Radius (km)",
    "dibuja_info": "Draw a rectangle or polygon on the map to the right.",
    "periodo_titulo": "Period",
    "tipo_titulo": "Hot spot type",
    "tipo_ayuda": "FIRMS classifies every detection: vegetation (wildfires and burning), industry and gas (gas "
                  "flaring at wells, refineries, steel mills), volcanoes and offshore (platforms at sea). All = the "
                  "sum.",
    "tipo_todos": "All",
    "tipo_veg": "Vegetation",
    "tipo_industria": "Industry and gas",
    "tipo_volcan": "Volcanoes",
    "tipo_mar": "Offshore",
    "tipo_vacio": "There are no “{tipo}” hot spots in {area} between {a0} and {a1}. Choose another type or “All” in "
                  "the sidebar.",
    "años_historia": "Years of history",
    "mes_evaluar": "Month to evaluate",
    "visual_titulo": "Display",
    "rampa": "Color ramp (colorblind-safe; Cividis recommended)",
    "escala_log": "Log scale",
    "escala_log_ayuda": "Makes low-fire months visible next to the peaks.",
    "nota_armonizacion": "Harmonization",
    "nota_datos": "Data: NASA FIRMS · MODIS C6.1, VIIRS S-NPP and NOAA-20 · 0.5° cells · {a0}–{a1}",
    "area_circulo": "{r} km around {lat:.2f}, {lon:.2f}",
    "area_dibujada": "Drawn area",
    "dibuja_titulo": "Draw your area of interest",
    # ---------------------------------------------------------------- globe
    "globo_sub": "Yearly average {a0}–{a1}, in VIIRS-equivalent detections.",
    "globo_hover": "detections / year",
    "globo_pista": "Tap a country to see its history · drag to spin the globe.",
    "hist_sub": "Fire history, {a0}–{a1}",
    "hist_reparto": "What is detected:",
    "hist_sin_tipo": "No {tipo} hot spots here in this period.",
    "hist_frase_mas": "{a} had {p} % more fire than a typical year. Its worst year was {pico}.",
    "hist_frase_menos": "{a} had {p} % less fire than a typical year. Its worst year was {pico}.",
    "hist_frase_igual": "{a} was a typical year. Its worst year was {pico}.",
    "hist_frase_pico": "{a} was its worst year: {p} % more fire than a typical year.",
    "hist_promedio": "Yearly average",
    "hist_pico": "Peak year",
    "hist_ultimo": "In {a}",
    "hist_promedio_nota": "harmonized detections",
    "hist_pico_nota": "{v} detections / month",
    "hist_ultimo_nota": "vs. average",
    "hist_factor": "VIIRS ÷ MODIS",
    "hist_factor_nota": "months with both sensors",
    "hist_arm": "Harmonized",
    "hist_modis": "MODIS as is",
    "hist_viirs": "VIIRS observed",
    "hist_estimado": "estimated from MODIS",
    "hist_entra_viirs": "VIIRS starts",
    "hist_nota": "Monthly average for each year (at least 9 months). Filled point: seen by VIIRS. Hollow point: "
                 "estimated from MODIS; the band is its range.",
    "dibuja_usa": "Use the ▭ or ⬠ tools on the map to draw. The analysis will appear below.",
    "area_vacia": "There are no cells with fire detections in this area. Try a larger area.",
    "faltan_datos": "The app data is missing (folder `data/app`).",
    "faltan_pasos": "1. Run the notebook `notebooks/03_modelo.ipynb` up to section 2 "
                    "(creates `data/modelo/celdas_0.5.parquet`).\n2. In the terminal: `python scripts/preparar_app.py`\n"
                    "3. Reload this page.",
    "calculando": "Computing the area's series…",
    "nivel_muy_alto": "Far above normal",
    "nivel_alto": "Above normal",
    "nivel_normal": "Within normal",
    "nivel_bajo": "Below normal",
    "nivel_sin_historia": "Not enough history",
    "frase_muy_alto": "{mes} {año} is far above normal in this area.",
    "frase_alto": "{mes} {año} is above normal.",
    "frase_normal": "{mes} {año} is within normal.",
    "frase_bajo": "{mes} {año} is below normal: there was less fire than usual.",
    "frase_sin_historia": "No comparison yet: at least 3 previous years of {mes} are needed.",
    "tab_alertas": "Alerts",
    "al_titulo": "Are there unusual rises in fire?",
    "al_sub_semana": "Each week in {area} against the same week of the year in previous years (from {a0}). The band "
                     "is normal (the middle half of the years), the blue line the median and the dotted line the "
                     "alert threshold. It ends in {mes} {año}, the month being evaluated.",
    "al_sub_mes": "Each month in {area} against the same month in previous years (from {a0}). The band is normal "
                  "(the middle half of the years), the blue line the median and the dotted line the alert "
                  "threshold. It ends in {mes} {año}, the month being evaluated.",
    "al_por_semana": "By week",
    "al_por_mes": "By month",
    "al_sin_semanas": "The weekly view is available for countries and example regions. For a drawn area or "
                      "coordinates, the comparison is month by month.",
    "al_u_semana": "week",
    "al_u_semanas": "weeks",
    "al_u_mes": "month",
    "al_u_meses": "months",
    "al_racha": "Alert: {n} {u} in a row above normal, since {inicio}. Overall, {r:.1f} times normal.",
    "al_racha_mes": "Alert: {n} {u} in a row above normal, since {inicio}. Overall, {r:.1f} times normal.",
    "al_pico": "Alert: {periodo} far above normal: {r:.1f} times the median, more than {pct:.0f} % of previous "
               "years.",
    "al_subiendo": "Watch: {periodo} above normal ({r:.1f} times). If it repeats for {k} {u} in a row, it is an "
                   "alert.",
    "al_subiendo_mes": "Watch: {periodo} above normal ({r:.1f} times). If it repeats for {k} {u} in a row, it is an "
                       "alert.",
    "al_termino": "Back to normal. There was a run of {n} {u} above normal, from {inicio} to {fin}.",
    "al_normal_semana": "No unusual rises in the last {u}.",
    "al_normal_mes": "No unusual rises in the last {u}.",
    "al_normal_bajo": "No rises: the last period is below normal.",
    "al_sin_historia": "No comparison yet: at least 3 previous years of the same {u} are needed.",
    "al_sin_datos": "No data for this period.",
    "al_la_semana": "the week of {f}",
    "al_el_mes": "{f}",
    "al_regla": "Rule: high above 1.25 times the median or the 75th percentile; very high above 2 times the median "
                "or the 90th percentile. To avoid alerting on noise, the rise must be at least {m} detections. An "
                "alert is a run of {k} high {u} in a row, or a single very high one that doubles the median and "
                "exceeds it by {m3} detections.",
    "al_regla_mes": "Rule: high above 1.25 times the median or the 75th percentile; very high above 2 times the "
                    "median or the 90th percentile. To avoid alerting on noise, the rise must be at least {m} "
                    "detections. An alert is a run of {k} high {u} in a row, or a single very high one that doubles "
                    "the median and exceeds it by {m3} detections.",
    "al_ep_titulo": "Runs of rises, {a0}–{a1}",
    "al_ep_sub": "Stretches of {u} above normal. Most recent first.",
    "al_ep_ninguna": "There were no unusual rises in this period.",
    "al_col_desde": "From",
    "al_col_hasta": "To",
    "al_col_dura": "Duration",
    "al_col_det": "Detections",
    "al_col_normal": "Normal",
    "al_col_veces": "× normal",
    "al_col_alerta": "Alert",
    "al_si": "Yes",
    "al_pa_titulo": "Countries above normal in {mes} {año}",
    "al_pa_sub": "Countries with a rise of at least {m} detections over their {mes} median ({a0}–{a1}). Tap one to "
                 "see it.",
    "al_pa_ninguno": "No country is above normal in {mes} {año}.",
    "al_pa_n": "{n} countries above normal; {k} far above.",
    "al_col_pais": "Country",
    "al_col_nivel": "Level",
    "al_pa_ver": "See a country from the list",
    "al_pa_ver_ph": "Choose a country…",
    "g_al_normal": "Normal range",
    "g_al_mediana": "Median since {a0}",
    "g_al_umbral": "Alert threshold",
    "g_al_det": "Detections",
    "g_al_semana": "Week of {f}",
    "g_al_lo_normal": "Normal",
    "g_al_det_semana": "detections / week",
    "cal_escala_log": "Log scale",
    "alerta_titulo": "{mes} {año} · {area}",
    "alerta_razon": "{r:.1f}× the median",
    "alerta_sin_fuego_previo": "no fire in previous years",
    "alerta_detalle": "<b>{x}</b> detections: {razon} for {mes} ({a0}–{a1}). It is the <b>#{rank} most active "
                      "{mes}</b> out of {n} years. Source: {fuente}.",
    "alerta_sin_historia": "At least 3 previous years of the same month are needed to compare.",
    "kpi_este_mes": "{mes} {año}",
    "kpi_vs_mediana": "{v:+.0f}% vs. median",
    "kpi_mediana": "Historical median for the month",
    "kpi_mediana_nota": "{mes}, {a0}–{a1}",
    "kpi_percentil": "Percentile",
    "kpi_percentil_nota": "% of previous years with less fire that month",
    "kpi_z": "Anomaly (robust z)",
    "kpi_z_nota": "deviations (MAD) from the median",
    "kpi_det_viirs": "VIIRS-equivalent detections",
    "tab_calendario": "Calendar",
    "tab_tendencias": "Trends",
    "tab_mapa": "Map",
    "tab_armonizacion": "How do we harmonize?",
    "tab_nrt": "Last few days",
    "tab_descargas": "Downloads",
    "tab_metodo": "Method",
    "cal_titulo": "The fire calendar",
    "cal_sub": "Each square is one month in {area}, {a0}–{a1}.",
    "vista": "View",
    "vista_armonizado": "Harmonized",
    "vista_anomalia": "Anomaly vs. monthly median",
    "vista_sin_armonizar": "Not harmonized (MODIS, then VIIRS)",
    "cal_leyenda_estrella": "evaluated month",
    "cal_leyenda_punto": "month estimated from MODIS (more uncertainty)",
    "cal_leyenda_cursor": "Hover to see the value, its range and the source sensor.",
    "criticos_titulo": "Critical periods",
    "criticos_sub": "The 10 months with the most fire in the period",
    "concentra_titulo": "Fire season",
    "concentra_sub": "Median of each month in the chosen period",
    "temporada_pico": "Peak season (median)",
    "temporada_nota": "{v:.0f}% of annual fire",
    "año_mas": "Most active year",
    "año_menos": "Least active year",
    "n_detecciones": "{v} detections",
    "col_año": "year",
    "col_mes": "month",
    "col_detecciones": "detections",
    "col_fuente": "source",
    "perfil_titulo": "Seasonal profile",
    "perfil_sub": "{año} against the area's history",
    "anual_titulo": "Annual activity",
    "anual_sub": "Color = source sensor · pale bars = incomplete year",
    "comp_titulo": "What produces the heat",
    "comp_sub": "Harmonized hot spots per year and type in {area} · pale bars = incomplete year",
    "comp_reparto": "In {a0}–{a1}:",
    "comp_nota": "FIRMS types. Each one is harmonized with its own model, because VIIRS does not see the same extra "
                 "amount everywhere: about 4 times more detections than MODIS in vegetation, 7 in volcanoes, 8 in "
                 "industry and gas, and 50 on offshore platforms.",
    "mapa_titulo": "Detection map",
    "mapa_mostrar": "Show",
    "capa_total": "Total {a0}–{a1}",
    "capa_anomalia": "{mes} {año} anomaly",
    "mapa_nota_total": "Harmonized detections accumulated in each 0.5° cell (~55 km).",
    "mapa_nota_anomalia": "Red: more detections than the {mes} median ({a0}–{a1}); blue: fewer. Shows where the "
                          "anomaly is concentrated.",
    "mapa_vacio": "There are no detections to show in this period.",
    "mapa_color_total": "detections",
    "mapa_color_anomalia": "difference vs.<br>median",
    "arm_titulo": "What harmonization fixes",
    "arm_texto": "MODIS (1 km, since 2000) sees far fewer small fires than VIIRS (375 m, since 2012). If the "
                 "records are merged as-is, a <b>false jump appears in 2012</b>: there was no more fire, only the "
                 "sensor changed. Once harmonized, everything is in <i>VIIRS-equivalent detections</i> and the "
                 "series is comparable end to end. It is done <b>per source type</b>, because the gap is not the "
                 "same: VIIRS sees about 4 times more than MODIS in vegetation fires, 8 in gas flaring and "
                 "industry, and 50 on offshore platforms.",
    "arm_modis": "MODIS · Terra and Aqua",
    "arm_modis_det": "1 km pixel · since Nov 2000 · misses many small fires",
    "arm_viirs": "VIIRS · S-NPP, NOAA-20 and NOAA-21",
    "arm_viirs_det": "375 m pixel · since 2012 · sees many more fires. S-NPP went dark on 2 Nov 2026; NOAA-20 and "
                     "NOAA-21 carry on",
    "arm_resultado": "One single series",
    "arm_resultado_det": "Everything in VIIRS-equivalent detections, with an uncertainty range",
    "antes_titulo": "Before and after harmonizing",
    "antes_sub": "Monthly average of each year, same axis in both panels: only MODIS changes",
    "global_titulo": "Harmonized worldwide series",
    "global_nota": "Worldwide total for each month, with all four hot spot types: MODIS as is, MODIS harmonized "
                   "with the integral model (with its range) and what VIIRS observed. In 2012–2025 the estimate is "
                   "the validation one: each year was predicted without seeing it. Details in “How do we "
                   "harmonize?”.",
    "nrt_titulo": "Early warning: last few days",
    "nrt_sub": "NASA FIRMS near real time",
    "nrt_texto": "Compares VIIRS detections from the last few days in this area with what is normal for this month "
                 "according to the harmonized series. Without a key it uses the public FIRMS files (last 7 days); "
                 "with a free MAP_KEY you choose 1 to 10 days and fill the calendar up to today.",
    "nrt_key_ayuda": "Free key: https://firms.modaps.eosdis.nasa.gov/api/map_key/",
    "nrt_dias": "Days back",
    "nrt_boton": "Query FIRMS",
    "nrt_consultando": "Querying FIRMS…",
    "nrt_det": "Detections, last {d} days",
    "nrt_normal": "Normal for {d} days of {mes}",
    "nrt_relacion": "Ratio",
    "nrt_arriba": "above normal",
    "nrt_normal_bajo": "within or below normal",
    "nrt_csv": "CSV of recent detections",
    "nrt_error": "Could not query FIRMS: {e}",
    "nrt_falta_key": "Enter your MAP_KEY (or set the `FIRMS_MAP_KEY` environment variable).",
    "desc_titulo": "Downloads for the selected area and period",
    "desc_cal": "Harmonized monthly calendar",
    "desc_cal_sub": "One record per month, with range and raw counts",
    "desc_cal_boton": "Calendar CSV",
    "desc_ultimos": "Last 12 months",
    "desc_puntos": "Original hot spots (all sensors)",
    "desc_puntos_sub": "From data/db_nasa.duckdb",
    "desc_puntos_sub_ca": "In the online demo: Central America (Belize, Costa Rica, El Salvador, Guatemala, Honduras, "
                          "Nicaragua and Panama). The rest of the world, by running the app with the full database.",
    "desc_max": "Maximum rows",
    "desc_preparar": "Prepare hot-spot CSV",
    "desc_consultando": "Querying db_nasa.duckdb…",
    "desc_n": "{n} detections",
    "desc_max_alcanzado": " (maximum reached)",
    "desc_puntos_boton": "Hot-spot CSV",
    "desc_sin_db": "`data/db_nasa.duckdb` was not found.",
    "desc_primeras": "First 200 rows",
    "met_titulo": "Method",
    "met_1_t": "Data",
    "met_1": "Every NASA FIRMS hot spot since November 2000: MODIS C6.1 (Terra and Aqua), VIIRS S-NPP (2012–2017) "
             "and VIIRS NOAA-20 (2018–today). S-NPP stopped delivering data on 2 Nov 2026, so NOAA-20 is the "
             "operational reference and NOAA-21 the near-real-time backup.",
    "met_2_t": "Common unit",
    "met_2": "The world is divided into 0.5° cells (~55 km) and detections are counted per cell, month and FIRMS "
             "source type: vegetation, volcanoes, other static land sources (gas, refineries, industry) and "
             "offshore. Only complete months of each satellite are used (months with missing days or outages are "
             "discarded).",
    "met_3_t": "Harmonization",
    "met_3": "{metodo}. The goal is to express everything as <i>detections VIIRS would have seen</i>: months with "
             "VIIRS use the observations; MODIS-only months are estimated. Calibration uses 2012–2021, before the "
             "Terra and Aqua orbits drifted (2022 onwards).",
    "met_4_t": "Uncertainty",
    "met_4": "The range of each estimated month comes from the model's own error: in the leave-one-year-out "
             "validation we measure, year by year, how much it overshot or fell short in that 10° region and month "
             "(5th–95th percentiles). Leave-one-year-out validation (2012–2021) and on never-seen years "
             "(2022–2025): details under “How do we harmonize?”.",
    "met_5_t": "Anomalies",
    "met_5": "Each month is compared with the median of the same month in the previous years of the chosen period: "
             "ratio, percentile and robust z (MAD). Traffic light: red ≥ 2× the median or percentile ≥ 90; "
             "yellow ≥ 1.25× or percentile ≥ 75; blue ≤ 0.5×.",
    "met_6_t": "Accessibility",
    "met_6": "Calendar and map in Cividis (perceptually uniform and colorblind-safe), optional log scale, a traffic "
             "light that always carries text and an icon, and every value available on hover and as CSV.",
    "met_pie": "Data generated: {generado} · {celdas} cells · {filas} cell-months.",
    "tour_titulo": "Judges' tour",
    "tour_paso": "Step {i} of {n}",
    "tour_mirar": "What to look at",
    "tour_anterior": "Back",
    "tour_siguiente": "Next",
    "tour_listo": "Done!",
    "tour_0_t": "Start with the globe",
    "tour_0": "Each country is colored by its average fire per year. Spin the globe, click a country and its full "
              "history shows up on the right as a single series.",
    "tour_0_m": "The orange (harmonized) line runs unbroken end to end; the blue one is MODIS as is, far below. That "
                "gap is what the model corrects. The click also switches the analysis below.",
    "tour_1_t": "The answer in 5 seconds",
    "tour_1": "The status panel answers “is this month normal in my area?” with one sentence, a 4-level scale "
              "and four numbers.",
    "tour_1_m": "The level scale (text + color) and the 4 numbers: this month, the historical median, the "
                "percentile and the anomaly (robust z), with their gauges.",
    "tour_2_t": "The fire calendar",
    "tour_2": "Each square is a month and each row a year: burning seasons and unusual years show up at a glance.",
    "tour_2_m": "The star marks the evaluated month; the small dots mark months estimated from MODIS. Switch the "
                "view to “Anomaly” to see which months were out of the ordinary.",
    "tour_3_t": "How do we harmonize?",
    "tour_3": "The harmonization tab shows before and after: merged as-is, MODIS and VIIRS create a false jump in "
              "2012; harmonized, the series is continuous.",
    "tour_3_m": "The two “Before and after” panels: on the left, the false jump of 2012; on the right, the same "
                "series without it. Below, the validation: each year is hidden during calibration and predicted from MODIS.",
    "tour_4_t": "From history to action",
    "tour_4": "“Last few days” compares the latest fires with the normal for that week of the year, no key needed. "
              "With a free MAP_KEY the calendar is filled up to today. “Downloads” delivers an HTML report, the "
              "summary and the CSVs.",
    "tour_4_m": "Try presentation mode (top right) and switch the area to “Brazilian Amazon” to see another region "
                "of the world.",
    "pie_credito": "Data: NASA FIRMS · Project for the NASA Space Apps Challenge 2026 Costa Rica. Not an official "
                   "NASA product. Sensors: MODIS C6.1 (Terra and Aqua), VIIRS S-NPP, NOAA-20 and NOAA-21.",
    "imp_franja_t": "Why it matters",
    "imp_n1_t": "deaths a year are linked to smoke from landscape fires, over 90 % in low- and middle-income countries",
    "imp_n1_f": "The Lancet, 2024",
    "imp_n2_t": "more fires seen by VIIRS than MODIS. Without harmonizing, 2012 looks like a wave of fires that never "
                "happened",
    "imp_n2_f": "NASA FIRMS 2012–2021, our calculation",
    "imp_n3": "25 years",
    "imp_n3_t": "of fire history in one series, right as MODIS shuts down (2027) and S-NPP has stopped sending data "
                "(2 Nov 2026)",
    "imp_n3_f": "NASA Earthdata",
    "imp_n4_t": "countries and territories. Free, built on NASA open data, in Spanish and English",
    "tab_impacto": "Why it matters",
    "imp_titulo": "Why it matters",
    "imp_intro": "Landscape fire is not just a forest problem. Its smoke is linked to about 1.5 million deaths a "
                 "year worldwide, mostly in low- and middle-income countries, and every season puts crops, water, "
                 "homes and biodiversity at risk. And not every hot spot is a wildfire: gas flaring at oil wells, "
                 "refineries, steel mills and volcanoes are also seen from space. Prevention and monitoring need to "
                 "know when and where heat is out of the ordinary, and only a long, comparable history can answer "
                 "that. Data Masters rebuilds it for any place on Earth and every source type, and hands it to the "
                 "people who have to decide.",
    "imp_area_t": "What the data say about {area}",
    "imp_tend_t": "A false conclusion avoided",
    "imp_tend": "If the sensors are merged as is, between {p0} and {p1} fire seems to change <b>{ni}</b>. "
                "Harmonized, the real change is <b>{nr}</b>.",
    "imp_tend_sin": "To see this effect, the period must include full years before and after 2012.",
    "imp_temp_t": "When to get ready",
    "imp_temp": "{meses} hold <b>{pct:.0f} %</b> of the year's fire and the busiest month is usually {pico}. "
                "Crews, campaigns and burn permits get ready from <b>{prep}</b>.",
    "imp_pico_t": "The year to remember",
    "imp_pico": "<b>{año}</b> was the year with the most fire in the period: {v} detections, <b>{r:.1f} times</b> a "
                "typical year.",
    "imp_quien_t": "Who uses it and what they decide",
    "imp_col_quien": "Who",
    "imp_col_decide": "What they decide with it",
    "imp_col_donde": "Where to look",
    "imp_q1": "Wildland firefighters and emergency committees",
    "imp_d1": "Bring crews, patrols and closures forward when the month is running above normal.",
    "imp_w1": "Month status · Last few days",
    "imp_q2": "Public health",
    "imp_d2": "Warn schools, clinics and people with asthma before the smokiest weeks.",
    "imp_w2": "Fire season · Calendar",
    "imp_q3": "Protected areas and land managers",
    "imp_d3": "Measure whether prevention works year over year, without the false jump of 2012.",
    "imp_w3": "Trends · Before and after",
    "imp_q4": "Agriculture and municipalities",
    "imp_d4": "Schedule burn permits around each area's real fire calendar.",
    "imp_w4": "Calendar · Map",
    "imp_q5": "Science and climate",
    "imp_d5": "Study 25 years of fire, El Niño or deforestation in one unit, with its uncertainty.",
    "imp_w5": "Downloads · Method",
    "imp_q6": "Journalists and the public",
    "imp_d6": "Check with data whether “there are more fires this year” is true.",
    "imp_w6": "Globe · Downloadable report",
    "imp_q7": "Environment and energy ministries",
    "imp_d7": "Track gas flaring at wells, refineries and platforms: in 2024 the world flared 151 billion m³ of "
              "gas, the highest level since 2007, about 389 million tonnes of CO₂ equivalent.",
    "imp_w7": "Type: Industry and gas · Offshore · Globe",
    "imp_q8": "Volcano observatories",
    "imp_d8": "See whether a volcano is hotter than in its 25-year history. In Costa Rica FIRMS records Arenal (hot "
              "until 2010), Turrialba and Poás.",
    "imp_w8": "Type: Volcanoes · Map · Calendar",
    "imp_ahora_t": "Why now",
    "imp_ahora_1": "Suomi NPP stopped delivering data on 2 November 2026. NOAA-20 and NOAA-21 carry on.",
    "imp_ahora_2": "NASA plans to stop collecting MODIS data in 2027. Without a bridge between sensors, 25 years of "
                   "record cannot be compared with what comes next.",
    "imp_ahora_3": "In Costa Rica, by the end of May 2026 the fire service counted 233 wildfires and 30,868 hectares "
                   "affected: 264 % more fires than in 2025. Knowing whether a season is extraordinary is no longer "
                   "an academic question.",
    "imp_alcance_t": "Reach",
    "imp_alcance": "{n} countries and territories, 0.5° cells across the planet, from {a0} to {a1}. Free and built on "
                   "NASA open data; it runs on a laptop and works offline, except for the near-real-time query. In "
                   "Spanish and English, with colour-blind-safe palettes and a presentation mode for crisis rooms.",
    "imp_limites_t": "What it does not do",
    "imp_lim_1": "It counts heat detections, not burned hectares or damage.",
    "imp_lim_2": "Clouds, thick smoke and very small or short fires can be missed from space.",
    "imp_lim_3": "Before 2012 the series is an estimate from MODIS: its typical error per country and year is "
                 "{e:.0f} % (leave-one-year-out validation).",
    "imp_lim_4": "Near-real-time data are provisional until NASA publishes standard processing.",
    "imp_fuentes_t": "Sources",
    "val_titulo": "Validation: hide a year and predict it",
    "val_sub": "Each year from 2012 to 2021 was left out of calibration and predicted from MODIS; 2022–2025 were never "
               "used for calibration. Circles: the prediction, with its range; black line: what VIIRS saw.",
    "val_anual": "Typical error per year",
    "val_anual_nota": "{n} years in this area",
    "val_mensual": "Typical error per month",
    "val_mensual_nota": "months with at least 20 detections",
    "val_modis": "Not harmonized",
    "val_modis_nota": "error of merging MODIS as is",
    "val_dentro": "Years inside the range",
    "val_dentro_nota": "p5–p95 range of the model's error in the region",
    "val_global": "Worldwide ({paises} countries), the typical error is {pa:.1f} % per country and year and {g:.1f} "
                  "% on the global monthly total; merging MODIS as is misses by {pm:.0f} %. In years the model "
                  "never saw (2022–2025), {fa:.1f} % per country and year. The range comes from the model's error "
                  "in the region and month; it does not include each cell's local noise, so it covers fewer years "
                  "than its name suggests.",
    "val_sin_datos": "There are not enough detections in this area to validate year by year.",
    "mod_titulo": "How we harmonize: the model the app uses",
    "mod_texto": "It is an integral model: each hot spot type is harmonized with the model that fits it. "
                 "Vegetation, over 90 % of what VIIRS sees, with LightGBM (600 trees, about {n:,} leaves) and a "
                 "regional correction. Volcanoes, industry and gas, and offshore platforms cell by cell, because "
                 "they are sources that do not move. Of the five models we tested it has the best R² (log) per cell "
                 "and per country, and fails in the fewest countries.",
    "mod_1": "MODIS and VIIRS detections are counted in each 0.5° cell (~55 km), each month and each FIRMS source "
             "type (vegetation, volcanoes, industry and gas, offshore), in 2012–2021, the years when both fly with "
             "normal orbits.",
    "mod_2": "Vegetation: for each cell and month, LightGBM receives 28 inputs: what MODIS saw (Terra and Aqua, day "
             "and night, fire power, confidence and how much comes from static sources), the neighborhood "
             "(surrounding cells, previous and next month, the cell's history), the Sun's position at overpass "
             "time, the place and the date.",
    "mod_3": "It learns with 2012–2016 and 2018–2020 to predict how many vegetation detections VIIRS saw, with a "
             "Poisson loss, the right one for counts. 2017 and 2021 are kept for testing and 2022–2025 are never "
             "used.",
    "mod_4": "Regional correction: in the leave-one-year-out validation we measure how much it over- or "
             "under-predicts in each 10° region and month (Σ VIIRS ÷ Σ predicted), and the prediction is multiplied "
             "by that factor, bounded between 0.5 and 2. The predicted year never enters its own factor.",
    "mod_5": "Volcanoes, industry and gas, offshore ({c:,} cells): each cell has its own MODIS–VIIRS relationship, "
             "because it is always the same stack, well or volcano. VIIRS = MODIS × the cell's factor, plus a "
             "baseline for what VIIRS sees and MODIS cannot (small wells and platforms). In 2018 that relationship "
             "shifts abruptly (VIIRS moves from S-NPP to NOAA-20 and MODIS starts flagging about 6 times more "
             "volcanoes), so it is learned separately before and after 2018. Assumption: the baseline holds back in "
             "time.",
    "mod_6": "In months without VIIRS (2002–2011) we predict the detections VIIRS would have seen: for vegetation, "
             "NOAA-20; for static sources, with the relationship learned in 2012–2017. Where VIIRS exists, "
             "observations are used. From November 2000 to June 2002 only Terra flew: there vegetation uses the "
             "region's and month's VIIRS/Terra ratio.",
    "mod_7": "The uncertainty range comes from each model's error in the same validation: how much it over- or "
             "under-predicted year by year in each region (5th and 95th percentiles). For static sources it is "
             "bounded between a third and three times the estimate.",
    "mod_8": "It was compared with four models that treat all types together, on the same years: a single worldwide "
             "factor (×{k:.1f}), a VIIRS/MODIS ratio per 10° region and month ({nr:,} factors), LightGBM and "
             "LightGBM with regional correction. Figures below.",
    "ev_titulo": "Metrics: R², MSE and error",
    "ev_sub": "The integral model, the app's, on the 2017 and 2021 test years, which it did not see while training, "
              "against every hot spot VIIRS actually observed (all four types).",
    "ev_col_nivel": "Level",
    "ev_col_r2": "R²",
    "ev_col_r2log": "R² (log)",
    "ev_col_mse": "MSE",
    "ev_col_rmse": "RMSE",
    "ev_col_err": "Typical error",
    "ev_col_sesgo": "Bias",
    "ev_nivel_celda_mes": "0.5° cell × month",
    "ev_nivel_pais_mes": "Country × month",
    "ev_nivel_pais_año": "Country × year",
    "ev_nivel_mundo_mes": "World × month",
    "ev_nota": "R²: 1 is perfect and 0 is the same as guessing the average. R² (log) is computed on "
               "log(1 + detections), so each cell or country weighs about the same regardless of size. MSE is the "
               "mean squared error (in detections²) and RMSE its square root, in detections. Typical error: median "
               "error in %, where VIIRS saw at least 20 (cell), 100 (country-month) or 1,000 (country-year) "
               "detections. Bias: how much the total overshoots (+) or falls short (−).",
    "ev_celda": "Cell by cell is the hardest (log R² {r2:.2f}): in a 55 km cell many months have few fires and "
                "chance weighs a lot. When a country or region is added up those errors cancel out (log R² "
                "{r2p:.2f} per country and month). The regional ratio, the simple model, stays at log R² {r2r:.2f} "
                "per cell: if MODIS saw nothing it predicts zero, even if VIIRS saw small fires.",
    "sob_titulo": "Does it overfit?",
    "sob_sub": "Overfitting means memorizing the training years and failing on new ones. If the error barely "
               "changes from training to test and to never-seen years, the model generalizes. Each cell reads "
               "training → test → never seen.",
    "sob_col_modelo": "Model",
    "sob_col_param": "Size",
    "sob_col_r2": "Log R² per cell",
    "sob_col_err": "Typical country-year error",
    "sob_col_ver": "Verdict",
    "sob_param_factor_global": "1 factor",
    "sob_param_razon": "{n:,} factors",
    "sob_param_lightgbm": "600 trees · {n:,} leaves",
    "sob_param_lightgbm_corregido": "600 trees + {n:,} factors",
    "sob_param_integral": "600 trees + {n:,} factors + {c:,} cells",
    "sob_modelo_factor_global": "Single worldwide factor",
    "sob_modelo_razon": "Ratio by region and month",
    "sob_modelo_lightgbm": "LightGBM without correction",
    "sob_modelo_lightgbm_corregido": "LightGBM + regional correction",
    "sob_modelo_integral": "Integral: one model per type (the app)",
    "sob_sin_sobreajuste": "No overfitting",
    "sob_leve": "Slight overfitting",
    "sob_sobreajuste": "Overfits",
    "sob_conclusion": "None of the five overfits: from training to test the per-cell R² drops at most {caida:.3f} "
                      "and the error per country and year rises at most {sube:.1f} points. In 2022–2025 it rises a "
                      "bit more, as expected for new years with the Terra and Aqua orbits already drifted. The "
                      "integral model has the best R² (log) per cell, per country-month and per country-year "
                      "({r2i:.3f} per cell against {r2c:.3f} for LightGBM with correction), a lower worldwide-total "
                      "error than LightGBM with correction ({gi:.1f} % against {gc:.1f} %) and fails in fewer "
                      "countries ({fi} against {fc}); that is why the app uses it.{ventaja}",
    "cmp_ventaja": "LightGBM with correction, which treats all types together, is slightly better in {donde}.",
    "cmp_err_pais_mes": "the error per country and month ({a:.1f} % against {b:.1f} %)",
    "cmp_err_pais_año": "the error per country and year ({a:.1f} % against {b:.1f} %)",
    "cmp_mse": "the MSE per {niveles}",
    "cmp_nivel_celda_mes": "cell",
    "cmp_nivel_pais_mes": "country-month",
    "cmp_nivel_pais_año": "country-year",
    "cmp_empeora": "On the other hand, {paises} now do not work well.",
    "sob_cr": "The exception closest to home is Costa Rica, where the simple ratio makes smaller errors ({cr:.1f} % "
              "vs {crl:.1f} % per year).",
    "pai_titulo": "Where it does not work well",
    "pai_sub": "Each country measured with predictions the model did not see: one year left out at a time in "
               "2012–2021, plus 2022–2025.",
    "pai_resumen": "Of {n} countries with at least 1,000 detections a year, the app's model works well in {bien} "
                   "(typical yearly error < 15 %), fairly in {regular} and not well in {mal} (> 25 % per year or > "
                   "40 % per month). Another {pocos} have too little fire to measure it.",
    "pai_por_que": "{nf} of the {mal} have a lot of non-vegetation burning (over 10 % of their MODIS detections; "
                   "where it works, the median is {fr:.1f} %): volcanoes that erupt in some years or gas wells that "
                   "open and close. The per-cell model learns what each source is like, but it cannot foresee an "
                   "eruption or a new well MODIS never saw. Separating the types fixed {arregla} of the {fc} "
                   "countries where LightGBM with correction failed ({arreglados}).{empeora} With the regional "
                   "ratio, the simple model, {mr} do not work well.",
    "pai_area": "{pais}: {estado}. Typical error {e:.1f} % per year{em}; {tendencia}.",
    "pai_area_mes": " and {v:.1f} % per month",
    "pai_estado_bien": "works well",
    "pai_estado_regular": "works fairly",
    "pai_estado_no funciona bien": "does not work well",
    "pai_estado_pocos datos": "has too little fire to measure the model",
    "pai_sube": "it overshoots by {v:.0f} % overall",
    "pai_baja": "it falls short by {v:.0f} % overall",
    "pai_col_pais": "Country",
    "pai_col_año": "Error per year",
    "pai_col_mes": "Error per month",
    "pai_col_tend": "Tendency",
    "pai_col_fijas": "Static sources",
    "pai_col_alt": "With the ratio",
    "pai_tend_sube": "overshoots {v:.0f} %",
    "pai_tend_baja": "falls short {v:.0f} %",
    "g_val_pred": "Predicted from MODIS",
    "g_val_fuera": "never seen →",
    "g_val_loyo": "← year hidden during calibration",
    "nrt_boton_publico": "Check the last 7 days",
    "nrt_satelite": "Satellite: VIIRS {s} · near real time",
    "nrt_sin_tipo": "FIRMS near-real-time data do not include the source type: this comparison uses all hot spots.",
    "nrt_recientes_t": "Fill the calendar up to today",
    "nrt_recientes": "Local data run to December {a}. With the MAP_KEY, the months from January {b} to today are "
                     "fetched (VIIRS NOAA-20, the same source as the history since 2018) and added to the calendar, "
                     "the month status and the downloads.",
    "nrt_recientes_boton": "Fetch the months up to today",
    "nrt_recientes_ok": "Done: {n} months added ({d} detections). They now show in the side panel.",
    "nrt_trayendo": "Querying FIRMS…",
    "cal_leyenda_reciente": "near-real-time month (provisional)",
    "alerta_parcial": " Current month: {d} of {n} days, compared with what is expected to date.",
    "desc_informe": "Area report",
    "desc_informe_sub": "Analytics and charts in a single HTML file that opens offline",
    "desc_informe_boton": "HTML report",
    "desc_resumen_boton": "Analytics summary (CSV)",
    "desc_png": "Each chart can also be saved as PNG with the camera icon that shows up on hover.",
    "desc_fechas": "From – to",
    "inf_titulo": "Report for {area}",
    "inf_generado": "Generated on {f} with Data Masters · period {a0}–{a1}",
    "inf_cifras": "Analytics",
    "inf_metrica": "Metric",
    "inf_valor": "Value",
    "inf_graficas": "Charts",
    "inf_nivel": "Month level",
    "inf_factor": "VIIRS ÷ MODIS in the area",
    "inf_val": "Typical error per year (validation)",
    "inf_temporada": "Fire season",
    "inf_tend_arm": "Real change (harmonized)",
    "inf_tend_ing": "Apparent change without harmonizing",
    "cob_titulo": "What the challenge asks and where it is",
    "cob_col_pide": "The challenge asks",
    "cob_col_donde": "Where it is in the app",
    "cob_1": "Harmonize MODIS and VIIRS into one series",
    "cob_1_d": "How do we harmonize? · Method",
    "cob_2": "Choose a region: draw it on a map or enter latitude/longitude",
    "cob_2_d": "Side panel: Country, Example region, Draw on the map, Coordinates",
    "cob_3": "Choose a date range",
    "cob_3_d": "Side panel (years and month) · Downloads (exact dates)",
    "cob_4": "Burn calendar from the early 2000s to today",
    "cob_4_d": "Calendar, from Nov 2000; the months from {b} to today, with a MAP_KEY in Last few days",
    "cob_5": "Times of year with the most fire and the most active years",
    "cob_5_d": "Calendar · Fire season · Critical periods · Trends",
    "cob_6": "Compare a current fire with past ones",
    "cob_6_d": "Alerts: each week or month against the same in previous years · Month status · Last few days",
    "cob_7": "Compare the current month with the historical median",
    "cob_7_d": "Month status: ratio, percentile and robust z · Alerts by week and by month · Anomaly map",
    "cob_8": "Download analytics, visualizations and a CSV of the hot spots",
    "cob_8_d": "Downloads: HTML report, summary CSV, calendar CSV, hot-spot CSV by dates · PNG on every chart",
    "cob_9": "Accessible color ramps",
    "cob_9_d": "Calendar and map in Cividis (colorblind-safe) · text next to every color",
    "cob_10": "Anomalies against multi-year averages",
    "cob_10_d": "Calendar, Anomaly view · Anomaly map",
    "cob_11": "Show method, validation and uncertainty",
    "cob_11_d": "How we harmonize: leave-one-year-out validation, R² and MSE, overfitting and countries where it fails · range on every estimated month · Method",
    "cob_12": "Near-real-time early warning",
    "cob_12_d": "Alerts (runs of rises, countries above normal) · Last few days (FIRMS, NOAA-20 and NOAA-21)",
    "cob_13": "Every hot spot type, not just wildfires",
    "cob_13_d": "Sidebar: Hot spot type (vegetation, industry and gas, volcanoes, offshore) · Trends: what produces "
                "the heat · each type with its own model and validation",
    "tour_5_t": "Why it matters",
    "tour_5": "“Why it matters” turns the analysis into decisions: who uses each part, which false conclusion it "
              "avoids and when to get ready in the chosen area.",
    "tour_5_m": "The false conclusion avoided: without harmonizing, fire seems to multiply after 2012; harmonized, "
                "you see the real change.",
    "tour_6_t": "Alerts: is there a pattern of rises?",
    "tour_6": "The Alerts tab compares each week (or month) with the same week in previous years and warns when "
              "there is a run of unusual rises, not just one odd month. It also lists which countries are above "
              "normal that month.",
    "tour_6_m": "Choose the United States and September 2020: 7 weeks in a row above normal. Red bars cross the "
                "alert threshold (dotted line); the band is normal.",
    "g_sin_datos": "no data",
    "g_det_viirs": "detections (VIIRS units)",
    "g_det_crudas": "raw detections",
    "g_detecciones": "detections",
    "g_rango": "range",
    "g_fuente": "Source",
    "g_sensor": "Sensor",
    "g_vs_mediana": "vs. monthly median",
    "g_pct_mediana": "% vs.<br>median",
    "g_det_mes": "detections / month",
    "g_det_año": "detections / year (VIIRS units)",
    "g_det_año_corto": "detections / year",
    "g_meses_datos": "months with data",
    "g_tendencia": "trend ({v:+.1f} %/yr)",
    "g_antes": "Before: merged as is",
    "g_despues": "After: harmonized",
    "g_modis_tal_cual": "MODIS as-is",
    "g_modis_arm": "Harmonized MODIS",
    "g_viirs_c": "VIIRS",
    "g_salto": "False jump: VIIRS sees {f:.1f}× more",
    "g_casi_sin_salto": "Almost no jump ({f:.2f}×)",
    "g_sin_salto": "No jump: one continuous series",
    "g_det_mes_prom": "detections / month (yearly average)",
    "g_modis_crudo": "Raw MODIS",
    "g_rango90": "90 % range",
    "g_lgbm": "MODIS → VIIRS (integral model)",
    "g_viirs_obs": "Observed VIIRS",
    "g_det_mundo": "detections / month (world)",
    "g_mediana": "median",
    "g_mediana_rango": "median {a0}–{a1}",
}

TEXTOS = {"es": ES, "en": EN}
RETO = "Harmonization of MODIS and VIIRS Hot Spots"


def t(clave: str, idioma: str = "es", **valores) -> str:
    texto = TEXTOS.get(idioma, ES).get(clave, ES.get(clave, clave))
    return texto.format(**valores) if valores else texto


_PAISES = json.loads((Path(__file__).resolve().parent / "paises_nombres.json").read_text(encoding="utf-8"))


def pais(nombre: str, idioma: str) -> str:
    """Nombre del país (como viene en FIRMS) en el idioma de la interfaz."""
    return _PAISES.get(nombre, {}).get(idioma, nombre)


def iso3(nombre: str) -> str | None:
    return _PAISES.get(nombre, {}).get("iso3")


def region(nombre: str, idioma: str) -> str:
    return REGIONES_EN.get(nombre, nombre) if idioma == "en" else nombre


def metodo(texto: str, idioma: str) -> str:
    return METODOS_EN.get(texto, texto) if idioma == "en" else texto


def pasos_tour(idioma: str) -> list[dict]:
    return [dict(titulo=t(f"tour_{i}_t", idioma), texto=t(f"tour_{i}", idioma),
                 mirar=t(f"tour_{i}_m", idioma)) for i in (0, 1, 6, 2, 3, 4, 5)]


# Fuentes de la pestaña "Para qué sirve" (se citan tal cual, en su idioma original)
FUENTES_IMPACTO = [
    ("Xu, R. et al. (2024). Global, regional, and national mortality burden attributable to air pollution from "
     "landscape fires: a health impact assessment study. The Lancet, 404, 2447–2459.",
     "https://pubmed.ncbi.nlm.nih.gov/39615506/"),
    ("NASA Earthdata (2026). Transitioning from Suomi NPP VIIRS & OMPS: What FIRMS Users Need to Know.",
     "https://www.earthdata.nasa.gov/news/blog/transitioning-from-suomi-npp-viirs-omps-what-firms-users-need-know"),
    ("NASA LAADS DAAC. MODIS to VIIRS Transition.", "https://ladsweb.modaps.eosdis.nasa.gov/learn/modis-to-viirs-transition/"),
    ("El Observador (2026). Costa Rica cerró mayo con un aumento del 264 % en los incendios forestales.",
     "https://observador.cr/costa-rica-cerro-mayo-con-un-aumento-del-264-en-los-incendios-forestales/"),
    ("World Bank (2025). 2025 Global Gas Flaring Tracker Report.",
     "https://www.worldbank.org/en/programs/gasflaringreduction/publication/2025-global-gas-flaring-tracker-report"),
]
