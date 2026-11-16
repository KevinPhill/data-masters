# AI-assisted code (Claude, Anthropic), directed and reviewed by the team. See README: "Use of artificial intelligence".
"""Exporta los puntos de calor originales de Centroamérica a un Parquet liviano.

La app descarga puntos de calor desde data/db_nasa.duckdb (~6 GB, todo el mundo). Donde esa base no está,
como en la demo en línea, usa este archivo: todos los sensores, 2000–2025, siete países.

Salida: data/app/puntos_centroamerica.parquet (~22 MB)

Uso:  python scripts/exportar_puntos.py
"""

from __future__ import annotations

import time
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "db_nasa.duckdb"
SALIDA = ROOT / "data" / "app" / "puntos_centroamerica.parquet"
PAISES = ["Belize", "Costa Rica", "El Salvador", "Guatemala", "Honduras", "Nicaragua", "Panama"]


def main():
    t0 = time.time()
    if not DB.exists():
        raise SystemExit(f"Falta {DB}. Créala con scripts/crear_db.py.")
    con = duckdb.connect(str(DB), read_only=True)
    lista = ", ".join(f"'{p}'" for p in PAISES)
    con.execute(f"""
    COPY (
      SELECT sensor, satellite, country, latitude, longitude, acq_date, CAST(acq_time AS SMALLINT) acq_time,
             confidence, frp, daynight, type
      FROM hotspots WHERE country IN ({lista}) ORDER BY country, acq_date
    ) TO '{SALIDA.as_posix()}' (FORMAT parquet, COMPRESSION zstd, COMPRESSION_LEVEL 19, ROW_GROUP_SIZE 200000)
    """)
    n = con.sql(f"SELECT count(*) FROM '{SALIDA.as_posix()}'").fetchall()[0][0]
    print(f"{n:,} puntos · {SALIDA.stat().st_size / 1e6:.1f} MB · {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
