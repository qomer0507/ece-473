"""Hand-computed examples: hedge effectiveness with the fixed TRAIN reference, worst seasons, useful payout, bootstrap."""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.hedge_eval import bootstrap as hb  # noqa: E402
from src.hedge_eval import metrics as hm  # noqa: E402


def test_semivariance_by_hand():
    # reference 5: excesses 0, 2, 4 -> squares 0, 4, 16 -> mean 20/3
    assert hm.semivariance([3, 7, 9], 5.0) == pytest.approx(20 / 3)


def test_hedge_effectiveness_by_hand():
    # unhedged SV = 20/3; hedged [4, 6, 7] -> (0 + 1 + 4)/3 = 5/3 -> HE = 1 - 5/20
    assert hm.hedge_effectiveness([4, 6, 7], [3, 7, 9], 5.0) == pytest.approx(0.75)


def test_reference_is_fixed_so_a_flat_premium_is_punished():
    # A hedge that only charges 1 every season: hedged = unhedged + 1 = [4, 8, 10].
    # Fixed reference 5: (0 + 9 + 25)/3 = 34/3 -> HE = 1 - 34/20 = -0.7.
    # A moving mean would give 0 (the spread is unchanged); the registered metric must not.
    assert hm.hedge_effectiveness([4, 8, 10], [3, 7, 9], 5.0) == pytest.approx(-0.7)


def test_reference_comes_from_train_not_from_the_window():
    # Same report seasons, two different TRAIN means -> different HE.
    he5 = hm.hedge_effectiveness([4, 6, 7], [3, 7, 9], 5.0)
    he6 = hm.hedge_effectiveness([4, 6, 7], [3, 7, 9], 6.0)   # unhedged (0+1+9)/3, hedged (0+0+1)/3 -> 0.9
    assert he6 == pytest.approx(0.9) and he5 != he6


def test_he_undefined_when_nothing_is_above_reference():
    assert np.isnan(hm.hedge_effectiveness([1, 2], [1, 2], 5.0))


def test_perfect_and_no_hedge():
    assert hm.hedge_effectiveness([5, 5, 5], [3, 7, 9], 5.0) == pytest.approx(1.0)
    assert hm.hedge_effectiveness([3, 7, 9], [3, 7, 9], 5.0) == pytest.approx(0.0)


def test_worst_count_rules():
    assert hm.worst_count(12, "worst3") == 3
    assert hm.worst_count(35, "worst10pct") == 4     # ceil(3.5)
    assert hm.worst_count(30, "worst10pct") == 3     # exactly 3.0
    assert hm.worst_count(5, "worst10pct") == 1
    with pytest.raises(ValueError):
        hm.worst_count(5, "other")


def test_worst_means_use_the_same_seasons_ranked_by_unhedged():
    # unhedged [5, 9, 7, 9]: worst two are positions 1 and 3 -> hedged (6 + 7)/2, unhedged 9
    assert hm.worst_means([4, 6, 8, 7], [5, 9, 7, 9], 2) == (6.5, 9.0)
    # tie at the cut: positions 1 (9) then 0 and 2 tie at 7 -> earlier season (position 0)
    assert hm.worst_means([1, 2, 3], [7, 9, 7], 2) == (1.5, 8.0)


def test_useful_payout_and_premium_ratio():
    # payout [3, 0, 5], loss [2, 4, 5] -> useful [2, 0, 5] = 7; premium 1 a season = 3 -> 3/7
    assert list(hm.useful_payout([3, 0, 5], [2, 4, 5])) == [2, 0, 5]
    assert hm.premium_per_useful_payout([1, 1, 1], [3, 0, 5], [2, 4, 5]) == pytest.approx(3 / 7)
    assert np.isnan(hm.premium_per_useful_payout([1], [0], [4]))


def test_all_metrics_by_hand():
    d, pay, prem = [3, 7, 9], [0, 2, 3], [1, 1, 1]          # net = [4, 6, 7]
    m = hm.all_metrics(d, pay, prem, 5.0, "worst3")
    assert m["he"] == pytest.approx(0.75)
    assert m["mean_net_cost"] == pytest.approx(17 / 3)
    assert m["sd_net_cost"] == pytest.approx(np.std([4, 6, 7], ddof=1))
    assert m["worst_mean_hedged"] == pytest.approx(17 / 3) and m["worst_mean_unhedged"] == pytest.approx(19 / 3)
    assert m["total_premium"] == 3
    assert m["premium_per_useful_payout"] == pytest.approx(3 / 5)   # useful = 0 + 2 + 3
    assert m["share_seasons_reduced"] == pytest.approx(2 / 3)        # 4 > 3 no; 6 < 7; 7 < 9


def test_bootstrap_draws_are_seeded_and_shaped():
    a = hb.draw_indices(12)
    b = hb.draw_indices(12)
    assert a.shape == (2000, 12) and (a == b).all() and a.min() >= 0 and a.max() <= 11
    assert (a == np.random.default_rng(473).integers(0, 12, size=(2000, 12))).all()


def test_bootstrap_interval_collapses_for_identical_seasons():
    d = np.full(6, 8.0)
    legs = {"x": (np.full(6, 2.0), np.full(6, 1.0))}       # net 7, reference 5 -> HE = 1 - 4/9
    iv, _ = hb.bootstrap_metrics(d, legs, 5.0, "worst3", n_draws=50)
    lo, hi, n = iv[("x", "he")]
    assert lo == pytest.approx(1 - 4 / 9) and hi == pytest.approx(1 - 4 / 9) and n == 50


def test_bootstrap_difference_is_paired():
    rng = np.random.default_rng(1)
    d = rng.integers(0, 12, 10).astype(float)
    legs = {"a": (0.5 * d, np.full(10, 2.0)), "b": (0.2 * d, np.full(10, 1.0))}
    iv, draws = hb.bootstrap_metrics(d, legs, 4.0, "worst3", differences=(("a", "b"),), n_draws=200)
    diff = draws[("a", "he")] - draws[("b", "he")]
    ok = diff[~np.isnan(diff)]
    assert iv[("a_minus_b", "he")][0] == pytest.approx(np.percentile(ok, 2.5))
    assert iv[("a_minus_b", "he")][1] == pytest.approx(np.percentile(ok, 97.5))


def test_percentile_interval_skips_nan():
    lo, hi, n = hb.percentile_interval([np.nan, 1.0, 2.0, 3.0])
    assert n == 3 and lo == pytest.approx(1.05) and hi == pytest.approx(2.95)
