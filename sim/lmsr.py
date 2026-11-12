"""Python reference for contracts/BracketLMSR.sol (ECE 473 Part 3).

Same maths as the contract:
    C(q) = b * ln(sum_j exp(q_j / b))
         = max(q) + b * ln(sum_j exp((q_j - max(q)) / b))
Shares are whole numbers. One winning share pays one unit.

Two layers:
  * float functions (cost, prices, quote_*) for the simulations;
  * cost_wei / quote_wei with 60-digit decimals, the reference the contract's
    64.64 fixed-point results are tested against.

Nothing here touches a chain. All markets built with this file are simulated.
"""
from __future__ import annotations

import csv
import math
from decimal import Decimal, getcontext, ROUND_FLOOR
from typing import Iterable, List, Optional, Sequence

getcontext().prec = 60

# Default ladder: "<80", 80-81, 82-83, ..., 98-99, ">=100"  (n = 12).
DEFAULT_BOUNDS: List[int] = list(range(80, 101, 2))
STRIKE = 90
# The contract treats exp(-x) as 0 for x >= 45 (below 2^-64).
EXP_CUTOFF = 45


# ----------------------------------------------------------------- brackets
def n_brackets(bounds: Sequence[int] = DEFAULT_BOUNDS) -> int:
    return len(bounds) + 1


def bracket_of(temp_f: int, bounds: Sequence[int] = DEFAULT_BOUNDS) -> int:
    """Index of the bracket containing temp_f. Same rule as bracketOf()."""
    for j, edge in enumerate(bounds):
        if temp_f < edge:
            return j
    return len(bounds)


def strike_index(bounds: Sequence[int] = DEFAULT_BOUNDS, strike: int = STRIKE) -> int:
    """First bracket with T >= strike. The strike must be a boundary."""
    if strike not in bounds:
        raise ValueError("strike is not a bracket boundary")
    return list(bounds).index(strike) + 1


def bracket_labels(bounds: Sequence[int] = DEFAULT_BOUNDS) -> List[str]:
    labels = [f"<{bounds[0]}"]
    for lo, hi in zip(bounds[:-1], bounds[1:]):
        labels.append(f"{lo}-{hi - 1}")
    labels.append(f">={bounds[-1]}")
    return labels


def check_bounds(bounds: Sequence[int]) -> None:
    if len(bounds) < 1:
        raise ValueError("need at least one boundary")
    if any(b2 <= b1 for b1, b2 in zip(bounds[:-1], bounds[1:])):
        raise ValueError("bounds must be strictly increasing")


# ------------------------------------------------------------- float LMSR
def cost(q: Sequence[float], b: float) -> float:
    """C(q) in payout units, log-sum-exp with the max subtracted."""
    top = max(q)
    return top + b * math.log(math.fsum(math.exp((x - top) / b) for x in q))


def prices(q: Sequence[float], b: float) -> List[float]:
    top = max(q)
    w = [math.exp((x - top) / b) for x in q]
    s = math.fsum(w)
    return [x / s for x in w]


def quote_range(q: Sequence[float], b: float, first: int, last: int, shares: float) -> float:
    """Cost of buying `shares` of every bracket in [first, last]."""
    q2 = list(q)
    for j in range(first, last + 1):
        q2[j] += shares
    return cost(q2, b) - cost(q, b)


def quote_buy(q: Sequence[float], b: float, bracket: int, shares: float) -> float:
    return quote_range(q, b, bracket, bracket, shares)


def quote_basket(q: Sequence[float], b: float, shares: float,
                 bounds: Sequence[int] = DEFAULT_BOUNDS, strike: int = STRIKE) -> float:
    """Cost of `shares` of every bracket at or above the strike (pays shares if T >= strike)."""
    return quote_range(q, b, strike_index(bounds, strike), len(q) - 1, shares)


def worst_case_loss(b: float, n: int) -> float:
    """Sponsor's worst-case loss from a uniform start: b ln n."""
    return b * math.log(n)


def seed_from_prior(p: Sequence[float], b: float, integer: bool = True) -> List[float]:
    """Seed quantities q0 with prices(q0) = p and min(q0) = 0: q0_j = b ln(p_j / p_min).

    The contract takes whole shares, so by default q0 is rounded to integers
    (the starting prices then differ from p by a rounding error of order 1/b)."""
    if any(x <= 0 for x in p):
        raise ValueError("prior probabilities must be positive")
    p_min = min(p)
    q0 = [b * math.log(x / p_min) for x in p]
    return [float(round(x)) for x in q0] if integer else q0


def seeded_worst_case_loss(q0: Sequence[float], b: float) -> float:
    """Worst-case sponsor loss when the market starts at q0: C(q0) - min(q0).

    Seed shares pay nobody. If bracket j wins the sponsor pays q_j - q0_j and has
    received C(q) - C(q0); since C(q) >= q_j the loss is at most C(q0) - q0_j.
    With min(q0) = 0 and exact prices p this equals b ln(1 / p_min)."""
    return cost(q0, b) - min(q0)


# ------------------------------------------------- exact reference (wei)
def _ln_sum(q: Sequence[int], b: int, cutoff: bool = True) -> Decimal:
    top = max(q)
    s = Decimal(0)
    for x in q:
        d = top - x
        if cutoff and d >= EXP_CUTOFF * b and d != 0:
            continue
        s += (-(Decimal(d) / Decimal(b))).exp()
    return s.ln()


def cost_wei(q: Sequence[int], b: int, unit: int, cutoff: bool = True) -> int:
    """C(q) in wei as the contract defines it: max(q)*unit + floor(ln(sum) * b * unit),
    evaluated with 60-digit decimals instead of 64.64 fixed point."""
    tail = (_ln_sum(q, b, cutoff) * b * unit).to_integral_value(rounding=ROUND_FLOOR)
    return max(q) * unit + int(tail)


def quote_wei(q: Sequence[int], b: int, unit: int, first: int, last: int, shares: int) -> int:
    q2 = list(q)
    for j in range(first, last + 1):
        q2[j] += shares
    return cost_wei(q2, b, unit) - cost_wei(q, b, unit)


def prices_1e18(q: Sequence[int], b: int) -> List[int]:
    top = max(q)
    w = [(-(Decimal(top - x) / Decimal(b))).exp() for x in q]
    s = sum(w)
    return [int((x / s * Decimal(10) ** 18).to_integral_value(rounding=ROUND_FLOOR)) for x in w]


# ------------------------------------------------------- simulated market
class Market:
    """Simulated LMSR bracket market with the contract's accounting (float units).

    Buy only, like the contract. `q0` is the sponsor's seed (pays nobody)."""

    def __init__(self, b: float, bounds: Sequence[int] = DEFAULT_BOUNDS, strike: int = STRIKE,
                 q0: Optional[Sequence[float]] = None):
        check_bounds(bounds)
        self.b = float(b)
        self.bounds = list(bounds)
        self.strike = strike
        self.n = n_brackets(bounds)
        self.k = strike_index(bounds, strike)
        self.q0 = [0.0] * self.n if q0 is None else [float(x) for x in q0]
        if len(self.q0) != self.n or min(self.q0) != 0:
            raise ValueError("q0 must have n entries and minimum 0")
        self.q = list(self.q0)
        self.revenue = 0.0
        self.funding = seeded_worst_case_loss(self.q0, self.b)

    def prices(self) -> List[float]:
        return prices(self.q, self.b)

    def price_at_or_above(self) -> float:
        return math.fsum(self.prices()[self.k:])

    def sold(self) -> List[float]:
        return [a - c for a, c in zip(self.q, self.q0)]

    def buy(self, bracket: int, shares: float) -> float:
        c = quote_buy(self.q, self.b, bracket, shares)
        self.q[bracket] += shares
        self.revenue += c
        return c

    def buy_basket(self, shares: float) -> float:
        c = quote_range(self.q, self.b, self.k, self.n - 1, shares)
        for j in range(self.k, self.n):
            self.q[j] += shares
        self.revenue += c
        return c

    def move_to(self, target: Sequence[float]) -> float:
        """Buy-only trade that moves the prices to `target` (an informed trader).

        Needs q' = b ln(target) + const with q' >= q. The smallest such const is used."""
        t = [self.b * math.log(x) for x in target]
        const = max(a - c for a, c in zip(self.q, t))
        q2 = [max(a, c + const) for a, c in zip(self.q, t)]
        c = cost(q2, self.b) - cost(self.q, self.b)
        self.q = q2
        self.revenue += c
        return c

    def sponsor_pnl(self, temp_f: int) -> float:
        """Sponsor profit if the day settles at temp_f: revenue minus payout."""
        w = bracket_of(temp_f, self.bounds)
        return self.revenue - self.sold()[w]

    def worst_pnl(self) -> float:
        return self.revenue - max(self.sold())


# ----------------------------------------------------------- climatology
def season_tmax(path: str, years: Iterable[int], months: Iterable[int] = (5, 6, 7, 8, 9)) -> List[int]:
    """Whole-degree TMAX values of a station file (columns DATE, TMAX) for the given years and months."""
    years, months = set(years), set(months)
    out: List[int] = []
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            v = (row.get("TMAX") or "").strip()
            if not v:
                continue
            y, m = int(row["DATE"][:4]), int(row["DATE"][5:7])
            if y in years and m in months:
                out.append(int(round(float(v))))
    return out


def bracket_counts(temps: Iterable[int], bounds: Sequence[int] = DEFAULT_BOUNDS) -> List[int]:
    counts = [0] * n_brackets(bounds)
    for t in temps:
        counts[bracket_of(t, bounds)] += 1
    return counts


def prior_from_counts(counts: Sequence[int], alpha: float = 1.0) -> List[float]:
    """Add-alpha (Laplace) smoothed bracket frequencies. alpha > 0 keeps every price positive."""
    total = sum(counts) + alpha * len(counts)
    return [(c + alpha) / total for c in counts]


def climatology_prior(path: str, bounds: Sequence[int] = DEFAULT_BOUNDS,
                      years: Iterable[int] = range(2015, 2020), alpha: float = 1.0) -> List[float]:
    """Bracket prior from May-Sep TMAX of the FIT window (2015-2019 by default)."""
    return prior_from_counts(bracket_counts(season_tmax(path, years), bounds), alpha)
