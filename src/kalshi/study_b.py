"""Study B: what a station heat-day hedge cost on Kalshi, on days it could be bought.

SPEC v2 rules implemented here:
  - Contract: P = 1{TMAX_station >= k}. Unit payout $1.
  - Only days where the market, the needed brackets and a quote existed.
  - Decision time: 24 h before market close. Price = yes_ask from the most recent
    hourly candle that ended at or before that time, at most 6 h stale.
  - Taker fee = ceil-to-cent(0.07 * C * P * (1 - P)).

Costs are TOP-OF-BOOK ESTIMATES. A candle gives the best ask, not its size.
An ask does not prove that a hedge-sized order would fill at that price.

Nothing here writes raw Kalshi rows to results/. Callers aggregate first.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Iterable, Sequence

SERIES = {"NYC": "KXHIGHNY", "Philadelphia": "KXHIGHPHIL", "Newark": "KXHIGHTEWR", "Trenton": "KXHIGHTTTN"}
GHCN = {"NYC": "USW00094728", "Philadelphia": "USW00013739", "Newark": "USW00014734", "Trenton": "USW00014792"}
ICAO = {"NYC": "KNYC", "Philadelphia": "KPHL", "Newark": "KEWR", "Trenton": "KTTN"}

DECISION_LAG_S = 24 * 3600
MAX_STALE_S = 6 * 3600
FEE_RATE_BP = 700  # 0.07 expressed in 1/10000


# --------------------------------------------------------------------------
# Bracket semantics
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Bracket:
    """A market that pays $1 if lo <= T <= hi (whole deg F). None means unbounded."""
    ticker: str
    lo: int | None
    hi: int | None

    def pays(self, t: int) -> bool:
        return (self.lo is None or t >= self.lo) and (self.hi is None or t <= self.hi)


def bracket_bounds(strike_type: str, floor_strike=None, cap_strike=None) -> tuple[int | None, int | None]:
    """Inclusive whole-degree YES range.

    between f..c -> [f, c];  greater f -> T >= f+1;  less c -> T <= c-1.
    """
    if strike_type == "between":
        lo, hi = _as_int(floor_strike), _as_int(cap_strike)
        if lo > hi:
            raise ValueError(f"between with floor {lo} > cap {hi}")
        return lo, hi
    if strike_type == "greater":
        return _as_int(floor_strike) + 1, None
    if strike_type == "less":
        return None, _as_int(cap_strike) - 1
    raise ValueError(f"unknown strike_type {strike_type!r}")


def _as_int(x) -> int:
    f = float(x)
    if f != int(f):
        raise ValueError(f"strike {x!r} is not a whole degree")
    return int(f)


_RE_BETWEEN = re.compile(r"between\s+(-?\d+)\s*(?:-|–|to|and)\s*(-?\d+)")
_RE_GREATER = re.compile(r"(?:greater than|above)\s+(-?\d+)")
_RE_LESS = re.compile(r"(?:less than|below)\s+(-?\d+)")


def bounds_from_rules(rules_primary: str) -> tuple[int | None, int | None]:
    """Fallback for old markets that carry no strike fields. Parses rules_primary."""
    m = _RE_BETWEEN.search(rules_primary)
    if m:
        return bracket_bounds("between", m.group(1), m.group(2))
    m = _RE_GREATER.search(rules_primary)
    if m:
        return bracket_bounds("greater", floor_strike=m.group(1))
    m = _RE_LESS.search(rules_primary)
    if m:
        return bracket_bounds("less", cap_strike=m.group(1))
    raise ValueError(f"cannot parse bracket from rules: {rules_primary[:120]!r}")


def bracket_from_market(m: dict) -> Bracket:
    """Build a Bracket from an API market row. Strike fields first, rules text second."""
    st = m.get("strike_type")
    if st in ("between", "greater", "less"):
        lo, hi = bracket_bounds(st, m.get("floor_strike"), m.get("cap_strike"))
    else:
        lo, hi = bounds_from_rules(m.get("rules_primary") or "")
    return Bracket(m["ticker"], lo, hi)


# --------------------------------------------------------------------------
# Ladder -> threshold replication
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Replication:
    """A set of legs whose payout is 1{T >= threshold} (+ a constant for multi-leg NO sets).

    side 'yes': buy YES on disjoint brackets whose union is [threshold, +inf).
    side 'no' : buy NO on disjoint brackets whose union is (-inf, threshold-1].
                n NO legs pay (n-1) + 1{T >= threshold}; the constant n-1 is
                returned for sure, so the net cost is sum(no_ask) - (n-1).
    """
    threshold: int
    side: str
    tickers: tuple[str, ...]


def replications(brackets: Sequence[Bracket]) -> list[Replication]:
    """All exact replications of 1{T >= k'} for every k' the ladder allows."""
    out: list[Replication] = []

    def up(start: int, used: tuple[str, ...]):  # cover [start, +inf) with YES legs
        for b in brackets:
            if b.lo == start and b.ticker not in used:
                if b.hi is None:
                    yield used + (b.ticker,)
                else:
                    yield from up(b.hi + 1, used + (b.ticker,))

    def down(end: int, used: tuple[str, ...]):  # cover (-inf, end] with NO legs
        for b in brackets:
            if b.hi == end and b.ticker not in used:
                if b.lo is None:
                    yield used + (b.ticker,)
                else:
                    yield from down(b.lo - 1, used + (b.ticker,))

    for k in sorted({b.lo for b in brackets if b.lo is not None}):
        for legs in up(k, ()):
            out.append(Replication(k, "yes", legs))
    for k in sorted({b.hi + 1 for b in brackets if b.hi is not None}):
        for legs in down(k - 1, ()):
            out.append(Replication(k, "no", legs))
    return out


def achievable_thresholds(brackets: Sequence[Bracket]) -> list[int]:
    return sorted({r.threshold for r in replications(brackets)})


def nearest_threshold(achievable: Iterable[int], k: int) -> int | None:
    """Nearest achievable threshold to k. Ties go to the lower one (over-hedge: pays whenever the target pays)."""
    a = sorted(achievable)
    if not a:
        return None
    return min(a, key=lambda x: (abs(x - k), x))


# --------------------------------------------------------------------------
# Fees and quotes
# --------------------------------------------------------------------------
def to_cents(price) -> int | None:
    """Dollar price (str or float) -> integer cents. None stays None."""
    if price is None:
        return None
    f = float(price)
    if math.isnan(f):
        return None
    return int(round(f * 100))


def taker_fee_cents(price_cents: int, contracts: int = 1) -> int:
    """ceil-to-cent(0.07 * C * P * (1 - P)), exact integer arithmetic. P in cents."""
    if not 0 <= price_cents <= 100:
        raise ValueError("price must be 0..100 cents")
    if contracts < 0:
        raise ValueError("contracts must be >= 0")
    num = FEE_RATE_BP * contracts * price_cents * (100 - price_cents)  # cents * 1e6
    return -(-num // 1_000_000)


def _close(side: dict | None):
    """Candle close of one book side. Historical tier uses key 'close', live tier 'close_dollars'."""
    if not side:
        return None
    v = side.get("close")
    return v if v is not None else side.get("close_dollars")


@dataclass(frozen=True)
class Quote:
    ask_c: int | None  # yes ask in cents; None if the ask side is empty
    bid_c: int | None  # yes bid in cents; None if the bid side is empty
    age_s: int         # decision time minus candle end


def quote_at(candles: Sequence[dict], close_ts: int, lag_s: int = DECISION_LAG_S,
             max_stale_s: int = MAX_STALE_S) -> Quote | None:
    """Quote at decision time = close_ts - lag_s.

    Uses the latest hourly candle with end_period_ts <= decision time. Returns None
    if there is none or it is more than max_stale_s old. An ask of $1.00 (or 0) and
    a bid of $0.00 mean an empty side and come back as None.
    """
    t0 = close_ts - lag_s
    best = None
    for c in candles:
        e = c["end_period_ts"]
        if e <= t0 and (best is None or e > best["end_period_ts"]):
            best = c
    if best is None or t0 - best["end_period_ts"] > max_stale_s:
        return None
    ask = to_cents(_close(best.get("yes_ask")))
    bid = to_cents(_close(best.get("yes_bid")))
    if ask is not None and not 1 <= ask <= 99:
        ask = None
    if bid is not None and not 1 <= bid <= 99:
        bid = None
    return Quote(ask, bid, t0 - best["end_period_ts"])


# --------------------------------------------------------------------------
# Pricing a replication
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Priced:
    rep: Replication
    cost_per_dollar: float   # net cost of $1 of protection, fees included
    fee_per_dollar: float
    premium_per_dollar: float


def price_replication(rep: Replication, quotes: dict[str, Quote | None], contracts: int = 100) -> Priced | None:
    """Net cost per $1 of protection when buying `contracts` units of each leg.

    YES leg price = yes ask. NO leg price = 1 - yes bid. Returns None if any leg has no usable quote.
    """
    prem_c, fee_c = 0, 0
    for t in rep.tickers:
        q = quotes.get(t)
        if q is None:
            return None
        if rep.side == "yes":
            if q.ask_c is None:
                return None
            p = q.ask_c
        else:
            if q.bid_c is None:
                return None
            p = 100 - q.bid_c
        prem_c += p * contracts
        fee_c += taker_fee_cents(p, contracts)
    if rep.side == "no":
        prem_c -= 100 * contracts * (len(rep.tickers) - 1)  # constant part of the payout comes back for sure
    n = 100.0 * contracts
    return Priced(rep, (prem_c + fee_c) / n, fee_c / n, prem_c / n)


@dataclass(frozen=True)
class HedgeDay:
    """Outcome of trying to buy 1{T >= k} on one event day."""
    status: str                 # 'exact' | 'inexact' | 'no_ladder'
    k_target: int
    k_achieved: int | None      # nearest achievable threshold (== k_target when exact)
    priced: Priced | None       # None => no-quote day (or no ladder)
    n_candidates: int

    @property
    def quoted(self) -> bool:
        return self.priced is not None

    @property
    def strike_gap(self) -> int | None:
        return None if self.k_achieved is None else self.k_achieved - self.k_target


def hedge_day(brackets: Sequence[Bracket], quotes: dict[str, Quote | None], k: int,
              contracts: int = 100, allow_no: bool = True) -> HedgeDay:
    """Cheapest listed replication of 1{T >= k}, or of the nearest achievable threshold."""
    reps = [r for r in replications(brackets) if allow_no or r.side == "yes"]
    if not reps:
        return HedgeDay("no_ladder", k, None, None, 0)
    k2 = nearest_threshold({r.threshold for r in reps}, k)
    cands = [r for r in reps if r.threshold == k2]
    priced = [p for p in (price_replication(r, quotes, contracts) for r in cands) if p is not None]
    best = min(priced, key=lambda p: (p.cost_per_dollar, len(p.rep.tickers))) if priced else None
    return HedgeDay("exact" if k2 == k else "inexact", k, k2, best, len(cands))


def replication_error(t: int, k_target: int, k_achieved: int) -> int:
    """+1 over-payment (hedge pays, target does not), -1 shortfall, 0 same payout."""
    return int(t >= k_achieved) - int(t >= k_target)


# --------------------------------------------------------------------------
# Year-block bootstrap (SPEC: whole years, 1,000 draws, seed 473)
# --------------------------------------------------------------------------
def year_block_bootstrap(years: Sequence[int], stat, n_draws: int = 1000, seed: int = 473,
                         q: tuple[float, float] = (0.025, 0.975)) -> tuple[float, float]:
    """Percentile interval for stat(list_of_years_with_repeats). NaN interval if fewer than 2 years."""
    import numpy as np
    ys = sorted(set(years))
    if len(ys) < 2:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n_draws):
        draw = rng.choice(ys, size=len(ys), replace=True)
        v = stat(list(draw))
        if v is not None and not (isinstance(v, float) and math.isnan(v)):
            vals.append(v)
    if not vals:
        return (float("nan"), float("nan"))
    lo, hi = np.quantile(vals, q)
    return float(lo), float(hi)
