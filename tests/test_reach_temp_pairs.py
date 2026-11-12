"""Pair construction, seasonal counts and the 60/40 split (Phase 3 temperature reach)."""
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.panel.hedge import haversine_km  # noqa: E402
from src.reach_temp import pairs as rp  # noqa: E402
from src.reach_temp import contract as rc  # noqa: E402


def stations_small():
    # A (cli), B (cli), C (no cli), D (cli but not exposure), E (far, no cli)
    return pd.DataFrame({
        "id": ["A", "B", "C", "D", "E"],
        "lat": [40.0, 40.0, 40.5, 40.1, 43.0],
        "lon": [-75.0, -74.0, -75.0, -75.0, -75.0],
        "elev_m": [10.0, 50.0, 100.0, 0.0, 300.0],
        "is_exposure": [True, True, True, False, True],
        "has_cli": [True, True, False, True, False],
    })


def test_build_pairs_sets_and_distance():
    p = rp.build_pairs(stations_small())
    # S in {A, B}; G in {A, B, C, E}; E is ~333 km from A and >200 from B -> excluded
    assert set(p["s_id"]) == {"A", "B"}
    assert "D" not in set(p["g_id"]) and "E" not in set(p["g_id"])
    assert len(p) == 6
    same = p[p["same_station"]]
    assert set(same["s_id"]) == {"A", "B"} and (same["dist_km"] == 0).all()
    ab = p[(p.s_id == "A") & (p.g_id == "B")]["dist_km"].item()
    assert ab == pytest.approx(haversine_km(40, -75, 40, -74))
    ba = p[(p.s_id == "B") & (p.g_id == "A")]["dist_km"].item()
    assert ab == ba  # both orders present
    assert p[(p.s_id == "A") & (p.g_id == "C")]["elev_diff_m"].item() == 90.0
    assert list(p.columns) == rp.PAIR_COLUMNS


def test_build_pairs_respects_max_km():
    st = stations_small()
    p = rp.build_pairs(st, max_km=60.0)  # A-C is 55.6 km, A-B 85 km
    assert set(zip(p.s_id, p.g_id)) == {("A", "A"), ("B", "B"), ("A", "C")}


def wide_two_seasons():
    days = pd.date_range("2015-01-01", "2016-12-31", freq="D")
    rng = np.random.default_rng(1)
    w = pd.DataFrame({"S": rng.uniform(70, 95, len(days)), "G": rng.uniform(70, 95, len(days))}, index=days)
    return w


def test_pair_seasons_counts_and_usable():
    w = wide_two_seasons()
    # make 2015: S has 5 hot days, G 3 hot days (2 overlap); 2016: knock out 20 G days -> unusable
    w.loc[:, :] = 80.0
    hot_s = pd.to_datetime(["2015-06-01", "2015-06-02", "2015-07-01", "2015-07-02", "2015-08-01"])
    hot_g = pd.to_datetime(["2015-06-01", "2015-06-02", "2015-09-30"])
    w.loc[hot_s, "S"] = 95.0
    w.loc[hot_g, "G"] = 90.0
    w.loc[pd.date_range("2016-06-01", periods=20), "G"] = np.nan
    s = rp.pair_seasons(w, "S", "G")
    assert list(s["season"]) == [2015, 2016]
    r = s.iloc[0]
    assert r["n_days"] == 153 and r["c_s"] == 5 and r["c_g"] == 3 and r["usable"]
    # agreement: 153 - (3 S-only + 1 G-only) = 149
    assert r["n_agree"] == 149
    assert s.iloc[1]["n_days"] == 133 and not s.iloc[1]["usable"]
    # days outside May-Sep are never counted even if hot
    w.loc[pd.Timestamp("2015-04-30"), "S"] = 100.0
    assert rp.pair_seasons(w, "S", "G").iloc[0]["c_s"] == 5


def test_usable_threshold_is_90_percent_of_153():
    w = wide_two_seasons()
    w.loc[:, :] = 80.0
    w.loc[pd.date_range("2015-05-01", periods=15), "S"] = np.nan  # 138 joint days: usable
    w.loc[pd.date_range("2016-05-01", periods=16), "S"] = np.nan  # 137: not usable
    s = rp.pair_seasons(w, "S", "G")
    assert bool(s.iloc[0]["usable"]) and not bool(s.iloc[1]["usable"])


@pytest.mark.parametrize("n,n_train", [(11, 6), (10, 6), (5, 3), (4, 2), (3, 1), (2, 1)])
def test_split_60_40(n, n_train):
    seasons = list(range(2015, 2015 + n))
    tr, rp_ = rc.split_seasons(seasons)
    assert len(tr) == n_train and tr == seasons[:n_train] and rp_ == seasons[n_train:]


def test_split_uses_calendar_order_of_usable_seasons_only():
    tr, rep = rc.split_seasons([2025, 2015, 2017, 2019, 2021])
    assert tr == [2015, 2017, 2019] and rep == [2021, 2025]


def test_evaluate_pair_too_few_seasons():
    s = pd.DataFrame({"season": [2015, 2016, 2017], "n_days": 153, "c_s": [1, 2, 3], "c_g": [1, 2, 3],
                      "n_agree": 153, "usable": [True, True, False]})
    out = rc.evaluate_pair(s)
    assert out["status"] == "too_few_seasons" and np.isnan(out["he"]) and out["n_usable"] == 2


def test_trigger_agreement_and_corr_use_usable_seasons_only():
    s = pd.DataFrame({"season": [2015, 2016, 2017], "n_days": [100, 100, 100], "c_s": [1, 5, 9],
                      "c_g": [2, 6, 100], "n_agree": [90, 80, 0], "usable": [True, True, False]})
    assert rp.trigger_agreement(s) == pytest.approx(170 / 200)
    assert rp.count_correlation(s) == pytest.approx(1.0)
