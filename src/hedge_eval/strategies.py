"""Strategies 0-5 of the pre-registration and their TRAIN-only parameters.

Two steps, kept apart so that nothing from REPORT seasons can reach a chosen parameter:
  fit_params(train_days, ...)      reads TRAIN days only and returns a Params object
  season_results(days, params)     applies fixed Params to any seasons (TRAIN or REPORT)

Units: L = 1 (one loss day costs 1). Weather is OBSERVED. Every premium is MODELLED.

Strategy keys
  "0"   no hedge
  "1"   Kalshi daily, 1 contract per day, modelled market price ("skill" model, fee, unfilled-order rule)
  "2"   Kalshi daily, n contracts per day, n chosen on TRAIN
  "3"   seasonal count contract, six buckets (the product)
  "4"   seasonal count contract, exact payout max(C_S - d, 0) (benchmark)
  "5n"  strategy 1 at the fair-comparison price: (1 + loading) * p per contract-day, no fee, every order filled
  "5"   strategy 2 at the fair-comparison price, n re-chosen on TRAIN at that price
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import Mapping, Sequence

import numpy as np
import pandas as pd

from ..kalshi.rain_price_model import modelled_cost
from .data import season_aggregates
from .metrics import hedge_effectiveness

N_GRID = tuple(round(0.05 * i, 2) for i in range(1, 21))   # 0.05, 0.10, ..., 1.00
D_GRID = tuple(range(0, 9))                                 # 0, 1, ..., 8
N_BUCKETS = 6
STRATEGIES = ("0", "1", "2", "3", "4", "5n", "5")
TIE_TOL = 1e-12


# ------------------------------------------------------------------ small pure rules
def bucket_edges(train_counts: Sequence[int], method: str = "inverse_cdf") -> tuple[list[int], list[int]]:
    """Five integer upper edges e1..e5 from TRAIN counts of C_S. Returns (edges, raw quantiles before repair).

    Bucket 1 is C <= e1, bucket j is e_{j-1} < C <= e_j, bucket 6 is C > e5.
    method 'inverse_cdf' (main): e_k = the smallest observed count x with at least k/6 of TRAIN seasons <= x,
        i.e. the ceil(k*N/6)-th smallest TRAIN count. Always an integer.
    method 'linear_floor' (sensitivity): floor of numpy's linearly interpolated k/6 quantile.
    Repair ("ties merged upward"): if an edge is not above the previous one it is set to previous + 1, so the six
    buckets are always distinct. The raw quantiles are returned so that any repair can be recorded.
    """
    c = np.sort(np.asarray(train_counts, dtype=float))
    n = len(c)
    if n == 0:
        raise ValueError("no TRAIN seasons")
    raw = []
    for k in range(1, N_BUCKETS):
        if method == "inverse_cdf":
            raw.append(int(c[math.ceil(k * n / N_BUCKETS - 1e-9) - 1]))
        elif method == "linear_floor":
            raw.append(int(math.floor(float(np.quantile(c, k / N_BUCKETS)) + 1e-9)))
        else:
            raise ValueError(f"unknown edge method {method!r}")
    edges = [raw[0]]
    for e in raw[1:]:
        edges.append(e if e > edges[-1] else edges[-1] + 1)
    return edges, raw


def bucket_index(count, edges: Sequence[int]) -> np.ndarray:
    """0-based bucket of each count: number of edges strictly below the count (C <= e1 -> 0, C > e5 -> 5)."""
    return np.searchsorted(np.asarray(edges), np.asarray(count), side="left")


def bucket_means(train_counts: Sequence[int], edges: Sequence[int]) -> tuple[list[float], list[int]]:
    """(m_j, n_j) for the six buckets from TRAIN counts.

    m_j = TRAIN mean of C_S inside bucket j. Empty bucket: the midpoint of its integer range (bucket 1 starts at
    0, bucket j at e_{j-1} + 1); empty top bucket: e5 + 2. n_j = number of TRAIN seasons in bucket j.
    """
    c = np.asarray(train_counts, dtype=float)
    b = bucket_index(c, edges)
    m, n = [], []
    for j in range(N_BUCKETS):
        inside = c[b == j]
        n.append(int(len(inside)))
        if len(inside):
            m.append(float(inside.mean()))
        elif j == N_BUCKETS - 1:
            m.append(float(edges[-1] + 2))
        else:
            lo = 0 if j == 0 else edges[j - 1] + 1
            m.append((lo + edges[j]) / 2.0)
    return m, n


def holdings(m: Sequence[float], d: float) -> list[float]:
    """h_j = max(m_j - d, 0)."""
    return [max(float(x) - d, 0.0) for x in m]


def add_half_probs(n_j: Sequence[int]) -> list[float]:
    """q_j = (n_j + 0.5) / (N + 3) for six buckets (add-half smoothing; sums to 1)."""
    total = sum(n_j)
    return [(x + 0.5) / (total + N_BUCKETS * 0.5) for x in n_j]


def bucket_premium(h: Sequence[float], q: Sequence[float], loading: float) -> float:
    """(1 + loading) * sum_j h_j q_j. MODELLED."""
    return (1.0 + loading) * float(sum(a * b for a, b in zip(h, q)))


def monthly_p(train_days: pd.DataFrame) -> dict[int, float]:
    """Share of TRAIN days with a Kalshi-pay outcome (k_s) per calendar month. Key 0 holds the all-month share
    and is used only if a month never occurs in TRAIN."""
    p = {int(k): float(v) for k, v in train_days.groupby("month")["k_s"].mean().items()}
    p[0] = float(train_days["k_s"].mean())
    return p


def argmax_first(values: Sequence[float]) -> int:
    """Index of the largest value; ties (within 1e-12) and NaN go to the EARLIEST grid point."""
    best, best_v = 0, -math.inf
    for i, v in enumerate(values):
        if v == v and v > best_v + TIE_TOL:
            best, best_v = i, v
    return best


# ------------------------------------------------------------------ Kalshi daily costs per season
def kalshi_unit_table(days: pd.DataFrame, p_month: Mapping[int, float], price_params: Mapping[str, float],
                      loading: float) -> pd.DataFrame:
    """Per season, for ONE contract bought every day: payout and premium under two prices. MODELLED prices.

    market price (strategies 1, 2): src.kalshi.rain_price_model.modelled_cost, model 'skill', parameters
        `price_params` (a, s, u), one-contract order. premium_mkt = sum of ask + taker fee, payout_mkt = pay days,
        both scaled by the fill share 1 - u on rain days (the unfilled-order rule).
    fair-comparison price (strategy 5): premium_fair = (1 + loading) * p per day, payout_fair = pay days.
    p for a day = `p_month` of its calendar month (TRAIN). Buying n contracts scales all four columns by n.
    """
    cache: dict[tuple[int, int], tuple[float, float]] = {}
    prem = np.zeros(len(days))
    pay = np.zeros(len(days))
    fair = np.zeros(len(days))
    months = days["month"].to_numpy()
    rain = days["k_s"].to_numpy()
    for i in range(len(days)):
        key = (int(months[i]), int(rain[i]))
        p = p_month.get(key[0], p_month[0])
        if key not in cache:
            c = modelled_cost(p, "skill", price_params, rain_today=key[1], contracts=1)
            cache[key] = (c["total"], c["payout"])
        prem[i], pay[i] = cache[key]
        fair[i] = (1.0 + loading) * p
    t = pd.DataFrame({"season": days["season"].to_numpy(), "premium_mkt": prem, "payout_mkt": pay,
                      "premium_fair": fair, "payout_fair": rain.astype(float)})
    return t.groupby("season").sum().reset_index()


# ------------------------------------------------------------------ TRAIN-only parameter choice
@dataclass
class Params:
    """Everything chosen on TRAIN seasons. Applied unchanged to REPORT seasons."""
    train_seasons: list[int]
    reference: float                 # TRAIN mean of unhedged net cost (D_park)
    p_month: dict[int, float]        # monthly Kalshi-pay frequency (key 0 = all months)
    price_params: dict[str, float]   # skill model a, s, u (fitted in Phase 1; not chosen here)
    loading: float
    n2: float                        # strategy 2 contracts per day
    n5: float                        # strategy 5 contracts per day (fair-comparison price)
    edges: list[int]
    edges_raw: list[int]
    edge_method: str
    m: list[float]
    n_j: list[int]
    q: list[float]
    d3: int
    h: list[float]
    premium3: float
    d4: int
    premium4: float
    train_he: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def _train_he(net: np.ndarray, d_park: np.ndarray, reference: float) -> float:
    return hedge_effectiveness(net, d_park, reference)


def fit_params(train_days: pd.DataFrame, price_params: Mapping[str, float], loading: float = 0.20,
               edge_method: str = "inverse_cdf") -> Params:
    """Choose every parameter from TRAIN days only.

    train_days   joint usable days of the TRAIN seasons (columns of hedge_eval.data.joint_daily)
    price_params skill-model parameters {"a", "s", "u"} (Phase 1 fit)
    loading      loading of strategies 3, 4 and 5
    Choices (ties go to the earliest grid value, i.e. the smallest n and the smallest d):
      reference  = TRAIN mean of D_park
      p_month    = TRAIN share of Kalshi-pay days per calendar month
      n2         = n in {0.05..1.00} with the highest TRAIN HE at the modelled market price
      n5         = the same at the fair-comparison price
      edges, m_j, n_j, q_j from TRAIN C_S;  d3 in {0..8} with the highest TRAIN HE of strategy 3 (premium included)
      d4         = the same rule applied to strategy 4, premium4 = (1 + loading) * TRAIN mean of max(C_S - d4, 0)
    """
    agg = season_aggregates(train_days)
    d_park = agg["D_park"].to_numpy(dtype=float)
    c_s = agg["C_S"].to_numpy(dtype=float)
    reference = float(d_park.mean())
    p_month = monthly_p(train_days)
    unit = kalshi_unit_table(train_days, p_month, price_params, loading)
    if list(unit["season"]) != list(agg["season"]):
        raise AssertionError("season order mismatch")

    def best_n(pay: np.ndarray, prem: np.ndarray) -> tuple[float, float]:
        he = [_train_he(d_park - n * pay + n * prem, d_park, reference) for n in N_GRID]
        i = argmax_first(he)
        return N_GRID[i], he[i]

    n2, he2 = best_n(unit["payout_mkt"].to_numpy(), unit["premium_mkt"].to_numpy())
    n5, he5 = best_n(unit["payout_fair"].to_numpy(), unit["premium_fair"].to_numpy())
    he1 = _train_he(d_park - unit["payout_mkt"].to_numpy() + unit["premium_mkt"].to_numpy(), d_park, reference)
    he5n = _train_he(d_park - unit["payout_fair"].to_numpy() + unit["premium_fair"].to_numpy(), d_park, reference)

    edges, raw = bucket_edges(c_s, edge_method)
    m, n_j = bucket_means(c_s, edges)
    q = add_half_probs(n_j)
    b = bucket_index(c_s, edges)
    he3 = []
    for d in D_GRID:
        h = holdings(m, d)
        pay = np.asarray(h)[b]
        he3.append(_train_he(d_park - pay + bucket_premium(h, q, loading), d_park, reference))
    i3 = argmax_first(he3)
    d3 = D_GRID[i3]
    h = holdings(m, d3)

    he4, prem4 = [], []
    for d in D_GRID:
        pay = np.maximum(c_s - d, 0.0)
        prem = (1.0 + loading) * float(pay.mean())
        prem4.append(prem)
        he4.append(_train_he(d_park - pay + prem, d_park, reference))
    i4 = argmax_first(he4)

    return Params(
        train_seasons=[int(x) for x in agg["season"]], reference=reference, p_month=p_month,
        price_params={k: float(v) for k, v in price_params.items() if k in ("a", "s", "u")}, loading=float(loading),
        n2=float(n2), n5=float(n5), edges=edges, edges_raw=raw, edge_method=edge_method, m=m, n_j=n_j, q=q,
        d3=int(d3), h=h, premium3=bucket_premium(h, q, loading), d4=int(D_GRID[i4]), premium4=float(prem4[i4]),
        train_he={"1": he1, "2": he2, "3": he3[i3], "4": he4[i4], "5n": he5n, "5": he5},
    )


# ------------------------------------------------------------------ apply fixed parameters
def season_results(days: pd.DataFrame, params: Params) -> pd.DataFrame:
    """Per season and strategy: payout, premium and net cost under fixed `params`. Long format.

    Columns: season, n_days, D_park, C_S, K_S (observed), strategy, payout, premium (MODELLED, fees included for
    strategies 1 and 2), net_cost = D_park - payout + premium.
    """
    agg = season_aggregates(days)
    unit = kalshi_unit_table(days, params.p_month, params.price_params, params.loading)
    if list(unit["season"]) != list(agg["season"]):
        raise AssertionError("season order mismatch")
    c_s = agg["C_S"].to_numpy(dtype=float)
    zeros = np.zeros(len(agg))
    pm, cm = unit["payout_mkt"].to_numpy(), unit["premium_mkt"].to_numpy()
    pf, cf = unit["payout_fair"].to_numpy(), unit["premium_fair"].to_numpy()
    legs = {
        "0": (zeros, zeros),
        "1": (pm, cm),
        "2": (params.n2 * pm, params.n2 * cm),
        "3": (np.asarray(params.h)[bucket_index(c_s, params.edges)], zeros + params.premium3),
        "4": (np.maximum(c_s - params.d4, 0.0), zeros + params.premium4),
        "5n": (pf, cf),
        "5": (params.n5 * pf, params.n5 * cf),
    }
    out = []
    for key in STRATEGIES:
        pay, prem = legs[key]
        t = agg.copy()
        t["strategy"] = key
        t["payout"] = pay
        t["premium"] = prem
        t["net_cost"] = t["D_park"] - t["payout"] + t["premium"]
        out.append(t)
    return pd.concat(out, ignore_index=True)
