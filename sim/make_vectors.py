"""Write high-precision reference vectors for the JavaScript contract tests.

Output: contracts/test/vectors/reference.json (temperature market, seed 473)
        contracts/test/vectors/reference_rain.json (rain-count market, seed 474).
Run:    python -m sim.make_vectors
The numbers are computed with 60-digit decimals (sim/lmsr.py), not with the EVM.
"""
from __future__ import annotations

import json
import os
import random
from decimal import Decimal, ROUND_FLOOR

from sim import lmsr

TWO64 = Decimal(2) ** 64
OUT = os.path.join(os.path.dirname(__file__), "..", "contracts", "test", "vectors", "reference.json")


def fl(x: Decimal) -> int:
    return int(x.to_integral_value(rounding=ROUND_FLOOR))


def build() -> dict:
    rng = random.Random(473)
    # exp(x) for x in [-44, 0], x given as a 64.64 integer.
    exp_x = [0, -1, -(1 << 32), -(1 << 63), -(1 << 64), -(10 << 64), -(40 << 64), -(44 << 64)]
    exp_x += [-rng.randrange(0, 44 << 64) for _ in range(40)]
    exp_cases = [{"x": str(x), "y": str(fl((Decimal(x) / TWO64).exp() * TWO64))} for x in exp_x]
    # ln(x) for x in [1, 32] (the sum of weights is in [1, n], n <= 32).
    ln_x = [1 << 64, (1 << 64) + 1, 2 << 64, 12 << 64, 32 << 64]
    ln_x += [rng.randrange(1 << 64, 32 << 64) for _ in range(40)]
    ln_cases = [{"x": str(x), "y": str(fl((Decimal(x) / TWO64).ln() * TWO64))} for x in ln_x]
    # weight exp(-d/b)
    w_cases = []
    for _ in range(30):
        b = rng.choice([1, 7, 50, 200, 1000, 5000, 10**6, 10**12])
        d = rng.randrange(0, 44 * b + 1)
        w_cases.append({"d": str(d), "b": str(b), "y": str(fl((-(Decimal(d) / Decimal(b))).exp() * TWO64))})
    # full cost C(q) in wei for n = 12
    cost_cases = []
    grids = [(50, 10**12), (200, 10**12), (1000, 10**12), (5000, 10**12), (1, 1), (1, 10**18),
             (10**12, 10**18), (10**6, 10**15), (3, 10**9)]
    for b, unit in grids:
        for kind in ("zero", "small", "wide", "extreme"):
            if kind == "zero":
                q = [0] * 12
            elif kind == "small":
                q = [rng.randrange(0, 2 * b + 1) for _ in range(12)]
            elif kind == "wide":
                q = [rng.randrange(0, 40 * b + 1) for _ in range(12)]
            else:
                q = [rng.randrange(0, min(10**15, 1000 * b) + 1) for _ in range(12)]
            cost_cases.append({"q": [str(x) for x in q], "b": str(b), "unit": str(unit), "kind": kind,
                               "cost": str(lmsr.cost_wei(q, b, unit)),
                               "prices": [str(x) for x in lmsr.prices_1e18(q, b)]})
    # Climatology prior (Newark, May-Sep, FIT 2015-2019, add-one smoothing) and its integer seeds.
    station = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "region", "tmax", "USW00014734.csv")
    prior = lmsr.climatology_prior(station)
    seeds = {str(b): [str(int(x)) for x in lmsr.seed_from_prior(prior, b)] for b in (50, 200, 1000, 5000)}
    return {"note": "Reference values from sim/lmsr.py with 60-digit decimals. Seed 473.",
            "bounds": lmsr.DEFAULT_BOUNDS, "strike": lmsr.STRIKE,
            "climatology_prior": prior, "climatology_seeds": seeds,
            "exp": exp_cases, "ln": ln_cases, "weight": w_cases, "cost": cost_cases}


OUT_RAIN = os.path.join(os.path.dirname(__file__), "..", "contracts", "test", "vectors", "reference_rain.json")


def build_rain() -> dict:
    """Reference vectors for RainCountLMSR (six buckets, uniform start). Seed 474."""
    rng = random.Random(474)
    n = lmsr.N_COUNT_BUCKETS
    grids = [(50, 10**12), (200, 10**12), (1000, 10**12), (5000, 10**12), (1, 10**9), (1, 10**18),
             (10**12, 10**18), (10**6, 10**15), (3, 10**9), (100, 10**14)]
    cost_cases = []
    for b, unit in grids:
        for kind in ("zero", "small", "wide", "extreme"):
            if kind == "zero":
                q = [0] * n
            elif kind == "small":
                q = [rng.randrange(0, 2 * b + 1) for _ in range(n)]
            elif kind == "wide":
                q = [rng.randrange(0, 40 * b + 1) for _ in range(n)]
            else:
                q = [rng.randrange(0, min(10**15, 1000 * b) + 1) for _ in range(n)]
            cost_cases.append({"q": [str(x) for x in q], "b": str(b), "unit": str(unit), "kind": kind,
                               "cost": str(lmsr.cost_wei(q, b, unit)),
                               "prices": [str(x) for x in lmsr.prices_1e18(q, b)]})
    # Vector buys from a random state: the contract must charge C(q + a) - C(q).
    basket_cases = []
    for b, unit in [(50, 10**12), (200, 10**12), (1000, 10**12), (5000, 10**12), (100, 10**14), (7, 10**9)]:
        for _ in range(5):
            q = [rng.randrange(0, 3 * b + 1) for _ in range(n)]
            a = [rng.choice([0, 0, 1, rng.randrange(1, 4 * b + 1)]) for _ in range(n)]
            if sum(a) == 0:
                a[rng.randrange(n)] = 1
            basket_cases.append({"q": [str(x) for x in q], "amounts": [str(x) for x in a], "b": str(b),
                                 "unit": str(unit), "cost": str(lmsr.quote_vector_wei(q, b, unit, a))})
    funding = [{"b": str(b), "unit": str(unit), "required": str(lmsr.required_funding_wei(b, unit)),
                "safe": str(lmsr.safe_funding_wei(b, unit))} for b, unit in grids]
    # States "after informed trading": integer q with prices close to the PLACEHOLDER count
    # distribution (Poisson, mean 5.3; not data). Used only to cross-check quotes away from q = 0.
    target = lmsr.bucket_probs_from_pmf(lmsr.placeholder_count_pmf(), lmsr.EXAMPLE_EDGES)
    informed = {str(b): [str(int(x)) for x in lmsr.seed_from_prior(target, b)] for b in (50, 200, 1000, 5000)}
    return {"note": "Reference values for RainCountLMSR from sim/lmsr.py with 60-digit decimals. Seed 474.",
            "n": n, "example_edges": lmsr.EXAMPLE_EDGES, "ln6": str(Decimal(6).ln()),
            "placeholder_target_probs": target, "informed_q": informed,
            "cost": cost_cases, "basket": basket_cases, "funding": funding}


def main() -> None:
    with open(OUT_RAIN, "w") as fh:
        json.dump(build_rain(), fh, indent=1)
    print("wrote", os.path.normpath(OUT_RAIN))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(build(), fh, indent=1)
    print("wrote", os.path.normpath(OUT))


if __name__ == "__main__":
    main()
