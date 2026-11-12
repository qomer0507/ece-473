"""Tests for aggregate statistics and the year-block bootstrap in src/panel/hedge.py. Synthetic test input."""
import numpy as np
import pandas as pd
import pytest

from src.panel import hedge as H


def yearly(rows):
    return pd.DataFrame(rows, columns=["location_id", "year"] + H.COUNT_COLS)


def test_aggregate_stats_hand_case():
    # loc X: n=10, hot=4, pay=3, fn=2, fp=1 -> R = 0.3.  loc Y: n=20, hot=0, pay=2, fn=0, fp=2 -> R = 0.1
    c = pd.DataFrame([[10, 4, 3, 2, 1], [20, 0, 2, 0, 2]], columns=H.COUNT_COLS)
    a = H.aggregate_stats(c)
    assert a["mean_R"] == pytest.approx(0.2)            # unweighted mean of 0.3 and 0.1
    assert a["miss_rate"] == pytest.approx(2 / 4)       # pooled FN / hot
    assert a["false_payout_rate"] == pytest.approx(3 / 5)  # pooled FP / pay


def test_aggregate_skips_locations_without_days():
    c = pd.DataFrame([[10, 4, 3, 2, 1], [0, 0, 0, 0, 0]], columns=H.COUNT_COLS)
    assert H.aggregate_stats(c)["mean_R"] == pytest.approx(0.3)


def test_draws_are_seeded_and_whole_years():
    d1 = H.bootstrap_year_draws([2023, 2024, 2025])
    d2 = H.bootstrap_year_draws([2025, 2023, 2024])
    assert d1.shape == (1000, 3) and (d1 == d2).all()
    assert set(np.unique(d1)) == {2023, 2024, 2025}
    assert (H.bootstrap_year_draws([2023, 2024, 2025], seed=474) != d1).any()
    assert H.BOOT_DRAWS == 1000 and H.BOOT_SEED == 473


def test_bootstrap_matches_manual_recomputation():
    y = yearly([["X", 2023, 10, 4, 3, 2, 1], ["X", 2024, 10, 2, 2, 0, 0], ["X", 2025, 10, 5, 1, 4, 0],
                ["Y", 2023, 10, 1, 1, 1, 1], ["Y", 2024, 10, 0, 3, 0, 3], ["Y", 2025, 8, 2, 2, 0, 0]])
    b = H.year_block_bootstrap({"arm": y}, n_draws=50)
    draws = H.bootstrap_year_draws([2023, 2024, 2025], 50)
    for k in (0, 7, 49):
        parts = [y[y.year == yr] for yr in draws[k]]          # same years for X and Y (joint resampling)
        c = pd.concat(parts).groupby("location_id")[H.COUNT_COLS].sum()
        a = H.aggregate_stats(c)
        assert b.loc[k, "arm:mean_R"] == pytest.approx(a["mean_R"])
        assert b.loc[k, "arm:miss_rate"] == pytest.approx(a["miss_rate"], nan_ok=True)
        assert b.loc[k, "arm:false_payout_rate"] == pytest.approx(a["false_payout_rate"], nan_ok=True)


def test_bootstrap_arms_are_paired_and_constant_data_gives_zero_width():
    y = yearly([["X", yr, 10, 4, 3, 2, 1] for yr in (2023, 2024, 2025)])
    b = H.year_block_bootstrap({"a": y, "b": y})
    assert len(b) == 1000
    assert (b["a:mean_R"] == b["b:mean_R"]).all()
    lo, hi = H.percentile_interval(b["a:mean_R"])
    assert lo == pytest.approx(0.3) and hi == pytest.approx(0.3)


def test_bootstrap_interval_covers_range_of_years():
    # R by year: 0.0, 0.1, 0.5. Draws of 3 years can give anything from 0.0 (all 2023) to 0.5 (all 2025).
    y = yearly([["X", 2023, 10, 0, 0, 0, 0], ["X", 2024, 10, 1, 0, 1, 0], ["X", 2025, 10, 5, 0, 5, 0]])
    b = H.year_block_bootstrap({"a": y})
    assert b["a:mean_R"].min() == pytest.approx(0.0) and b["a:mean_R"].max() == pytest.approx(0.5)
    lo, hi = H.percentile_interval(b["a:mean_R"])
    assert 0.0 <= lo < 0.2 < hi <= 0.5
