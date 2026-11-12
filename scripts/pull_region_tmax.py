"""Pull daily TMAX (deg F) for every candidate station in the region from NOAA NCEI.

Source: NCEI Access Data Service, dataset daily-summaries (GHCN-Daily), no token needed.
  https://www.ncei.noaa.gov/access/services/data/v1
Station list: ghcnd-stations.txt + ghcnd-inventory.txt (same NCEI folder), filtered to
states NY NJ PA CT DE MD with a TMAX record whose first year <= 2015 and last year >= 2025.

Outputs (under data/raw/region/):
  stations_region.csv   id, name, state, lat, lon, elev_m, tmax_first, tmax_last
  tmax/{ID}.csv         DATE, TMAX (deg F, units=standard), one file per station
  pull_log.csv          id, rows, status, pulled_utc

Usage: python scripts/pull_region_tmax.py [--workers 6]
Re-running skips stations already saved.
"""
from __future__ import annotations

import argparse
import csv
import io
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "region"
META = "https://www.ncei.noaa.gov/pub/data/ghcn/daily/"
API = "https://www.ncei.noaa.gov/access/services/data/v1"
STATES = {"NY", "NJ", "PA", "CT", "DE", "MD"}
START, END = "2015-01-01", "2025-12-31"


def fetch(url: str, tries: int = 4, timeout: int = 120) -> bytes:
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001 - retry any network error, re-raise at the end
            last = e
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"failed after {tries} tries: {url}: {last}")


def station_list() -> list[dict]:
    meta = OUT / "meta"
    meta.mkdir(parents=True, exist_ok=True)
    for name in ("ghcnd-stations.txt", "ghcnd-inventory.txt"):
        p = meta / name
        if not p.exists():
            p.write_bytes(fetch(META + name))
    st = {}
    for line in (meta / "ghcnd-stations.txt").read_text().splitlines():
        st[line[:11]] = dict(lat=float(line[12:20]), lon=float(line[21:30]), elev_m=float(line[31:37]),
                             state=line[38:40].strip(), name=line[41:71].strip())
    rows = []
    for line in (meta / "ghcnd-inventory.txt").read_text().splitlines():
        p = line.split()
        if p[3] != "TMAX" or p[0] not in st:
            continue
        s = st[p[0]]
        if s["state"] in STATES and int(p[4]) <= 2015 and int(p[5]) >= 2025:
            rows.append(dict(id=p[0], **s, tmax_first=int(p[4]), tmax_last=int(p[5])))
    rows.sort(key=lambda r: r["id"])
    with open(OUT / "stations_region.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "name", "state", "lat", "lon", "elev_m", "tmax_first", "tmax_last"])
        w.writeheader()
        w.writerows(rows)
    return rows


def pull_one(sid: str) -> tuple[str, int, str]:
    dest = OUT / "tmax" / f"{sid}.csv"
    if dest.exists() and dest.stat().st_size > 0:
        return sid, sum(1 for _ in open(dest)) - 1, "cached"
    url = (f"{API}?dataset=daily-summaries&stations={sid}&startDate={START}&endDate={END}"
           f"&dataTypes=TMAX&units=standard&format=csv")
    try:
        raw = fetch(url).decode("utf-8", "replace")
    except RuntimeError as e:
        return sid, 0, f"error: {e}"
    rdr = csv.DictReader(io.StringIO(raw))
    if not rdr.fieldnames or "DATE" not in rdr.fieldnames:
        return sid, 0, "error: unexpected response"
    n = 0
    with open(dest, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["DATE", "TMAX"])
        for r in rdr:
            v = (r.get("TMAX") or "").strip()
            if v:
                w.writerow([r["DATE"], v])
                n += 1
    return sid, n, "ok"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    (OUT / "tmax").mkdir(parents=True, exist_ok=True)
    stations = station_list()
    print(f"{len(stations)} candidate stations", flush=True)
    log = []
    with ThreadPoolExecutor(a.workers) as ex:
        futs = [ex.submit(pull_one, s["id"]) for s in stations]
        for i, fu in enumerate(as_completed(futs), 1):
            sid, n, status = fu.result()
            log.append((sid, n, status, datetime.now(timezone.utc).isoformat(timespec="seconds")))
            if i % 25 == 0 or status.startswith("error"):
                print(f"{i}/{len(stations)} {sid} rows={n} {status}", flush=True)
    with open(OUT / "pull_log.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "rows", "status", "pulled_utc"])
        w.writerows(sorted(log))
    bad = [r for r in log if r[2].startswith("error")]
    print(f"done: {len(log) - len(bad)} ok, {len(bad)} errors", flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
