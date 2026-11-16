# AI-assisted code (Claude, Anthropic), directed and reviewed by the team. See README: "Use of artificial intelligence".
"""Consolidates the yearly NASA FIRMS ZIPs (data/raw) into a single Parquet table.

Input:   data/raw/<sensor>_<year>_all_countries.zip   (as downloaded, not unzipped)
Output:  data/consolidado/<SENSOR>/<SENSOR>_<YEAR>.parquet

Every row ends up with the same columns, whatever the sensor:
    sensor, satellite, country, latitude, longitude, acq_date, acq_time,
    confidence, bright_mir, bright_tir, scan, track, frp, daynight, type, version

    bright_mir = MODIS `brightness` / VIIRS `bright_ti4`
    bright_tir = MODIS `bright_t31` / VIIRS `bright_ti5`

It does not filter or modify data: it only joins files and unifies columns.

Usage:
    python scripts/consolidar.py                  # everything, in parallel, resumable
    python scripts/consolidar.py --workers 6
    python scripts/consolidar.py --paises "Costa Rica" Nicaragua Panama
    python scripts/consolidar.py --force          # redo even if it already exists

Reading the result:
    import pandas as pd
    df = pd.read_parquet("data/consolidado", filters=[("country", "==", "Costa Rica")])
    df = pd.read_parquet("data/consolidado/MODIS")          # a single sensor
    # or with DuckDB:  SELECT * FROM 'data/consolidado/**/*.parquet'
"""

from __future__ import annotations

import argparse
import io
import os
import re
import time
import zipfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "consolidado"

SENSORS = {  # file prefix -> sensor name
    "modis": "MODIS",
    "viirs-snpp": "VIIRS_SNPP",
    "viirs-jpss1": "VIIRS_NOAA20",
    "viirs-jpss2": "VIIRS_NOAA21",
}
RENAME = {"brightness": "bright_mir", "bright_ti4": "bright_mir",
          "bright_t31": "bright_tir", "bright_ti5": "bright_tir"}
SCHEMA = pa.schema([
    ("sensor", pa.string()), ("satellite", pa.string()), ("country", pa.string()),
    ("latitude", pa.float64()), ("longitude", pa.float64()),
    ("acq_date", pa.date32()), ("acq_time", pa.int16()),
    ("confidence", pa.string()), ("bright_mir", pa.float32()), ("bright_tir", pa.float32()),
    ("scan", pa.float32()), ("track", pa.float32()), ("frp", pa.float32()),
    ("daynight", pa.string()), ("type", pa.int8()), ("version", pa.string()),
])
FILE_RE = re.compile(r"^(?P<prefix>[a-z0-9-]+?)_(?P<year>\d{4})_all_countries\.zip$", re.I)
COUNTRY_RE = re.compile(r"_\d{4}_(?P<country>.+)\.csv$", re.I)


def parse_name(path: Path):
    m = FILE_RE.match(path.name)
    if not m or m.group("prefix").lower() not in SENSORS:
        return None
    return SENSORS[m.group("prefix").lower()], int(m.group("year"))


def out_path(sensor: str, year: int) -> Path:
    return OUT / sensor / f"{sensor}_{year}.parquet"


def normalize(df: pd.DataFrame, sensor: str, country: str) -> pa.Table:
    df.columns = [c.strip().lower() for c in df.columns]
    df = df.rename(columns=RENAME)
    df["sensor"] = sensor
    df["country"] = country
    if "type" not in df.columns:
        df["type"] = 0
    for f in SCHEMA:
        if f.name not in df.columns:
            df[f.name] = None
    df = df[SCHEMA.names]
    df["acq_date"] = pd.to_datetime(df["acq_date"]).dt.date
    for c in ("satellite", "confidence", "daynight", "version"):
        df[c] = df[c].astype("string")
    return pa.Table.from_pandas(df, schema=SCHEMA, preserve_index=False, safe=False)


def consolidate_zip(path: str, paises: list[str] | None) -> dict:
    path = Path(path)
    sensor, year = parse_name(path)
    dest = out_path(sensor, year)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".tmp")
    t0, rows, n_countries = time.time(), 0, 0
    writer = pq.ParquetWriter(tmp, SCHEMA, compression="zstd")
    try:
        with zipfile.ZipFile(path) as zf:
            for info in zf.infolist():
                m = COUNTRY_RE.search(info.filename)
                if not m:
                    continue
                country = m.group("country").replace("_", " ")
                if paises and country not in paises:
                    continue
                with zf.open(info) as fh:
                    df = pd.read_csv(io.TextIOWrapper(fh, encoding="utf-8", errors="replace"),
                                     dtype={"confidence": str, "satellite": str, "version": str},
                                     low_memory=False)
                if df.empty:
                    continue
                writer.write_table(normalize(df, sensor, country))
                rows += len(df)
                n_countries += 1
    finally:
        writer.close()
    tmp.replace(dest)
    return {"archivo": path.name, "filas": rows, "paises": n_countries, "seg": round(time.time() - t0, 1)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--paises", nargs="*", help='solo estos países, p. ej. "Costa Rica" Nicaragua')
    ap.add_argument("--force", action="store_true", help="redo even if the output already exists")
    ap.add_argument("--raw", type=Path, default=RAW)
    args = ap.parse_args()

    zips = [p for p in sorted(args.raw.glob("*.zip")) if parse_name(p)]
    if not zips:
        raise SystemExit(f"No hay ZIP de FIRMS en {args.raw}")
    todo = [p for p in zips if args.force or not out_path(*parse_name(p)).exists()]
    print(f"{len(zips)} ZIPs found, {len(todo)} to consolidate, {args.workers} processes -> {OUT}")

    t0, total = time.time(), 0
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(consolidate_zip, str(p), args.paises): p for p in todo}
        for i, fut in enumerate(as_completed(futs), 1):
            try:
                r = fut.result()
                total += r["filas"]
                print(f"  [{i}/{len(todo)}] {r['archivo']}: {r['filas']:,} rows, {r['paises']} countries ({r['seg']} s)")
            except Exception as e:
                print(f"  [{i}/{len(todo)}] ERROR {futs[fut].name}: {e}")
    print(f"Done: {total:,} new rows in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
