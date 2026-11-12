"""Metrics of the pre-registration ("Metrics").

Every function takes per-season arrays for one window (TRAIN or REPORT). The reference level of the semi-variance
is always passed in: it is the TRAIN mean of the unhedged net cost, fixed before any REPORT season is read.
"""
from __future__ import annotations

import math

import numpy as np

METRICS = ("he", "mean_net_cost", "sd_net_cost", "worst_mean_hedged", "worst_mean_unhedged", "worst_reduction",
           "premium_per_useful_payout", "total_premium", "share_seasons_reduced", "mean_payout", "mean_premium")


def semivariance(x, reference: float) -> float:
    """SV = mean of max(x - reference, 0)^2 over seasons."""
    x = np.asarray(x, dtype=float)
    return float(np.mean(np.maximum(x - reference, 0.0) ** 2))


def hedge_effectiveness(hedged, unhedged, reference: float) -> float:
    """HE = 1 - SV(hedged) / SV(unhedged), both measured against the same fixed `reference`.

    NaN when SV(unhedged) is zero (no season is worse than the reference, so there is nothing to hedge).
    """
    sv_u = semivariance(unhedged, reference)
    if sv_u <= 0.0:
        return float("nan")
    return 1.0 - semivariance(hedged, reference) / sv_u


def worst_count(n_seasons: int, rule: str) -> int:
    """How many seasons form the 'worst' group. rule 'worst3': 3 (Trenton). rule 'worst10pct': ceil(10% of N)."""
    if rule == "worst3":
        return min(3, n_seasons)
    if rule == "worst10pct":
        return max(1, math.ceil(0.10 * n_seasons - 1e-9))
    raise ValueError(f"unknown worst rule {rule!r}")


def worst_means(hedged, unhedged, k: int) -> tuple[float, float]:
    """(mean hedged, mean unhedged) net cost over the k seasons with the highest UNHEDGED cost.

    Ties in the unhedged cost are broken by position (earlier season first), so the group is deterministic.
    """
    h = np.asarray(hedged, dtype=float)
    u = np.asarray(unhedged, dtype=float)
    idx = np.argsort(-u, kind="stable")[:k]
    return float(h[idx].mean()), float(u[idx].mean())


def useful_payout(payout, d_park) -> np.ndarray:
    """Per season: min(payout, D_park). Money paid beyond the season's loss is not useful."""
    return np.minimum(np.asarray(payout, dtype=float), np.asarray(d_park, dtype=float))


def premium_per_useful_payout(premium, payout, d_park) -> float:
    """Total premium / total useful payout over the seasons. NaN when the useful payout is zero."""
    up = float(useful_payout(payout, d_park).sum())
    return float(np.sum(premium)) / up if up > 0 else float("nan")


def all_metrics(d_park, payout, premium, reference: float, worst_rule: str) -> dict:
    """Every registered metric for one strategy in one window.

    d_park   unhedged net cost per season (loss days, L = 1)
    payout   hedge payout per season
    premium  premium (including fees where the strategy has them) per season
    reference  TRAIN mean of the unhedged net cost
    Net cost = d_park - payout + premium.
    """
    d = np.asarray(d_park, dtype=float)
    pay = np.asarray(payout, dtype=float)
    prem = np.asarray(premium, dtype=float)
    net = d - pay + prem
    k = worst_count(len(d), worst_rule)
    wh, wu = worst_means(net, d, k)
    return {
        "he": hedge_effectiveness(net, d, reference),
        "mean_net_cost": float(net.mean()),
        "sd_net_cost": float(net.std(ddof=1)) if len(net) > 1 else float("nan"),
        "worst_mean_hedged": wh,
        "worst_mean_unhedged": wu,
        "worst_reduction": wu - wh,
        "premium_per_useful_payout": premium_per_useful_payout(prem, pay, d),
        "total_premium": float(prem.sum()),
        "share_seasons_reduced": float(np.mean(net < d - 1e-12)),
        "mean_payout": float(pay.mean()),
        "mean_premium": float(prem.mean()),
    }
