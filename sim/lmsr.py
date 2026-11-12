"""Python reference for the LMSR contracts (ECE 473).

Two markets share the same maths:
  * contracts/RainCountLMSR.sol: six buckets on a season's count of loss days,
    uniform start, vector buys. See the section "count buckets" at the end.
  * contracts/BracketLMSR.sol: the earlier 12-bracket temperature market.

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


# ======================================================================
# Count buckets: reference for contracts/RainCountLMSR.sol
# ======================================================================
# Six buckets on the count of loss days in a season. `edges` holds five
# increasing whole numbers; each is the LAST count of a bucket (inclusive).
# The market always starts at q = 0 (uniform prices 1/6), so the sponsor's
# worst-case loss is b ln 6.

N_COUNT_BUCKETS = 6
# Example only. The real edges are chosen on the training seasons by the rain workstream.
EXAMPLE_EDGES: List[int] = [2, 4, 6, 8, 10]
MIN_UNIT_WEI = 10 ** 9
MAX_Q = 10 ** 15


def check_edges(edges: Sequence[int], season_days: Optional[int] = None) -> None:
    """Same rules as the contract constructor."""
    if len(edges) != N_COUNT_BUCKETS - 1:
        raise ValueError("need five edges")
    if any(e < 0 for e in edges) or any(e2 <= e1 for e1, e2 in zip(edges[:-1], edges[1:])):
        raise ValueError("edges must be non-negative and strictly increasing")
    if season_days is not None and edges[-1] >= season_days:
        raise ValueError("last edge must be below the number of season days")


def count_bucket_of(count: int, edges: Sequence[int] = EXAMPLE_EDGES) -> int:
    """Bucket index of a loss-day count. Same rule as bucketOf() in RainCountLMSR."""
    if count < 0:
        raise ValueError("count can not be negative")
    for j, edge in enumerate(edges):
        if count <= edge:
            return j
    return len(edges)


def count_bucket_labels(edges: Sequence[int] = EXAMPLE_EDGES) -> List[str]:
    labels = []
    lo = 0
    for e in edges:
        labels.append(f"{lo}-{e}" if e > lo else f"{e}")
        lo = e + 1
    labels.append(f"{lo}+")
    return labels


def quote_vector(q: Sequence[float], b: float, amounts: Sequence[float]) -> float:
    """Cost of buying the vector `amounts` (one number per bucket): C(q + amounts) - C(q)."""
    if len(amounts) != len(q):
        raise ValueError("one amount per bucket")
    if any(a < 0 for a in amounts):
        raise ValueError("buy only: amounts can not be negative")
    return cost([x + a for x, a in zip(q, amounts)], b) - cost(q, b)


def quote_vector_wei(q: Sequence[int], b: int, unit: int, amounts: Sequence[int]) -> int:
    """Exact-reference cost in wei of a vector buy, as the contract charges it."""
    if len(amounts) != len(q):
        raise ValueError("one amount per bucket")
    if any(a < 0 for a in amounts):
        raise ValueError("buy only: amounts can not be negative")
    return cost_wei([x + a for x, a in zip(q, amounts)], b, unit) - cost_wei(q, b, unit)


def required_funding_wei(b: int, unit: int, n: int = N_COUNT_BUCKETS) -> int:
    """Wei the sponsor must send at deployment: floor(b * ln(n) * unit).

    The contract computes ln(6) in 64.64 fixed point and can differ from this by
    about b * unit * 2^-60 wei (well below 1 gwei for any sensible market)."""
    return cost_wei([0] * n, b, unit)


def safe_funding_wei(b: int, unit: int, n: int = N_COUNT_BUCKETS) -> int:
    """A value that is certainly enough to send: the exact requirement plus a
    margin for the contract's fixed-point rounding. The excess comes back with sponsorWithdraw()."""
    return required_funding_wei(b, unit, n) + b * unit // 2 ** 56 + 2


def stepped_vector(start_bucket: int = 3, n: int = N_COUNT_BUCKETS) -> List[int]:
    """Stepped hedge of size 1: 1 share of `start_bucket`, 2 of the next, and so on.
    start_bucket = 3 gives [0, 0, 0, 1, 2, 3]."""
    if not 0 <= start_bucket < n:
        raise ValueError("bad start bucket")
    return [max(0, j - start_bucket + 1) for j in range(n)]


def payout(holdings: Sequence[float], count: int, edges: Sequence[int] = EXAMPLE_EDGES) -> float:
    """Payout units a holder of `holdings` receives if the season ends with `count` loss days."""
    return holdings[count_bucket_of(count, edges)]


def expected_payout(holdings: Sequence[float], probs: Sequence[float]) -> float:
    return math.fsum(h * p for h, p in zip(holdings, probs))


def bucket_probs_from_pmf(pmf: Sequence[float], edges: Sequence[int] = EXAMPLE_EDGES) -> List[float]:
    """Bucket probabilities from a pmf over counts 0, 1, 2, ..."""
    out = [0.0] * (len(edges) + 1)
    for count, p in enumerate(pmf):
        out[count_bucket_of(count, edges)] += p
    total = math.fsum(out)
    return [x / total for x in out]


def bucket_probs_from_counts(counts: Iterable[int], edges: Sequence[int] = EXAMPLE_EDGES,
                             alpha: float = 0.5) -> List[float]:
    """Add-alpha smoothed bucket frequencies of observed season counts (alpha > 0 keeps prices positive)."""
    tally = [0] * (len(edges) + 1)
    for c in counts:
        tally[count_bucket_of(int(c), edges)] += 1
    return prior_from_counts(tally, alpha)


def placeholder_count_pmf(mean: float = 5.3, season_days: int = 102) -> List[float]:
    """PLACEHOLDER distribution of season loss-day counts: Poisson(mean) cut at season_days.

    Not data. The mean 5.3 is the preliminary Trenton figure in docs/status/phase0_verdict.md.
    Replace with the observed season counts when the rain workstream supplies them."""
    pmf = [math.exp(-mean + k * math.log(mean) - math.lgamma(k + 1)) for k in range(season_days + 1)]
    total = math.fsum(pmf)
    return [x / total for x in pmf]


def read_season_counts(path: str, years: Optional[Iterable[int]] = None, calendar: str = "all_days") -> List[dict]:
    """Season loss-day counts from the rain workstream's CSV
    (data/processed/rain/season_counts_<station>.csv).

    Columns used: season, loss_days, and when present calendar (only rows equal to
    `calendar` are kept), season_usable (rows marked False are dropped) and days.
    Returns one dict per kept season: {"season", "loss_days", "days"}."""
    wanted = None if years is None else set(years)
    out: List[dict] = []
    with open(path, newline="") as fh:
        reader = csv.DictReader(fh)
        cols = reader.fieldnames or []
        if "season" not in cols or "loss_days" not in cols:
            raise ValueError("expected columns season and loss_days in " + path + ", found: " + ", ".join(cols))
        for row in reader:
            if "calendar" in cols and row["calendar"] != calendar:
                continue
            if "season_usable" in cols and row["season_usable"].strip().lower() in ("false", "0", "no"):
                continue
            if (row["loss_days"] or "").strip() == "":
                continue
            season = int(float(row["season"]))
            if wanted is not None and season not in wanted:
                continue
            days = int(float(row["days"])) if "days" in cols and (row["days"] or "").strip() else None
            out.append({"season": season, "loss_days": int(float(row["loss_days"])), "days": days})
    seasons = [r["season"] for r in out]
    if len(set(seasons)) != len(seasons):
        raise ValueError("more than one row per season after filtering in " + path)
    return sorted(out, key=lambda r: r["season"])


class CountMarket:
    """Simulated six-bucket count market with the contract's accounting (float units).

    Uniform start only, buy only, like RainCountLMSR."""

    def __init__(self, b: float, edges: Sequence[int] = EXAMPLE_EDGES):
        check_edges(edges)
        self.b = float(b)
        self.edges = list(edges)
        self.n = N_COUNT_BUCKETS
        self.q = [0.0] * self.n
        self.revenue = 0.0
        self.funding = worst_case_loss(self.b, self.n)  # b ln 6

    def prices(self) -> List[float]:
        return prices(self.q, self.b)

    def quote(self, amounts: Sequence[float]) -> float:
        return quote_vector(self.q, self.b, amounts)

    def buy_vector(self, amounts: Sequence[float]) -> float:
        c = self.quote(amounts)
        self.q = [x + a for x, a in zip(self.q, amounts)]
        self.revenue += c
        return c

    def buy(self, bucket: int, shares: float) -> float:
        amounts = [0.0] * self.n
        amounts[bucket] = shares
        return self.buy_vector(amounts)

    def move_to(self, target: Sequence[float]) -> float:
        """Buy-only trade that moves the prices to `target` (an informed trader).

        Prices equal `target` when q_j = b ln(target_j) + const. Buy only means q can
        only grow, so the smallest const with q' >= q is used. Returns the cost."""
        if len(target) != self.n or any(x <= 0 for x in target):
            raise ValueError("target must be six positive probabilities")
        t = [self.b * math.log(x) for x in target]
        const = max(a - c for a, c in zip(self.q, t))
        amounts = [max(0.0, c + const - a) for a, c in zip(self.q, t)]
        return self.buy_vector(amounts)

    def sponsor_pnl(self, count: int) -> float:
        """Sponsor profit if the season ends with `count` loss days: revenue minus payout."""
        return self.revenue - self.q[count_bucket_of(count, self.edges)]

    def worst_pnl(self) -> float:
        return self.revenue - max(self.q)


def _main(argv=None) -> None:
    """Small command line: funding amount for a deployment.

    python -m sim.lmsr funding --b 100 --unit-wei 100000000000000"""
    import argparse
    ap = argparse.ArgumentParser(description="LMSR reference helpers")
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("funding", help="wei the sponsor must send when deploying RainCountLMSR")
    f.add_argument("--b", type=int, required=True, help="liquidity parameter in shares")
    f.add_argument("--unit-wei", type=int, required=True, help="wei paid per winning share")
    a = ap.parse_args(argv)
    if not (0 < a.b <= 10 ** 12) or not (MIN_UNIT_WEI <= a.unit_wei <= 10 ** 18):
        raise SystemExit("b must be 1..1e12 and unit 1e9..1e18 wei")
    need = required_funding_wei(a.b, a.unit_wei)
    send = safe_funding_wei(a.b, a.unit_wei)
    print(f"b = {a.b} shares, unit = {a.unit_wei} wei")
    print(f"required funding  floor(b ln 6 unit) = {need} wei = {need / 1e18:.12f} ETH")
    print(f"send at least (with rounding margin)  = {send} wei = {send / 1e18:.12f} ETH")
    print("Anything above the requirement comes back with sponsorWithdraw() after settle or cancel.")


if __name__ == "__main__":
    _main()
