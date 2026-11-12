"""Pull GHCN-Daily TMAX straight from NOAA NCEI (for a laptop with normal internet).

Writes the same long format as scripts/pull_ceraunic_cache.py, so src/load_weather.py can read either:
    data/raw/ghcnd_tmax_ncei.csv   columns: date, station_id, tmax_f, qflag
and appends one row per HTTP request to data/manifests/ncei_pull_manifest.csv.

Source: NCEI Access Data Service, daily-summaries dataset (GHCN-Daily). No key, no account.
    https://www.ncei.noaa.gov/access/services/data/v1?dataset=daily-summaries&stations=ID
        &startDate=YYYY-MM-DD&endDate=YYYY-MM-DD&dataTypes=TMAX&units=standard&format=csv
        &includeAttributes=true

Usage:
    python scripts/pull_ghcnd.py                    # all stations in data/manifests/stations.csv
    python scripts/pull_ghcnd.py --start 2015-01-01 --end 2025-12-31
    python scripts/pull_ghcnd.py --stations USW00094728,USW00014792

Values with a non-blank GHCN quality flag are kept in the file but set to missing by the loader.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIONS = ROOT / "data" / "manifests" / "stations.csv"
OUT = ROOT / "data" / "raw" / "ghcnd_tmax_ncei.csv"
MANIFEST = ROOT / "data" / "manifests" / "ncei_pull_manifest.csv"
BASE = "https://www.ncei.noaa.gov/access/services/data/v1"


def url_for(station: str, start: str, end: str) -> str:
    return (f"{BASE}?dataset=daily-summaries&stations={station}&startDate={start}&endDate={end}"
            "&dataTypes=TMAX&units=standard&format=csv&includeAttributes=true")


def parse(text: str, station: str) -> list[dict]:
    """Parse one NCEI CSV response. TMAX_ATTRIBUTES is 'mflag,qflag,sflag,obstime'."""
    rows = []
    for r in csv.DictReader(io.StringIO(text)):
        v = (r.get("TMAX") or "").strip()
        if v == "":
            continue
        attrs = (r.get("TMAX_ATTRIBUTES") or "").split(",")
        q = attrs[1].strip() if len(attrs) > 1 else ""
        rows.append({"date": r["DATE"], "station_id": r.get("STATION", station),
                     "tmax_f": int(round(float(v))), "qflag": q})
    return rows


def fetch(url: str, tries: int = 3) -> bytes:
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=120) as resp:
                return resp.read()
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(5 * (i + 1))
    raise RuntimeError("unreachable")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2010-01-01")
    ap.add_argument("--end", default="2025-12-31")
    ap.add_argument("--stations", default="")
    a = ap.parse_args()
    if a.stations:
        ids = a.stations.split(",")
    else:
        with STATIONS.open() as f:
            ids = sorted({r["station_id"] for r in csv.DictReader(f)})
    all_rows: list[dict] = []
    man: list[dict] = []
    for sid in ids:
        # one request per station per 5-year block keeps responses small
        y0, y1 = int(a.start[:4]), int(a.end[:4])
        for ys in range(y0, y1 + 1, 5):
            s = max(a.start, f"{ys}-01-01")
            e = min(a.end, f"{min(ys + 4, y1)}-12-31")
            u = url_for(sid, s, e)
            body = fetch(u)
            rows = parse(body.decode("utf-8"), sid)
            all_rows += rows
            man.append({"url": u, "station_id": sid, "start": s, "end": e, "bytes": len(body),
                        "md5": hashlib.md5(body).hexdigest(), "rows": len(rows),
                        "fetched_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
            print(sid, s, e, len(rows))
            time.sleep(1)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["date", "station_id", "tmax_f", "qflag"])
        w.writeheader()
        w.writerows(sorted(all_rows, key=lambda r: (r["station_id"], r["date"])))
    new = not MANIFEST.exists()
    with MANIFEST.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(man[0]))
        if new:
            w.writeheader()
        w.writerows(man)
    print(f"wrote {OUT} rows={len(all_rows)}")


if __name__ == "__main__":
    main()
