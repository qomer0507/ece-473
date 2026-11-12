"""Daily inputs and the joint usable-day alignment (pre-registration, "Notation").

D_park, C_S and K_S are counted over the same set of days: season days whose opening window is complete at BOTH
the settlement station S and the park gauge. Seasons must pass the Phase 1 usable-season rule at both locations.
All values are observed station data.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import numpy as np
import pandas as pd

CONTRACT_LOSS_COLUMN = "loss_0p25_10_18"   # the contract's index: >= 0.25 inch in 10:00-18:00, all days
MAIN_USABLE_COLUMN = "usable_10_18"
KALSHI_THRESHOLD_IN = 0.01
JOINT_COLUMNS = ["date", "season", "month", "c_s", "k_s", "d_park"]


@dataclass(frozen=True)
class ParkLoss:
    """How the park's true loss day is defined at the park gauge.

    threshold_tag  '0p10', '0p25' or '0p50' (inches in the window)
    window_tag     '10_16', '10_18' or '10_20' (local clock hours)
    weekend_holiday_only  True: only Saturdays, Sundays, Memorial Day, July 4 and Labor Day can be loss days
    """
    threshold_tag: str = "0p25"
    window_tag: str = "10_18"
    weekend_holiday_only: bool = False

    @property
    def loss_column(self) -> str:
        return f"loss_{self.threshold_tag}_{self.window_tag}"

    @property
    def usable_column(self) -> str:
        return f"usable_{self.window_tag}"


def load_daily(rain_dir: str, station: str) -> pd.DataFrame:
    """Read data/processed/rain/daily_<station>.parquet (Phase 1 format). `date` becomes datetime64."""
    d = pd.read_parquet(os.path.join(rain_dir, f"daily_{station}.parquet"))
    d["date"] = pd.to_datetime(d["date"])
    return d


def joint_daily(s_daily: pd.DataFrame, park_daily: pd.DataFrame, park_loss: ParkLoss = ParkLoss()) -> pd.DataFrame:
    """One row per day that is usable at both locations, in seasons usable at both locations.

    s_daily     daily table of the settlement station S. Needs date, season, season_usable, usable_10_18,
                loss_0p25_10_18 and ghcn_prcp_in (the official daily total; the Kalshi rule uses this column).
    park_daily  daily table of the park gauge. Needs date, season, season_usable, usable_10_18, weekend_or_holiday,
                and the usable and loss columns named by `park_loss`. Pass s_daily itself for a same-station case.
    Rules
      * a season is kept only if season_usable is True at S and at the park gauge;
      * a day is kept only if the main opening window (10:00-18:00) is complete at S and at the park gauge, and
        the park's own loss window (if different) is complete at the park gauge;
      * c_s    = 1 if S had >= 0.25 inch in 10:00-18:00 (the contract's index);
      * k_s    = 1 if the GHCN daily total at S is >= 0.01 inch. A missing daily total counts as No;
      * d_park = 1 if the park gauge had a loss day under `park_loss`.
    Returns columns date, season, month, c_s, k_s, d_park (ints), sorted by date. Days are dropped, never imputed.
    """
    s = s_daily[["date", "season", "season_usable", MAIN_USABLE_COLUMN, CONTRACT_LOSS_COLUMN, "ghcn_prcp_in"]].copy()
    s.columns = ["date", "season", "s_season_usable", "s_usable", "s_loss", "s_ghcn"]
    cols = ["date", "season_usable", MAIN_USABLE_COLUMN, "weekend_or_holiday", park_loss.usable_column,
            park_loss.loss_column]
    p = park_daily.loc[:, list(dict.fromkeys(cols))].copy()
    p = pd.DataFrame({
        "date": p["date"].to_numpy(),
        "p_season_usable": p["season_usable"].to_numpy(dtype=bool),
        "p_usable_main": p[MAIN_USABLE_COLUMN].to_numpy(dtype=bool),
        "p_usable_win": p[park_loss.usable_column].to_numpy(dtype=bool),
        "p_weekend": p["weekend_or_holiday"].to_numpy(dtype=bool),
        "p_loss": p[park_loss.loss_column].fillna(False).to_numpy(dtype=bool),
    })
    if s["date"].duplicated().any() or p["date"].duplicated().any():
        raise ValueError("duplicate dates in a daily table")
    m = s.merge(p, on="date", how="inner")
    keep = (m["s_season_usable"].to_numpy(dtype=bool) & m["p_season_usable"].to_numpy(dtype=bool)
            & m["s_usable"].to_numpy(dtype=bool) & m["p_usable_main"].to_numpy(dtype=bool)
            & m["p_usable_win"].to_numpy(dtype=bool))
    m = m[keep]
    d_park = m["p_loss"].to_numpy(dtype=bool)
    if park_loss.weekend_holiday_only:
        d_park = d_park & m["p_weekend"].to_numpy(dtype=bool)
    out = pd.DataFrame({
        "date": m["date"].to_numpy(),
        "season": m["season"].to_numpy(dtype=int),
        "month": pd.DatetimeIndex(m["date"]).month.to_numpy(dtype=int),
        "c_s": m["s_loss"].fillna(False).to_numpy(dtype=bool).astype(int),
        "k_s": (m["s_ghcn"].to_numpy(dtype=float) >= KALSHI_THRESHOLD_IN).astype(int),  # NaN >= x is False
        "d_park": d_park.astype(int),
    })
    return out.sort_values("date").reset_index(drop=True)[JOINT_COLUMNS]


def split_windows(joint: pd.DataFrame, train: tuple[int, int], report: tuple[int, int]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(TRAIN days, REPORT days): rows of `joint` whose season lies in the inclusive year ranges."""
    tr = joint[(joint["season"] >= train[0]) & (joint["season"] <= train[1])].reset_index(drop=True)
    rp = joint[(joint["season"] >= report[0]) & (joint["season"] <= report[1])].reset_index(drop=True)
    return tr, rp


def season_aggregates(joint: pd.DataFrame) -> pd.DataFrame:
    """Per season: n_days (joint usable days), D_park, C_S, K_S. Observed."""
    g = joint.groupby("season").agg(n_days=("c_s", "size"), D_park=("d_park", "sum"), C_S=("c_s", "sum"),
                                    K_S=("k_s", "sum")).reset_index()
    return g.astype(int)
