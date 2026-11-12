"""Tests of the rain-count simulation (sim/experiment.py). All numbers are simulated."""
import csv
import json
import math
import os

import pytest

from sim import experiment, lmsr

PROBS = [0.24, 0.18, 0.29, 0.13, 0.03, 0.13]
EDGES = lmsr.EXAMPLE_EDGES


def row(state, b, s, probs=PROBS):
    return experiment.hedge_row(state, b, s, probs, EDGES, 3)


def test_uniform_start_closed_form():
    for b in (50, 200, 1000, 5000):
        for s in (10, 100, 1000):
            r = row("uniform", b, s)
            assert r["label"] == "SIMULATED"
            closed = b * math.log((3 + math.exp(s / b) + math.exp(2 * s / b) + math.exp(3 * s / b)) / 6)
            assert r["cost_units"] == pytest.approx(closed, rel=1e-12)
            assert r["expected_payout_units"] == pytest.approx(s * (0.13 + 2 * 0.03 + 3 * 0.13))
            assert r["max_payout_units"] == 3 * s
            assert r["value_at_pre_trade_prices"] == pytest.approx(s)  # (1 + 2 + 3) / 6 per unit of size
            assert r["top_bucket_price_before"] == pytest.approx(1 / 6)
            assert r["sponsor_worst_case_loss_b_ln6"] == pytest.approx(b * math.log(6))
            assert r["informed_trader_cost_units"] == 0.0
            assert r["sponsor_worst_pnl_units"] >= -r["sponsor_worst_case_loss_b_ln6"] * (1 + 1e-9)


def test_informed_start_prices_the_hedge_at_expected_payout_plus_impact():
    for b in (50, 200, 1000, 5000):
        for s in (10, 100, 1000):
            r = row("informed", b, s)
            # before the hedge the prices equal the distribution, so marginal value = expected payout
            assert r["value_at_pre_trade_prices"] == pytest.approx(r["expected_payout_units"], rel=1e-9)
            assert r["top_bucket_price_before"] == pytest.approx(PROBS[-1], rel=1e-9)
            assert r["price_per_1_expected_payout"] > 1.0  # a buy always pays more than the pre-trade value
            assert r["price_per_1_expected_payout"] == pytest.approx(1 + r["impact_rel"], rel=1e-9)
            assert r["informed_trader_cost_units"] > 0
            assert r["sponsor_worst_pnl_units"] >= -r["sponsor_worst_case_loss_b_ln6"] * (1 + 1e-9)
    # a tiny trade in a deep market pays almost exactly fair value
    assert row("informed", 5000, 1)["price_per_1_expected_payout"] == pytest.approx(1.0, abs=1e-3)


def test_impact_falls_with_b_and_rises_with_size():
    for state in ("uniform", "informed"):
        imp = lambda b, s: row(state, b, s)["impact_rel"]
        assert imp(50, 100) > imp(200, 100) > imp(1000, 100) > imp(5000, 100) > 0
        assert imp(200, 10) < imp(200, 100) < imp(200, 1000)


def test_distribution_prefers_the_counts_file_and_labels_the_placeholder(tmp_path):
    f = tmp_path / "season_counts_TTN.csv"
    f.write_text("station,season,calendar,days,loss_days,season_usable\n" + "".join(
        f"TTN,{y},all_days,102,{c},True\n" for y, c in [(1999, 2), (2000, 6), (2001, 6), (2002, 12), (2016, 50)]))
    d = experiment.count_distribution(str(f), EDGES, 0.5)
    assert d["kind"] == "OBSERVED" and d["counts"] == [2, 6, 6, 12]  # 2016 is not a training season
    assert d["tally"] == [1, 0, 2, 0, 0, 1] and sum(d["probs"]) == pytest.approx(1.0)
    p = experiment.count_distribution(str(tmp_path / "missing.csv"), EDGES, 0.5)
    assert p["kind"] == "PLACEHOLDER" and "PLACEHOLDER" in p["description"] and p["counts"] is None
    forced = experiment.count_distribution(str(f), EDGES, 0.5, force_placeholder=True)
    assert forced["kind"] == "PLACEHOLDER"


@pytest.mark.parametrize("placeholder", [True, False])
def test_experiment_runs_writes_labelled_outputs_and_is_deterministic(tmp_path, placeholder):
    args = ["--out", str(tmp_path)] + (["--placeholder"] if placeholder else [])
    ctx = experiment.main(args)
    for name in ("hedge_pricing.csv", "distribution.csv", "stepped_hedge_price.png", "summary.md", "manifest.json"):
        assert (tmp_path / name).stat().st_size > 0
    assert len(ctx["rows"]) == 2 * 4 * 3
    with open(tmp_path / "hedge_pricing.csv") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 24 and all(r["label"] == "SIMULATED" for r in rows)
    summary = (tmp_path / "summary.md").read_text()
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert "SIMULATED" in summary and "SIMULATED" in manifest["label"]
    kind = ctx["dist"]["kind"]
    assert manifest["distribution"] == kind and all(r["distribution"] == kind for r in rows)
    if placeholder:
        assert kind == "PLACEHOLDER" and "PLACEHOLDER, not data" in summary
    elif os.path.exists(experiment.DEFAULT_COUNTS):
        assert kind == "OBSERVED" and "PLACEHOLDER" not in summary
        assert all(1998 <= y <= 2014 for y in ctx["dist"]["seasons"])  # training seasons only
    for r in ctx["rows"]:
        assert r["sponsor_worst_pnl_units"] >= -r["sponsor_worst_case_loss_b_ln6"] * (1 + 1e-9)
    again = experiment.main(args)
    assert again["rows"] == ctx["rows"]
