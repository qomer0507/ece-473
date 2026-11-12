"""Build daily rain tables for the stand-in gauges PNE (Philadelphia NE) and DYL (Doylestown), Phase 2.

    python scripts/hedge_build_standins.py

Reads   data/processed/rain_probe/hourly_maysep_<SID>_<SOURCE>.csv.gz   (Phase 0 hourly reduction)
Writes  data/processed/rain/daily_PNE.parquet, daily_DYL.parquet   same columns as daily_TTN.parquet except
                                                                   ghcn_prcp_in (no GHCN reference is needed:
                                                                   the stand-in only supplies park loss days)
        data/processed/hedge/standin_seasons.csv                   per season: share of opening hours present,
                                                                   usable flag, usable days
Uses the Phase 1 library src/rain unchanged (rain.daily.build_daily). Observed station data; nothing imputed.
"""
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from rain import daily as rd  # noqa: E402
from rain import hourly as rh  # noqa: E402

PROBE = os.path.join(ROOT, "data", "processed", "rain_probe")
OUT = os.path.join(ROOT, "data", "processed", "rain")
HEDGE = os.path.join(ROOT, "data", "processed", "hedge")
STANDINS = ("PNE", "DYL")
LAST_SEASON = 2026


def build(station: str) -> pd.DataFrame:
    """Daily table for one stand-in gauge, every season from its first present hour to LAST_SEASON."""
    per_source = {s: rh.load_source(PROBE, station, s) for s in rh.SOURCES}
    per_source = {k: v for k, v in per_source.items() if v is not None}
    first = min(v.index[v["present"]].min().year for v in per_source.values() if v["present"].any())
    daily = rd.build_daily(per_source, station, list(range(first, LAST_SEASON + 1)))
    daily["date"] = pd.to_datetime(daily["date"])
    return daily


if __name__ == "__main__":
    os.makedirs(HEDGE, exist_ok=True)
    rows = []
    for sid in STANDINS:
        d = build(sid)
        d.to_parquet(os.path.join(OUT, f"daily_{sid}.parquet"), index=False)
        share = rd.season_hour_share(d)
        g = d.groupby("season").agg(days=("usable", "size"), usable_days=("usable", "sum"),
                                    source=("source", "first")).reset_index()
        g.insert(0, "station", sid)
        g["share_open_hours_present"] = g["season"].map(share).round(4)
        g["season_usable"] = g["share_open_hours_present"] >= rd.USABLE_SEASON_SHARE
        rows.append(g)
        us = rd.usable_seasons(d)
        print(f"{sid}: rows={len(d)} seasons={d.season.nunique()} usable seasons={len(us)}: {us}")
    pd.concat(rows, ignore_index=True).to_csv(os.path.join(HEDGE, "standin_seasons.csv"), index=False)
