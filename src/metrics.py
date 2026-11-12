"""Comparison metrics and pricing objectives for Strategies A and B (Viktor workstream).

Notation (per day t, all in $):
    target_t  local target payout, N * 1{local_tmax >= k}
    station_t Strategy A payout
    R_t       residual payout max(target_t - station_t, 0)
    payout_t  gross payout of the strategy being evaluated
              (A: station_t ; B: station_t + R_t)

Payout-matching metrics (SPEC "Metrics"):
    local_only_rate   share of days local triggers, station does not
    station_only_rate share of days station triggers, local does not
    mean_shortfall    mean(max(target - payout, 0))
    mean_overhedge    mean(max(payout - target, 0))
    mean_abs_error    mean(|target - payout|)

Key structural fact. Strategy B pays max(target, station). So:
    shortfall_B = 0 on every day, BY CONSTRUCTION, and
    overhedge_B = overhedge_A (the residual never offsets overpayment).
Showing that B "has less shortfall" is therefore not a finding. The decision
question is whether the residual premium (1 + L) * E[R] is worth the shortfall
it removes. That depends on the pricing loading L and on the buyer's objective.

Pricing (ASSUMED, not observed market prices):
    premium = E[payout] * (1 + loading)
E[payout] is estimated on the training window and charged as a flat daily
premium in the test window. Premiums are kept separate from payouts.

Objectives. The business minimizes rho(C), with daily net cost
    C_t = premium_t + target_t - payout_t
(target_t stands in for the stylized local loss; payout_t is what the hedge
returns). Three objectives are provided:
    risk_neutral : rho = E[C]
    mean_variance: rho = E[C] + (a / N) * Var(C)           a = risk aversion (dimensionless, ASSUMED)
    mean_cvar    : rho = E[C] + g * CVaR_alpha(C)          g, alpha ASSUMED
All three are translation-equivariant in a constant premium. So the station
premium for A cancels when comparing A and B, and rho_B is affine in the
residual loading L. Break-even L* solves rho_B(L*) = rho_A.

Under risk_neutral with fair premium base, rho_B - rho_A = L * E[R], so the
break-even loading is 0: any positive loading makes B worse. That is why a
risk-averse objective is needed for a non-trivial answer. Assumptions:
daily i.i.d. view of costs (no seasonal aggregation), no discounting, no
default/counterparty risk, no transaction costs beyond the loading.
"""
from __future__ import annotations

from typing import Callable, Dict

import numpy as np

__all__ = [
    "trigger_mismatch_rates",
    "payout_metrics",
    "premium",
    "net_cost",
    "risk_neutral",
    "mean_variance",
    "mean_cvar",
    "make_objective",
    "objective_for_loading",
    "break_even_loading",
    "loading_sweep",
]


def _f(x) -> np.ndarray:
    return np.asarray(x, dtype=float)


def _check_complete(*arrays) -> None:
    for a in arrays:
        if np.any(np.isnan(_f(a))):
            raise ValueError("metrics received NaN values; drop or flag missing rows first")


# --------------------------------------------------------------------------- matching

def trigger_mismatch_rates(local_trig, station_trig) -> Dict[str, float]:
    """Trigger mismatch shares in both directions.

    local_only_rate:   local triggers, station does not (source of shortfall).
    station_only_rate: station triggers, local does not (source of overhedge).
    Inputs are boolean arrays (no NaN; filter missing rows first).
    """
    lt = np.asarray(local_trig, dtype=bool)
    st = np.asarray(station_trig, dtype=bool)
    n = lt.size
    if n == 0:
        return {"n_days": 0, "local_only_rate": np.nan, "station_only_rate": np.nan,
                "both_rate": np.nan, "neither_rate": np.nan, "mismatch_rate": np.nan}
    lo = np.mean(lt & ~st)
    so = np.mean(st & ~lt)
    return {
        "n_days": int(n),
        "local_only_rate": float(lo),
        "station_only_rate": float(so),
        "both_rate": float(np.mean(lt & st)),
        "neither_rate": float(np.mean(~lt & ~st)),
        "mismatch_rate": float(lo + so),
    }


def payout_metrics(target, payout) -> Dict[str, float]:
    """Shortfall, overhedge and absolute error of a gross payout vs. the target."""
    t, p = _f(target), _f(payout)
    _check_complete(t, p)
    if t.size == 0:
        return {k: np.nan for k in ("mean_target", "mean_payout", "mean_shortfall",
                                    "mean_overhedge", "mean_abs_error")}
    return {
        "mean_target": float(t.mean()),
        "mean_payout": float(p.mean()),
        "mean_shortfall": float(np.maximum(t - p, 0).mean()),
        "mean_overhedge": float(np.maximum(p - t, 0).mean()),
        "mean_abs_error": float(np.abs(t - p).mean()),
    }


# --------------------------------------------------------------------------- pricing

def premium(expected_payout: float, loading: float) -> float:
    """Daily premium = E[payout] * (1 + loading). Loading is ASSUMED, not observed."""
    if loading < -1:
        raise ValueError("loading must be >= -1")
    return float(expected_payout) * (1.0 + float(loading))


def net_cost(target, payout, daily_premium) -> np.ndarray:
    """C_t = premium_t + target_t - payout_t (positive = money out of pocket)."""
    return _f(daily_premium) + _f(target) - _f(payout)


# --------------------------------------------------------------------------- objectives

def risk_neutral(c) -> float:
    return float(np.mean(_f(c)))


def mean_variance(c, a: float = 1.0, notional: float = 800.0) -> float:
    """E[C] + (a/N) Var(C). Scaling by N keeps `a` dimensionless."""
    c = _f(c)
    return float(c.mean() + (a / notional) * c.var())


def mean_cvar(c, gamma: float = 0.25, alpha: float = 0.95) -> float:
    """E[C] + gamma * CVaR_alpha(C); CVaR = mean of the worst (1-alpha) share of days.

    Uses the Rockafellar-Uryasev form with linear interpolation of the tail
    so the tail weight is exactly (1-alpha) even with ties.
    """
    c = np.sort(_f(c))[::-1]
    n = c.size
    m = (1.0 - alpha) * n
    k = int(np.floor(m))
    tail = c[:k].sum() + (m - k) * (c[k] if k < n else 0.0)
    cvar = tail / m if m > 0 else c[0]
    return float(c.mean() + gamma * cvar)


def make_objective(name: str, notional: float = 800.0, a: float = 1.0,
                   gamma: float = 0.25, alpha: float = 0.95) -> Callable[[np.ndarray], float]:
    if name == "risk_neutral":
        return risk_neutral
    if name == "mean_variance":
        return lambda c: mean_variance(c, a=a, notional=notional)
    if name == "mean_cvar":
        return lambda c: mean_cvar(c, gamma=gamma, alpha=alpha)
    raise ValueError(f"unknown objective {name!r}")


# --------------------------------------------------------------------------- A vs B

def objective_for_loading(target, station, residual, er_base: float,
                          residual_loading: float, objective,
                          station_premium: float = 0.0) -> Dict[str, float]:
    """rho_A and rho_B for one residual loading.

    er_base: E[R] used to price the residual (from the training window).
    station_premium: daily premium of A (cancels in A-B but kept for levels).
    """
    t, s, r = _f(target), _f(station), _f(residual)
    _check_complete(t, s, r)
    c_a = net_cost(t, s, station_premium)
    c_b = net_cost(t, s + r, station_premium + premium(er_base, residual_loading))
    rho_a, rho_b = objective(c_a), objective(c_b)
    return {"rho_A": rho_a, "rho_B": rho_b, "delta_B_minus_A": rho_b - rho_a}


def break_even_loading(target, station, residual, er_base: float, objective) -> float:
    """Loading L* where rho_B(L*) = rho_A. B is preferred for L < L*.

    rho_B is affine in L for translation-equivariant objectives, so two
    evaluations give the exact root. Returns nan if er_base == 0 (no
    residual exposure, nothing to price) and can be negative (B not worth it
    even at a subsidized price).
    """
    if not np.isfinite(er_base) or er_base <= 0:
        return float("nan")
    d0 = objective_for_loading(target, station, residual, er_base, 0.0, objective)["delta_B_minus_A"]
    d1 = objective_for_loading(target, station, residual, er_base, 1.0, objective)["delta_B_minus_A"]
    slope = d1 - d0  # equals er_base for the objectives above
    return float(-d0 / slope)


def loading_sweep(target, station, residual, er_base: float, objective,
                  loadings=np.linspace(0.0, 1.0, 21)) -> list:
    """rho_B - rho_A over a grid of residual loadings (SPEC: 0-100%)."""
    rows = []
    for L in loadings:
        d = objective_for_loading(target, station, residual, er_base, float(L), objective)
        rows.append({"loading": float(L), **d})
    return rows
