"""Cross-check: quotes returned by contracts/BracketLMSR.sol against sim/lmsr.py.

The contract numbers are in contracts/test/vectors/contract_quotes.json. That file is
written by the JavaScript test suite (cd contracts && npm test), which runs the compiled
contract in the local Hardhat EVM. It is not data from a live chain.
"""
import json
import os

import pytest

from sim import lmsr, make_vectors

ROOT = os.path.join(os.path.dirname(__file__), "..")
VEC = os.path.join(ROOT, "contracts", "test", "vectors")
QUOTES = os.path.join(VEC, "contract_quotes.json")
STATION = os.path.join(ROOT, "data", "raw", "region", "tmax", "USW00014734.csv")

pytestmark = pytest.mark.skipif(not os.path.exists(QUOTES),
                                reason="run `cd contracts && npm test` first to write contract_quotes.json")


@pytest.fixture(scope="module")
def doc():
    with open(QUOTES) as fh:
        return json.load(fh)


def tol(b, unit):
    # two cost evaluations, each within b*unit*2^-60 + 1 wei of the exact value (measured: 4.1e-19 * b * unit)
    return 2 * (b * unit // 2 ** 60 + 1)


def test_file_covers_the_experiment_grid(doc):
    assert doc["bounds"] == lmsr.DEFAULT_BOUNDS and doc["strike"] == lmsr.STRIKE
    grid = {(c["b"], c["size"], c["prior"]) for c in doc["cases"]}
    for b in (50, 200, 1000, 5000):
        for size in (10, 100, 1000):
            assert (b, size, "uniform") in grid and (b, size, "climatology") in grid
    assert len(doc["cases"]) == 32


def test_contract_quotes_match_the_exact_reference(doc):
    unit = int(doc["unit"])
    worst = 0
    for c in doc["cases"]:
        q, b, size = [int(x) for x in c["q0"]], c["b"], c["size"]
        for key, first, last in (("quoteBasket", 6, 11), ("quoteBuy6", 6, 6), ("quoteBuy0", 0, 0)):
            ref = lmsr.quote_wei(q, b, unit, first, last, size)
            err = abs(int(c[key]) - ref)
            worst = max(worst, err)
            assert err <= tol(b, unit), (c["prior"], b, size, key, err)
    assert worst <= 2  # with unit = 1e12 wei the quotes agree to 2 wei or better


def test_contract_quotes_match_the_float_simulation(doc):
    unit = int(doc["unit"])
    for c in doc["cases"]:
        q, b, size = [float(x) for x in c["q0"]], c["b"], c["size"]
        assert int(c["quoteBasket"]) / unit == pytest.approx(lmsr.quote_range(q, b, 6, 11, size), rel=1e-9)
        assert int(c["quoteBuy6"]) / unit == pytest.approx(lmsr.quote_buy(q, b, 6, size), rel=1e-9)


def test_contract_prices_match(doc):
    for c in doc["cases"]:
        q, b = [int(x) for x in c["q0"]], c["b"]
        ref = lmsr.prices_1e18(q, b)
        got = [int(x) for x in c["prices"]]
        assert all(abs(g - r) <= 2 for g, r in zip(got, ref))
        assert abs(sum(got) - 10 ** 18) <= 13
        assert abs(int(c["priceAtOrAbove"]) - sum(ref[6:])) <= 12


def test_contract_funding_requirement_matches(doc):
    unit = int(doc["unit"])
    for c in doc["cases"]:
        if c["requiredFunding"] is None:
            continue
        q, b = [int(x) for x in c["q0"]], c["b"]
        assert abs(int(c["requiredFunding"]) - lmsr.cost_wei(q, b, unit)) <= tol(b, unit)
        if c["prior"] == "uniform":
            assert int(c["requiredFunding"]) / unit == pytest.approx(lmsr.worst_case_loss(b, 12), rel=1e-12)


def test_seeded_cases_use_the_climatology_seed_from_the_station_file(doc):
    prior = lmsr.climatology_prior(STATION)
    for c in doc["cases"]:
        if c["prior"] == "climatology":
            assert [int(x) for x in c["q0"]] == [int(x) for x in lmsr.seed_from_prior(prior, c["b"])]


def test_reference_vector_file_is_reproducible():
    with open(os.path.join(VEC, "reference.json")) as fh:
        on_disk = json.load(fh)
    assert json.loads(json.dumps(make_vectors.build())) == on_disk
