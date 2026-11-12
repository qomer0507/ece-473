"""Whole-season bootstrap of the REPORT window (pre-registration: 2,000 draws, seed 473, 95% percentile interval).

One set of season draws is used for every strategy of a case, so differences between strategies are paired.
The TRAIN reference level is fixed; it is never re-estimated inside the bootstrap.
"""
from __future__ import annotations

import numpy as np

from .metrics import all_metrics, METRICS

N_DRAWS = 2000
SEED = 473
INTERVAL = (2.5, 97.5)


def draw_indices(n_seasons: int, n_draws: int = N_DRAWS, seed: int = SEED) -> np.ndarray:
    """(n_draws, n_seasons) array of season positions sampled with replacement: numpy default_rng(seed).integers."""
    return np.random.default_rng(seed).integers(0, n_seasons, size=(n_draws, n_seasons))


def percentile_interval(values) -> tuple[float, float, int]:
    """(2.5th, 97.5th percentile, number of draws that were not NaN). NaN draws (undefined metric) are left out."""
    v = np.asarray(values, dtype=float)
    ok = v[~np.isnan(v)]
    if len(ok) == 0:
        return float("nan"), float("nan"), 0
    lo, hi = np.percentile(ok, INTERVAL)
    return float(lo), float(hi), int(len(ok))


def bootstrap_metrics(d_park, legs: dict, reference: float, worst_rule: str, differences=(),
                      n_draws: int = N_DRAWS, seed: int = SEED) -> tuple[dict, dict]:
    """Bootstrap every metric for every strategy, plus HE differences.

    d_park       unhedged cost per REPORT season
    legs         {strategy: (payout array, premium array)} per REPORT season
    reference    TRAIN mean of unhedged cost
    differences  pairs (a, b): the interval of HE(a) - HE(b) is computed on the same draws
    Returns (intervals, draws): intervals[(strategy, metric)] = (lo, hi, n_valid); the pair key is
    ("a_minus_b", "he"). draws[(strategy, metric)] is the array of bootstrap values.
    """
    d = np.asarray(d_park, dtype=float)
    idx = draw_indices(len(d), n_draws, seed)
    draws = {(s, m): np.empty(n_draws) for s in legs for m in METRICS}
    for r in range(n_draws):
        i = idx[r]
        for s, (pay, prem) in legs.items():
            res = all_metrics(d[i], np.asarray(pay, dtype=float)[i], np.asarray(prem, dtype=float)[i], reference,
                              worst_rule)
            for m in METRICS:
                draws[(s, m)][r] = res[m]
    for a, b in differences:
        draws[(f"{a}_minus_{b}", "he")] = draws[(a, "he")] - draws[(b, "he")]
    return {k: percentile_interval(v) for k, v in draws.items()}, draws
