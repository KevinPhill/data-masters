# Data Masters — El calendario del fuego visto desde el espacio

NASA Space Apps Challenge 2026 · Costa Rica · Reto **Harmonization of MODIS and VIIRS Hot Spots**.

- **Demo:** https://data-masters.streamlit.app
- **Código:** https://github.com/KevinPhill/data-masters
- **Presentación** (7 filminas, en inglés): [PDF](docs/presentacion/Data_Masters.pdf) · [PowerPoint](docs/presentacion/Data_Masters.pptx)

MODIS (desde 2000) y VIIRS (desde 2012) cuentan el fuego de forma distinta: VIIRS ve unas 4.5 veces más detecciones. Si se unen tal cual, 2012 parece una ola de incendios que nunca existió. Data Masters los armoniza en una sola serie de 25 años, en detecciones equivalentes a VIIRS, para que brigadas forestales, gestores de alerta temprana y científicos sepan en segundos si **este mes es normal en su zona**.

Es integral: armoniza los cuatro tipos de punto de calor de FIRMS, cada uno con su propio modelo. Son la vegetación (incendios y quemas), la industria y el gas (quema de gas en pozos, refinerías, siderúrgicas), los volcanes y las plataformas costa afuera.

Datos: NASA FIRMS · Proyecto para NASA Space Apps Challenge 2026 Costa Rica. No es un producto oficial de la NASA.

![Data Masters: globo de países e historia del fuego de Costa Rica](docs/inicio.jpg)

## Qué hace
- **Globo de todos los países**: clic en uno y sale su historia del fuego (una frase, tres cifras y la serie armonizada contra MODIS tal cual); todo el análisis cambia a ese país.
- **Área de interés**: país (también con un clic en el globo), región de ejemplo o coordenadas con un radio; periodo de años y mes a evaluar.
- **Tipo de punto de calor**: todos, vegetación, industria y gas, volcanes o costa afuera. Cambia el globo, la ficha del país, el calendario, el mapa y la validación; la pestaña Tendencias muestra qué produce el calor año a año.
- **Estado del mes**: lo compara con la mediana histórica del mismo mes (razón, percentil y z robusto) y lo dice en una frase con semáforo.
- **Alertas por semana o por mes**: cada semana (o mes) contra la misma semana del año en los años anteriores. Avisa cuando hay una racha de alzas fuera de lo normal (3 semanas o 2 meses seguidos), o una sola semana que duplica lo normal. Lista las rachas del periodo y los países del mundo que están por encima de lo normal ese mes; con un clic se pasa a cualquiera de ellos. La vista por semana está para países y regiones de ejemplo.
- **Calendario de quemas** 2000–2025 (y hasta hoy con una MAP_KEY de FIRMS), tendencias, mapa de anomalías.
- **Últimos días**: detecciones VIIRS en tiempo casi real de FIRMS (NOAA-20 y NOAA-21) contra lo normal para esa semana del año.
- **Descargas**: informe HTML del área (se abre sin internet), resumen analítico CSV, calendario CSV y puntos de calor originales CSV entre dos fechas. Cada gráfica se guarda como PNG.
- **¿Cómo armonizamos?**: el modelo, antes y después, validación, R² y MSE, sobreajuste y en qué países no funciona.
- Tour para jueces, modo presentación, inglés (por defecto) y español, modo claro y noche.

## Cómo armonizamos
Modelo de la app: **integral**, un modelo para cada tipo de punto de calor de FIRMS.

1. El mundo se divide en celdas de 0.5° (~55 km) y se cuentan las detecciones de MODIS y de VIIRS por celda, mes y tipo: vegetación, volcanes, industria y gas, costa afuera.
2. **Vegetación** (93 % de lo que ve VIIRS): LightGBM (600 árboles, pérdida de Poisson) recibe 28 datos por celda y mes. Son lo que vio MODIS (Terra y Aqua, día y noche, potencia del fuego, confianza), la vecindad (celdas de alrededor, mes anterior y siguiente, historia de la celda), la posición del Sol, el lugar y la fecha. Aprende con 2012–2016 y 2018–2020 a predecir las detecciones de vegetación de VIIRS.
3. **Corrección regional** de la vegetación: en la validación dejando un año fuera se mide cuánto se pasa o se queda corto en cada región de 10° y mes (Σ VIIRS ÷ Σ predicho), y la predicción se multiplica por ese factor, acotado entre 0.5 y 2. El año que se predice nunca entra en su propio factor, y solo cuentan los meses con Terra, Aqua y VIIRS a la vez.
4. **Fuentes fijas** (volcanes, industria y gas, costa afuera; 31,332 celdas): cada celda tiene su propia relación, porque es siempre la misma chimenea, el mismo pozo o el mismo volcán. VIIRS = MODIS × el factor de la celda, más una base para lo que VIIRS ve y MODIS no alcanza (pozos y plataformas chicas). En 2018 esa relación cambia de golpe: VIIRS pasa de S-NPP a NOAA-20 y MODIS empieza a marcar unas 6 veces más volcanes. Por eso se aprende por separado antes y después de 2018. Supuesto: la base se mantiene hacia atrás en el tiempo.
5. En los meses sin VIIRS (2002–2011) se usa la predicción; donde hay VIIRS, lo observado. De noviembre de 2000 a junio de 2002 solo volaba Terra: ahí la vegetación usa la razón VIIRS/Terra de la región y el mes.
6. El rango de incertidumbre de cada mes estimado sale del error de cada modelo en la validación (percentiles 5 y 95 por región). En las fuentes fijas se acota entre un tercio y el triple de lo estimado.

**Validación** con predicciones que el modelo no vio: un año fuera a la vez en 2012–2021, y 2022–2025 enteros (años nunca vistos). Es el error típico por país y año:

| Tipo | Un año fuera | 2022–2025 | MODIS tal cual (un año fuera) |
|---|---|---|---|
| Todos | 5.5 % | 7.4 % | 80 % |
| Vegetación | 7.2 % | 8.9 % | 79 % |
| Industria y gas | 10.9 % | 17.4 % | 95 % |
| Costa afuera | 21.4 % | 29.2 % | 100 % |
| Volcanes | 22.1 % | 36.1 % | 94 % |

El total mundial por mes se equivoca 1.3 % (un año fuera) y 1.5 % (2022–2025).

**Evaluación** en los años de prueba 2017 y 2021, que el modelo no vio:

| Nivel | R² | R² (log) | MSE | RMSE | Error típico |
|---|---|---|---|---|---|
| Celda de 0.5° × mes | 0.941 | 0.817 | 4,661 | 68 | 26.1 % |
| País × mes | 0.997 | 0.967 | 2.9 × 10⁶ | 1,700 | 13.2 % |
| País × año | 0.999 | 0.975 | 4.8 × 10⁷ | 6,909 | 6.7 % |
| Mundo × mes | 0.998 | 0.996 | 8.2 × 10⁸ | 28,711 | 1.3 % |

![Antes y después de armonizar, validación y métricas](docs/validacion.jpg)

- **Sobreajuste**: no. De entrenamiento a prueba, el R² (log) por celda pasa de 0.836 a 0.817 y el error por país y año de 4.5 % a 6.7 %. En años nunca vistos (2022–2025) quedan en 0.794 y 7.5 %.
- **Comparación**: se probaron cinco modelos con los mismos años. Este es el error típico por país y año en prueba:

  | Modelo | Error típico |
  |---|---|
  | Un solo factor mundial | 19.8 % |
  | Razón VIIRS/MODIS por región y mes | 10.0 % |
  | LightGBM | 7.0 % |
  | LightGBM con corrección regional | 6.7 % |
  | Integral | 6.7 % |

  El integral tiene el mejor R² (log) por celda: 0.817, contra 0.775 de LightGBM con corrección. También tiene el mejor R² (log) por país y mes y por país y año, y es el que falla en menos países. LightGBM con corrección se equivoca un poco menos por país y mes (12.7 % contra 13.2 %). En MSE gana LightGBM sin corrección en todos los niveles: el MSE pesa sobre todo las celdas con miles de detecciones, y el integral acierta mejor también en las celdas chicas.
- **Dónde no funciona**: son 149 los países con al menos 1,000 detecciones al año. El integral funciona bien en 130, regular en 13 y no funciona bien en 6: Yemen, Trinidad y Tobago, Vanuatu, Haití, Islandia y Baréin. Cuatro de ellos tienen mucha quema que no es de vegetación: volcanes que entran en erupción algunos años, o pozos de gas que se abren y se cierran. El modelo por celda no puede adivinar una erupción ni un pozo nuevo que MODIS no vio.
  - Separar los tipos arregló Corea del Norte, Grecia, Noruega y Suecia, donde fallaba LightGBM con corrección.
  - Con la razón simple fallan 31.
  - En Costa Rica funciona bien: 9.2 % de error típico por año (igual que la razón simple) y 15.0 % por mes.

## Uso de inteligencia artificial
Las guías de Space Apps 2026 llaman a estas herramientas "Super Intelligence (SI)". Aquí está todo lo que se usó y cómo.

- **IA generativa, como asistente de programación**: Claude (Anthropic), usado a través de Claude Code.
  - Código: escribió y refactorizó la mayor parte del Python: la app, el flujo de datos, los scripts de entrenamiento y validación del modelo y las pruebas automáticas de la interfaz.
  - Diseño y textos: el diseño de la interfaz y el CSS, los textos de la interfaz en español e inglés y sus traducciones, y este README.
  - Fuentes: ayudó a buscar y revisar las fuentes públicas que se citan.
  - Presentación: las filminas de `docs/presentacion/` se redactaron con Claude y se dibujan desde HTML.
- **Aprendizaje automático dentro del producto (no generativo)**: LightGBM (gradient boosting), entrenado con datos de NASA FIRMS, estima las detecciones equivalentes a VIIRS a partir de MODIS para los fuegos de vegetación. Lo demás es estadística: un factor de corrección regional y una relación lineal por celda para las fuentes fijas. También se probaron y compararon un solo factor mundial, la razón por región y mes y, en el notebook del modelo, una red neuronal pequeña. En la app no corre ningún modelo de lenguaje ni de imágenes.
- **Lo que hizo el equipo**: eligió el reto y la idea, definió las prioridades y la dirección del diseño, tomó las decisiones (qué modelo usar, el enfoque integral, la regla de alertas) y revisó y probó los resultados.
- **Sin imágenes, video ni audio generados con IA**: las gráficas y el globo se dibujan con los datos, los contornos del mapa vienen de un TopoJSON público y las tipografías son Fira Sans y Overpass (OFL). Las imágenes de la presentación son capturas de la app.

## Correr la app
```bash
pip install -r requirements.txt
python run_app.py              # abre http://localhost:8501
python run_app.py --headless   # solo el servidor
```
El repositorio trae los datos que usa la app (`data/app`, ~110 MB), así que funciona sin descargar nada más. Tipografías y mapas se sirven desde `app/static`: no necesita internet, salvo "Últimos días", que consulta FIRMS. Para completar el calendario hasta hoy hace falta una MAP_KEY gratuita de FIRMS (https://firms.modaps.eosdis.nasa.gov/api/map_key/), en la app o en la variable `FIRMS_MAP_KEY`.

Sin la base completa de detecciones (`data/db_nasa.duckdb`, ~6 GB), la descarga de puntos de calor originales cubre Centroamérica (`data/app/puntos_centroamerica.parquet`).

## Reproducir desde cero
Con `pip install -r requirements-modelo.txt` (agrega LightGBM, scikit-learn, PyTorch y matplotlib).

1. Descargar de NASA FIRMS los resúmenes anuales por país (https://firms.modaps.eosdis.nasa.gov/country/, procesamiento estándar) a `data/raw/`: `modis_2000..2025_all_countries.zip`, `viirs-snpp_2012..2017_all_countries.zip` y `viirs-jpss1_2018..2025_all_countries.zip`.
2. `python scripts/crear_db.py`: une los ZIP en Parquet (`scripts/consolidar.py`) y crea `data/db_nasa.duckdb`.
3. `notebooks/03_modelo.ipynb`: arma la tabla celda × mes, entrena y valida los modelos y guarda `data/modelo/` (el análisis exploratorio global está en `02_eda`).
4. `python scripts/modelo_integral.py` (~40 min): conteos por tipo de fuente y LightGBM de vegetación, con su validación dejando un año fuera → `data/modelo/tipos_celdas.parquet`, `veg_celdas.parquet`, `veg_loyo.parquet`.
5. `python scripts/preparar_app.py`: arma `data/app` (celdas armonizadas por tipo, meses, países).
6. `python scripts/semanas.py`: reparte cada mes armonizado entre sus semanas según lo que vio el sensor de ese mes, por país y región de ejemplo → `data/app/semanas.parquet` y `paises_mes.parquet` (alertas).
7. `python scripts/validar.py`: validación dejando un año fuera y en años nunca vistos, total y por tipo → `data/app/validacion.*` y `serie_mundial.csv`.
8. `python scripts/evaluar_modelos.py` (~6 min): R², MSE, sobreajuste y países donde falla, para los cinco modelos → `data/app/evaluacion.*`.
9. `python scripts/exportar_puntos.py`: puntos de calor de Centroamérica para correr sin la base completa.

**Presentación**: `python scripts/presentacion.py` vuelve a generar `docs/presentacion/Data_Masters.pdf` y `.pptx` desde `docs/presentacion/fuente/` (HTML, CSS y capturas de la app). Necesita `pip install playwright python-pptx pypdf` y Google Chrome (o `playwright install chromium`). Con `--demo URL` cambia el enlace de la demo y con `--equipo "Nombres"` agrega a los integrantes en la portada.

## Estructura
```
app/                 la app de Streamlit (streamlit_app.py, datos, gráficas, textos ES/EN, estilos)
app/static/          tipografías (OFL) y mapas servidos localmente
data/app/            datos listos para la app
data/modelo/         serie mundial armonizada (los Parquet del modelo se regeneran con el notebook 03 y scripts/modelo_integral.py)
docs/presentacion/   presentación en PDF y PPTX; en fuente/ están el HTML, el CSS y las capturas con que se genera
notebooks/           análisis exploratorio y modelo
scripts/             consolidar, base de datos, modelo integral, preparar, semanas, validar, evaluar, exportar y presentación
```

Colores y tipografías siguen la guía de marca de NASA Space Apps: azules Electric, Neon, Blue Yonder y Deep Blue, Rocket Red y Martian Red para el fuego, Neon Yellow solo como acento; Fira Sans y Overpass. No se usa ningún logo de la NASA ni de Space Apps.
