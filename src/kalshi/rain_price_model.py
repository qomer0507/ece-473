"""MODELLED price of the Kalshi daily rain contract (SPEC_v3 "Baseline: Price").

Everything returned by this module is MODELLED, not observed. It gives the cost a buyer pays for
$1 of "measurable rain today" protection, bought about 24 hours before the market closes (around
midnight at the start of the rain day), for any day of any season, from inputs that exist for all
29 seasons. Parameters are fitted on observed Kalshi asks (scripts/kalshi_rain_aggregates.py) and
stored in data/processed/kalshi_rain/price_model.json.

Three candidate models. p = climatological probability that the contract pays on that day
(share of past days with measurable rain in that calendar month at the station, supplied by the
caller from training seasons).

  "clim"     ask = clamp(p + a)
             The market knows only the calendar. Same price every day of a month.
  "persist"  ask = clamp(p + k * (rain_yesterday - p) + a)
             Two-state Markov chain: k is the day-to-day persistence of the station's rain
             indicator (estimated from station history, not from prices).
  "skill"    ask = clamp(p + s * (rain_today - p) + a)            (RECOMMENDED)
             The market sees a forecast. The forecast is not available back to 1998, so the day's
             own outcome stands in for it: the price moves a share s of the way from climatology
             to the outcome. s is fitted so that the modelled ask is as much higher on rain days
             than on dry days as the observed ask is. s = 0 gives "clim"; s = 1 is a perfect forecast.

a = fitted markup of the ask over the fair probability (half the spread plus any bias).
clamp() keeps the ask on Kalshi's price grid: whole cents between $0.01 and $0.99.
Cost per contract = ask + taker fee, fee = round_up_to_cent(0.07 * C * ask * (1 - ask)) / C.

Limits (see docs/status/phase1_kalshi.md)
- "skill" uses the day's outcome inside the price. It is valid only for a buyer who buys the same
  quantity every day (the SPEC baseline). Never use it for a strategy that picks days by price.
- "skill" is deterministic: one price for rain days and one for dry days per value of p. Real
  prices scatter around those two levels (resid_sd in the JSON). The seasonal total is what the
  hedge evaluation uses, and the scatter mostly averages out there.
- Real quotes are missing or one-sided on some days; the model always returns a price.
  The one case that matters is handled by the optional parameter u: on a share u of rain days the
  real ask was $1.00 (nobody sold), so the buyer got no contract, paid nothing and was paid nothing.
  modelled_cost() and season_cost() scale that day's order by fill = 1 - u (an expected value).
  u = 0 if the parameter is absent.
- a is fitted to reproduce the mean observed ask. The fit seasons were wetter than climatology, so
  a is a little higher than the observed mean of (ask - result); the JSON stores that second number
  as a_net_matched for a sensitivity run.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Mapping, Sequence

from .rain_quotes import FEE_RATE, taker_fee

REPO = Path(__file__).resolve().parents[2]
PARAMS_PATH = REPO / "data" / "processed" / "kalshi_rain" / "price_model.json"
MODELS = ("clim", "persist", "skill")
TICK = 0.01


def clamp_price(x: float) -> float:
    """Round to the cent and keep inside [0.01, 0.99]."""
    return min(0.99, max(0.01, math.floor(x * 100.0 + 0.5) / 100.0))


def fair_probability(p_clim: float, model: str, params: Mapping[str, float], rain_today: int | None = None,
                     rain_yesterday: int | None = None) -> float:
    """The probability the modelled market assigns before markup (unclamped)."""
    if not 0.0 <= p_clim <= 1.0:
        raise ValueError("p_clim must be in [0, 1]")
    if model == "clim":
        return p_clim
    if model == "persist":
        if rain_yesterday not in (0, 1):
            raise ValueError("model 'persist' needs rain_yesterday = 0 or 1")
        return p_clim + params["k"] * (rain_yesterday - p_clim)
    if model == "skill":
        if rain_today not in (0, 1):
            raise ValueError("model 'skill' needs rain_today = 0 or 1")
        return p_clim + params["s"] * (rain_today - p_clim)
    raise ValueError(f"unknown model {model!r}; choose from {MODELS}")


def modelled_ask(p_clim: float, model: str = "skill", params: Mapping[str, float] | None = None,
                 rain_today: int | None = None, rain_yesterday: int | None = None) -> float:
    """MODELLED ask in dollars per $1 contract, on the cent grid in [0.01, 0.99].

    Non-decreasing in p_clim, in rain_today ("skill") and in rain_yesterday ("persist").
    """
    params = params if params is not None else load_params()["models"][model]
    return clamp_price(fair_probability(p_clim, model, params, rain_today, rain_yesterday) + params["a"])


def modelled_cost(p_clim: float, model: str = "skill", params: Mapping[str, float] | None = None,
                  rain_today: int | None = None, rain_yesterday: int | None = None,
                  contracts: int = 1, fee_rate: float = FEE_RATE) -> dict:
    """MODELLED cost of buying `contracts` contracts in one order at the 24-hour decision time.

    Returns dollars: ask (per contract), fee_per_contract, cost_per_contract, and for the order:
    fill (expected share of the order that finds a seller), premium, fee, total, and payout
    (None if rain_today is not given). premium, fee, total and payout are already scaled by fill.
    The payout is $1 per contract if the station reports measurable rain (>= 0.01 inch) that day.
    fill = 1 - u on rain days when the parameters hold u (share of rain days with no offer below
    $1.00) and rain_today is given; otherwise 1.
    """
    params = params if params is not None else load_params()["models"][model]
    ask = modelled_ask(p_clim, model, params, rain_today, rain_yesterday)
    fee = taker_fee(ask, contracts, fee_rate)
    fpc = fee / contracts if contracts else 0.0
    u = float(params.get("u", 0.0))
    if not 0.0 <= u <= 1.0:
        raise ValueError("u must be in [0, 1]")
    fill = 1.0 - u if rain_today == 1 else 1.0
    return {"ask": ask, "fee_per_contract": fpc, "cost_per_contract": ask + fpc, "fill": fill,
            "premium": ask * contracts * fill, "fee": fee * fill, "total": (ask * contracts + fee) * fill,
            "payout": None if rain_today is None else float(contracts * rain_today) * fill, "label": "modelled"}


def season_cost(p_clim: Sequence[float], rain_today: Sequence[int], model: str = "skill",
                params: Mapping[str, float] | None = None, rain_yesterday: Sequence[int] | None = None,
                contracts: int = 1) -> dict:
    """Sum of modelled_cost over a list of days (one order per day). MODELLED."""
    params = params if params is not None else load_params()["models"][model]
    prem = fee = pay = 0.0
    for i, p in enumerate(p_clim):
        c = modelled_cost(p, model, params, rain_today[i], rain_yesterday[i] if rain_yesterday is not None else None,
                          contracts)
        prem += c["premium"]; fee += c["fee"]; pay += c["payout"]
    return {"days": len(p_clim), "premium": prem, "fee": fee, "payout": pay, "net": pay - prem - fee,
            "label": "modelled"}


def load_params(path: Path = PARAMS_PATH) -> dict:
    return json.loads(Path(path).read_text())


# ---------------------------------------------------------------- fitting (closed form)
def fit_model(model: str, ask: Sequence[float], p_clim: Sequence[float], rain_today: Sequence[int],
              rain_yesterday: Sequence[int] | None = None, k: float | None = None) -> dict:
    """Least-squares fit of one candidate on observed asks (clamp ignored in the fit).

    clim, persist: a = mean(ask - fair).   skill: OLS of (ask - p) on (rain_today - p) with intercept:
    slope = s (kept inside [0, 1]), intercept = a.
    """
    n = len(ask)
    if n == 0:
        raise ValueError("no observations")
    if model == "clim":
        return {"a": sum(x - p for x, p in zip(ask, p_clim)) / n}
    if model == "persist":
        if k is None or rain_yesterday is None:
            raise ValueError("persist needs k and rain_yesterday")
        return {"a": sum(x - (p + k * (r - p)) for x, p, r in zip(ask, p_clim, rain_yesterday)) / n, "k": k}
    if model == "skill":
        u = [y - p for y, p in zip(rain_today, p_clim)]
        v = [x - p for x, p in zip(ask, p_clim)]
        mu, mv = sum(u) / n, sum(v) / n
        suu = sum((a - mu) ** 2 for a in u)
        s = sum((a - mu) * (b - mv) for a, b in zip(u, v)) / suu if suu > 0 else 0.0
        s = min(1.0, max(0.0, s))
        return {"a": mv - s * mu, "s": s}
    raise ValueError(f"unknown model {model!r}")
