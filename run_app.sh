#!/usr/bin/env bash
# Lanza Data Masters (Streamlit) desde la raíz del proyecto. El tema está en .streamlit/config.toml.
cd "$(dirname "$0")"
[ -f .venv/bin/activate ] && source .venv/bin/activate
if [ ! -f data/app/celdas.parquet ]; then
  echo "Preparando datos de la app (solo la primera vez)…"
  python scripts/preparar_app.py || exit 1
fi
exec streamlit run app/streamlit_app.py \
  --server.enableStaticServing true --client.toolbarMode minimal \
  --browser.gatherUsageStats false "$@"
