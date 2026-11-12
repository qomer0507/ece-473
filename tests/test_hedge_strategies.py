"""Hand-computed examples: bucket edges, holdings, add-half smoothing, premium, Kalshi daily cost, TRAIN choices."""
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.hedge_eval import strategies as hs  # noqa: E402
from src.hedge_eval.metrics import hedge_effectiveness  # noqa: E402

PRICE = {"a": 0.10, "s": 0.50, "u": 0.10}


def days_from_seasons(rows):
    """rows: list of (season, [(month, c_s, k_s, d_park), ...]) -> joint-day frame."""
    out = []
    for season, days in rows:
        for i, (month, c, k, d) in enumerate(days):
            out.append({"date": pd.Timestamp(season, month, 1) + pd.Timedelta(days=i), "season": season,
                        "month": month, "c_s": c, "k_s": k, "d_park": d})
    return pd.DataFrame(out)


def random_days(seed, seasons, n_days=60, shift=0.0):
    rng = np.random.default_rng(seed)
    rows = []
    for s in seasons:
        wet = rng.uniform(0.2, 0.5) + shift
        k = rng.random(n_days) < wet
        c = k & (rng.random(n_days) < 0.25)
        d = np.where(rng.random(n_days) < 0.8, c, k & (rng.random(n_days) < 0.2))
        rows.append((s, [(6 + (i // 30), int(c[i]), int(k[i]), int(d[i])) for i in range(n_days)]))
    return days_from_seasons(rows)


# ---------------------------------------------------------------- bucket edges
def test_edges_twelve_seasons_one_to_twelve():
    # N = 12: e_k is the ceil(2k)-th smallest = 2, 4, 6, 8, 10
    edges, raw = hs.bucket_edges(range(1, 13))
    assert edges == [2, 4, 6, 8, 10] and raw == edges


def test_edges_trenton_style_sixteen_seasons():
    # sorted: 1 2 2 2 3 4 4 5 5 6 6 6 8 8 12 12; ranks ceil(16k/6) = 3, 6, 8, 11, 14 -> 2, 4, 5, 6, 8
    counts = [2, 6, 6, 4, 8, 5, 5, 8, 2, 4, 12, 2, 1, 6, 12, 3]
    assert hs.bucket_edges(counts)[0] == [2, 4, 5, 6, 8]


def test_edges_ties_are_moved_upward_and_recorded():
    edges, raw = hs.bucket_edges([2] * 12)
    assert raw == [2, 2, 2, 2, 2] and edges == [2, 3, 4, 5, 6]
    edges, raw = hs.bucket_edges([0, 0, 0, 0, 5, 5, 5, 5, 9, 9, 9, 9])   # ranks 2,4,6,8,10 -> 0,0,5,5,9
    assert raw == [0, 0, 5, 5, 9] and edges == [0, 1, 5, 6, 9]


def test_edges_linear_floor_sensitivity():
    # numpy linear quantiles of 1..12 at k/6: 2.83, 4.67, 6.5, 8.33, 10.17 -> floors 2, 4, 6, 8, 10
    assert hs.bucket_edges(range(1, 13), "linear_floor")[0] == [2, 4, 6, 8, 10]
    with pytest.raises(ValueError):
        hs.bucket_edges([1, 2], "nope")


def test_bucket_index_upper_edges_are_inclusive():
    assert list(hs.bucket_index([0, 2, 3, 4, 5, 10, 11, 40], [2, 4, 6, 8, 10])) == [0, 0, 1, 1, 2, 4, 5, 5]


# ---------------------------------------------------------------- holdings and probabilities
def test_bucket_means_full():
    m, n = hs.bucket_means(range(1, 13), [2, 4, 6, 8, 10])
    assert m == [1.5, 3.5, 5.5, 7.5, 9.5, 11.5] and n == [2] * 6


def test_bucket_means_empty_buckets_use_midpoints():
    # counts 1, 1, 5, 12 with edges 2,4,6,8,10: buckets 3-4, 7-8, 9-10 are empty -> 3.5, 7.5, 9.5
    m, n = hs.bucket_means([1, 1, 5, 12], [2, 4, 6, 8, 10])
    assert m == [1.0, 3.5, 5.0, 7.5, 9.5, 12.0] and n == [2, 0, 1, 0, 0, 1]
    # empty first bucket: range 0..2 -> 1.0 ; empty top bucket: e5 + 2
    m, n = hs.bucket_means([3], [2, 4, 6, 8, 10])
    assert m[0] == 1.0 and m[5] == 12.0 and n == [0, 1, 0, 0, 0, 0]


def test_holdings_rule():
    assert hs.holdings([1.5, 3.5, 5.5, 7.5, 9.5, 11.5], 4) == [0.0, 0.0, 1.5, 3.5, 5.5, 7.5]
    assert hs.holdings([1.5, 3.5], 0) == [1.5, 3.5]


def test_add_half_smoothing():
    q = hs.add_half_probs([4, 3, 2, 3, 2, 2])            # N = 16 -> denominators 19
    assert q == pytest.approx([4.5 / 19, 3.5 / 19, 2.5 / 19, 3.5 / 19, 2.5 / 19, 2.5 / 19])
    assert sum(q) == pytest.approx(1.0)
    assert hs.add_half_probs([0, 0, 0, 0, 0, 6])[0] == pytest.approx(0.5 / 9)   # an empty bucket keeps weight


def test_bucket_premium():
    # expected payout = (0 + 0 + 1 + 2 + 3 + 4)/6 = 10/6 ; loading 0.20 -> 2.0
    assert hs.bucket_premium([0, 0, 1, 2, 3, 4], [1 / 6] * 6, 0.20) == pytest.approx(2.0)
    assert hs.bucket_premium([0, 0, 1, 2, 3, 4], [1 / 6] * 6, 0.0) == pytest.approx(10 / 6)


# ---------------------------------------------------------------- Kalshi daily
def test_monthly_p():
    d = days_from_seasons([(2001, [(6, 0, 1, 0), (6, 0, 0, 0), (7, 0, 1, 0), (7, 0, 1, 0)])])
    assert hs.monthly_p(d) == {6: 0.5, 7: 1.0, 0: 0.75}


def test_kalshi_unit_table_by_hand():
    # p = 0.30 everywhere. Rain day: ask = 0.30 + 0.5*0.70 + 0.10 = 0.75, fee = ceil(0.07*0.75*0.25*100)/100 = 0.02,
    # filled share 0.9 -> premium 0.693, payout 0.9. Dry day: ask = 0.30 - 0.15 + 0.10 = 0.25, fee 0.02 -> 0.27.
    d = days_from_seasons([(2001, [(6, 0, 1, 0), (6, 0, 0, 0), (6, 0, 0, 0)])])
    t = hs.kalshi_unit_table(d, {6: 0.30, 0: 0.30}, PRICE, 0.20)
    assert t["premium_mkt"][0] == pytest.approx(0.693 + 0.27 + 0.27)
    assert t["payout_mkt"][0] == pytest.approx(0.9)
    assert t["premium_fair"][0] == pytest.approx(3 * 1.2 * 0.30)      # (1 + loading) * p per day, no fee
    assert t["payout_fair"][0] == pytest.approx(1.0)                  # every order filled


def test_argmax_first_tie_goes_to_earliest():
    assert hs.argmax_first([0.1, 0.5, 0.5, 0.2]) == 1
    assert hs.argmax_first([float("nan"), float("nan")]) == 0
    assert hs.argmax_first([-1.0, float("nan"), -0.5]) == 2


def test_grids_are_as_registered():
    assert hs.N_GRID == tuple(round(0.05 * i, 2) for i in range(1, 21)) and len(hs.N_GRID) == 20
    assert hs.N_GRID[0] == 0.05 and hs.N_GRID[-1] == 1.0
    assert hs.D_GRID == (0, 1, 2, 3, 4, 5, 6, 7, 8)


# ---------------------------------------------------------------- TRAIN choices
def test_fit_params_choices_are_the_grid_maxima():
    train = random_days(7, range(2000, 2012))
    p = hs.fit_params(train, PRICE, 0.20)
    agg = train.groupby("season").agg(D=("d_park", "sum"), C=("c_s", "sum"))
    d_park, c_s = agg["D"].to_numpy(float), agg["C"].to_numpy(float)
    assert p.reference == pytest.approx(d_park.mean())
    unit = hs.kalshi_unit_table(train, p.p_month, PRICE, 0.20)
    he_n = [hedge_effectiveness(d_park - n * unit["payout_mkt"] + n * unit["premium_mkt"], d_park, p.reference)
            for n in hs.N_GRID]
    assert p.n2 == hs.N_GRID[int(np.nanargmax(he_n))] and p.train_he["2"] == pytest.approx(np.nanmax(he_n))
    he_d = []
    for d in hs.D_GRID:
        h = hs.holdings(p.m, d)
        pay = np.asarray(h)[hs.bucket_index(c_s, p.edges)]
        he_d.append(hedge_effectiveness(d_park - pay + hs.bucket_premium(h, p.q, 0.20), d_park, p.reference))
    assert p.d3 == int(np.nanargmax(he_d))
    assert p.h == hs.holdings(p.m, p.d3)
    assert p.premium3 == pytest.approx(1.2 * sum(a * b for a, b in zip(p.h, p.q)))
    pay4 = np.maximum(c_s - p.d4, 0)
    assert p.premium4 == pytest.approx(1.2 * pay4.mean())


def test_season_results_net_cost_identity_and_strategy_three_payout():
    train = random_days(7, range(2000, 2012))
    report = random_days(8, range(2012, 2018))
    p = hs.fit_params(train, PRICE, 0.20)
    r = hs.season_results(report, p)
    assert np.allclose(r["net_cost"], r["D_park"] - r["payout"] + r["premium"])
    r0 = r[r.strategy == "0"]
    assert (r0["payout"] == 0).all() and (r0["premium"] == 0).all() and (r0["net_cost"] == r0["D_park"]).all()
    r3 = r[r.strategy == "3"]
    assert np.allclose(r3["payout"], [p.h[int(hs.bucket_index(c, p.edges))] for c in r3["C_S"]])
    assert np.allclose(r3["premium"], p.premium3)
    r1, r2 = r[r.strategy == "1"], r[r.strategy == "2"]
    assert np.allclose(r2["payout"].to_numpy(), p.n2 * r1["payout"].to_numpy())
    assert np.allclose(r2["premium"].to_numpy(), p.n2 * r1["premium"].to_numpy())
    r4 = r[r.strategy == "4"]
    assert np.allclose(r4["payout"], np.maximum(r4["C_S"] - p.d4, 0))


def test_strategy_three_by_hand_small_example():
    # Six TRAIN seasons with C_S = D_park = 1, 2, 3, 4, 5, 6 (one bucket each: edges 1..5, m = 1..6, q = 1/6).
    rows = [(2000 + i, [(6, 1, 1, 1)] * (i + 1) + [(6, 0, 0, 0)] * (10 - i)) for i in range(6)]
    p = hs.fit_params(days_from_seasons(rows), PRICE, 0.20)
    assert p.edges == [1, 2, 3, 4, 5] and p.m == [1, 2, 3, 4, 5, 6] and p.n_j == [1] * 6
    assert p.q == pytest.approx([1 / 6] * 6) and p.reference == pytest.approx(3.5)
    # d = 0: payout = C, net = premium = 1.2 * 3.5 = 4.2 every season -> SV = 0.49; unhedged SV = (0.25+2.25+6.25)/6
    # d = 3: h = 0,0,0,1,2,3, premium = 1.2 * 1 = 1.2, net = 2.2, 3.2, 4.2, 4.2, 4.2, 4.2 -> SV = 4*0.49/6
    # d = 4: h = ..,1,2, premium = 0.6, net = 1.6, 2.6, 3.6, 4.6, 4.6, 4.6 -> SV = 3*1.21/6  (worse than d = 3)
    # d = 2: h = 0,0,1,2,3,4, premium = 2.0, net = 3, 4, 4, 4, 4, 4 -> SV = 5*0.25/6  (best)
    # d = 1: premium = 1.2 * 2.5 = 3.0, net = 4 x5 and 3+... all 4 except season 1 (1 - 0 + 3 = 4) -> SV = 6*0.25/6
    assert p.d3 == 2 and p.h == [0, 0, 1, 2, 3, 4] and p.premium3 == pytest.approx(2.0)
    assert p.train_he["3"] == pytest.approx(1 - (5 * 0.25 / 6) / (8.75 / 6))
