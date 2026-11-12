"""Pair construction and per-pair seasonal tables (reading choices 1-3, 7 of docs/status/phase3_temp.md).

Inputs are the station table (data/processed/panel/stations.csv) and the TMAX panel in wide form
(src.panel.hedge.to_wide: index = date, columns = station id, NaN where missing). Observed data only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..panel.hedge import haversine_km

THRESHOLD_F = 90.0
MAX_KM = 200.0
SEASON_MONTHS = (5, 6, 7, 8, 9)
SEASON_DAYS = 153
USABLE_SHARE = 0.90
PAIR_COLUMNS = ["s_id", "g_id", "dist_km", "same_station", "elev_s_m", "elev_g_m", "elev_diff_m"]


def build_pairs(stations: pd.DataFrame, max_km: float = MAX_KM) -> pd.DataFrame:
    """Every ordered (S, G): S an exposure station with has_cli, G any exposure station, distance <= max_km.

    S = G is included at distance 0 (same_station True). Distance is haversine on stations.csv coordinates.
    Sorted by s_id, then g_id. Columns PAIR_COLUMNS.
    """
    exp = stations[stations["is_exposure"].astype(bool)].sort_values("id").reset_index(drop=True)
    cli = exp[exp["has_cli"].astype(bool)].reset_index(drop=True)
    rows = []
    for s in cli.itertuples():
        d = haversine_km(s.lat, s.lon, exp["lat"].to_numpy(), exp["lon"].to_numpy())
        for g, dk in zip(exp.itertuples(), d):
            same = g.id == s.id
            if same:
                dk = 0.0
            if dk <= max_km:
                rows.append((s.id, g.id, float(dk), bool(same), float(s.elev_m), float(g.elev_m),
                             abs(float(g.elev_m) - float(s.elev_m))))
    return pd.DataFrame(rows, columns=PAIR_COLUMNS)


def season_of(dates) -> np.ndarray:
    """Season label (calendar year) of each date; -1 outside May-Sep."""
    idx = pd.DatetimeIndex(dates)
    return np.where(np.isin(idx.month, SEASON_MONTHS), idx.year, -1)


def pair_seasons(wide: pd.DataFrame, s_id: str, g_id: str, threshold: float = THRESHOLD_F,
                 usable_share: float = USABLE_SHARE) -> pd.DataFrame:
    """Per season of the panel: joint-present days, counts at S and G, trigger agreement, usable flag.

    Columns: season, n_days (days with TMAX present at both), c_s (days TMAX_S >= threshold), c_g (same at G),
    n_agree (days where the two triggers agree), usable (n_days >= usable_share x SEASON_DAYS).
    Days with either value missing are dropped. Seasons that never appear in the panel are absent.
    """
    ts = wide[s_id].to_numpy(dtype=float)
    tg = wide[g_id].to_numpy(dtype=float)
    seas = season_of(wide.index)
    both = ~np.isnan(ts) & ~np.isnan(tg) & (seas > 0)
    hs = ts >= threshold
    hg = tg >= threshold
    t = pd.DataFrame({"season": seas[both], "c_s": hs[both].astype(int), "c_g": hg[both].astype(int),
                      "agree": (hs[both] == hg[both]).astype(int)})
    g = t.groupby("season").agg(n_days=("c_s", "size"), c_s=("c_s", "sum"), c_g=("c_g", "sum"),
                                n_agree=("agree", "sum")).reset_index()
    g["usable"] = g["n_days"] >= usable_share * SEASON_DAYS - 1e-9
    return g.sort_values("season").reset_index(drop=True)


def trigger_agreement(seasons: pd.DataFrame) -> float:
    """Share of joint days in USABLE seasons where 1{TMAX_G >= 90} equals 1{TMAX_S >= 90}. NaN if no days."""
    u = seasons[seasons["usable"]]
    n = int(u["n_days"].sum())
    return float(u["n_agree"].sum()) / n if n > 0 else float("nan")


def count_correlation(seasons: pd.DataFrame) -> float:
    """Pearson r of the seasonal counts c_s, c_g over usable seasons. NaN if fewer than 2 seasons or no variance."""
    u = seasons[seasons["usable"]]
    if len(u) < 2 or u["c_s"].std() == 0 or u["c_g"].std() == 0:
        return float("nan")
    return float(np.corrcoef(u["c_s"].to_numpy(dtype=float), u["c_g"].to_numpy(dtype=float))[0, 1])
