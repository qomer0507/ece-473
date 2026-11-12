"""Build the daily rain tables and season counts for TTN, PHL, ABE (SPEC_v3).

    python scripts/rain_build_daily.py

Reads   data/processed/rain_probe/hourly_maysep_<SID>_<SOURCE>.csv.gz   (Phase 0 hourly reduction)
        data/raw/rain/ncei_daily/                                        (GHCN-Daily PRCP, reference column only)
Writes  data/processed/rain/daily_<SID>.parquet            one row per season day, every season with hourly data
        data/processed/rain/season_counts_<SID>.csv        main case (0.25 in, 10:00-18:00), both calendars,
                                                           plus loss days at 0.10 and 0.50
        data/processed/rain/season_counts_cases_<SID>.csv  every threshold x window x calendar, long format
All values are observed station data. Nothing is imputed.
"""
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from rain import calendar as cal  # noqa: E402
from rain import daily as rd  # noqa: E402
from rain import hourly as rh  # noqa: E402
from rain import reference as ref  # noqa: E402

PROBE = os.path.join(ROOT, "data", "processed", "rain_probe")
NCEI_DAILY = os.path.join(ROOT, "data", "raw", "rain", "ncei_daily")
OUT = os.path.join(ROOT, "data", "processed", "rain")
STATIONS = ("TTN", "PHL", "ABE")
LAST_SEASON = 2026


def build_station(station: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    per_source = {s: rh.load_source(PROBE, station, s) for s in rh.SOURCES}
    per_source = {k: v for k, v in per_source.items() if v is not None}
    first = min(v.index[v["present"]].min().year for v in per_source.values() if v["present"].any())
    daily = rd.build_daily(per_source, station, list(range(first, LAST_SEASON + 1)))
    ghcn = ref.load_ghcn_prcp(NCEI_DAILY, station)
    daily["ghcn_prcp_in"] = daily["date"].map(ghcn)
    daily["date"] = pd.to_datetime(daily["date"])

    main = [rd.season_counts(daily, variant=v) for v in cal.VARIANTS]
    for v, m in zip(cal.VARIANTS, main):
        for thr in rd.THRESHOLDS:
            c = rd.season_counts(daily, threshold=thr, variant=v)
            m[f"loss_days_{rd.threshold_tag(thr)}"] = c["loss_days"].to_numpy()
    main = pd.concat(main, ignore_index=True)
    main.insert(0, "station", station)

    cases = pd.concat(
        [rd.season_counts(daily, thr, win, v) for v in cal.VARIANTS for win in rd.WINDOWS for thr in rd.THRESHOLDS],
        ignore_index=True,
    )
    cases.insert(0, "station", station)
    return daily, main, cases


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for sid in STATIONS:
        daily, main, cases = build_station(sid)
        daily.to_parquet(os.path.join(OUT, f"daily_{sid}.parquet"), index=False)
        main.to_csv(os.path.join(OUT, f"season_counts_{sid}.csv"), index=False)
        cases.to_csv(os.path.join(OUT, f"season_counts_cases_{sid}.csv"), index=False)
        seasons = rd.usable_seasons(daily)
        allv = main[(main.calendar == cal.ALL_DAYS) & main.season_usable]
        print(
            f"{sid}: rows={len(daily)} seasons with rows={daily.season.nunique()} usable seasons={len(seasons)} "
            f"({min(seasons)}-{max(seasons)}) not usable={sorted(set(daily.season) - set(seasons))}"
        )
        print(
            f"   main case, usable seasons: loss days mean {allv.loss_days.mean():.2f} ({allv.loss_days.min()}-{allv.loss_days.max()}), "
            f"Kalshi-pay days mean {allv.kalshi_pay_days.mean():.2f} ({allv.kalshi_pay_days.min()}-{allv.kalshi_pay_days.max()}), "
            f"unusable days {allv.days_unusable.sum()} of {allv.days.sum()}, loss_not_paid {allv.loss_not_paid.sum()}"
        )
