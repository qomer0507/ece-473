"""Cross-check: quotes returned by contracts/RainCountLMSR.sol against sim/lmsr.py.

The contract numbers are in contracts/test/vectors/rain_contract_quotes.json. That file is
written by the JavaScript suite (cd contracts && npm test), which runs the compiled contract
in the local Hardhat EVM. It is not data from a live chain.

Unlike the older temperature cross-check, these tests FAIL (not skip) when the file is
missing or was written from a different version of the contract source. Fix: run
`npm test` in contracts/ again.
"""
import hashlib
import json
import os

import pytest

from sim import lmsr, make_vectors

ROOT = os.path.join(os.path.dirname(__file__), "..")
VEC = os.path.join(ROOT, "contracts", "test", "vectors")
QUOTES = os.path.join(VEC, "rain_contract_quotes.json")
SOURCE = os.path.join(ROOT, "contracts", "RainCountLMSR.sol")


@pytest.fixture(scope="module")
def doc():
    assert os.path.exists(QUOTES), "run `cd contracts && npm test` first to write rain_contract_quotes.json"
    with open(QUOTES) as fh:
        return json.load(fh)


def tol(b, unit):
    # two cost evaluations, each within b*unit*2^-60 + 1 wei of the exact value
    return 2 * (b * unit // 2 ** 60 + 1)


def test_snapshot_was_written_from_the_current_contract_source(doc):
    with open(SOURCE, "rb") as fh:
        current = hashlib.sha256(fh.read()).hexdigest()
    assert doc["source_sha256"]["RainCountLMSR.sol"] == current, \
        "RainCountLMSR.sol changed since the quotes were written: run `cd contracts && npm test` again"


def test_file_covers_the_experiment_grid(doc):
    assert doc["edges"] == lmsr.EXAMPLE_EDGES and doc["stepped"] == lmsr.stepped_vector()
    grid = {(c["b"], c["size"], c["state"]) for c in doc["cases"]}
    for b in (50, 200, 1000, 5000):
        for size in (10, 100, 1000):
            assert (b, size, "uniform") in grid and (b, size, "informed") in grid
    assert len(doc["cases"]) == 24
    for c in doc["cases"]:
        assert c["vector"] == [x * c["size"] for x in lmsr.stepped_vector()]
        if c["state"] == "uniform":
            assert [int(x) for x in c["q"]] == [0] * 6
        else:
            assert max(int(x) for x in c["q"]) > 0


def test_contract_basket_quotes_match_the_exact_reference(doc):
    unit = int(doc["unit"])
    worst = 0
    for c in doc["cases"]:
        q, b = [int(x) for x in c["q"]], c["b"]
        ref = lmsr.quote_vector_wei(q, b, unit, c["vector"])
        err = abs(int(c["quoteBasket"]) - ref)
        worst = max(worst, err)
        assert err <= tol(b, unit), (c["state"], b, c["size"], err)
        for key, bucket in (("quoteBuy5", 5), ("quoteBuy0", 0)):
            leg = [0] * 6
            leg[bucket] = c["size"]
            assert abs(int(c[key]) - lmsr.quote_vector_wei(q, b, unit, leg)) <= tol(b, unit)
    assert worst <= 2  # with unit = 1e12 wei the quotes agree to 2 wei or better


def test_contract_basket_quotes_match_the_float_simulation(doc):
    unit = int(doc["unit"])
    for c in doc["cases"]:
        q, b = [float(x) for x in c["q"]], c["b"]
        assert int(c["quoteBasket"]) / unit == pytest.approx(lmsr.quote_vector(q, b, c["vector"]), rel=1e-9)
    # and the uniform cases match the experiment's market object
    for c in doc["cases"]:
        if c["state"] == "uniform":
            m = lmsr.CountMarket(c["b"])
            assert int(c["quoteBasket"]) / unit == pytest.approx(m.buy_vector(c["vector"]), rel=1e-9)


def test_contract_prices_match(doc):
    for c in doc["cases"]:
        q, b = [int(x) for x in c["q"]], c["b"]
        ref = lmsr.prices_1e18(q, b)
        got = [int(x) for x in c["prices"]]
        assert all(abs(g - r) <= 2 for g, r in zip(got, ref))
        assert abs(sum(got) - 10 ** 18) <= 7
        if c["state"] == "uniform":
            assert all(abs(g - 10 ** 18 // 6) <= 2 for g in got)


def test_contract_funding_and_stored_cost_match(doc):
    unit = int(doc["unit"])
    for c in doc["cases"]:
        q, b = [int(x) for x in c["q"]], c["b"]
        need = int(c["requiredFunding"])
        assert abs(need - lmsr.required_funding_wei(b, unit)) <= tol(b, unit)
        assert need <= lmsr.safe_funding_wei(b, unit)
        assert need / unit == pytest.approx(lmsr.worst_case_loss(b, 6), rel=1e-12)
        assert abs(int(c["costNow"]) - lmsr.cost_wei(q, b, unit)) <= tol(b, unit)


def test_informed_states_are_the_ones_in_the_reference_file(doc):
    with open(os.path.join(VEC, "reference_rain.json")) as fh:
        ref = json.load(fh)
    for c in doc["cases"]:
        if c["state"] == "informed":
            assert c["q"] == ref["informed_q"][str(c["b"])]


def test_rain_reference_vector_file_is_reproducible():
    with open(os.path.join(VEC, "reference_rain.json")) as fh:
        on_disk = json.load(fh)
    assert json.loads(json.dumps(make_vectors.build_rain())) == on_disk
