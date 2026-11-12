"""Phase 3 rain reach: pair construction, the contract, the leak test."""
import os
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.rain import calendar as cal  # noqa: E402
from src.reach import rain_pairs as rp  # noqa: E402


def stations():
    return pd.DataFrame({
        "sid": ["AAA", "BBB", "CCC", "DDD"],
        "lat": [40.0, 40.0, 40.0, 40.0],
        "lon": [-75.0, -75.5, -74.0, -72.0],   # BBB ~42 km, CCC ~85 km, DDD ~255 km from AAA
        "elev_m": [10.0, 110.0, 10.0, 10.0],
        "has_cli": [True, False, True, False],
        "kept": [True, True, True, True],
        "coastal": [False, True, False, True],
        "coast_km": [50.0, 5.0, 40.0, 1.0],
    })


def test_build_pairs_rules():
    p = rp.build_pairs(stations())
    # S in {AAA, CCC}; G within 200 km of S; DDD is beyond 200 km of AAA but 170 km from CCC
    keys = set(zip(p.s_id, p.g_id))
    assert ("AAA", "AAA") in keys and ("CCC", "CCC") in keys
    assert ("AAA", "DDD") not in keys and ("CCC", "DDD") in keys
    assert ("BBB", "AAA") not in keys  # BBB has no climate report
    same = p[p.same_station]
    assert (same.dist_km == 0).all() and len(same) == 2
    r = p[(p.s_id == "AAA") & (p.g_id == "BBB")].iloc[0]
    assert 40 < r.dist_km < 45 and r.elev_diff_m == 100 and r.coast_g and not r.coast_s
    assert list(p.columns) == rp.PAIR_COLUMNS


def fake_daily(sid, years, usable_days, loss_days):
    """Daily table with every season day usable except `usable_days` False dates; loss on `loss_days`."""
    rows = []
    for y in years:
        for d in cal.season_days(y):
            u = d not in usable_days
            rows.append({"station": sid, "date": pd.Timestamp(d), "season": y, "usable": u,
                         rp.LOSS_COLUMN: (d in loss_days) if u else pd.NA, "season_usable": True})
    return pd.DataFrame(rows)


def test_pair_seasons_joint_days_and_counts():
    years = [2000, 2001]
    d1 = cal.season_days(2000)
    a = fake_daily("AAA", years, usable_days={d1[0]}, loss_days={d1[1], d1[2]})
    b = fake_daily("BBB", years, usable_days={d1[1]}, loss_days={d1[2], d1[3]})
    m = rp.build_day_matrix({"AAA": a, "BBB": b}, 2000, 2001)
    s = rp.pair_seasons(m, "AAA", "BBB")
    r = s[s.season == 2000].iloc[0]
    assert r.n_days == len(d1) - 2            # two days not joint
    assert r.c_s == 1 and r.c_g == 2          # day 1 at AAA is not joint; day 2 shared; day 3 at BBB only
    assert r.n_agree == len(d1) - 2 - 1       # one joint day disagrees (day 3)
    assert bool(r.usable)


def test_split_windows():
    tr, rp_ = rp.split_windows(np.arange(2000, 2020))
    assert len(tr) == 12 and len(rp_) == 8 and tr[-1] == 2011 and rp_[0] == 2012
    tr, rp_ = rp.split_windows(np.array([3, 1, 2, 5, 4]))
    assert list(tr) == [1, 2, 3] and list(rp_) == [4, 5]


def test_fit_contract_by_hand():
    # S and G identical. Hand recomputation of the rule: for each d, premium = 1.2 x mean(max(c - d, 0)),
    # net = c - max(c - d, 0) + premium, HE against reference mean(c) = 6; d = the argmax (ties to the smallest).
    c = np.array([2, 4, 6, 8, 10], dtype=float)
    k = rp.fit_contract(c, c)
    hes = []
    for d in range(9):
        pay = np.maximum(c - d, 0)
        prem = 1.2 * pay.mean()
        net = c - pay + prem
        hes.append(1 - np.mean(np.maximum(net - 6, 0) ** 2) / np.mean(np.maximum(c - 6, 0) ** 2))
    assert k.d == int(np.argmax(hes)) and k.train_he == pytest.approx(max(hes)) and k.reference == 6.0
    assert k.premium == pytest.approx(1.2 * np.maximum(c - k.d, 0).mean())
    # with d = 0 and no premium the identical hedge would be perfect; the premium is what keeps HE below 1
    assert hes[0] < 1.0
    # independent S: payout never covers the bad G seasons any better than noise; HE must be <= 1 and d is chosen
    rng = np.random.default_rng(0)
    k2 = rp.fit_contract(rng.integers(0, 10, 30), rng.integers(0, 10, 30))
    assert k2.d in rp.D_GRID and k2.train_he <= 1.0


def test_report_he_definition():
    c = rp.Contract(d=2, premium=1.0, reference=5.0, train_he=0.0, train_seasons=[])
    # REPORT: c_g = [8, 3], c_s = [6, 1] -> payout [4, 0], net = [8-4+1, 3+1] = [5, 4]; SV_u = (3^2)/2, SV_h = 0
    assert rp.report_he([6, 1], [8, 3], c) == pytest.approx(1.0)
    # no REPORT season above the reference -> NaN
    assert np.isnan(rp.report_he([6, 1], [4, 3], c))


def test_leak_report_seasons_cannot_change_d():
    """Changing the REPORT seasons' counts must not change d, premium or reference."""
    rng = np.random.default_rng(473)
    n = 30
    seasons = pd.DataFrame({"season": np.arange(1990, 1990 + n), "n_days": 100,
                            "c_s": rng.integers(0, 12, n), "c_g": rng.integers(0, 12, n),
                            "n_agree": 90, "usable": True})
    base = rp.evaluate_pair(seasons)
    train, report = rp.split_windows(seasons.season.to_numpy())
    for trial in range(5):
        alt = seasons.copy()
        mask = alt.season.isin(report)
        alt.loc[mask, "c_s"] = rng.integers(0, 40, mask.sum())
        alt.loc[mask, "c_g"] = rng.integers(0, 40, mask.sum())
        out = rp.evaluate_pair(alt)
        assert out["d"] == base["d"] and out["premium"] == base["premium"] and out["reference"] == base["reference"]
        assert out["train_he"] == base["train_he"]
    # and TRAIN changes do change the fit (sanity that the test can fail)
    alt = seasons.copy()
    alt.loc[alt.season.isin(train), "c_g"] = 0
    assert rp.evaluate_pair(alt)["reference"] != base["reference"]


def test_evaluate_pair_status_rules():
    n = 10
    s = pd.DataFrame({"season": np.arange(2000, 2000 + n), "n_days": 100, "c_s": np.arange(n), "c_g": np.arange(n),
                      "n_agree": 100, "usable": True})
    out = rp.evaluate_pair(s)
    assert out["status"] == "few_joint_seasons" and out["n_train"] == 6 and out["n_report"] == 4
    assert out["he_defined"]
    s2 = s.copy()
    s2["usable"] = [True, True, False, False, False, False, False, False, False, False]
    assert rp.evaluate_pair(s2)["status"] == "too_few_for_windows"
    s3 = pd.concat([s] * 2, ignore_index=True)
    s3["season"] = np.arange(2000, 2020)
    assert rp.evaluate_pair(s3)["status"] == "ok"
