"""Phase 3 rain reach, step 2: pull hourly precipitation for every candidate station, one request at a time.

    python scripts/reach_rain_fetch.py iem    # IEM asos.py, p01i + METAR text, 1990-01-01 .. 2026-11-01 (UTC)
    python scripts/reach_rain_fetch.py ncei   # NCEI global-hourly (ISD) AA1..AA4, 1941-2005 in 10-year blocks

Same requests as Phase 0 (scripts/p0_rain_fetch_iem.py, p0_rain_fetch_ncei_hourly.py), same parsing later.
Cache (never re-fetched when present): data/raw/rain/reach/iem_asos/<SID>_B.csv.gz,
data/raw/rain/reach/ncei_global_hourly/<SID>_<y0>_<y1>.csv.gz. Every request is appended to requests.log.
The 12 Phase 0 stations already have reduced hourly files in data/processed/rain_probe/ and are skipped.
Stations are pulled in order of archive_begin (long records first). The NCEI pull is skipped for stations whose
IEM archive begins in 1990 or later (nothing pre-ASOS to find) or that have no USAF/WBAN id, and 10-year blocks
outside the station's isd-history BEGIN..END years are not requested.
"""
import gzip
import os
import subprocess
import sys
import time

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw", "rain", "reach")
PHASE0 = ("TTN", "PHL", "PNE", "ABE", "EWR", "NYC", "JFK", "LGA", "WRI", "NEL", "BLM", "DYL")
IEM = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"
NCEI = "https://www.ncei.noaa.gov/access/services/data/v1"


def _curl(url: str, timeout: int) -> tuple[str, bytes, str]:
    r = subprocess.run(["curl", "-sS", "--compressed", "-m", str(timeout), "-w", "%{http_code}", "-o", "-", url],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return r.stdout[-3:].decode(), r.stdout[:-3], r.stderr.decode()[:200]


def _log(kind: str, sid: str, code: str, n: int, url: str) -> None:
    with open(os.path.join(RAW, kind, "requests.log"), "a") as lg:
        lg.write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\t{sid}\t{code}\t{n}\t{url}\n")


def fetch_iem(sid: str) -> None:
    dst = os.path.join(RAW, "iem_asos", f"{sid}_B.csv.gz")
    if os.path.exists(dst):
        return
    url = (f"{IEM}?station={sid}&data=p01i&data=metar&sts=1990-01-01T00:00:00Z&ets=2026-11-01T00:00:00Z"
           f"&report_type=3&report_type=4&tz=UTC&format=onlycomma&missing=M&trace=T")
    for attempt in range(4):
        t0 = time.time()
        code, body, err = _curl(url, 1500)
        ok = code == "200" and body.startswith(b"station,valid")
        print(f"IEM {sid} http={code} bytes={len(body)} secs={time.time()-t0:.0f} ok={ok} {err}", flush=True)
        _log("iem_asos", sid, code, len(body), url)
        if ok:
            with open(dst + ".part", "wb") as fh:
                fh.write(gzip.compress(body, 6))
            os.replace(dst + ".part", dst)
            return
        time.sleep(20 * (attempt + 1))
    print(f"FAILED IEM {sid}", flush=True)


def isd_years(ids: str, hist: pd.DataFrame) -> tuple[int, int]:
    """(first, last) year covered by isd-history for these USAF+WBAN ids; blocks outside are not requested."""
    h = hist[(hist["USAF"] + hist["WBAN"]).isin(ids.split(","))]
    return int(h["BEGIN"].str[:4].min()), int(h["END"].str[:4].max())


def fetch_ncei(sid: str, ids: str, years: tuple[int, int] = (1941, 2005)) -> None:
    for y0 in range(1941, 2006, 10):
        y1 = min(y0 + 9, 2005)
        dst = os.path.join(RAW, "ncei_global_hourly", f"{sid}_{y0}_{y1}.csv.gz")
        if os.path.exists(dst) or y1 < years[0] or y0 > years[1]:
            continue
        url = (f"{NCEI}?dataset=global-hourly&stations={ids}&dataTypes=AA1,AA2,AA3,AA4"
               f"&startDate={y0}-01-01&endDate={y1}-12-31&format=csv")
        for attempt in range(4):
            t0 = time.time()
            code, body, err = _curl(url, 900)
            print(f"NCEI {sid} {y0}-{y1} http={code} bytes={len(body)} secs={time.time()-t0:.0f} {err}", flush=True)
            _log("ncei_global_hourly", sid, code, len(body), url)
            if code == "200":
                with open(dst + ".part", "wb") as fh:
                    fh.write(gzip.compress(body, 6))
                os.replace(dst + ".part", dst)
                break
            time.sleep(15 * (attempt + 1))
        time.sleep(1.5)


if __name__ == "__main__":
    kind = sys.argv[1]
    st = pd.read_csv(os.path.join(ROOT, "data", "processed", "reach", "rain_stations_candidates.csv"), dtype=str)
    st = st[~st["sid"].isin(PHASE0)].sort_values(["archive_begin", "sid"])
    os.makedirs(os.path.join(RAW, "iem_asos"), exist_ok=True)
    os.makedirs(os.path.join(RAW, "ncei_global_hourly"), exist_ok=True)
    hist = pd.read_csv(os.path.join(ROOT, "data", "raw", "rain", "ncei_global_hourly_probe", "isd-history.csv"),
                       dtype=str)
    for _, r in st.iterrows():
        if kind == "iem":
            fetch_iem(r["sid"])
            time.sleep(3)
        elif kind == "ncei":
            if r["archive_begin"] >= "1990" or not isinstance(r["isd_ids"], str) or not r["isd_ids"]:
                continue
            fetch_ncei(r["sid"], r["isd_ids"], isd_years(r["isd_ids"], hist))
    print("done", kind, flush=True)
