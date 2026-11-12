"""Tests of the rain-count simulation (sim/experiment.py). All prices are simulated.

The registered product (docs/PHASE2_PREREG.md, strategy 3) is recomputed here from the data file."""
import csv
import json
import math
import os

import pytest

from sim import experiment, lmsr

EDGES = lmsr.REGISTERED_EDGES_TTN
TRAIN_COUNTS = [2, 6, 6, 4, 8, 5, 5, 8, 2, 4, 12, 2, 1, 6, 12, 3]  # Trenton 1999-2014, as in the data file
M = [1.75, 11 / 3, 5.0, 6.0, 8.0, 12.0]
Q = [4.5 / 19, 3.5 / 19, 2.5 / 19, 3.5 / 19, 2.5 / 19, 2.5 / 19]
HAVE_DATA = os.path.exists(experiment.DEFAULT_COUNTS)


def row(state, b, s, d=3, probs=Q):
    return experiment.hedge_row(state, b, s, probs, EDGES, lmsr.registered_holdings(M, d), d)


# ------------------------------------------------------------ the registered product
def test_registered_edges_rule_on_the_train_counts():
    reg = lmsr.registered_edges(TRAIN_COUNTS)
    assert reg["sorted_counts"] == [1, 2, 2, 2, 3, 4, 4, 5, 5, 6, 6, 6, 8, 8, 12, 12]
    assert reg["quantiles_inverted_cdf"] == [2, 4, 5, 6, 8]
    assert reg["quantiles_linear"] == pytest.approx([2, 4, 5, 6, 8])
    assert reg["edges"] == EDGES == [2, 4, 5, 6, 8] and reg["adjusted"] == []  # six distinct buckets, no ties
    bm = lmsr.bucket_means(TRAIN_COUNTS, EDGES)
    assert bm["tally"] == [4, 3, 2, 3, 2, 2] and bm["means"] == pytest.approx(M)
    assert lmsr.prior_from_counts(bm["tally"], 0.5) == pytest.approx(Q)
    assert lmsr.count_bucket_labels(EDGES) == ["0-2", "3-4", "5", "6", "7-8", "9+"]
    assert lmsr.registered_holdings(M, 2) == pytest.approx([0, 5 / 3, 3, 4, 6, 10])
    assert lmsr.registered_holdings(M, 4) == pytest.approx([0, 0, 1, 2, 4, 8])
    # twelve times any holding is a whole number of shares (used by the contract tests)
    for d in (2, 3, 4):
        assert all(abs(12 * h - round(12 * h)) < 1e-9 for h in lmsr.registered_holdings(M, d))


def test_ties_are_moved_up_and_recorded_and_empty_buckets_get_the_registered_fallback():
    reg = lmsr.registered_edges([3] * 10 + [7, 9])
    assert reg["quantiles_inverted_cdf"] == [3, 3, 3, 3, 3]
    assert reg["edges"] == [3, 4, 5, 6, 7] and len(reg["adjusted"]) == 4
    lmsr.check_edges(reg["edges"])
    bm = lmsr.bucket_means([3] * 10 + [7], reg["edges"])
    assert bm["means"] == pytest.approx([3, 4, 5, 6, 7, 9])  # midpoints of empty buckets; top = last edge + 2
    assert bm["source"][1].startswith("bucket midpoint") and bm["source"][5].startswith("last edge + 2")


@pytest.mark.skipif(not HAVE_DATA, reason="season counts file not present")
def test_data_file_gives_the_registered_product():
    p = experiment.registered_product(experiment.DEFAULT_COUNTS)
    assert p["kind"] == "OBSERVED" and p["seasons"] == list(range(1999, 2015))
    assert p["counts"] == TRAIN_COUNTS
    assert p["edges"] == EDGES and p["edges_rule"] == "registered quantile rule"
    assert p["means"] == pytest.approx(M) and p["probs"] == pytest.approx(Q)
    # a real past season: Trenton 2025 had 5 loss days, bucket 2 (the bucket "5")
    y2025 = lmsr.read_season_counts(experiment.DEFAULT_COUNTS, [2025])[0]["loss_days"]
    assert y2025 == 5 and lmsr.count_bucket_of(y2025, EDGES) == 2


# ----------------------------------------------------------------------- pricing
def test_uniform_start_closed_form():
    for d in (2, 3, 4):
        h = lmsr.registered_holdings(M, d)
        for b in (50, 200, 1000, 5000):
            for s in (10, 100, 1000):
                r = row("uniform", b, s, d)
                assert r["label"] == "SIMULATED" and r["deductible_d"] == d
                top = max(h) * s / b
                closed = b * (top + math.log(sum(math.exp(s * x / b - top) for x in h) / 6))
                assert r["cost_units"] == pytest.approx(closed, rel=1e-10)
                assert r["expected_payout_units"] == pytest.approx(s * sum(x * q for x, q in zip(h, Q)))
                assert r["registered_premium_units"] == pytest.approx(1.2 * r["expected_payout_units"])
                assert r["max_payout_units"] == pytest.approx(s * (12 - d))
                assert r["value_at_pre_trade_prices"] == pytest.approx(s * sum(h) / 6)
                assert r["top_bucket_price_before"] == pytest.approx(1 / 6)
                assert r["sponsor_worst_case_loss_b_ln6"] == pytest.approx(b * math.log(6))
                assert r["informed_trader_cost_units"] == 0.0
                assert r["sponsor_worst_pnl_units"] >= -r["sponsor_worst_case_loss_b_ln6"] * (1 + 1e-9)


def test_informed_start_prices_the_hedge_at_expected_payout_plus_impact():
    for b in (50, 200, 1000, 5000):
        for s in (10, 100, 1000):
            r = row("informed", b, s)
            assert r["value_at_pre_trade_prices"] == pytest.approx(r["expected_payout_units"], rel=1e-9)
            assert r["top_bucket_price_before"] == pytest.approx(Q[-1], rel=1e-9)
            assert r["price_per_1_expected_payout"] > 1.0
            assert r["price_per_1_expected_payout"] == pytest.approx(1 + r["impact_rel"], rel=1e-9)
            assert r["lmsr_cost_over_registered_premium"] == pytest.approx(r["price_per_1_expected_payout"] / 1.2)
            assert r["informed_trader_cost_units"] > 0
            assert r["sponsor_worst_pnl_units"] >= -r["sponsor_worst_case_loss_b_ln6"] * (1 + 1e-9)
    assert row("informed", 5000, 1)["price_per_1_expected_payout"] == pytest.approx(1.0, abs=1e-3)


def test_impact_falls_with_b_and_rises_with_size():
    for state in ("uniform", "informed"):
        imp = lambda b, s: row(state, b, s)["impact_rel"]
        assert imp(50, 100) > imp(200, 100) > imp(1000, 100) > imp(5000, 100) > 0
        assert imp(200, 10) < imp(200, 100) < imp(200, 1000)


def test_break_even_fee_accounting():
    kl = experiment.informed_loss_per_b(Q)
    assert kl == pytest.approx(sum(q * math.log(6 * q) for q in Q)) and 0.02 < kl < 0.03
    for b, s in ((5000, 100), (20000, 1000), (1000, 100), (200, 10)):
        r = row("informed", b, s)
        # the informed trader's expected profit is b * KL(q || uniform), whatever the hedge
        assert r["informed_trader_expected_profit_units"] == pytest.approx(b * kl, rel=1e-9)
        excess = r["cost_units"] - r["expected_payout_units"]
        assert r["sponsor_expected_pnl_units"] == pytest.approx(excess - b * kl, rel=1e-6, abs=1e-9)
        short = max(0.0, -r["sponsor_expected_pnl_units"])
        assert r["break_even_fee_on_hedger_only"] == pytest.approx(short / r["cost_units"])
        assert r["break_even_fee_on_all_trades"] == pytest.approx(short / (r["cost_units"] + r["informed_trader_cost_units"]))
        assert r["break_even_fee_on_all_trades"] <= r["break_even_fee_on_hedger_only"]
        # with the fee the sponsor's expected result is zero (or already positive)
        assert r["sponsor_expected_pnl_units"] + r["break_even_fee_on_hedger_only"] * r["cost_units"] >= -1e-9
    assert row("informed", 1000, 100)["break_even_fee_on_hedger_only"] == 0.0   # impact covers the sponsor
    assert row("informed", 5000, 100)["break_even_fee_on_hedger_only"] > 0.3    # deep market: it does not
    assert row("uniform", 5000, 100)["break_even_fee_on_hedger_only"] == 0.0    # nobody to lose to at the uniform start


def test_self_financing_point_and_registered_premium_point():
    for d in (2, 3, 4):
        h = lmsr.registered_holdings(M, d)
        sf = experiment.self_financing_point(Q, EDGES, h)
        at = experiment.hedge_row("informed", sf["b_per_unit_size"] * 37, 37, Q, EDGES, h)  # any size: only b / size matters
        assert at["sponsor_expected_pnl_units"] == pytest.approx(0.0, abs=1e-6)
        assert at["price_per_1_expected_payout"] == pytest.approx(sf["price_per_1_expected_payout"], rel=1e-9)
        assert 1.0 < sf["price_per_1_expected_payout"] < 1.2  # cheaper than the registered premium
        bp = experiment.b_for_price(Q, EDGES, h, 1.2)
        assert bp < sf["b_per_unit_size"]
        assert experiment.hedge_row("informed", bp * 10, 10, Q, EDGES, h)["price_per_1_expected_payout"] == pytest.approx(1.2, rel=1e-6)


# ------------------------------------------------------------------- the script
def test_distribution_prefers_the_counts_file_and_labels_the_placeholder(tmp_path):
    f = tmp_path / "season_counts_TTN.csv"
    f.write_text("station,season,calendar,days,loss_days,season_usable\n" + "".join(
        f"TTN,{y},all_days,102,{c},True\n" for y, c in [(1998, 40), (1999, 2), (2000, 6), (2001, 6), (2002, 12), (2016, 50)]))
    d = experiment.count_distribution(str(f), lmsr.EXAMPLE_EDGES, 0.5)
    assert d["kind"] == "OBSERVED" and d["counts"] == [2, 6, 6, 12]  # 1998 and 2016 are not TRAIN seasons
    assert d["tally"] == [1, 0, 2, 0, 0, 1] and sum(d["probs"]) == pytest.approx(1.0)
    assert d["edges_rule"] == "given on the command line"
    p = experiment.registered_product(str(tmp_path / "missing.csv"))
    assert p["kind"] == "PLACEHOLDER" and "PLACEHOLDER" in p["description"] and p["counts"] is None
    assert sum(p["probs"]) == pytest.approx(1.0) and p["means"] == sorted(p["means"])
    forced = experiment.registered_product(str(f), force_placeholder=True)
    assert forced["kind"] == "PLACEHOLDER"


@pytest.mark.parametrize("placeholder", [True, False])
def test_experiment_runs_writes_labelled_outputs_and_is_deterministic(tmp_path, placeholder):
    args = ["--out", str(tmp_path)] + (["--placeholder"] if placeholder else [])
    ctx = experiment.main(args)
    for name in ("registered_buckets.csv", "hedge_pricing.csv", "break_even.csv", "distribution.csv",
                 "stepped_hedge_price.png", "summary.md", "manifest.json"):
        assert (tmp_path / name).stat().st_size > 0
    n = 2 * len(experiment.DEFAULT_B) * len(experiment.DEFAULT_SIZES) * len(experiment.DEFAULT_D)
    assert len(ctx["rows"]) == n == 90
    with open(tmp_path / "hedge_pricing.csv") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == n and all(r["label"] == "SIMULATED" for r in rows)
    assert {r["deductible_d"] for r in rows} == {"2", "3", "4"} and {r["size"] for r in rows} == {"10", "100", "1000"}
    summary = (tmp_path / "summary.md").read_text()
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert "SIMULATED" in summary and "SIMULATED" in manifest["label"]
    assert "not known yet" in summary and "NOT CHOSEN YET" in manifest["deductible_status"]
    kind = ctx["prod"]["kind"]
    assert manifest["distribution"] == kind and all(r["distribution"] == kind for r in rows)
    with open(tmp_path / "registered_buckets.csv") as fh:
        buckets = list(csv.DictReader(fh))
    assert len(buckets) == 6
    if placeholder:
        assert kind == "PLACEHOLDER" and "PLACEHOLDER, not data" in summary
    elif HAVE_DATA:
        assert kind == "OBSERVED" and "PLACEHOLDER" not in summary
        assert manifest["edges"] == EDGES and manifest["ties_adjusted"] == []
        assert [b["upper_edge"] for b in buckets] == ["2", "4", "5", "6", "8", ""]
        assert [int(b["n_train_seasons"]) for b in buckets] == [4, 3, 2, 3, 2, 2]
        assert [float(b["m_j"]) for b in buckets] == pytest.approx(M, rel=1e-5)
        assert [float(b["q_j"]) for b in buckets] == pytest.approx(Q, rel=1e-5)
        assert all(b["ties"].startswith("no ties") for b in buckets)
    for r in ctx["rows"]:
        assert r["sponsor_worst_pnl_units"] >= -r["sponsor_worst_case_loss_b_ln6"] * (1 + 1e-9)
    again = experiment.main(args)
    assert again["rows"] == ctx["rows"]
