"""Station-settled contract payouts and costs (Strategy A building blocks).

Owner: Ehfaz Zoha. Spec: docs/SPEC.md. Contract facts: docs/contract_spec.md.

What is OBSERVED vs ASSUMED here
--------------------------------
- station_payout: the payout rule mirrors a binary exchange contract that pays
  $1 per contract when the reference-station daily max temperature meets the
  threshold. The rule is a modelling choice (SPEC Strategy A). Inputs
  (station TMAX) are observed data supplied by the caller.
- kalshi_fee: implements Kalshi's PUBLISHED taker/maker fee formula
  (fee = round_up(M * rate * C * P * (1 - P)), taker rate 0.07, maker rate
  0.0175, multiplier M = 1 for KXHIGHNY and KXHIGHTTTN). Source:
  https://kalshi.com/docs/kalshi-fee-schedule.pdf (effective 2026-07-07,
  fetched 2026-10-30 UTC). The rounding unit is ambiguous in that document
  (text says "centicent"; its table shows whole cents), so it is a parameter.
  Default is $0.01, which matches the published table.
- station_premium: the event probability and the markup are ASSUMED inputs.
  Nothing here is an observed market price unless the caller passes one.

Conventions: threshold equality triggers (TMAX >= k). NaN in gives NaN out.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Union

import numpy as np
import pandas as pd

__all__ = [
    "PAYOUT_PER_CONTRACT",
    "TAKER_RATE",
    "MAKER_RATE",
    "station_payout",
    "contracts_for_notional",
    "kalshi_fee",
    "station_premium",
]

ArrayLike = Union[float, int, np.ndarray, pd.Series, list]

#: Kalshi binary contracts settle at $1.00 (VERIFIED, see docs/contract_spec.md).
PAYOUT_PER_CONTRACT = 1.0
#: Published Kalshi fee coefficients (VERIFIED, fee schedule PDF).
TAKER_RATE = Fraction(7, 100)
MAKER_RATE = Fraction(175, 10000)


def station_payout(station_tmax: ArrayLike, threshold: float, notional: float = 800.0):
    """Strategy A payout: ``notional * 1{station_tmax >= threshold}``.

    Parameters
    ----------
    station_tmax : scalar, list, ndarray or Series
        OBSERVED daily max temperature (deg F) at the reference station.
        NaN means missing; the payout is then NaN (never imputed as 0).
    threshold : float
        Trigger level k in deg F (SPEC: 90, sensitivity 85 and 95). Equality
        triggers, matching a Kalshi "at least" / ladder "k or above" leg.
    notional : float
        Dollars paid on a trigger day (SPEC default $800 = 800 contracts at $1).

    Returns
    -------
    Same shape as input: a float ndarray, or a Series with the same index
    when a Series is passed, or a float for scalar input.
    """
    if isinstance(station_tmax, pd.Series):
        vals = station_tmax.to_numpy(dtype=float)
        return pd.Series(_payout_array(vals, threshold, notional),
                         index=station_tmax.index, name="station_payout")
    arr = np.asarray(station_tmax, dtype=float)
    out = _payout_array(arr, threshold, notional)
    if out.ndim == 0:
        return float(out)
    return out


def _payout_array(arr: np.ndarray, threshold: float, notional: float) -> np.ndarray:
    hit = (arr >= threshold).astype(float) * float(notional)
    return np.where(np.isnan(arr), np.nan, hit)


def contracts_for_notional(notional: float) -> int:
    """Number of $1 contracts needed to pay ``notional`` on a trigger day."""
    n = notional / PAYOUT_PER_CONTRACT
    if n < 0 or abs(n - round(n)) > 1e-9:
        raise ValueError("notional must be a non-negative whole number of dollars")
    return int(round(n))


def _to_fraction(x: float) -> Fraction:
    # Round to 1e-6 first so binary float noise (0.07*100*...) cannot bump a
    # ceiling up by one unit. Kalshi prices are quoted to at most 4 decimals.
    return Fraction(str(round(float(x), 6)))


def _fee_scalar(price: float, contracts: float, rate: Fraction, multiplier: float,
                rounding_unit: float) -> float:
    if np.isnan(price) or np.isnan(contracts):
        return float("nan")
    if not (0.0 <= price <= 1.0):
        raise ValueError(f"price must be in [0, 1] dollars, got {price}")
    if contracts < 0:
        raise ValueError("contracts must be non-negative")
    p = _to_fraction(price)
    raw = _to_fraction(multiplier) * rate * _to_fraction(contracts) * p * (1 - p)
    unit = _to_fraction(rounding_unit)
    units = -((-raw) // unit)  # exact ceiling
    return float(units * unit)


def kalshi_fee(price: ArrayLike, contracts: ArrayLike, *, maker: bool = False,
               multiplier: float = 1.0, rounding_unit: float = 0.01):
    """Kalshi trading fee in dollars for one fill of ``contracts`` at ``price``.

    Formula (VERIFIED, https://kalshi.com/docs/kalshi-fee-schedule.pdf,
    effective 2026-07-07): ``fee = round_up(M * rate * C * P * (1 - P))``,
    rate = 0.07 for takers, 0.0175 for makers. P is price in dollars, C is
    the number of contracts, M is the series multiplier (1 for KXHIGHNY and
    KXHIGHTTTN per Kalshi's series API, fetched 2026-10-30 UTC).

    ASSUMPTIONS (labelled): rounding is applied once per call (per fill); the
    schedule does not say per order vs per fill. ``rounding_unit`` defaults to
    $0.01 because the schedule's table shows 1 contract at $0.50 -> $0.02.
    Pass ``rounding_unit=0.0001`` for the "centicent" reading. Note the
    schedule's maker multiplier is 0 by default for series that do not list one;
    pass ``multiplier`` accordingly if modelling maker fills.

    Scalars return a float; arrays/Series broadcast and return arrays/Series.
    NaN price or count gives NaN.
    """
    rate = MAKER_RATE if maker else TAKER_RATE
    if np.ndim(price) == 0 and np.ndim(contracts) == 0:
        return _fee_scalar(float(price), float(contracts), rate, multiplier, rounding_unit)
    index = None
    for obj in (price, contracts):
        if isinstance(obj, pd.Series):
            index = obj.index
            break
    p, c = np.broadcast_arrays(np.asarray(price, dtype=float), np.asarray(contracts, dtype=float))
    out = np.array([_fee_scalar(pi, ci, rate, multiplier, rounding_unit)
                    for pi, ci in zip(p.ravel(), c.ravel())]).reshape(p.shape)
    if index is not None:
        return pd.Series(out, index=index, name="kalshi_fee")
    return out


def station_premium(prob: ArrayLike, notional: float = 800.0, markup: float = 0.0, *,
                    include_fee: bool = False, rounding_unit: float = 0.01):
    """Up-front cost of the station leg for one day.

    ``premium = notional * min(prob * (1 + markup), 1)`` plus, optionally, the
    Kalshi taker fee on ``notional`` contracts at that per-contract price.

    Parameters
    ----------
    prob : ASSUMED or MODELLED probability that station TMAX >= k (for example
        a training-window climatological frequency). Not an observed price.
    notional : dollars paid on a trigger day; equals the contract count.
    markup : ASSUMED proportional overround over fair value (0.10 = 10%).
        Captures spread, favourite-longshot pricing and ladder construction
        slippage. See docs/contract_spec.md section 5 for the basis of
        the default scenarios. If you have an OBSERVED ask price, pass it as
        ``prob`` with ``markup=0`` and say so in outputs.
    include_fee : add ``kalshi_fee(price, notional)`` (taker).

    NaN prob gives NaN. Per-contract price is capped at $1.00.
    """
    if markup < -1:
        raise ValueError("markup must be > -1")
    n = contracts_for_notional(notional)
    scalar = np.ndim(prob) == 0
    index = prob.index if isinstance(prob, pd.Series) else None
    pr = np.asarray(prob, dtype=float)
    if np.any((pr < 0) | (pr > 1)):
        raise ValueError("prob must be in [0, 1]")
    price = np.minimum(pr * (1.0 + markup), 1.0)
    cost = price * n
    if include_fee:
        cost = cost + np.asarray(kalshi_fee(price, n, rounding_unit=rounding_unit), dtype=float)
    if scalar:
        return float(cost)
    if index is not None:
        return pd.Series(cost, index=index, name="station_premium")
    return cost
