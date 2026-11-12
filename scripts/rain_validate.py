"""Validation of the rain tables (SPEC_v3 Phase 1, deliverable 3). Rules are not tuned here; this only reports.

    python scripts/rain_validate.py

(a) Kalshi-rule flag from hourly data vs the NWS daily climate report (CLI, via IEM json), every season day with a
    CLI row. CLI side: pays if precip >= 0.01 in; trace and missing = No.
(b) Kalshi-rule flag vs Kalshi's own settled daily results (KXRAIN-<date>-TTN / -PHIL). Day-level rows are read
    from data/raw/kalshi/rain/ and only aggregate agreement counts are written.
(c) Hourly climate-day sum vs GHCN-Daily PRCP, per season.

Writes to data/processed/rain/:
    validation_kalshi_vs_cli_summary.csv, validation_kalshi_vs_cli_by_season.csv,
    validation_kalshi_vs_cli_disagreements.csv, validation_kalshi_settled_summary.csv,
    validation_hourly_vs_ghcn_by_season.csv, validation_hourly_vs_ghcn_summary.csv
"""
import datetime as dt
import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from rain import daily as rd  # noqa: E402
from rain import hourly as rh  # noqa: E402
from rain import reference as ref  # noqa: E402

OUT = os.path.join(ROOT, "data", "processed", "rain")
PROBE = os.path.join(ROOT, "data", "processed", "rain_probe")
CLI_DIRS = [os.path.join(ROOT, "data", "raw", "rain", "iem_cli"), os.path.join(ROOT, "data", "raw", "kalshi", "iem_cli")]
KALSHI_MARKETS = os.path.join(ROOT, "data", "raw", "kalshi", "rain", "markets_KXRAIN.json")
KALSHI_CITY = {"TTN": "TTN", "PHL": "PHIL"}
STATIONS = ("TTN", "PHL", "ABE")
MONTHS = {m: i + 1 for i, m in enumerate("JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split())}


def load_daily(station):
    d = pd.read_parquet(os.path.join(OUT, f"daily_{station}.parquet"))
    d["date"] = pd.to_datetime(d["date"]).dt.date
    return d


def agree_row(station, label, x):
    n = len(x)
    a = int((x["kalshi_pays"] == x["cli_pays"]).sum())
    return dict(
        station=station, day_set=label, days=n, agree=a, share_agree=round(a / n, 4) if n else np.nan,
        hourly_yes_cli_no=int((x["kalshi_pays"] & ~x["cli_pays"]).sum()),
        hourly_no_cli_yes=int((~x["kalshi_pays"] & x["cli_pays"]).sum()),
        cli_yes_days=int(x["cli_pays"].sum()), hourly_yes_days=int(x["kalshi_pays"].sum()),
        cli_trace_days=int((x["cli_kind"] == "trace").sum()), cli_missing_days=int((x["cli_kind"] == "missing").sum()),
    )


def check_cli(station, daily):
    cli = ref.load_cli(CLI_DIRS, station)
    x = daily.merge(cli, on="date", how="inner")
    complete = x["climate_hours_present"] == 24
    summary = [
        agree_row(station, "all season days with a CLI row", x),
        agree_row(station, "usable days (opening hours complete)", x[x["usable"]]),
        agree_row(station, "climate day complete (24 hours)", x[complete]),
        agree_row(station, "climate day incomplete", x[~complete]),
        agree_row(station, "usable days in usable seasons", x[x["usable"] & x["season_usable"]]),
    ]
    by_season = []
    for season, g in x.groupby("season"):
        r = agree_row(station, "all season days with a CLI row", g)
        r["season"] = season
        by_season.append(r)
    dis = x[x["kalshi_pays"] != x["cli_pays"]][
        ["station", "date", "season", "source", "usable", "climate_hours_present", "climate_day_total_in",
         "kalshi_pays", "cli_precip_in", "cli_kind", "cli_pays", "ghcn_prcp_in"]
    ]
    return summary, by_season, dis


def kalshi_settled(station, daily):
    """Aggregate agreement of the hourly-rule flag with Kalshi's settled daily results. No day-level output."""
    if station not in KALSHI_CITY or not os.path.exists(KALSHI_MARKETS):
        return None
    with open(KALSHI_MARKETS) as fh:
        markets = json.load(fh)
    rows = []
    for m in markets:
        parts = m["ticker"].split("-")
        if len(parts) != 3 or parts[2] != KALSHI_CITY[station] or m.get("result") not in ("yes", "no"):
            continue
        code = parts[1]  # e.g. 26SEP10
        rows.append((dt.date(2000 + int(code[:2]), MONTHS[code[2:5]], int(code[5:])), m["result"] == "yes"))
    k = pd.DataFrame(rows, columns=["date", "kalshi_result_yes"])
    # hourly flag for every May-Sep climate day, not only season days
    per_source = {s: rh.load_source(PROBE, station, s) for s in rh.SOURCES}
    h = rh.add_time_columns(per_source["IEM_METAR"])
    ct = rd.climate_day_totals(h)
    k["hours"] = k["date"].map(ct["hours_present"])
    k["flag"] = rd.kalshi_flag(k["date"].map(ct["total_in"]))
    out = []
    season_dates = set(daily["date"])
    for label, x in (
        ("all settled days with hourly data (through 30 Sep 2026)", k[k["hours"].notna()]),
        ("of those, SPEC season days", k[k["hours"].notna() & k["date"].isin(season_dates)]),
    ):
        out.append(dict(
            station=station, day_set=label, first=str(x["date"].min()) if len(x) else "", last=str(x["date"].max()) if len(x) else "",
            days=len(x), agree=int((x["flag"] == x["kalshi_result_yes"]).sum()),
            kalshi_yes=int(x["kalshi_result_yes"].sum()), hourly_yes=int(x["flag"].sum()),
            hourly_yes_kalshi_no=int((x["flag"] & ~x["kalshi_result_yes"]).sum()),
            hourly_no_kalshi_yes=int((~x["flag"] & x["kalshi_result_yes"]).sum()),
            settled_days_without_hourly_data=int(k["hours"].isna().sum()),
        ))
    return out


def check_ghcn(station, daily):
    x = daily[(daily["climate_hours_present"] == 24) & daily["ghcn_prcp_in"].notna()].copy()
    x["diff"] = (x["climate_day_total_in"] - x["ghcn_prcp_in"]).round(2)
    x["within"] = x["diff"].abs() <= 0.02 + 1e-9
    x["wet_h"] = x["climate_day_total_in"] >= 0.01
    x["wet_g"] = x["ghcn_prcp_in"] >= 0.01
    rows = []
    for season, g in x.groupby("season"):
        n_season = int((daily["season"] == season).sum())
        rows.append(dict(
            station=station, season=season, season_usable=bool(g["season_usable"].iloc[0]), source=g["source"].iloc[0],
            season_days=n_season, days_compared=len(g), share_within_0p02=round(g["within"].mean(), 4),
            days_off=int((~g["within"]).sum()), wet_flag_agree=int((g["wet_h"] == g["wet_g"]).sum()),
            hourly_wet_ghcn_dry=int((g["wet_h"] & ~g["wet_g"]).sum()), hourly_dry_ghcn_wet=int((~g["wet_h"] & g["wet_g"]).sum()),
            hourly_total_in=round(g["climate_day_total_in"].sum(), 2), ghcn_total_in=round(g["ghcn_prcp_in"].sum(), 2),
            max_abs_diff_in=round(g["diff"].abs().max(), 2),
        ))
    t = pd.DataFrame(rows)
    u = t[t["season_usable"]]
    summ = dict(
        station=station, usable_seasons_compared=len(u), days_compared=int(u["days_compared"].sum()),
        share_days_within_0p02=round(1 - u["days_off"].sum() / u["days_compared"].sum(), 4),
        share_wet_flag_agree=round(u["wet_flag_agree"].sum() / u["days_compared"].sum(), 4),
        hourly_wet_ghcn_dry=int(u["hourly_wet_ghcn_dry"].sum()), hourly_dry_ghcn_wet=int(u["hourly_dry_ghcn_wet"].sum()),
        hourly_total_in=round(u["hourly_total_in"].sum(), 2), ghcn_total_in=round(u["ghcn_total_in"].sum(), 2),
        total_ratio=round(u["hourly_total_in"].sum() / u["ghcn_total_in"].sum(), 4),
        worst_season_share_within=round(u["share_within_0p02"].min(), 4),
        worst_season=int(u.loc[u["share_within_0p02"].idxmin(), "season"]),
        seasons_total_off_by_more_than_5pct=int(((u["hourly_total_in"] / u["ghcn_total_in"] - 1).abs() > 0.05).sum()),
    )
    return t, summ


if __name__ == "__main__":
    pd.set_option("display.width", 250)
    cli_s, cli_y, cli_d, ks, gh_t, gh_s = [], [], [], [], [], []
    for sid in STATIONS:
        daily = load_daily(sid)
        s, y, d = check_cli(sid, daily)
        cli_s += s; cli_y += y; cli_d.append(d)
        k = kalshi_settled(sid, daily)
        if k:
            ks += k
        t, summ = check_ghcn(sid, daily)
        gh_t.append(t); gh_s.append(summ)
    S = pd.DataFrame(cli_s); S.to_csv(os.path.join(OUT, "validation_kalshi_vs_cli_summary.csv"), index=False)
    Y = pd.DataFrame(cli_y); Y.insert(1, "season", Y.pop("season")); Y.drop(columns="day_set").to_csv(os.path.join(OUT, "validation_kalshi_vs_cli_by_season.csv"), index=False)
    D = pd.concat(cli_d); D.to_csv(os.path.join(OUT, "validation_kalshi_vs_cli_disagreements.csv"), index=False)
    K = pd.DataFrame(ks); K.to_csv(os.path.join(OUT, "validation_kalshi_settled_summary.csv"), index=False)
    pd.concat(gh_t).to_csv(os.path.join(OUT, "validation_hourly_vs_ghcn_by_season.csv"), index=False)
    G = pd.DataFrame(gh_s); G.to_csv(os.path.join(OUT, "validation_hourly_vs_ghcn_summary.csv"), index=False)
    print(S.to_string(index=False)); print(); print(K.to_string(index=False)); print(); print(G.to_string(index=False))
    print("\nCLI seasons per station:", Y.groupby("station").season.agg(["min", "max", "count"]).to_dict("index"))
    print("disagreements:", D.groupby("station").size().to_dict())
