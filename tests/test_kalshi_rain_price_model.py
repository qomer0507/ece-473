"""Kalshi rain price model (MODELLED prices): bounds, monotonicity, fee, fitting."""
import itertools
import json
from pathlib import Path

import pytest

from src.kalshi.rain_price_model import (MODELS, PARAMS_PATH, clamp_price, fair_probability, fit_model,
                                         modelled_ask, modelled_cost, season_cost)

PAR = {"clim": {"a": 0.03}, "persist": {"a": 0.03, "k": 0.15}, "skill": {"a": 0.03, "s": 0.4}}
GRID = [i / 50 for i in range(51)]


def ask(model, p, rt=0, ry=0, par=None):
    return modelled_ask(p, model, par or PAR[model], rain_today=rt, rain_yesterday=ry)


def test_clamp_price():
    assert clamp_price(-0.2) == 0.01 and clamp_price(0.0) == 0.01 and clamp_price(1.7) == 0.99
    assert clamp_price(0.3349) == 0.33 and clamp_price(0.335) == pytest.approx(0.34)


@pytest.mark.parametrize("model", MODELS)
def test_output_bounds_and_cent_grid(model):
    for p, rt, ry in itertools.product(GRID, (0, 1), (0, 1)):
        for par in (PAR[model], {**PAR[model], "a": 0.9}, {**PAR[model], "a": -0.9}):
            x = ask(model, p, rt, ry, par)
            assert 0.01 <= x <= 0.99
            assert abs(x * 100 - round(x * 100)) < 1e-9
            c = modelled_cost(p, model, par, rain_today=rt, rain_yesterday=ry)
            assert c["label"] == "modelled"
            assert 0.01 <= c["fee_per_contract"] <= 0.02           # one contract: 1 or 2 cents
            assert c["cost_per_contract"] == pytest.approx(c["ask"] + c["fee_per_contract"])
            assert c["cost_per_contract"] <= 1.0 + 1e-9


@pytest.mark.parametrize("model", MODELS)
def test_monotone_in_climatological_probability(model):
    for rt, ry in itertools.product((0, 1), (0, 1)):
        xs = [ask(model, p, rt, ry) for p in GRID]
        assert all(b >= a for a, b in zip(xs, xs[1:]))
        assert xs[-1] > xs[0]


def test_monotone_in_signals_and_markup():
    for p in GRID:
        assert ask("skill", p, rt=1) >= ask("skill", p, rt=0)
        assert ask("persist", p, ry=1) >= ask("persist", p, ry=0)
        assert ask("clim", p, rt=1, ry=1) == ask("clim", p, rt=0, ry=0)      # ignores both signals
        assert ask("skill", p, rt=0, par={"a": 0.05, "s": 0.4}) >= ask("skill", p, rt=0, par={"a": 0.01, "s": 0.4})
    assert ask("skill", 0.35, rt=1) > ask("skill", 0.35, rt=0)
    assert ask("persist", 0.35, ry=1) > ask("persist", 0.35, ry=0)


def test_skill_limits():
    assert fair_probability(0.35, "skill", {"s": 0.0}, rain_today=1) == pytest.approx(0.35)   # s = 0 is climatology
    assert fair_probability(0.35, "skill", {"s": 1.0}, rain_today=1) == pytest.approx(1.0)    # s = 1 is a perfect forecast
    assert fair_probability(0.35, "skill", {"s": 1.0}, rain_today=0) == pytest.approx(0.0)
    # the fair probability averages back to climatology over rain and dry days
    p, s = 0.35, 0.4
    avg = p * fair_probability(p, "skill", {"s": s}, rain_today=1) + (1 - p) * fair_probability(p, "skill", {"s": s}, rain_today=0)
    assert avg == pytest.approx(p)


def test_missing_inputs_raise():
    with pytest.raises(ValueError):
        modelled_ask(0.3, "skill", PAR["skill"])
    with pytest.raises(ValueError):
        modelled_ask(0.3, "persist", PAR["persist"])
    with pytest.raises(ValueError):
        modelled_ask(1.3, "clim", PAR["clim"])
    with pytest.raises(ValueError):
        modelled_ask(0.3, "other", PAR["clim"])


def test_cost_with_many_contracts_and_season_sum():
    c = modelled_cost(0.47, "clim", {"a": 0.03}, contracts=100)       # ask 0.50
    assert c["ask"] == 0.50 and c["fee"] == pytest.approx(1.75) and c["total"] == pytest.approx(51.75)
    s = season_cost([0.47, 0.47, 0.47], [1, 0, 1], "clim", {"a": 0.03})
    assert s["days"] == 3 and s["premium"] == pytest.approx(1.5) and s["fee"] == pytest.approx(0.06)
    assert s["payout"] == 2 and s["net"] == pytest.approx(2 - 1.5 - 0.06) and s["label"] == "modelled"


def test_no_offer_share_scales_rain_days_only():
    par = {"a": 0.03, "s": 0.4, "u": 0.1}
    wet = modelled_cost(0.35, "skill", par, rain_today=1, contracts=10)
    dry = modelled_cost(0.35, "skill", par, rain_today=0, contracts=10)
    full = modelled_cost(0.35, "skill", {"a": 0.03, "s": 0.4}, rain_today=1, contracts=10)
    assert wet["fill"] == pytest.approx(0.9) and dry["fill"] == 1.0 and full["fill"] == 1.0
    assert wet["ask"] == full["ask"]                                  # the price itself does not change
    assert wet["payout"] == pytest.approx(9.0) and full["payout"] == 10.0 and dry["payout"] == 0.0
    assert wet["premium"] == pytest.approx(0.9 * full["premium"]) and wet["fee"] == pytest.approx(0.9 * full["fee"])
    s = season_cost([0.35, 0.35], [1, 0], "skill", par)
    assert s["payout"] == pytest.approx(0.9)
    with pytest.raises(ValueError):
        modelled_cost(0.35, "skill", {"a": 0.03, "s": 0.4, "u": 1.5}, rain_today=1)


def test_fit_recovers_known_parameters():
    p = [0.3, 0.35, 0.4, 0.3, 0.35, 0.4, 0.3, 0.4]
    y = [1, 0, 0, 0, 1, 1, 0, 1]
    ry = [0, 1, 0, 0, 0, 1, 1, 0]
    a_true, s_true, k_true = 0.04, 0.45, 0.2
    asks = [pi + s_true * (yi - pi) + a_true for pi, yi in zip(p, y)]
    f = fit_model("skill", asks, p, y)
    assert f["a"] == pytest.approx(a_true) and f["s"] == pytest.approx(s_true)
    f = fit_model("clim", [pi + a_true for pi in p], p, y)
    assert f["a"] == pytest.approx(a_true)
    f = fit_model("persist", [pi + k_true * (r - pi) + a_true for pi, r in zip(p, ry)], p, y, ry, k=k_true)
    assert f["a"] == pytest.approx(a_true) and f["k"] == k_true
    with pytest.raises(ValueError):
        fit_model("clim", [], [], [])


def test_skill_fit_is_kept_inside_zero_one():
    p = [0.3] * 4
    y = [1, 0, 1, 0]
    assert fit_model("skill", [0.1, 0.9, 0.1, 0.9], p, y)["s"] == 0.0     # prices move the wrong way
    assert fit_model("skill", [3.0, -2.0, 3.0, -2.0], p, y)["s"] == 1.0


@pytest.mark.skipif(not Path(PARAMS_PATH).exists(), reason="price_model.json not built yet")
def test_saved_parameters_are_usable():
    js = json.loads(Path(PARAMS_PATH).read_text())
    assert js["recommended"] in MODELS and "MODELLED" in js["label"]
    for m in MODELS:
        par = js["models"][m]
        assert -0.2 < par["a"] < 0.2
        x = modelled_ask(0.35, m, par, rain_today=1, rain_yesterday=1)
        assert 0.01 <= x <= 0.99
    assert 0.0 <= js["models"]["skill"]["s"] <= 1.0 and 0.0 <= js["models"]["skill"]["u"] <= 0.5
    assert modelled_ask(0.35, rain_today=1) > modelled_ask(0.35, rain_today=0)    # default = recommended model from file
