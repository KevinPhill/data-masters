"""Lanzador de Data Masters: instala lo que falte, prepara los datos y abre la app en el navegador.

En VS Code: abre este archivo y presiona ▷ (Run Python File).
En terminal: python run_app.py              (abre el navegador)
             python run_app.py --headless   (solo el servidor, p. ej. para pruebas)
"""

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable

# Usar un entorno virtual del proyecto si el Python actual no es uno (p. ej. Homebrew no deja instalar paquetes)
CANDIDATOS = [ROOT / ".venv" / "bin" / "python", Path.home() / ".venvs" / "ds" / "bin" / "python"]
if sys.prefix == sys.base_prefix:
    for c in CANDIDATOS:
        if c.exists():
            print(f"Usando el entorno {c.parent.parent}", flush=True)
            sys.exit(subprocess.call([str(c), __file__, *sys.argv[1:]]))
    print("Creando entorno .venv del proyecto…", flush=True)
    subprocess.check_call([PY, "-m", "venv", str(ROOT / ".venv")])
    sys.exit(subprocess.call([str(CANDIDATOS[0]), __file__, *sys.argv[1:]]))

faltan = [m for m in ("streamlit", "plotly", "folium", "streamlit_folium", "duckdb", "pyarrow", "requests")
          if importlib.util.find_spec(m) is None]
if faltan:
    print(f"Instalando dependencias que faltan: {faltan} …", flush=True)
    req = str(ROOT / "requirements.txt")
    uv = shutil.which("uv") or next((str(p) for p in (Path.home() / ".local/bin/uv", Path.home() / ".cargo/bin/uv",
                                                      Path("/opt/homebrew/bin/uv")) if p.exists()), None)
    intentos = []
    if uv:
        intentos.append([uv, "pip", "install", "--python", PY, "-q", "-r", req])
    intentos.append([PY, "-m", "pip", "install", "-q", "-r", req])
    for cmd in intentos:
        if subprocess.call(cmd) == 0:
            break
    else:  # ni uv ni pip: activar pip y reintentar
        subprocess.check_call([PY, "-m", "ensurepip", "--upgrade"])
        subprocess.check_call([PY, "-m", "pip", "install", "-q", "-r", req])

if not (ROOT / "data" / "app" / "celdas.parquet").exists():
    print("Preparando datos de la app (solo la primera vez, 1–3 min)…", flush=True)
    subprocess.check_call([PY, str(ROOT / "scripts" / "preparar_app.py")], cwd=ROOT)

HEADLESS = "--headless" in sys.argv[1:]
PUERTO = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--port=")), "8501")
print(f"\nAbriendo Data Masters en http://localhost:{PUERTO}  (Ctrl+C para detener)\n", flush=True)
# El tema (colores, fuentes locales) está en .streamlit/config.toml
subprocess.call([
    PY, "-m", "streamlit", "run", str(ROOT / "app" / "streamlit_app.py"),
    "--server.headless", "true" if HEADLESS else "false", "--server.port", PUERTO,
    "--server.enableStaticServing", "true", "--browser.gatherUsageStats", "false", "--client.toolbarMode", "minimal",
], cwd=ROOT)
