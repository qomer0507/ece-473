"""Tasks 3 and 4: MODELLED price of the daily contract by lead time, and hedge effectiveness by lead.

Price at lead L (MODELLED):  ask = clamp(PoP_L + a),  cost = ask + taker fee (one-contract order),
fill = 1 - u on rain days (Phase 2 strategy 2's unfilled-order rule). Lead = infinity: PoP = monthly
climatology of the TRAIN seasons. Premium and payout are scaled by n contracts per day.

Hedge rules follow Phase 2 strategy 2 (src/hedge_eval, imported, not edited): n chosen on TRAIN from
{0.05..1.0} to maximise TRAIN HE (ties to the smallest n), reference = TRAIN mean of D_park, HE on REPORT
seasons, bootstrap over REPORT seasons (2,000 draws, seed 473).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np
import pandas as pd

from ..hedge_eval.bootstrap import N_DRAWS, SEED, bootstrap_metrics
from ..hedge_eval.data import season_aggregates
from ..hedge_eval.metrics import all_metrics, hedge_effectiveness
from ..hedge_eval.strategies import N_GRID, argmax_first, monthly_p
from ..kalshi.rain_price_model import clamp_price
from ..kalshi.rain_quotes import taker_fee

A_MAIN = 0.0851          # price_model.json, skill model
A_SENS = 0.068           # a_net_matched sensitivity
U_DEFAULT = 0.0833       # share of rain days with no offer (price_model.json)
AVAILABILITY_SHARE = 0.9  # a season is available for a lead if >= 90% of its joint usable days have a MOS value


def modelled_ask(pop: float, a: float) -> float:
    """clamp(PoP + a): whole cents in [0.01, 0.99]. MODELLED."""
    if not 0.0 <= pop <= 1.0:
        raise ValueError("pop must be in [0, 1]")
    return clamp_price(pop + a)


def modelled_day_cost(pop: float, rain: int, a: float, u: float = U_DEFAULT) -> tuple[float, float, float]:
    """(premium incl. fee, payout, ask) for one contract on one day, scaled by the fill share. MODELLED."""
    ask = modelled_ask(pop, a)
    fill = 1.0 - u if rain == 1 else 1.0
    return (ask + taker_fee(ask, 1)) * fill, float(rain) * fill, ask


def pop_with_carry_forward(days: pd.DataFrame, pop_by_date: Mapping[pd.Timestamp, float],
                           p_month: Mapping[int, float]) -> tuple[np.ndarray, np.ndarray]:
    """PoP per day: the MOS value when one exists, else the month's climatology. Returns (pop, used_mos flag)."""
    pop = np.empty(len(days))
    used = np.zeros(len(days), dtype=bool)
    dates = pd.DatetimeIndex(days["date"])
    months = days["month"].to_numpy()
    for i in range(len(days)):
        v = pop_by_date.get(dates[i])
        if v is not None and not (isinstance(v, float) and math.isnan(v)):
            pop[i] = float(v)
            used[i] = True
        else:
            pop[i] = p_month.get(int(months[i]), p_month[0])
    return pop, used


def season_unit_table(days: pd.DataFrame, pop: np.ndarray, a: float, u: float = U_DEFAULT) -> pd.DataFrame:
    """Per season: premium (incl. fee) and payout of ONE contract per day, and the mean ask. MODELLED."""
    prem = np.empty(len(days)); pay = np.empty(len(days)); ask = np.empty(len(days))
    rain = days["k_s"].to_numpy()
    for i in range(len(days)):
        prem[i], pay[i], ask[i] = modelled_day_cost(float(pop[i]), int(rain[i]), a, u)
    t = pd.DataFrame({"season": days["season"].to_numpy(), "premium": prem, "payout": pay, "ask": ask})
    g = t.groupby("season").agg(premium=("premium", "sum"), payout=("payout", "sum"), mean_ask=("ask", "mean"),
                                n_days=("ask", "size")).reset_index()
    return g


def choose_n(d_park: np.ndarray, pay: np.ndarray, prem: np.ndarray, reference: float) -> tuple[float, float]:
    """Strategy 2 rule: n in N_GRID with the highest TRAIN HE; ties to the smallest n. Returns (n, TRAIN HE)."""
    he = [hedge_effectiveness(d_park - n * pay + n * prem, d_park, reference) for n in N_GRID]
    i = argmax_first(he)
    return N_GRID[i], he[i]


def available_seasons(days: pd.DataFrame, used_mos: np.ndarray, share: float = AVAILABILITY_SHARE) -> list[int]:
    t = pd.DataFrame({"season": days["season"].to_numpy(), "u": used_mos})
    g = t.groupby("season")["u"].mean()
    return [int(s) for s, v in g.items() if v >= share - 1e-12]


@dataclass
class LeadResult:
    lead_label: str
    n: float
    train_he: float
    train_seasons: list[int]
    report_seasons: list[int]
    reference: float
    metrics: dict
    intervals: dict
    carry_forward_days_train: int
    carry_forward_days_report: int
    mean_ask_report: float


def evaluate_lead(train_days: pd.DataFrame, report_days: pd.DataFrame, pop_train: np.ndarray, pop_report: np.ndarray,
                  used_train: np.ndarray, used_report: np.ndarray, a: float, worst_rule: str, label: str,
                  u: float = U_DEFAULT, n_fixed: float | None = None, reference_fixed: float | None = None,
                  n_draws: int = N_DRAWS, seed: int = SEED) -> LeadResult:
    """Fit n on TRAIN (or use n_fixed), apply to REPORT, bootstrap REPORT. One lead, one case."""
    agg_tr = season_aggregates(train_days) if len(train_days) else None
    agg_rp = season_aggregates(report_days)
    if agg_tr is not None and len(agg_tr):
        d_tr = agg_tr["D_park"].to_numpy(dtype=float)
        reference = float(d_tr.mean()) if reference_fixed is None else reference_fixed
        unit_tr = season_unit_table(train_days, pop_train, a, u)
        if list(unit_tr["season"]) != list(agg_tr["season"]):
            raise AssertionError("season order mismatch (TRAIN)")
        if n_fixed is None:
            n, he_tr = choose_n(d_tr, unit_tr["payout"].to_numpy(), unit_tr["premium"].to_numpy(), reference)
        else:
            n = n_fixed
            he_tr = hedge_effectiveness(d_tr - n * unit_tr["payout"].to_numpy() + n * unit_tr["premium"].to_numpy(),
                                        d_tr, reference)
        train_seasons = [int(x) for x in agg_tr["season"]]
    else:
        if n_fixed is None or reference_fixed is None:
            raise ValueError("no TRAIN seasons: n_fixed and reference_fixed are required")
        n, he_tr, reference, train_seasons = n_fixed, float("nan"), reference_fixed, []
    d_rp = agg_rp["D_park"].to_numpy(dtype=float)
    unit_rp = season_unit_table(report_days, pop_report, a, u)
    if list(unit_rp["season"]) != list(agg_rp["season"]):
        raise AssertionError("season order mismatch (REPORT)")
    pay, prem = n * unit_rp["payout"].to_numpy(), n * unit_rp["premium"].to_numpy()
    metrics = all_metrics(d_rp, pay, prem, reference, worst_rule)
    metrics["premium_per_payout"] = float(prem.sum() / pay.sum()) if pay.sum() > 0 else float("nan")
    intervals, _ = bootstrap_metrics(d_rp, {label: (pay, prem)}, reference, worst_rule, (), n_draws, seed)
    return LeadResult(label, float(n), float(he_tr), train_seasons, [int(x) for x in agg_rp["season"]], reference,
                      metrics, {m: v for (s, m), v in intervals.items()},
                      int((~used_train).sum()) if len(train_days) else 0, int((~used_report).sum()),
                      float(np.average(unit_rp["mean_ask"], weights=unit_rp["n_days"])))


def split_60_40(seasons: Sequence[int]) -> tuple[list[int], list[int]]:
    """Question 1's rule: the first 60% of the seasons (rounded down, at least 1) are TRAIN, the rest REPORT."""
    s = sorted(int(x) for x in seasons)
    k = max(1, int(math.floor(0.6 * len(s))))
    return s[:k], s[k:]
