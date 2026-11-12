"""The registered cases (pre-registration, "Cases") and the runner.

A case = settlement station S, park gauge, the park's true loss-day definition, TRAIN and REPORT windows, the
rule for the "worst seasons" metric and the strategies reported. run_case() fits on TRAIN, applies to both
windows, computes the metrics and bootstraps the REPORT seasons.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping

import numpy as np
import pandas as pd

from .bootstrap import bootstrap_metrics, N_DRAWS, SEED
from .data import ParkLoss, joint_daily, season_aggregates, split_windows
from .metrics import METRICS, all_metrics
from .strategies import STRATEGIES, Params, fit_params, season_results

TRENTON_WINDOWS = ((1999, 2014), (2015, 2026))
PHILADELPHIA_WINDOWS = ((1941, 1990), (1991, 2026))
DIFFERENCES = (("3", "2"), ("3", "5"), ("5", "2"), ("3", "4"))
STRATEGY_LABEL = {
    "0": "0 no hedge",
    "1": "1 Kalshi daily, 1 per day",
    "2": "2 Kalshi daily, sized n",
    "3": "3 seasonal, six buckets",
    "4": "4 seasonal, exact (benchmark)",
    "5n": "5n Kalshi daily at fair-comparison price, 1 per day",
    "5": "5 Kalshi daily at fair-comparison price, sized n",
}
BASIS = {"0": "observed weather"}


@dataclass(frozen=True)
class Case:
    """One registered case.

    case_id      short id used in every table
    settlement   station whose count the contracts settle on (S)
    park         gauge standing in for the park (equal to `settlement` in same-station cases)
    park_loss    the park's true loss-day definition
    train, report  inclusive season ranges
    worst_rule   'worst3' (Trenton) or 'worst10pct' (Philadelphia)
    strategies   strategies reported for this case
    registered   False for runs that are sensitivities added by the evaluator (always labelled)
    bucket_source  None, or a station id: take the C_S counts for edges, m_j, q_j from that station's own
                 same-station TRAIN seasons instead of the joint TRAIN seasons (non-registered sensitivity)
    """
    case_id: str
    settlement: str
    park: str
    park_loss: ParkLoss = ParkLoss()
    train: tuple[int, int] = TRENTON_WINDOWS[0]
    report: tuple[int, int] = TRENTON_WINDOWS[1]
    worst_rule: str = "worst3"
    strategies: tuple[str, ...] = STRATEGIES
    description: str = ""
    registered: bool = True
    bucket_source: str | None = None


MISSPEC = {
    "c1": (ParkLoss("0p10", "10_18"), "park loss day is >= 0.10 inch"),
    "c2": (ParkLoss("0p50", "10_18"), "park loss day is >= 0.50 inch"),
    "c3": (ParkLoss("0p25", "10_20"), "park loss window is 10:00-20:00"),
    "c4": (ParkLoss("0p25", "10_16"), "park loss window is 10:00-16:00"),
    "c5": (ParkLoss("0p25", "10_18", True), "park loses on weekends and holidays only"),
}


def registered_cases() -> list[Case]:
    """Cases A, B1, B2, C (ten sub-cases), D (three runs), E, in the order of the pre-registration."""
    tw, pw = TRENTON_WINDOWS, PHILADELPHIA_WINDOWS
    cases = [
        Case("A", "TTN", "TTN", description="same-station ceiling at Trenton (circular by construction)"),
        Case("B1", "TTN", "PNE", description="HEADLINE: settle at Trenton, park loss at Philadelphia NE gauge"),
        Case("B2", "TTN", "DYL", description="settle at Trenton, park loss at Doylestown gauge"),
    ]
    for key, (pl, text) in MISSPEC.items():
        cases.append(Case(f"C-{key}-TTN", "TTN", "TTN", park_loss=pl, description=f"Trenton same-station; {text}"))
    for key, (pl, text) in MISSPEC.items():
        cases.append(Case(f"C-{key}-B1", "TTN", "PNE", park_loss=pl, description=f"B1 (PNE stand-in); {text}"))
    cases += [
        Case("D-same", "PHL", "PHL", train=pw[0], report=pw[1], worst_rule="worst10pct",
             description="long history, Philadelphia same-station"),
        Case("D-same-ex4147", "PHL", "PHL", train=(1948, 1990), report=pw[1], worst_rule="worst10pct",
             description="Philadelphia same-station, doubtful seasons 1941-47 excluded from TRAIN"),
        Case("D-PNE", "PHL", "PNE", train=pw[0], report=pw[1], worst_rule="worst10pct",
             description="settle at Philadelphia Intl, park loss at Philadelphia NE gauge"),
        Case("E", "ABE", "ABE", train=pw[0], report=pw[1], worst_rule="worst10pct", strategies=("0", "3", "4"),
             description="Allentown same-station ('should be listed'); no Kalshi market, strategies 0, 3, 4"),
    ]
    return cases


def sensitivity_cases() -> list[Case]:
    """Runs that are NOT registered cases; added because a registered rule was ambiguous or thin. Labelled."""
    pw = PHILADELPHIA_WINDOWS
    return [
        Case("E-trenton-windows", "ABE", "ABE", worst_rule="worst3", strategies=("0", "3", "4"), registered=False,
             description="Allentown with the Trenton windows (the pre-registration names no window for E)"),
        Case("D-PNE-phl-buckets", "PHL", "PNE", train=pw[0], report=pw[1], worst_rule="worst10pct", registered=False,
             bucket_source="PHL",
             description="D-PNE with bucket edges, m_j, q_j from all Philadelphia TRAIN seasons (not only the "
                         "few joint TRAIN seasons); n and d still from the joint TRAIN seasons"),
    ]


def run_case(case: Case, daily: Mapping[str, pd.DataFrame], price_params: Mapping[str, float], loading: float = 0.20,
             edge_method: str = "inverse_cdf", n_draws: int = N_DRAWS, seed: int = SEED) -> dict:
    """Fit on TRAIN, apply to TRAIN and REPORT, compute metrics and REPORT bootstrap intervals.

    daily         {station id: daily table} (hedge_eval.data.load_daily)
    price_params  skill-model parameters {"a", "s", "u"}
    Returns a dict:
      "params"   Params (TRAIN-chosen)
      "seasons"  long table: one row per season x strategy with window ('TRAIN' or 'REPORT'), observed counts,
                 payout, premium, net_cost
      "metrics"  long table: strategy, window, metric, value, lo, hi, n_seasons, n_boot_valid. Intervals exist for
                 REPORT only. HE differences appear as strategy 'a_minus_b', metric 'he'.
    """
    joint = joint_daily(daily[case.settlement], daily[case.park], case.park_loss)
    train_days, report_days = split_windows(joint, case.train, case.report)
    if train_days.empty or report_days.empty:
        raise ValueError(f"case {case.case_id}: empty TRAIN or REPORT window")
    params = fit_params(train_days, price_params, loading, edge_method)
    if case.bucket_source is not None:
        params = _refit_with_bucket_source(case, daily, train_days, params, price_params, loading, edge_method)

    frames, rows = [], []
    for window, days in (("TRAIN", train_days), ("REPORT", report_days)):
        res = season_results(days, params)
        res.insert(0, "window", window)
        frames.append(res)
        d_park = res[res["strategy"] == "0"]["D_park"].to_numpy(dtype=float)
        legs = {s: (g["payout"].to_numpy(), g["premium"].to_numpy()) for s, g in res.groupby("strategy", sort=False)}
        point = {s: all_metrics(d_park, pay, prem, params.reference, case.worst_rule) for s, (pay, prem) in legs.items()}
        intervals = {}
        if window == "REPORT":
            intervals, _ = bootstrap_metrics(d_park, legs, params.reference, case.worst_rule, DIFFERENCES, n_draws, seed)
        for s in legs:
            for m in METRICS:
                lo, hi, nv = intervals.get((s, m), (np.nan, np.nan, 0))
                rows.append((s, window, m, point[s][m], lo, hi, len(d_park), nv))
        for a, b in DIFFERENCES:
            lo, hi, nv = intervals.get((f"{a}_minus_{b}", "he"), (np.nan, np.nan, 0))
            rows.append((f"{a}_minus_{b}", window, "he", point[a]["he"] - point[b]["he"], lo, hi, len(d_park), nv))
    metrics = pd.DataFrame(rows, columns=["strategy", "window", "metric", "value", "lo", "hi", "n_seasons",
                                          "n_boot_valid"])
    seasons = pd.concat(frames, ignore_index=True)
    keep = set(case.strategies)
    metrics = metrics[[all(p in keep for p in s.split("_minus_")) for s in metrics["strategy"]]].reset_index(drop=True)
    seasons = seasons[seasons["strategy"].isin(keep)].reset_index(drop=True)
    return {"case": case, "params": params, "seasons": seasons, "metrics": metrics}


def _refit_with_bucket_source(case: Case, daily, train_days, params: Params, price_params, loading, edge_method) -> Params:
    """Sensitivity only: edges, m_j, n_j, q_j from the same-station TRAIN seasons of `case.bucket_source`.

    d3 is then re-chosen on the joint TRAIN seasons with those buckets. Everything else in `params` is kept.
    Uses TRAIN seasons only.
    """
    from .strategies import (D_GRID, add_half_probs, argmax_first, bucket_edges, bucket_index, bucket_means,
                             bucket_premium, holdings)
    from .metrics import hedge_effectiveness
    src = daily[case.bucket_source]
    src_train, _ = split_windows(joint_daily(src, src), case.train, case.report)
    counts = season_aggregates(src_train)["C_S"].to_numpy(dtype=float)
    edges, raw = bucket_edges(counts, edge_method)
    m, n_j = bucket_means(counts, edges)
    q = add_half_probs(n_j)
    agg = season_aggregates(train_days)
    d_park, c_s = agg["D_park"].to_numpy(dtype=float), agg["C_S"].to_numpy(dtype=float)
    b = bucket_index(c_s, edges)
    he = []
    for d in D_GRID:
        h = holdings(m, d)
        he.append(hedge_effectiveness(d_park - np.asarray(h)[b] + bucket_premium(h, q, loading), d_park,
                                      params.reference))
    i = argmax_first(he)
    h = holdings(m, D_GRID[i])
    th = dict(params.train_he)
    th["3"] = he[i]
    return replace(params, edges=edges, edges_raw=raw, m=m, n_j=n_j, q=q, d3=int(D_GRID[i]), h=h,
                   premium3=bucket_premium(h, q, loading), train_he=th)
