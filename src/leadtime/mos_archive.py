"""IEM MOS archive (https://mesonet.agron.iastate.edu/mos/): bulk download and cache.

Endpoint (the "Download the raw data" form on /mos/fe.phtml):
  /cgi-bin/request/mos.py?station=KTTN&model=GFS&year1=..&month1=..&day1=..&hour1=0&year2=..&month2=..&day2=..&hour2=23
It returns one CSV with every run of the model in the range and every forecast row of each run.
Columns of interest: runtime, ftime (valid time, UTC), p06, p12 (probability of measurable precipitation in the
6 or 12 hours ending at ftime, percent), p24 (MEX only: 24 hours ending at ftime, percent).

Archive status printed on /mos/ (read 2026-11-12): AVN 2000-06-01 to 2003-12-16; GFS (MAV) 2003-12-16 to now;
MEX 2020-07-12 to now; NBS 2018-11-07 to now; NBE 2020-07-23 to now. The archive keeps only the 6-hourly forecast
rows of NBS/NBE after seven days, and only four runs a day.

One request at a time, with a pause between requests; the server answers 429 when asked too fast.
Every response is cached as data/raw/mos/<model>_<station>_<year>.csv and never fetched twice.
"""
from __future__ import annotations

import time
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RAW_MOS = REPO / "data" / "raw" / "mos"
BASE = "https://mesonet.agron.iastate.edu/cgi-bin/request/mos.py"
STATIONS = ("KTTN", "KPHL")
# first and last season the archive can serve for each model (May-Sep seasons; partial first seasons noted)
MODEL_YEARS = {
    "AVN": range(2000, 2004),   # 2000 from June 1 (archive start)
    "GFS": range(2004, 2027),
    "MEX": range(2020, 2027),   # 2020 from July 12
    "NBS": range(2019, 2027),
    "NBE": range(2020, 2027),   # 2020 from July 23
}
PULL_START = (4, 23)   # April 23: a 7-day lead for May 1 needs runs from April 25
PULL_END = (9, 30)
GAP_SECONDS = 6.0


def cache_path(model: str, station: str, year: int, raw: Path = RAW_MOS) -> Path:
    return raw / f"{model}_{station}_{year}.csv"


def request_url(model: str, station: str, year: int) -> str:
    q = {"station": station, "model": model,
         "year1": year, "month1": PULL_START[0], "day1": PULL_START[1], "hour1": 0,
         "year2": year, "month2": PULL_END[0], "day2": PULL_END[1], "hour2": 23}
    return BASE + "?" + urllib.parse.urlencode(q)


def fetch(url: str, timeout: float = 120.0, retries: int = 6) -> bytes:
    """GET with a retry on HTTP 429 or 5xx (sleeps 60 s, then 120 s, ...)."""
    wait = 60.0
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "mos-archive-cache/1.0"}),
                                        timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(wait)
                wait *= 2
                continue
            raise
    raise RuntimeError("unreachable")


def pull_one(model: str, station: str, year: int, raw: Path = RAW_MOS, gap: float = GAP_SECONDS,
             log=print) -> tuple[Path, bool]:
    """Fetch one model-station-season CSV into the cache. Returns (path, fetched_now)."""
    path = cache_path(model, station, year, raw)
    if path.exists() and path.stat().st_size > 0:
        return path, False
    raw.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    body = fetch(request_url(model, station, year))
    tmp = path.with_suffix(".part")
    tmp.write_bytes(body)
    tmp.replace(path)
    log(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {model} {station} {year} {len(body)} bytes "
        f"{time.time() - t0:.1f} s")
    time.sleep(gap)
    return path, True


CHECK_STATIONS = ("KEWR", "KNYC")   # the other two Kalshi cities, 2025-2026 only, for the observed-end price check
CHECK_YEARS = (2025, 2026)


def pull_plan(models=("GFS", "MEX", "AVN", "NBS", "NBE"), stations=STATIONS) -> list[tuple[str, str, int]]:
    """(model, station, year) in pull order: GFS first (longest record), then MEX, AVN, NBS, NBE; then the
    price-check stations for 2025-2026 (GFS, MEX, NBS)."""
    plan = []
    for m in models:
        for y in MODEL_YEARS[m]:
            for s in stations:
                plan.append((m, s, y))
    for m in ("GFS", "MEX", "NBS"):
        if m in models:
            for y in CHECK_YEARS:
                for s in CHECK_STATIONS:
                    plan.append((m, s, y))
    return plan
