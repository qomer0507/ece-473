"""Phase 0 rain probe: reduce raw reports to an hourly series, measure coverage, compare with daily totals,
and make the preliminary any-rain vs opening-hours counts.

Inputs (all cached by the p0_rain_fetch_* scripts):
  data/raw/rain/iem_asos/<SID>_B.csv.gz          IEM asos.py, p01i + METAR text, 1990-2026 (UTC)
  data/raw/rain/ncei_global_hourly/<SID>_*.csv.gz NCEI ISD AA1..AA4 groups, 1941-2005 (UTC)
  data/raw/rain/ncei_daily/<GHCN>_*.csv           NCEI GHCN-Daily PRCP (inches)
Outputs: data/processed/rain_probe/*.csv

Hourly reduction (both sources)
  * The routine report closes an accumulation hour at minute rm (modal report minute of that station-year,
    e.g. :53 at TTN, :00 before ASOS). A report at time t belongs to the hour that closes at the next minute rm.
  * The hour is labelled by the clock hour it mostly overlaps: label = floor_hour(close - 30 min).
    So label 13:00 at TTN is 12:53-13:53.
  * IEM/METAR: hour is PRESENT if a closing report (minute rm-3..rm) exists and either it does not carry the PNO (precip sensor
    not operating) remark and either it carries a precipitation value or it is an automated AO2 report, in which
    case no P-group means zero. Value = max p01i in the hour, trace = 0.
  * ISD: hour is PRESENT if a closing report carries a 1-hour group (AAx period 01) with depth != 9999 and
    quality not 3/7. Value = depth (0.1 mm) converted to inches, condition code 2 = trace = 0.
Local time: America/New_York via zoneinfo (handles daylight saving). Opening hours 10:00-18:00 local = labels 10..17.
Climate day for comparison with daily PRCP: local standard time (UTC-5) midnight to midnight, which is what
ASOS daily summaries and the NWS daily climate report use.
"""
import glob, os, sys
import numpy as np, pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw", "rain")
OUT = os.path.join(ROOT, "data", "processed", "rain_probe")
GHCN = {"TTN": "USW00014792", "PHL": "USW00013739", "PNE": "USW00094732", "ABE": "USW00014737",
        "EWR": "USW00014734", "NYC": "USW00094728", "JFK": "USW00094789", "LGA": "USW00014732",
        "WRI": "USW00014706", "NEL": "USW00014780", "BLM": "USW00054760", "DYL": "USW00054786"}
TZ = "America/New_York"


def _label(df):
    """df has t (UTC naive Timestamp). Adds close time, closing flag, label (UTC hour)."""
    df["y"] = df.t.dt.year
    df["minute"] = df.t.dt.minute
    rm = df.groupby("y")["minute"].agg(lambda s: s.value_counts().index[0])
    df["rm"] = df.y.map(rm)
    gap = (df.rm - df.minute) % 60
    df["closing"] = gap <= 3
    df["label"] = (df.t + pd.to_timedelta(gap, unit="m") - pd.Timedelta(minutes=30)).dt.floor("h")
    return df


def reduce_iem(sid):
    f = os.path.join(RAW, "iem_asos", f"{sid}_B.csv.gz")
    if not os.path.exists(f):
        return None
    d = pd.read_csv(f, dtype=str, usecols=[1, 2, 3], names=["t", "p", "metar"], header=0, on_bad_lines="skip")
    d["t"] = pd.to_datetime(d.t, errors="coerce")
    d = d.dropna(subset=["t"]).drop_duplicates(subset=["t", "metar"])
    m = d.metar.fillna("")
    d["ao2"] = m.str.contains(r"\bAO2", regex=True)
    d["pno"] = m.str.contains(r"\bPNO\b", regex=True)
    d["isd"] = m.str.contains("IEM_DS3505|IEM_GHCNH", regex=True)
    d["hasval"] = d.p != "M"
    d["trace"] = d.p == "T"
    d["val"] = pd.to_numeric(d.p, errors="coerce").fillna(0.0)
    d = _label(d)
    d["ok"] = d.closing & ~d.pno & (d.hasval | (d.ao2 & ~d.isd))
    d["pno_close"] = d.closing & d.pno
    g = d.groupby("label").agg(present=("ok", "max"), precip_in=("val", "max"), trace=("trace", "max"),
                               pno=("pno_close", "max"), closing=("closing", "max"))
    g["source"] = "IEM_METAR"
    return g


def reduce_isd(sid):
    fs = sorted(glob.glob(os.path.join(RAW, "ncei_global_hourly", f"{sid}_*.csv.gz")))
    if not fs:
        return None
    d = pd.concat([pd.read_csv(f, dtype=str) for f in fs], ignore_index=True)
    if d.empty:
        return None
    d["t"] = pd.to_datetime(d.DATE, errors="coerce")
    d = d.dropna(subset=["t"])
    val = pd.Series(np.nan, index=d.index)
    tr = pd.Series(False, index=d.index)
    for c in ("AA1", "AA2", "AA3", "AA4"):
        if c not in d:
            continue
        s = d[c].fillna("").str.split(",", expand=True)
        if s.shape[1] < 4:
            continue
        good = (s[0] == "01") & (s[1] != "9999") & ~s[3].isin(["3", "7"]) & (s[1].str.len() == 4)
        v = pd.to_numeric(s[1], errors="coerce") / 10.0 / 25.4
        val = val.where(~(good & val.isna()), v)
        tr = tr | (good & (s[2] == "2"))
    d["val"], d["trace"] = val, tr
    d = d[d.val.notna()].copy()
    if d.empty:
        return None
    d = _label(d)
    d = d[d.closing]
    g = d.groupby("label").agg(precip_in=("val", "max"), trace=("trace", "max"))
    g["present"], g["pno"], g["closing"], g["source"] = True, False, True, "NCEI_ISD"
    return g


def add_local(g):
    g = g.copy()
    loc = g.index.tz_localize("UTC").tz_convert(TZ)
    g["ldate"] = loc.strftime("%Y-%m-%d")
    g["lhour"] = loc.hour
    lst = g.index - pd.Timedelta(hours=5)
    g["lst_date"] = lst.strftime("%Y-%m-%d")
    g["season"] = loc.year
    g["lmonth"] = loc.month
    return g


def coverage(g, sid, source):
    s = g[(g.lmonth >= 5) & (g.lmonth <= 9) & (g.lhour >= 10) & (g.lhour <= 17)]
    rows = []
    for yr, x in s.groupby("season"):
        rows.append(dict(station=sid, source=source, season=yr, hours_expected=153 * 8,
                         hours_present=int(x.present.sum()), share_present=round(x.present.sum() / (153 * 8), 4),
                         hours_with_closing_report=int(x.closing.sum()), hours_flagged_pno=int(x.pno.sum()),
                         wet_hours=int(((x.precip_in >= 0.005) & x.present).sum()),
                         trace_hours=int((x.trace & x.present & (x.precip_in < 0.005)).sum())))
    return pd.DataFrame(rows)


def load_daily(sid):
    fs = sorted(glob.glob(os.path.join(RAW, "ncei_daily", f"{GHCN[sid]}_*.csv")))
    d = pd.concat([pd.read_csv(f, dtype=str) for f in fs if os.path.getsize(f) > 0], ignore_index=True)
    if d.empty or "PRCP" not in d:
        return pd.DataFrame(columns=["date", "prcp", "attr"])
    d = d.rename(columns={"DATE": "date", "PRCP": "prcp", "PRCP_ATTRIBUTES": "attr"})
    d["prcp"] = pd.to_numeric(d.prcp, errors="coerce")
    d = d.dropna(subset=["prcp"])
    d["attr"] = d.attr.fillna("")
    return d[["date", "prcp", "attr"]].drop_duplicates("date")


def holidays(year):
    may = pd.date_range(f"{year}-05-01", f"{year}-05-31")
    mem = may[may.dayofweek == 0][-1]
    sep = pd.date_range(f"{year}-09-01", f"{year}-09-30")
    lab = sep[sep.dayofweek == 0][0]
    return mem, pd.Timestamp(f"{year}-07-04"), lab


def op_days(year):
    """Stand-in operating days: Sat/Sun from the Saturday before Memorial Day through Labor Day, plus
    Memorial Day, July 4 and Labor Day."""
    mem, j4, lab = holidays(year)
    days = pd.date_range(mem - pd.Timedelta(days=2), lab)
    return [d for d in days if d.dayofweek >= 5 or d in (mem, j4, lab)]


def daily_all(year):
    mem, j4, lab = holidays(year)
    return list(pd.date_range(mem - pd.Timedelta(days=2), lab))


def prelim(g, daily, sid, seasons, dayfun, tag):
    dl = daily.set_index("date").prcp
    open_ = g[(g.lhour >= 10) & (g.lhour <= 17)].groupby("ldate").agg(n=("present", "sum"), s=("precip_in", "sum"))
    rows = []
    for yr in seasons:
        days = [d.strftime("%Y-%m-%d") for d in dayfun(yr)]
        any_rain = hit = both = unk_open = unk_daily = 0
        for d in days:
            p = dl.get(d, np.nan)
            o = open_.loc[d] if d in open_.index else None
            full = o is not None and o.n == 8
            if np.isnan(p):
                unk_daily += 1
            elif p > 0:
                any_rain += 1
            if not full:
                unk_open += 1
            elif o.s >= 0.25 - 1e-9:
                hit += 1
                if not np.isnan(p) and p > 0:
                    both += 1
        rows.append(dict(station=sid, rule=tag, season=yr, days=len(days), any_rain_days=any_rain,
                         open_hours_ge_0p25_days=hit, both=both, days_open_hours_incomplete=unk_open,
                         days_daily_missing=unk_daily))
    return pd.DataFrame(rows)


def hourly_vs_daily(g, daily, sid, seasons):
    x = g[g.season.isin(seasons) | True]
    lst = x.groupby("lst_date").agg(n=("present", "sum"), s=("precip_in", "sum"), tr=("trace", "max"))
    loc = x.groupby("ldate").agg(n_loc=("present", "sum"), s_loc=("precip_in", "sum"))
    d = daily.copy()
    d = d[d.date.str[5:7].astype(int).between(5, 9) & d.date.str[:4].astype(int).isin(seasons)]
    d = d.join(lst, on="date").join(loc, on="date")
    d["station"] = sid
    d["hours_present_lst"] = d.n.fillna(0).astype(int)
    d["hourly_sum_lst"] = d.s.round(2)
    d["hourly_sum_localclock"] = d.s_loc.round(2)
    d["diff"] = (d.hourly_sum_lst - d.prcp).round(2)
    d["diff_localclock"] = (d.hourly_sum_localclock - d.prcp).round(2)
    return d[["station", "date", "prcp", "attr", "hours_present_lst", "hourly_sum_lst", "diff",
              "hourly_sum_localclock", "diff_localclock"]]


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    cov, series, dcov = [], {}, []
    for sid in GHCN:
        for name, fn in (("IEM_METAR", reduce_iem), ("NCEI_ISD", reduce_isd)):
            g = fn(sid)
            if g is None or g.empty:
                print(sid, name, "no data")
                continue
            g = add_local(g)
            series[(sid, name)] = g
            cov.append(coverage(g, sid, name))
            keep = g[(g.lmonth >= 5) & (g.lmonth <= 9)]
            keep[["source", "ldate", "lhour", "lst_date", "present", "precip_in", "trace", "pno"]].to_csv(
                os.path.join(OUT, f"hourly_maysep_{sid}_{name}.csv.gz"), index_label="hour_label_utc")
        d = load_daily(sid)
        d["y"] = d.date.str[:4].astype(int)
        d["m"] = d.date.str[5:7].astype(int)
        for yr, x in d[d.m.between(5, 9)].groupby("y"):
            dcov.append(dict(station=sid, ghcn_id=GHCN[sid], season=yr, days_present=len(x),
                             share_present=round(len(x) / 153, 4), wet_days=int((x.prcp > 0).sum()),
                             season_total_in=round(x.prcp.sum(), 2)))
        series[(sid, "daily")] = d
    cov = pd.concat(cov, ignore_index=True)
    cov.to_csv(os.path.join(OUT, "hourly_coverage_by_season.csv"), index=False)
    dcov = pd.DataFrame(dcov)
    dcov.to_csv(os.path.join(OUT, "daily_coverage_by_season.csv"), index=False)

    # best source per station-season, summary
    has = cov[cov.hours_present > 0]
    best = has.sort_values("share_present").groupby(["station", "season"]).tail(1)
    best.sort_values(["station", "season"]).to_csv(os.path.join(OUT, "hourly_coverage_best_source.csv"), index=False)
    rows = []
    for sid in GHCN:
        r = dict(station=sid)
        for name in ("IEM_METAR", "NCEI_ISD"):
            x = has[(has.station == sid) & (has.source == name)]
            r[f"{name}_first"] = int(x.season.min()) if len(x) else None
            r[f"{name}_last"] = int(x.season.max()) if len(x) else None
            r[f"{name}_seasons_ge90"] = int((x.share_present >= 0.9).sum())
        b = best[best.station == sid]
        g90 = b[b.share_present >= 0.9]
        r["combined_first"] = int(b.season.min()) if len(b) else None
        r["combined_seasons_ge90"] = len(g90)
        r["combined_first_ge90"] = int(g90.season.min()) if len(g90) else None
        r["combined_ge90_since_1980"] = int((g90.season >= 1980).sum())
        dd = dcov[dcov.station == sid]
        r["daily_first_year"] = int(dd.season.min()) if len(dd) else None
        r["daily_first_year_wet"] = int(dd[dd.wet_days > 0].season.min()) if (dd.wet_days > 0).any() else None
        r["daily_seasons_ge90"] = int((dd.share_present >= 0.9).sum())
        r["daily_seasons_complete"] = int((dd.days_present == 153).sum())
        rows.append(r)
    summ = pd.DataFrame(rows)
    summ.to_csv(os.path.join(OUT, "coverage_summary.csv"), index=False)
    print(summ.to_string())
