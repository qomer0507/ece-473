"""Phase 3 rain reach, step 3: hourly reduction, daily tables, season counts and the station table.

    python scripts/reach_rain_build.py

Reads  data/processed/reach/rain_stations_candidates.csv
       data/raw/rain/reach/iem_asos/<SID>_B.csv.gz, data/raw/rain/reach/ncei_global_hourly/<SID>_*.csv.gz
       data/processed/rain_probe/hourly_maysep_<SID>_<SOURCE>.csv.gz   (the 12 Phase 0 stations, not re-pulled)
       data/processed/panel/outlines.csv                                (GSHHS shoreline, coast indicator)
Writes data/processed/reach/rain_hourly/hourly_maysep_<SID>_<SOURCE>.csv.gz   (reach stations only)
       data/processed/reach/rain_daily/daily_<SID>.parquet       (src.rain.daily.build_daily, all seasons with data)
       data/processed/reach/rain_season_counts.csv               (per station and season: usable, loss days ...)
       data/processed/reach/rain_stations.csv                    (one row per candidate: seasons, kept, coast ...)
A station is KEPT when it has at least 20 usable seasons (SPEC_v3 90% rule on the 10:00-18:00 window).
Stations are never removed from the table; `kept` and `why_not_kept` say what happened. Observed data only.
"""
import os
import sys
import time

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.rain import daily as rd  # noqa: E402
from src.rain import hourly as srh  # noqa: E402
from src.reach import rain_geo as geo  # noqa: E402
from src.reach import rain_hourly as rh  # noqa: E402

RAW = os.path.join(ROOT, "data", "raw", "rain", "reach")
PROBE = os.path.join(ROOT, "data", "processed", "rain_probe")
OUT = os.path.join(ROOT, "data", "processed", "reach")
HOURLY = os.path.join(OUT, "rain_hourly")
DAILY = os.path.join(OUT, "rain_daily")
PHASE0 = ("TTN", "PHL", "PNE", "ABE", "EWR", "NYC", "JFK", "LGA", "WRI", "NEL", "BLM", "DYL")
MIN_SEASONS = 20
LAST_SEASON = 2026


def log(msg: str) -> None:
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def hourly_dir(sid: str) -> str:
    return PROBE if sid in PHASE0 else HOURLY


def reduce_if_needed(sid: str) -> dict:
    """Reach stations: reduce raw pulls when the IEM file is newer than the reduced file (or none exists)."""
    if sid in PHASE0:
        return {"skipped": "phase0"}
    iem = os.path.join(RAW, "iem_asos", f"{sid}_B.csv.gz")
    isd = rh.isd_paths_for(os.path.join(RAW, "ncei_global_hourly"), sid)
    if not os.path.exists(iem):
        return {"skipped": "no_iem_pull"}
    marker = os.path.join(HOURLY, f"hourly_maysep_{sid}_IEM_METAR.csv.gz")
    newest_raw = max([os.path.getmtime(iem)] + [os.path.getmtime(p) for p in isd])
    if os.path.exists(marker) and os.path.getmtime(marker) >= newest_raw:
        return {"skipped": "up_to_date"}
    return rh.write_station(sid, iem, isd, HOURLY)


def build_station(sid: str) -> tuple[pd.DataFrame | None, str]:
    per_source = {s: srh.load_source(hourly_dir(sid), sid, s) for s in srh.SOURCES}
    per_source = {k: v for k, v in per_source.items() if v is not None and v["present"].any()}
    if not per_source:
        return None, "no_present_hour"
    first = min(v.index[v["present"]].min().year for v in per_source.values())
    daily = rd.build_daily(per_source, sid, list(range(first, LAST_SEASON + 1)))
    daily["date"] = pd.to_datetime(daily["date"])
    return daily, ""


if __name__ == "__main__":
    os.makedirs(HOURLY, exist_ok=True)
    os.makedirs(DAILY, exist_ok=True)
    cand = pd.read_csv(os.path.join(OUT, "rain_stations_candidates.csv"), dtype={"sid": str, "cli_id": str})
    outlines = pd.read_csv(os.path.join(ROOT, "data", "processed", "panel", "outlines.csv"))
    shore = geo.atlantic_shoreline(outlines)
    cand["coast_km"] = geo.coast_distance_km(cand["lat"], cand["lon"], shore).round(2)
    cand["coastal"] = geo.coast_flag(cand["coast_km"])

    rows, counts = [], []
    for r in cand.itertuples():
        sid = r.sid
        red = reduce_if_needed(sid)
        daily, why = build_station(sid)
        info = dict(sid=sid, reduced=str(red))
        if daily is None:
            info.update(n_seasons_with_data=0, n_usable=0, first_usable=None, last_usable=None,
                        kept=False, why_not_kept=why)
            rows.append(info)
            log(f"{sid}: {why}")
            continue
        daily.to_parquet(os.path.join(DAILY, f"daily_{sid}.parquet"), index=False)
        sc = rd.season_counts(daily)
        sc.insert(0, "station", sid)
        sc["source"] = sc["season"].map(daily.groupby("season")["source"].first())
        counts.append(sc)
        usable = sc[sc["season_usable"]]
        n_us = int(len(usable))
        info.update(n_seasons_with_data=int(sc["season"].nunique()), n_usable=n_us,
                    first_usable=int(usable["season"].min()) if n_us else None,
                    last_usable=int(usable["season"].max()) if n_us else None,
                    n_usable_isd=int((usable["source"] == "NCEI_ISD").sum()),
                    n_usable_iem=int((usable["source"] == "IEM_METAR").sum()),
                    mean_loss_days=round(float(usable["loss_days"].mean()), 2) if n_us else None,
                    kept=n_us >= MIN_SEASONS, why_not_kept="" if n_us >= MIN_SEASONS else f"usable_seasons<{MIN_SEASONS}")
        rows.append(info)
        log(f"{sid}: usable {n_us} ({info['first_usable']}-{info['last_usable']}), kept={info['kept']}")
    st = cand.merge(pd.DataFrame(rows), on="sid", how="left")
    st.to_csv(os.path.join(OUT, "rain_stations.csv"), index=False)
    pd.concat(counts, ignore_index=True).to_csv(os.path.join(OUT, "rain_season_counts.csv"), index=False)
    k = st[st["kept"] == True]  # noqa: E712
    log(f"{len(st)} candidates, {int(st['kept'].sum())} kept, {int(k['has_cli'].sum())} kept with a climate report; "
        f"{int(st['coastal'].sum())} coastal")
