"""The exact seasonal count contract (Phase 2 strategy 4) on a (S, G) pair, and HE on REPORT.

Rules (docs/PHASE3_PREREG.md, Question 1; reading choices 3-6 of docs/status/phase3_temp.md):
  unhedged cost at G per season    D = C_G (one hot day costs 1)
  payout of the contract on S      max(C_S - d, 0)
  d chosen on TRAIN from {0..8}    highest TRAIN HE, ties to the smallest d (hedge_eval.strategies.argmax_first)
  premium                          (1 + 0.20) x TRAIN mean payout, charged every season
  TRAIN / REPORT                   first floor(0.6 N) joint usable seasons in calendar order / the rest
  HE on REPORT                     hedge_eval.metrics.hedge_effectiveness with reference = TRAIN mean of D

The metric and the tie rule are imported from src.hedge_eval, which is not edited. Weather is observed; the
premium is modelled.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..hedge_eval.metrics import hedge_effectiveness
from ..hedge_eval.strategies import D_GRID, argmax_first

LOADING = 0.20
TRAIN_SHARE = 0.60
MIN_SEASONS_PER_WINDOW = 2


def split_seasons(usable_seasons) -> tuple[list[int], list[int]]:
    """(TRAIN, REPORT) season labels: the first floor(0.6 N) of the sorted usable seasons, then the rest."""
    s = sorted(int(x) for x in usable_seasons)
    n_train = int(np.floor(TRAIN_SHARE * len(s) + 1e-9))
    return s[:n_train], s[n_train:]


@dataclass
class Fit:
    """Everything chosen on TRAIN for one pair."""
    train_seasons: list[int]
    report_seasons: list[int]
    reference: float      # TRAIN mean of C_G
    d: int
    premium: float        # MODELLED: (1 + LOADING) x TRAIN mean of max(C_S - d, 0)
    train_he: float


def fit_contract(c_s_train, c_g_train, train_seasons, report_seasons, loading: float = LOADING,
                 d_grid=D_GRID) -> Fit:
    """Choose d and the premium on TRAIN seasons only (strategy 4 rule of Phase 2).

    d_grid defaults to the registered {0..8}. Any other grid is a labelled sensitivity, not the registered rule.
    """
    cs = np.asarray(c_s_train, dtype=float)
    cg = np.asarray(c_g_train, dtype=float)
    reference = float(cg.mean())
    he, prem = [], []
    for d in d_grid:
        pay = np.maximum(cs - d, 0.0)
        p = (1.0 + loading) * float(pay.mean())
        prem.append(p)
        he.append(hedge_effectiveness(cg - pay + p, cg, reference))
    i = argmax_first(he)
    return Fit(train_seasons=[int(x) for x in train_seasons], report_seasons=[int(x) for x in report_seasons],
               reference=reference, d=int(d_grid[i]), premium=float(prem[i]), train_he=float(he[i]))


def report_he(c_s_report, c_g_report, fit: Fit) -> float:
    """HE on REPORT seasons with the fixed TRAIN parameters. NaN if no REPORT season is above the reference."""
    cs = np.asarray(c_s_report, dtype=float)
    cg = np.asarray(c_g_report, dtype=float)
    net = cg - np.maximum(cs - fit.d, 0.0) + fit.premium
    return hedge_effectiveness(net, cg, fit.reference)


def evaluate_pair(seasons: pd.DataFrame, d_grid=D_GRID) -> dict:
    """Fit on TRAIN and score on REPORT from a pair's season table (src.reach_temp.pairs.pair_seasons).

    Returns a flat dict: n_usable, n_train, n_report, train_first, train_last, report_first, report_last,
    reference, d, premium, train_he, he, mean_payout_report, status ('ok', 'too_few_seasons', 'he_undefined').
    A pair with fewer than MIN_SEASONS_PER_WINDOW TRAIN or REPORT seasons gets no fit (status too_few_seasons).
    """
    u = seasons[seasons["usable"]].sort_values("season")
    train, report = split_seasons(u["season"])
    out = {"n_usable": int(len(u)), "n_train": len(train), "n_report": len(report),
           "train_first": train[0] if train else np.nan, "train_last": train[-1] if train else np.nan,
           "report_first": report[0] if report else np.nan, "report_last": report[-1] if report else np.nan,
           "reference": np.nan, "d": np.nan, "premium": np.nan, "train_he": np.nan, "he": np.nan,
           "mean_payout_report": np.nan, "status": "too_few_seasons"}
    if len(train) < MIN_SEASONS_PER_WINDOW or len(report) < MIN_SEASONS_PER_WINDOW:
        return out
    tr = u[u["season"].isin(train)]
    rp = u[u["season"].isin(report)]
    fit = fit_contract(tr["c_s"], tr["c_g"], train, report, d_grid=d_grid)
    he = report_he(rp["c_s"], rp["c_g"], fit)
    out.update(reference=fit.reference, d=fit.d, premium=fit.premium, train_he=fit.train_he, he=he,
               mean_payout_report=float(np.maximum(rp["c_s"].to_numpy(dtype=float) - fit.d, 0.0).mean()),
               status="ok" if he == he else "he_undefined")
    return out
