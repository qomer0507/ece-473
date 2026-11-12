"""Contract fit, leak test, bins, bootstrap by gauge, reach (Phase 3 temperature reach)."""
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.hedge_eval.metrics import hedge_effectiveness  # noqa: E402
from src.reach_temp import contract as rc  # noqa: E402
from src.reach_temp import curve as rcv  # noqa: E402
from src.reach_temp import regress as rr  # noqa: E402


# ------------------------------------------------------------------ contract
def test_fit_contract_by_hand():
    # TRAIN C_S = C_G = [2, 4, 6]; reference = 4. d = 4: payout [0,0,2], premium 1.2*2/3 = 0.8
    # net = [2.8, 4.8, 4.8] -> SV = (0 + 0.64 + 0.64)/3; unhedged SV = (0+0+4)/3 -> HE = 1 - 1.28/4 = 0.68
    fit = rc.fit_contract([2, 4, 6], [2, 4, 6], [2015, 2016, 2017], [2018, 2019])
    assert fit.reference == 4.0
    d4_he = hedge_effectiveness(np.array([2.8, 4.8, 4.8]), np.array([2, 4, 6.0]), 4.0)
    assert d4_he == pytest.approx(0.68)
    # the chosen d must be at least as good as d = 4 and its premium 1.2 x TRAIN mean payout
    assert fit.train_he >= d4_he - 1e-12
    pay = np.maximum(np.array([2, 4, 6.0]) - fit.d, 0)
    assert fit.premium == pytest.approx(1.2 * pay.mean())
    assert fit.d in range(0, 9)


def test_report_he_matches_phase2_metric():
    fit = rc.Fit([2015], [2016, 2017], reference=4.0, d=3, premium=1.0, train_he=np.nan)
    cs, cg = np.array([5.0, 1.0]), np.array([6.0, 2.0])
    net = cg - np.maximum(cs - 3, 0) + 1.0  # [5, 3]
    assert rc.report_he(cs, cg, fit) == pytest.approx(hedge_effectiveness(net, cg, 4.0))


def test_he_undefined_when_no_report_season_above_reference():
    fit = rc.Fit([2015], [2016, 2017], reference=10.0, d=0, premium=0.0, train_he=np.nan)
    assert np.isnan(rc.report_he([1, 2], [1, 2], fit))


def test_tie_goes_to_smallest_d():
    # S never pays whatever d: every d ties at HE = HE of the pure premium (0 premium) -> d = 0
    fit = rc.fit_contract([0, 0, 0], [1, 3, 5], [2015, 2016, 2017], [2018, 2019])
    assert fit.d == 0


def test_leak_report_seasons_do_not_change_train_choice():
    """Changing REPORT counts must not change d, premium, reference or TRAIN HE."""
    base = pd.DataFrame({"season": range(2015, 2026), "n_days": 153, "usable": True,
                         "c_s": [3, 8, 2, 9, 5, 7, 4, 10, 1, 6, 12], "c_g": [2, 9, 3, 8, 6, 6, 5, 9, 2, 7, 11],
                         "n_agree": 150})
    a = rc.evaluate_pair(base)
    assert a["n_train"] == 6 and a["train_last"] == 2020 and a["report_first"] == 2021
    alt = base.copy()
    alt.loc[alt["season"] >= 2021, ["c_s", "c_g"]] = [[30, 0], [0, 30], [15, 15], [7, 1], [1, 7]]
    b = rc.evaluate_pair(alt)
    for k in ("d", "premium", "reference", "train_he"):
        assert a[k] == b[k]
    assert a["he"] != b["he"]
    # and changing a TRAIN season does change the fit's reference
    alt2 = base.copy()
    alt2.loc[alt2["season"] == 2015, "c_g"] = 40
    assert rc.evaluate_pair(alt2)["reference"] != a["reference"]


# ------------------------------------------------------------------ bins and bootstrap
def test_bin_index_edges():
    idx = rcv.bin_index([0.0, 0.0, 5.0, 10.0, 10.0001, 199.9, 200.0], [True, False, False, False, False, False, False])
    assert list(idx) == [0, 1, 1, 1, 2, 20, 20]
    assert len(rcv.bin_edges()) == 21


def synthetic_pairs():
    # 3 gauges; gauge C has one pair with HE 1.0 and one NaN; gauge A pairs at 0 and 15 km; B at 25 km
    return pd.DataFrame({
        "s_id": ["A", "A", "B", "A", "B"], "g_id": ["A", "C", "B", "B", "C"],
        "dist_km": [0.0, 15.0, 0.0, 25.0, 95.0], "same_station": [True, False, True, False, False],
        "he": [0.8, 1.0, 0.6, -0.4, np.nan], "elev_diff_m": [0, 100, 0, 50, 200], "coast_g": [1, 0, 0, 0, 0],
    })


def test_curve_table_means_and_counts():
    c = rcv.curve_table(synthetic_pairs(), n_draws=50, seed=1)
    assert c.loc[0, "n_pairs"] == 2 and c.loc[0, "mean_he"] == pytest.approx(0.7)
    assert c.loc[2, "mean_he"] == pytest.approx(1.0) and c.loc[3, "mean_he"] == pytest.approx(-0.4)
    assert c.loc[10, "n_pairs"] == 1 and c.loc[10, "n_he"] == 0 and np.isnan(c.loc[10, "mean_he"])
    assert np.isnan(c.loc[10, "lo_pair"]) and c.loc[10, "empty_draws_pair"] == 50


def test_gauge_bootstrap_keeps_whole_gauges_with_multiplicity():
    p = synthetic_pairs()
    draws = rcv.bootstrap_bins(p, "gauge", n_draws=200, seed=3)
    # bin 0 holds pairs (A,A)=0.8 and (B,B)=0.6: a draw's mean is a multiplicity-weighted mean of 0.8 and 0.6
    b0 = draws[:, 0][~np.isnan(draws[:, 0])]
    assert b0.min() >= 0.6 - 1e-12 and b0.max() <= 0.8 + 1e-12
    assert np.isclose(b0, 0.8).any() and np.isclose(b0, 0.6).any()  # draws without B, draws without A
    # bin 3 holds only (A,B): whenever present it is exactly -0.4; absent when gauge B was not drawn
    b3 = draws[:, 3]
    assert np.all(np.isnan(b3) | np.isclose(b3, -0.4)) and np.isnan(b3).any()
    # same draw: bins 0 and 3 are tied to the same gauge draw. If B is absent, bin 0 must be exactly 0.8.
    absent_b = np.isnan(b3)
    b0_absent_b = draws[absent_b, 0]
    assert np.all(np.isnan(b0_absent_b) | np.isclose(b0_absent_b, 0.8))  # NaN only when A is absent too


def test_gauge_bootstrap_reproducible_and_differs_from_pair_bootstrap():
    p = synthetic_pairs()
    a = rcv.bootstrap_bins(p, "gauge", n_draws=20, seed=473)
    b = rcv.bootstrap_bins(p, "gauge", n_draws=20, seed=473)
    assert np.array_equal(a, b, equal_nan=True)
    c = rcv.bootstrap_bins(p, "pair", n_draws=20, seed=473)
    assert not np.array_equal(a, c, equal_nan=True)


def test_reach_definitions():
    c = pd.DataFrame({"bin": [0, 1, 2, 3, 4], "hi_km": [0, 10, 20, 30, 40],
                      "lo": [0.5, 0.2, -0.1, 0.1, np.nan]})
    r = rcv.reach_km(c, "lo")
    assert r["reach_km"] == 30 and r["contiguous_reach_km"] == 10 and r["n_bins_above"] == 3
    c["lo"] = [-0.5, -0.2, np.nan, np.nan, np.nan]
    r = rcv.reach_km(c, "lo")
    assert np.isnan(r["reach_km"]) and r["contiguous_reach_km"] == 0


def test_regression_recovers_planted_slope():
    rng = np.random.default_rng(0)
    n = 300
    g = np.repeat(np.arange(30), 10)
    dist = rng.uniform(0, 200, n)
    elev = rng.uniform(0, 500, n)
    coast = (g % 3 == 0).astype(int)
    he = 0.7 - 0.3 * dist / 100 - 0.05 * elev / 100 + 0.1 * coast + rng.normal(0, 0.01, n)
    p = pd.DataFrame({"g_id": [f"g{i}" for i in g], "he": he, "dist_km": dist, "elev_diff_m": elev, "coast_g": coast})
    tab, info = rr.ols_table(p, n_draws=100, seed=1)
    coef = tab.set_index("term")["coef"]
    assert coef["dist_100km"] == pytest.approx(-0.3, abs=0.01)
    assert coef["abs_elev_diff_100m"] == pytest.approx(-0.05, abs=0.01)
    assert coef["coast"] == pytest.approx(0.1, abs=0.01)
    assert (tab["lo_gauge"] <= tab["coef"]).all() and (tab["hi_gauge"] >= tab["coef"]).all()
    assert info["n_pairs"] == n and info["n_gauges"] == 30
