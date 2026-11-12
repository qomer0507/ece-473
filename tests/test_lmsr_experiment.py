"""Tests of the earlier temperature simulation (sim/experiment_temperature.py). All numbers are simulated.
The rain-count experiment is tested in tests/test_lmsr_rain_experiment.py."""
import csv
import math
import os

import pytest

from sim import experiment_temperature as experiment, lmsr

STATION = experiment.DEFAULT_STATION
needs_data = pytest.mark.skipif(not os.path.exists(STATION), reason="station file missing")


def test_basket_row_uniform_closed_form():
    # From a uniform start with n = 12 and 6 basket brackets:
    # cost = b ln((6 e^{s/b} + 6) / 12)
    for b in (50, 200, 1000, 5000):
        for s in (10, 100, 1000):
            r = experiment.basket_row("uniform", [1 / 12] * 12, b, s, lmsr.DEFAULT_BOUNDS, 90)
            assert r["label"] == "SIMULATED"
            assert r["pre_trade_price"] == pytest.approx(0.5)
            assert r["cost_units"] == pytest.approx(b * math.log((math.exp(s / b) + 1) / 2), rel=1e-12)
            assert r["sponsor_worst_case_loss"] == pytest.approx(b * math.log(12))
            assert r["extra_subsidy_vs_uniform"] == pytest.approx(0.0, abs=1e-9)
            assert r["pre_trade_price"] < r["avg_price_per_unit"] < r["post_trade_price"]


def test_impact_falls_with_b_and_rises_with_size():
    def impact(b, s):
        return experiment.basket_row("uniform", [1 / 12] * 12, b, s, lmsr.DEFAULT_BOUNDS, 90)["impact_abs"]
    assert impact(50, 100) > impact(200, 100) > impact(1000, 100) > impact(5000, 100)
    assert impact(200, 10) < impact(200, 100) < impact(200, 1000)
    # small trades: impact is about s / (8 b) for a 0.5 price (p (1 - p) s / (2 b))
    assert impact(5000, 10) == pytest.approx(10 / (8 * 5000), rel=1e-2)


def test_normal_bracket_probs_sum_to_one():
    p = experiment.normal_bracket_probs(91.3, 3.0, lmsr.DEFAULT_BOUNDS)
    assert sum(p) == pytest.approx(1.0)
    assert max(range(12), key=lambda j: p[j]) == lmsr.bracket_of(91)


@needs_data
def test_climatology_prior_uses_only_the_fit_window():
    fit = lmsr.season_tmax(STATION, range(2015, 2020))
    assert len(fit) == 765  # 5 seasons x 153 days, no gaps at this station
    later = lmsr.season_tmax(STATION, range(2020, 2026))
    prior = lmsr.climatology_prior(STATION)
    assert prior == lmsr.prior_from_counts(lmsr.bracket_counts(fit))
    assert prior != lmsr.prior_from_counts(lmsr.bracket_counts(fit + later))
    assert sum(prior) == pytest.approx(1.0) and min(prior) > 0


@needs_data
def test_experiment_runs_and_respects_the_loss_bound(tmp_path):
    ctx = experiment.main(["--out", str(tmp_path)])
    for name in ("basket_pricing.csv", "sponsor_pnl.csv", "priors.csv", "price_impact.png", "summary.md", "manifest.json"):
        assert (tmp_path / name).stat().st_size > 0
    assert len(ctx["basket"]) == 2 * 4 * 3
    assert len(ctx["pnl"]) == 2 * 4 * 3
    for r in ctx["pnl"]:
        assert r["label"] == "SIMULATED"
        assert r["sponsor_pnl_min"] >= r["sponsor_worst_case_bound"] * (1 + 1e-9)
        assert r["worst_possible_over_days"] >= r["sponsor_worst_case_bound"] * (1 + 1e-9)
    with open(tmp_path / "basket_pricing.csv") as fh:
        rows = list(csv.DictReader(fh))
    assert all(r["label"] == "SIMULATED" for r in rows)
    assert "SIMULATED" in (tmp_path / "summary.md").read_text()
    # deterministic
    again = experiment.main(["--out", str(tmp_path)])
    assert again["pnl"] == ctx["pnl"]
