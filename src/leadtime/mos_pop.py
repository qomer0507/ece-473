"""Probability of measurable precipitation for a climate day, by lead time, from cached MOS CSVs.

Definitions (docs/status/phase3_leadtime.md, reading choices 1-2)
- Climate day D = local calendar day at the station (America/New_York). Its Kalshi close is midnight local at
  the end of D: 04:00Z on D+1 in summer (EDT).
- Lead of a run (days) = (close of D - run time) / 24 h.
- PoP for D from one run:
    p24 ending 00Z D+1 if the model carries a 24-h PoP (MEX; window 00Z D to 00Z D+1);
    otherwise 1 - (1 - p12 ending 12Z D)(1 - p12 ending 00Z D+1) (same window, independence assumed).
  Values in the archive are percent; here they are probabilities in [0, 1].
- For a whole-day lead L the run used is the one whose lead is closest to L days. If two runs tie, the earlier
  one. A run is usable for D only if it has the fields needed for D.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import pandas as pd

from .mos_archive import RAW_MOS

LEADS_DAYS = (1, 2, 3, 4, 5, 6, 7)
CHECK_LEAD_DAYS = 1.5          # the observed end: Kalshi's 36-hour decision time
CLOSE_HOUR_UTC = 4             # 04:00Z the next day = midnight EDT at the end of the climate day
TZ = "America/New_York"


def combine_independent(ps: Iterable[float]) -> float:
    """1 - prod(1 - p) over the periods: probability of rain in at least one period if they were independent.

    Overstates the true probability when rain persists from one period to the next.
    """
    out = 1.0
    for p in ps:
        if not 0.0 <= p <= 1.0:
            raise ValueError(f"probability {p} outside [0, 1]")
        out *= 1.0 - p
    return 1.0 - out


def close_time_utc(day: pd.Timestamp) -> pd.Timestamp:
    """Kalshi close of climate day `day`: midnight local at the end of the day, converted to UTC (naive)."""
    local_end = (pd.Timestamp(day).normalize() + pd.Timedelta(days=1)).tz_localize(TZ)
    return local_end.tz_convert("UTC").tz_localize(None)


def read_mos_csv(path: Path) -> pd.DataFrame:
    """Read one cached archive CSV; keep runtime, ftime, p06, p12, p24 (percent -> probability)."""
    d = pd.read_csv(path, low_memory=False)
    keep = pd.DataFrame({"runtime": pd.to_datetime(d["runtime"]), "ftime": pd.to_datetime(d["ftime"])})
    for c in ("p06", "p12", "p24"):
        keep[c] = pd.to_numeric(d[c], errors="coerce") / 100.0 if c in d.columns else np.nan
    return keep.sort_values(["runtime", "ftime"]).reset_index(drop=True)


def load_model(model: str, station: str, years: Sequence[int], raw: Path = RAW_MOS) -> pd.DataFrame:
    frames = []
    for y in years:
        p = raw / f"{model}_{station}_{y}.csv"
        if p.exists() and p.stat().st_size > 0:
            frames.append(read_mos_csv(p))
    if not frames:
        return pd.DataFrame(columns=["runtime", "ftime", "p06", "p12", "p24"])
    return pd.concat(frames, ignore_index=True).drop_duplicates(["runtime", "ftime"]).reset_index(drop=True)


def day_pop_by_run(mos: pd.DataFrame, days: Sequence[pd.Timestamp]) -> pd.DataFrame:
    """For every (run, climate day) pair the run can price: the PoP and how it was formed.

    Columns: date, runtime, lead_days, pop (main: p24 if the model has it, else p12x2), pop_p12 (the two
    12-h PoPs ending 12Z D and 00Z D+1 combined), pop_p24 (24 h ending 00Z D+1; NaN without the field),
    pop_p06 (the four 6-h PoPs ending 12Z D, 18Z D, 00Z D+1, 06Z D+1 combined; window 06Z D - 06Z D+1),
    field ('p24' or 'p12x2'). A (run, day) row exists if any of the three can be formed.
    """
    p06 = mos.dropna(subset=["p06"]).set_index(["runtime", "ftime"])["p06"]
    p12 = mos.dropna(subset=["p12"]).set_index(["runtime", "ftime"])["p12"]
    p24 = mos.dropna(subset=["p24"]).set_index(["runtime", "ftime"])["p24"]
    runs = mos["runtime"].drop_duplicates().to_numpy()
    rows = []
    for day in days:
        day = pd.Timestamp(day).normalize()
        t12 = day + pd.Timedelta(hours=12)
        t00 = day + pd.Timedelta(days=1)
        t18 = day + pd.Timedelta(hours=18)
        t06n = day + pd.Timedelta(hours=30)
        close = close_time_utc(day)
        lo, hi = np.datetime64(day - pd.Timedelta(days=8)), np.datetime64(t12)
        for rt in runs[(runs <= hi) & (runs >= lo)]:
            rt = pd.Timestamp(rt)
            a, b = p12.get((rt, t12), np.nan), p12.get((rt, t00), np.nan)
            c = p24.get((rt, t00), np.nan)
            q = [p06.get((rt, t), np.nan) for t in (t12, t18, t00, t06n)]
            v12 = combine_independent((a, b)) if not (np.isnan(a) or np.isnan(b)) else np.nan
            v06 = combine_independent(q) if not any(np.isnan(x) for x in q) else np.nan
            if np.isnan(c) and np.isnan(v12) and np.isnan(v06):
                continue
            main = c if not np.isnan(c) else v12
            rows.append({"date": day, "runtime": rt, "lead_days": (close - rt) / pd.Timedelta(days=1),
                         "pop": main, "pop_p12": v12, "pop_p24": c, "pop_p06": v06,
                         "field": "p24" if not np.isnan(c) else ("p12x2" if not np.isnan(v12) else "none")})
    return pd.DataFrame(rows, columns=["date", "runtime", "lead_days", "pop", "pop_p12", "pop_p24", "pop_p06", "field"])


def pick_lead(by_run: pd.DataFrame, lead: float, column: str = "pop", tol_days: float = 0.5) -> pd.DataFrame:
    """One row per climate day: the run whose lead is closest to `lead` days among runs that have `column`
    (ties -> earlier run). Rows further than `tol_days` from the target lead are not used.
    """
    t = by_run.dropna(subset=[column])
    if t.empty:
        return by_run.iloc[0:0].assign(target_lead=lead)
    t = t.assign(gap=(t["lead_days"] - lead).abs())
    t = t[t["gap"] <= tol_days + 1e-9]
    t = t.sort_values(["date", "gap", "runtime"], ascending=[True, True, True])
    out = t.drop_duplicates("date", keep="first").drop(columns="gap").reset_index(drop=True)
    out["target_lead"] = lead
    return out


def pop_table(mos: pd.DataFrame, days: Sequence[pd.Timestamp], leads: Sequence[float] = LEADS_DAYS + (CHECK_LEAD_DAYS,),
              column: str = "pop") -> pd.DataFrame:
    """Long table: date, target_lead, runtime, lead_days, pop, pop_p12, pop_p24, pop_p06, field."""
    by_run = day_pop_by_run(mos, days)
    return pd.concat([pick_lead(by_run, L, column) for L in leads], ignore_index=True)


# ---------------------------------------------------------------- skill
def brier_score(p: Sequence[float], y: Sequence[int]) -> float:
    p = np.asarray(p, dtype=float)
    y = np.asarray(y, dtype=float)
    return float(np.mean((p - y) ** 2)) if len(p) else float("nan")


def calibration(p: Sequence[float], y: Sequence[int], edges=(0, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1.0 + 1e-9)) -> pd.DataFrame:
    p = np.asarray(p, dtype=float)
    y = np.asarray(y, dtype=float)
    b = np.clip(np.searchsorted(np.asarray(edges), p, side="right") - 1, 0, len(edges) - 2)
    rows = []
    for i in range(len(edges) - 1):
        m = b == i
        rows.append({"bin_lo": round(edges[i], 1), "bin_hi": round(min(edges[i + 1], 1.0), 1), "n": int(m.sum()),
                     "mean_pop": float(p[m].mean()) if m.any() else np.nan,
                     "rain_share": float(y[m].mean()) if m.any() else np.nan})
    return pd.DataFrame(rows)
