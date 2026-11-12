"""Phase 0 rain probe, PRELIMINARY: (d) hourly-sum vs daily PRCP check, (e) any-rain vs opening-hours counts.

Reads data/processed/rain_probe/hourly_maysep_<SID>_<SOURCE>.csv.gz (from p0_rain_analyze.py) and the cached
GHCN-Daily PRCP. Writes hourly_vs_daily_days.csv, hourly_vs_daily_summary.csv, prelim_counts_<SID>.csv,
prelim_counts_summary.csv in data/processed/rain_probe/.
Day for the daily comparison: local standard time (UTC-5) midnight to midnight, all 24 hours present.
Opening hours: hour labels 10..17 America/New_York, all 8 present, sum >= 0.25 in (trace = 0).
Any rain: GHCN-Daily PRCP > 0 (>= 0.01 in; a trace is recorded as 0.00 and does not count).
"""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from p0_rain_analyze import OUT, load_daily, op_days, daily_all

def hourly(sid, src):
    return pd.read_csv(os.path.join(OUT, f"hourly_maysep_{sid}_{src}.csv.gz"), dtype={"ldate": str, "lst_date": str})

def best(sid):
    """Per season, the source with more opening-hour coverage."""
    cov = pd.read_csv(os.path.join(OUT, "hourly_coverage_best_source.csv"))
    cov = cov[cov.station == sid]
    parts = []
    for src in cov.source.unique():
        h = hourly(sid, src)
        h["season"] = h.ldate.str[:4].astype(int)
        parts.append(h[h.season.isin(cov[cov.source == src].season)])
    return pd.concat(parts), cov

def cmp_daily(sid, h, tag, seasons):
    d = load_daily(sid)
    g = h.groupby("lst_date").agg(n=("present", "sum"), s=("precip_in", "sum"))
    d = d.join(g, on="date")
    d["season"] = d.date.str[:4].astype(int)
    d = d[d.season.isin(seasons) & (d.n == 24)].copy()
    d["hourly_sum"] = d.s.round(2)
    d["diff"] = (d.hourly_sum - d.prcp).round(2)
    d.insert(0, "station", sid); d.insert(1, "set", tag)
    return d[["station", "set", "date", "prcp", "attr", "hourly_sum", "diff"]]

def summarize(d):
    a = d["diff"].abs()
    wet = (d.prcp > 0) | (d.hourly_sum > 0)
    return dict(station=d.station.iloc[0], set=d.set.iloc[0], days_compared=len(d),
                share_within_0p02=round((a <= 0.02 + 1e-9).mean(), 4), days_off=int((a > 0.02 + 1e-9).sum()),
                wet_days=int(wet.sum()), share_wet_days_within_0p02=round((a[wet] <= 0.02 + 1e-9).mean(), 4),
                hourly_lower=int((d["diff"] < -0.02 - 1e-9).sum()), hourly_higher=int((d["diff"] > 0.02 + 1e-9).sum()),
                daily_wet_hourly_zero=int(((d.prcp >= 0.03) & (d.hourly_sum == 0)).sum()),
                median_abs_diff_when_off=round(a[a > 0.02 + 1e-9].median(), 2) if (a > 0.02 + 1e-9).any() else 0,
                max_abs_diff=round(a.max(), 2), season_total_hourly=round(d.hourly_sum.sum(), 2),
                season_total_daily=round(d.prcp.sum(), 2))

def counts(sid, h, seasons, dayfun, rule):
    dl = load_daily(sid).set_index("date").prcp
    o = h[(h.lhour >= 10) & (h.lhour <= 17)].groupby("ldate").agg(n=("present", "sum"), s=("precip_in", "sum"))
    rows = []
    for yr in seasons:
        r = dict(station=sid, rule=rule, season=yr, days=0, any_rain_days=0, open_hours_ge_0p25_days=0,
                 any_rain_not_open_hit=0, open_hit_without_daily_rain=0, days_unusable=0)
        for d in dayfun(yr):
            k = d.strftime("%Y-%m-%d"); r["days"] += 1
            p = dl.get(k, np.nan)
            if np.isnan(p) or k not in o.index or o.loc[k, "n"] < 8:
                r["days_unusable"] += 1; continue
            hit = o.loc[k, "s"] >= 0.25 - 1e-9
            r["any_rain_days"] += p > 0; r["open_hours_ge_0p25_days"] += hit
            r["any_rain_not_open_hit"] += (p > 0) and not hit
            r["open_hit_without_daily_rain"] += hit and not p > 0
        rows.append(r)
    return pd.DataFrame(rows)

if __name__ == "__main__":
    days, summ = [], []
    sets = [("TTN", "IEM_METAR", "recent 2021-2025", range(2021, 2026)), ("PHL", "IEM_METAR", "recent 2021-2025", range(2021, 2026)),
            ("TTN", "IEM_METAR", "all ASOS 1998-2026", range(1998, 2027)), ("PHL", "IEM_METAR", "all ASOS 1997-2026", range(1997, 2027)),
            ("PHL", "NCEI_ISD", "pre-ASOS 1941-1995", range(1941, 1996)), ("EWR", "NCEI_ISD", "pre-ASOS 1948-1995", range(1948, 1996)),
            ("ABE", "NCEI_ISD", "pre-ASOS 1948-1995", range(1948, 1996))]
    for sid, src, tag, seasons in sets:
        d = cmp_daily(sid, hourly(sid, src), f"{src} {tag}", list(seasons))
        days.append(d); summ.append(summarize(d))
    pd.concat(days).to_csv(os.path.join(OUT, "hourly_vs_daily_days.csv"), index=False)
    S = pd.DataFrame(summ); S.to_csv(os.path.join(OUT, "hourly_vs_daily_summary.csv"), index=False)
    pd.set_option("display.width", 250); print(S.to_string(index=False))
    out = []
    for sid in ("TTN", "PHL", "ABE", "EWR"):
        h, cov = best(sid)
        seasons = sorted(cov[cov.share_present >= 0.9].season)
        t = pd.concat([counts(sid, h, seasons, op_days, "weekends+3 holidays"), counts(sid, h, seasons, daily_all, "every day")])
        t.to_csv(os.path.join(OUT, f"prelim_counts_{sid}.csv"), index=False)
        for rule, x in t.groupby("rule"):
            for lab, y in (("all", x), ("since 1998", x[x.season >= 1998])):
                out.append(dict(station=sid, rule=rule, seasons_set=lab, n_seasons=len(y), first=int(y.season.min()), last=int(y.season.max()),
                    days_per_season=round(y.days.mean(), 1), unusable_days_total=int(y.days_unusable.sum()),
                    any_mean=round(y.any_rain_days.mean(), 2), any_min=int(y.any_rain_days.min()), any_max=int(y.any_rain_days.max()),
                    hit_mean=round(y.open_hours_ge_0p25_days.mean(), 2), hit_min=int(y.open_hours_ge_0p25_days.min()),
                    hit_max=int(y.open_hours_ge_0p25_days.max()),
                    share_any_rain_not_hit=round(y.any_rain_not_open_hit.sum() / y.any_rain_days.sum(), 4),
                    hits_without_daily_rain=int(y.open_hit_without_daily_rain.sum())))
    P = pd.DataFrame(out); P.to_csv(os.path.join(OUT, "prelim_counts_summary.csv"), index=False)
    print(P.to_string(index=False))
