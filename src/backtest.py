"""Integrated A vs B backtest (Viktor workstream).

Input: a DataFrame shaped like data/processed/aligned_daily.csv
    date, city, local_station_id, ref_station_id, local_tmax_f, ref_tmax_f, data_quality

Steps per (city, local_station_id, ref_station_id) pair and threshold k:
  1. Keep season days (May 1 - Sep 30). Dates are calendar dates as reported
     (local standard time day per SPEC), parsed without time zone.
  2. Drop rows with missing local or reference TMAX. Count them; never impute.
  3. Split: train = 2015-2021, test = 2022-2025 (SPEC).
  4. Daily payouts: target, station (A), residual, two-part (B).
  5. Price on TRAIN only: E[station], E[R]. Station premium uses an ASSUMED
     markup; residual premium uses loading L swept 0-100%.
  6. Report metrics for both splits (train = in-sample, test = held out).
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd

from src import local_residual as lr
from src import metrics as mt

REQUIRED_COLUMNS = ["date", "city", "local_station_id", "ref_station_id",
                    "local_tmax_f", "ref_tmax_f", "data_quality"]
PAIR_KEYS = ["city", "local_station_id", "ref_station_id"]
TRAIN_YEARS = (2015, 2021)
TEST_YEARS = (2022, 2025)
SEASON_MONTHS = (5, 6, 7, 8, 9)
DEFAULT_THRESHOLDS = (85.0, 90.0, 95.0)
DEFAULT_NOTIONAL = 800.0
DEFAULT_STATION_MARKUP = 0.20  # ASSUMED, not an observed exchange price
DEFAULT_LOADINGS = np.round(np.linspace(0.0, 1.0, 21), 4)


def validate_columns(df: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"aligned data is missing columns: {missing}")


def prepare(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Season filter, split label, missing-row flag.

    Returns (clean_rows, row_accounting). Missing rows are dropped from
    clean_rows and counted in row_accounting by pair, split, data_quality.
    """
    validate_columns(df)
    d = df.copy()
    d["date"] = pd.to_datetime(d["date"], errors="coerce")
    bad_date = d["date"].isna()
    d = d[~bad_date]
    d = d[d["date"].dt.month.isin(SEASON_MONTHS)]
    yr = d["date"].dt.year
    d["split"] = np.select(
        [yr.between(*TRAIN_YEARS), yr.between(*TEST_YEARS)], ["train", "test"], default="out_of_range")
    d = d[d["split"] != "out_of_range"]
    for c in ("local_tmax_f", "ref_tmax_f"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["missing"] = lr.missing_mask(d["local_tmax_f"], d["ref_tmax_f"])
    d["data_quality"] = d["data_quality"].fillna("NA").astype(str)

    acct = (d.groupby(PAIR_KEYS + ["split", "data_quality"], dropna=False)
              .agg(rows=("missing", "size"), missing_rows=("missing", "sum"))
              .reset_index())
    acct["unparseable_dates_total"] = int(bad_date.sum())
    return d[~d["missing"]].copy(), acct


def daily_payouts(local_tmax, ref_tmax, threshold: float, notional: float) -> Dict[str, np.ndarray]:
    target = lr.local_target_payout(local_tmax, threshold, notional)
    station = lr.station_payout(ref_tmax, threshold, notional)
    resid = lr.residual_shortfall_payout(target, station)
    return {
        "target": target,
        "station": station,
        "residual": resid,
        "two_part": lr.two_part_payout(target, station),
        "local_trig": np.asarray(local_tmax, float) >= threshold,
        "station_trig": np.asarray(ref_tmax, float) >= threshold,
    }


def _objectives(notional: float, mv_a: float, cvar_gamma: float, cvar_alpha: float):
    return {
        "risk_neutral": mt.make_objective("risk_neutral"),
        "mean_variance": mt.make_objective("mean_variance", notional=notional, a=mv_a),
        "mean_cvar": mt.make_objective("mean_cvar", gamma=cvar_gamma, alpha=cvar_alpha),
    }


def run_backtest(df: pd.DataFrame,
                 thresholds: Iterable[float] = DEFAULT_THRESHOLDS,
                 notional: float = DEFAULT_NOTIONAL,
                 station_markup: float = DEFAULT_STATION_MARKUP,
                 loadings: Iterable[float] = DEFAULT_LOADINGS,
                 mv_a: float = 1.0, cvar_gamma: float = 0.25, cvar_alpha: float = 0.95
                 ) -> Dict[str, pd.DataFrame]:
    """Run A and B on identical rows. Returns dict of result tables."""
    clean, acct = prepare(df)
    objs = _objectives(notional, mv_a, cvar_gamma, cvar_alpha)
    metric_rows: List[dict] = []
    be_rows: List[dict] = []
    sweep_rows: List[dict] = []

    for pair, g in clean.groupby(PAIR_KEYS):
        pair_d = dict(zip(PAIR_KEYS, pair))
        for k in thresholds:
            p = {s: daily_payouts(gs["local_tmax_f"].to_numpy(), gs["ref_tmax_f"].to_numpy(), k, notional)
                 for s, gs in g.groupby("split")}
            if "train" not in p:
                continue  # cannot price without a training window
            er_station = float(np.mean(p["train"]["station"])) if p["train"]["station"].size else np.nan
            er_resid = float(np.mean(p["train"]["residual"])) if p["train"]["residual"].size else np.nan
            prem_a = mt.premium(er_station, station_markup)

            for split, x in p.items():
                base = {**pair_d, "threshold_f": k, "split": split, "notional": notional,
                        "station_markup_ASSUMED": station_markup,
                        "train_E_station": er_station, "train_E_residual": er_resid}
                mm = mt.trigger_mismatch_rates(x["local_trig"], x["station_trig"])
                mean_target = float(np.mean(x["target"])) if x["target"].size else np.nan
                for strat, pay, prem in (("A_station_only", x["station"], prem_a),
                                         ("B_two_part", x["two_part"], None)):
                    pm = mt.payout_metrics(x["target"], pay)
                    row = {**base, "strategy": strat, **mm, **pm,
                           "mean_residual_payout": float(np.mean(x["residual"])) if strat.startswith("B") else 0.0,
                           "station_premium_per_day": prem_a}
                    if prem is not None:  # Strategy A: premium fully specified
                        row["total_premium_per_day"] = prem
                        row["premium_per_target_dollar"] = prem / mean_target if mean_target else np.nan
                        row["net_cost_per_target_dollar"] = ((prem - pm["mean_payout"]) / mean_target
                                                             if mean_target else np.nan)
                    metric_rows.append(row)
                # B premium depends on loading; report a few reference loadings
                for L in (0.0, 0.2, 0.5, 1.0):
                    prem_b = prem_a + mt.premium(er_resid, L)
                    mb = float(np.mean(x["two_part"]))
                    metric_rows.append({**base, "strategy": f"B_two_part@L={L:.2f}",
                                        "residual_loading_ASSUMED": L,
                                        "residual_premium_per_day": mt.premium(er_resid, L),
                                        "station_premium_per_day": prem_a,
                                        "total_premium_per_day": prem_b,
                                        "mean_payout": mb, "mean_target": mean_target,
                                        "premium_per_target_dollar": prem_b / mean_target if mean_target else np.nan,
                                        "net_cost_per_target_dollar": ((prem_b - mb) / mean_target
                                                                       if mean_target else np.nan)})
                for oname, f in objs.items():
                    args = (x["target"], x["station"], x["residual"], er_resid)
                    be = mt.break_even_loading(*args, f) if x["target"].size else np.nan
                    be_rows.append({**base, "objective": oname, "break_even_loading": be,
                                    "mv_a": mv_a, "cvar_gamma": cvar_gamma, "cvar_alpha": cvar_alpha})
                    if np.isfinite(er_resid) and er_resid > 0 and x["target"].size:
                        for r in mt.loading_sweep(*args, f, loadings=loadings):
                            sweep_rows.append({**base, "objective": oname, **r})

    return {
        "metrics": pd.DataFrame(metric_rows),
        "break_even": pd.DataFrame(be_rows),
        "loading_sweep": pd.DataFrame(sweep_rows),
        "row_accounting": acct,
    }
