"""Checks of the NCEI pull against Iowa Environmental Mesonet (IEM).

1. Teterboro (USW00094741 / KTEB), September 2025: old pull (data/processed/aligned_daily.csv),
   new pull (data/raw/region/tmax) and IEM ASOS daily maximum. KTEB has no CLI product, so the
   ASOS daily summary is the only IEM record available.
2. Spot check: 20 random season station-days at each of 3 other USW exposure stations with a CLI,
   new pull vs the NWS CLI "high" as archived by IEM. Stations and days drawn with seed 473.

Outputs: results/part1/teterboro_check.csv, results/part1/iem_spotcheck.csv
Run: python scripts/panel_iem_checks.py
"""
import io
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/part1"
CACHE = ROOT / "data/processed/panel/iem_cache"
SEED = 473


def fetch(url, path):
    if not path.exists() or path.stat().st_size == 0:
        for attempt in range(4):
            r = subprocess.run(["curl", "-sS", "-f", "-m", "90", "-o", str(path), url])
            if r.returncode == 0:
                break
            time.sleep(3 * (attempt + 1))
        else:
            path.unlink(missing_ok=True)
            raise RuntimeError(f"download failed: {url}")
        time.sleep(0.3)
    return path.read_text()


def teterboro():
    a = pd.read_csv(ROOT / "data/processed/aligned_daily.csv")
    old = a[a.local_station_id == "USW00094741"].drop_duplicates("date").set_index("date")["local_tmax_f"]
    new = pd.read_csv(ROOT / "data/raw/region/tmax/USW00094741.csv").set_index("DATE")["TMAX"]
    url = ("https://mesonet.agron.iastate.edu/cgi-bin/request/daily.py?network=NJ_ASOS&stations=TEB"
           "&year1=2025&month1=5&day1=1&year2=2025&month2=9&day2=30&var=max_temp_f&format=csv")
    iem = pd.read_csv(io.StringIO(fetch(url, CACHE / "asos_daily_TEB_2025.csv"))).set_index("day")["max_temp_f"]
    d = pd.DataFrame({"old_pull_f": old, "new_pull_f": new, "iem_asos_daily_f": iem}).loc["2025-05-01":"2025-09-30"]
    d.index.name = "date"
    both = d["old_pull_f"].notna() & d["new_pull_f"].notna()
    d["pulls_differ"] = both & (d["old_pull_f"] != d["new_pull_f"])
    d["old_eq_iem"] = d["old_pull_f"] == d["iem_asos_daily_f"]
    d["new_eq_iem"] = d["new_pull_f"] == d["iem_asos_daily_f"]
    # Station's own 24-hour maximum from the METAR remarks ("4sTTTsTTT" group in the 0451Z report,
    # which covers the local-standard-time calendar day that just ended). Raw METARs via IEM.
    murl = ("https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?station=TEB&data=metar"
            "&year1=2025&month1=5&day1=1&year2=2025&month2=10&day2=2&tz=UTC&format=onlycomma"
            "&report_type=3&report_type=4")
    m = pd.read_csv(io.StringIO(fetch(murl, CACHE / "asos_metar_TEB_2025season.csv")))
    m["valid"] = pd.to_datetime(m["valid"])
    m24 = {}
    for _, r in m.iterrows():
        g = re.search(r" 4([01])(\d{3})([01])(\d{3})(?: |$)", str(r.metar).split("RMK")[-1])
        if g and r.valid.hour in (4, 5):
            c = (-1 if g.group(1) == "1" else 1) * int(g.group(2)) / 10
            m24[(r.valid - pd.Timedelta(hours=6)).strftime("%Y-%m-%d")] = round(c * 9 / 5 + 32, 1)
    d["metar_24h_max_f"] = pd.Series(m24)
    d["old_eq_metar24"] = d["old_pull_f"] == d["metar_24h_max_f"].round()
    d["new_eq_metar24"] = d["new_pull_f"] == d["metar_24h_max_f"].round()
    d.to_csv(OUT / "teterboro_check.csv")
    flag = m["metar"].astype(str).str.contains(r"\$")
    print("  share of METARs with maintenance flag '$' by month:",
          flag.groupby(m["valid"].dt.month).mean().round(2).to_dict())
    z = d[d.pulls_differ & d.metar_24h_max_f.notna()]
    print(f"  differing days with a METAR 24-h max: {len(z)}; old == METAR {int(z.old_eq_metar24.sum())}, "
          f"new == METAR {int(z.new_eq_metar24.sum())}")
    w = d[both & ~d.pulls_differ & d.metar_24h_max_f.notna()]
    print(f"  agreeing days with a METAR 24-h max: {len(w)}; new == METAR {int(w.new_eq_metar24.sum())}")
    late = w[(w.index >= "2025-08-27")]
    print(f"  of those from 2025-08-27 on: {len(late)}; new == METAR {int(late.new_eq_metar24.sum())}; "
          f"mean (METAR - new) {float((late.metar_24h_max_f - late.new_pull_f).mean()):.2f} F")
    x = d[d.pulls_differ]
    y = d[both & ~d.pulls_differ & d.iem_asos_daily_f.notna()]
    print("Teterboro 2025 season")
    print(f"  days where pulls differ: {len(x)} ({x.index.min()}..{x.index.max()})")
    print(f"  on those: old == IEM {int(x.old_eq_iem.sum())}, new == IEM {int(x.new_eq_iem.sum())}")
    print(x[~x.new_eq_iem][["old_pull_f", "new_pull_f", "iem_asos_daily_f"]].to_string())
    print(f"  days where pulls agree: {len(y)}; new == IEM on {int(y.new_eq_iem.sum())}")
    print(f"  mean (new - IEM) on agreeing days: {float((y.new_pull_f - y.iem_asos_daily_f).mean()):.2f} F")
    for name in ("old_pull_f", "new_pull_f", "iem_asos_daily_f"):
        print(f"  90F days in the differing span by {name}: {int((x[name] >= 90).sum())}")


def spotcheck():
    st = pd.read_csv(ROOT / "data/processed/panel/stations.csv")
    pool = st[st.is_exposure & st.has_cli & st.is_listed.isna()
              & (st.id != "USW00094741")].sort_values("id")
    rng = np.random.default_rng(SEED)
    pick = pool.iloc[np.sort(rng.choice(len(pool), 3, replace=False))]
    rows = []
    for _, s in pick.iterrows():
        g = pd.read_csv(ROOT / f"data/raw/region/tmax/{s.id}.csv")
        g = g[g.TMAX.notna() & g.DATE.str[5:].between("05-01", "09-30") & g.DATE.str[:4].between("2015", "2025")]
        days = g.iloc[np.sort(rng.choice(len(g), 20, replace=False))]
        for _, r in days.iterrows():
            yr = r.DATE[:4]
            res = json.loads(fetch(f"https://mesonet.agron.iastate.edu/json/cli.py?station={s.cli_id}&year={yr}",
                                   CACHE / f"cli_{s.cli_id}_{yr}.json"))["results"]
            hit = [x for x in res if x["valid"] == r.DATE]
            high = hit[0]["high"] if hit else None
            high = float(high) if isinstance(high, (int, float)) else np.nan
            rows.append({"id": s.id, "name": s["name"], "cli_id": s.cli_id, "date": r.DATE,
                         "ncei_tmax_f": float(r.TMAX), "iem_cli_high_f": high})
    d = pd.DataFrame(rows)
    d["diff_f"] = d.ncei_tmax_f - d.iem_cli_high_f
    d["match"] = d.diff_f == 0
    d.to_csv(OUT / "iem_spotcheck.csv", index=False)
    print("Spot check, NCEI pull vs IEM CLI high")
    print(d.groupby(["id", "name", "cli_id"]).agg(n=("match", "size"), cli_found=("iem_cli_high_f", "count"),
                                                    match=("match", "sum")).to_string())
    print(d[~d.match].to_string(index=False))


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    teterboro()
    spotcheck()
