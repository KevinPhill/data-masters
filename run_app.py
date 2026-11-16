# AI-assisted code (Claude, Anthropic), directed and reviewed by the team. See README: "Use of artificial intelligence".
"""Data Masters launcher: installs what is missing, prepares the data and opens the app in the browser.

In VS Code: open this file and press ▷ (Run Python File).
In a terminal: python run_app.py              (opens the browser)
               python run_app.py --headless   (server only, e.g. for tests)
"""

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable

# Use a project virtual environment if the current Python is not one (e.g. Homebrew does not allow installing packages)
CANDIDATOS = [ROOT / ".venv" / "bin" / "python", Path.home() / ".venvs" / "ds" / "bin" / "python"]
if sys.prefix == sys.base_prefix:
    for c in CANDIDATOS:
        if c.exists():
            print(f"Using the environment {c.parent.parent}", flush=True)
            sys.exit(subprocess.call([str(c), __file__, *sys.argv[1:]]))
    print("Creating the project .venv environment…", flush=True)
    subprocess.check_call([PY, "-m", "venv", str(ROOT / ".venv")])
    sys.exit(subprocess.call([str(CANDIDATOS[0]), __file__, *sys.argv[1:]]))

faltan = [m for m in ("streamlit", "plotly", "duckdb", "pyarrow", "requests")
          if importlib.util.find_spec(m) is None]
if faltan:
    print(f"Installing missing dependencies: {faltan} …", flush=True)
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
    else:  # neither uv nor pip: enable pip and retry
        subprocess.check_call([PY, "-m", "ensurepip", "--upgrade"])
        subprocess.check_call([PY, "-m", "pip", "install", "-q", "-r", req])

if not (ROOT / "data" / "app" / "celdas.parquet").exists():
    print("Preparing the app data (first time only, 1–3 min)…", flush=True)
    subprocess.check_call([PY, str(ROOT / "scripts" / "preparar_app.py")], cwd=ROOT)

HEADLESS = "--headless" in sys.argv[1:]
PUERTO = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--port=")), "8501")
print(f"\nOpening Data Masters at http://localhost:{PUERTO}  (Ctrl+C to stop)\n", flush=True)
# The theme (colours, local fonts) is in .streamlit/config.toml
subprocess.call([
    PY, "-m", "streamlit", "run", str(ROOT / "app" / "streamlit_app.py"),
    "--server.headless", "true" if HEADLESS else "false", "--server.port", PUERTO,
    "--server.enableStaticServing", "true", "--browser.gatherUsageStats", "false", "--client.toolbarMode", "minimal",
], cwd=ROOT)
