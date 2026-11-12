"""Phase 3 rain reach: binning, bootstrap shape, reach, regression."""
import os
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.reach import rain_curve as rc  # noqa: E402


def test_assign_bins_edges():
    d = np.array([0.0, 0.0, 0.01, 10.0, 10.01, 19.99, 20.0, 199.9, 200.0, 200.1])
    same = np.array([True, False, False, False, False, False, False, False, False, False])
    b = rc.assign_bins(d, same)
    assert list(b) == [0, 0, 1, 1, 2, 2, 2, 20, 20, -1]


def test_bin_labels():
    t = rc.bin_labels(21)
    assert t.bin_lo_km.iloc[0] == 0 and t.bin_hi_km.iloc[0] == 0
    assert t.bin_lo_km.iloc[1] == 0 and t.bin_hi_km.iloc[1] == 10
    assert t.bin_hi_km.iloc[20] == 200


def fake_pairs(n=300, seed=1):
    rng = np.random.default_rng(seed)
    d = rng.uniform(0, 200, n)
    g = rng.integers(0, 30, n).astype(str)
    he = 0.8 - d / 150 + rng.normal(0, 0.2, n)
    p = pd.DataFrame({"s_id": "S", "g_id": g, "dist_km": d, "same_station": False, "he": he,
                      "count_corr": 0.9 - d / 300, "trigger_agreement": 0.95, "elev_diff_m": rng.uniform(0, 300, n),
                      "coast_g": rng.integers(0, 2, n).astype(bool)})
    p.loc[:4, ["dist_km", "same_station", "he"]] = [0.0, True, 0.9]
    return p


def test_bootstrap_shape_and_seed():
    p = fake_pairs()
    bins = rc.assign_bins(p.dist_km, p.same_station)
    a = rc.bootstrap_bins(p.he.to_numpy(), bins, None, 21, n_draws=50, seed=473)
    b = rc.bootstrap_bins(p.he.to_numpy(), bins, p.g_id.to_numpy(), 21, n_draws=50, seed=473)
    assert a.shape == (50, 21) and b.shape == (50, 21)
    a2 = rc.bootstrap_bins(p.he.to_numpy(), bins, None, 21, n_draws=50, seed=473)
    assert np.array_equal(a, a2, equal_nan=True)
    lo, hi, empty = rc.band(a)
    assert lo.shape == (21,) and (lo[~np.isnan(lo)] <= hi[~np.isnan(hi)]).all()


def test_curve_table_and_reach():
    p = fake_pairs()
    t = rc.curve_table(p, n_draws=100)
    assert len(t) == 21 and t.n_pairs.sum() == len(p)
    assert t.loc[0, "n_pairs"] == 5 and t.loc[0, "mean_he"] == pytest.approx(0.9)
    # mean HE falls with distance in the fake data
    assert t.mean_he.iloc[1] > t.mean_he.iloc[20]
    r = rc.reach_km(t, "he_lo_pair")
    assert 0 <= r["contiguous_reach_km"] <= r["reach_km"] <= 200
    # hand check of the registered definition
    above = t[(t.bin > 0) & (t.he_lo_pair > 0)]
    assert r["reach_km"] == (above.bin_hi_km.max() if len(above) else 0)


def test_bin_means_ignores_nan():
    v = np.array([1.0, np.nan, 3.0, 5.0])
    b = np.array([1, 1, 1, 2])
    m = rc.bin_means(v, b, 3)
    assert np.isnan(m[0]) and m[1] == 2.0 and m[2] == 5.0


def test_regression_recovers_slope():
    p = fake_pairs(n=2000, seed=2)
    reg = rc.regression(p, n_draws=50)
    slope = reg.loc[reg.term == "dist_100km", "coef"].iloc[0]
    assert slope == pytest.approx(-100 / 150, abs=0.1)
    assert (reg.lo_gauge_boot <= reg.coef).all() and (reg.coef <= reg.hi_gauge_boot).all()
