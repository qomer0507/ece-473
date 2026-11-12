"""Tests for src/station_hedge.py (Ehfaz). Deterministic, no network."""

import math

import numpy as np
import pandas as pd
import pytest

from src.station_hedge import (
    contracts_for_notional,
    kalshi_fee,
    station_payout,
    station_premium,
)


# ---------- station_payout ----------

def test_equality_triggers():
    assert station_payout(90.0, 90, 800) == 800.0
    assert station_payout(89.9, 90, 800) == 0.0
    assert station_payout(91, 90, 800) == 800.0


def test_nan_in_nan_out_array():
    out = station_payout(np.array([95.0, np.nan, 80.0]), 90, 800)
    assert out[0] == 800.0
    assert math.isnan(out[1])
    assert out[2] == 0.0


def test_scalar_nan():
    assert math.isnan(station_payout(float("nan"), 90, 800))


def test_series_keeps_index_and_handles_none():
    s = pd.Series([90, None, 85], index=pd.to_datetime(["2022-07-01", "2022-07-02", "2022-07-03"]))
    out = station_payout(s, 90, 100)
    assert isinstance(out, pd.Series)
    assert list(out.index) == list(s.index)
    assert out.iloc[0] == 100.0 and math.isnan(out.iloc[1]) and out.iloc[2] == 0.0


def test_list_input_and_notional():
    out = station_payout([84, 85, 86], 85, 1.0)
    assert np.array_equal(out, np.array([0.0, 1.0, 1.0]))


def test_contracts_for_notional():
    assert contracts_for_notional(800) == 800
    with pytest.raises(ValueError):
        contracts_for_notional(800.5)


# ---------- kalshi_fee ----------

def test_fee_published_table_values():
    # Kalshi fee schedule table: 100 contracts at $0.50 -> $1.75; 1 at $0.50 -> $0.02.
    assert kalshi_fee(0.50, 100) == pytest.approx(1.75)
    assert kalshi_fee(0.50, 1) == pytest.approx(0.02)


def test_fee_rounds_up_not_nearest():
    # 0.07 * 1 * 0.10 * 0.90 = 0.0063 -> rounds UP to 0.01
    assert kalshi_fee(0.10, 1) == pytest.approx(0.01)
    # 0.07 * 10 * 0.30 * 0.70 = 0.147 -> 0.15
    assert kalshi_fee(0.30, 10) == pytest.approx(0.15)


def test_fee_exact_cent_not_bumped_by_float_noise():
    # 0.07 * 800 * 0.5 * 0.5 = 14.00 exactly; must not become 14.01
    assert kalshi_fee(0.50, 800) == pytest.approx(14.00)
    # 0.07 * 100 * 0.2 * 0.8 = 1.12 exactly
    assert kalshi_fee(0.20, 100) == pytest.approx(1.12)


def test_fee_centicent_option():
    assert kalshi_fee(0.10, 1, rounding_unit=0.0001) == pytest.approx(0.0063)


def test_fee_maker_rate():
    # 0.0175 * 100 * 0.5 * 0.5 = 0.4375 -> 0.44
    assert kalshi_fee(0.50, 100, maker=True) == pytest.approx(0.44)


def test_fee_zero_at_extremes_and_zero_contracts():
    assert kalshi_fee(0.0, 100) == 0.0
    assert kalshi_fee(1.0, 100) == 0.0
    assert kalshi_fee(0.5, 0) == 0.0


def test_fee_vectorized_and_nan():
    out = kalshi_fee(np.array([0.5, np.nan, 0.1]), 100)
    assert out[0] == pytest.approx(1.75)
    assert math.isnan(out[1])
    assert out[2] == pytest.approx(0.63)


def test_fee_rejects_bad_price():
    with pytest.raises(ValueError):
        kalshi_fee(1.5, 1)


# ---------- station_premium ----------

def test_premium_fair_and_markup():
    assert station_premium(0.10, 800, 0.0) == pytest.approx(80.0)
    assert station_premium(0.10, 800, 0.25) == pytest.approx(100.0)


def test_premium_capped_at_one_dollar_per_contract():
    assert station_premium(0.9, 800, 0.5) == pytest.approx(800.0)


def test_premium_with_fee():
    # price 0.10, 800 contracts: fee = ceil(0.07*800*0.1*0.9 = 5.04) = 5.04
    assert station_premium(0.10, 800, 0.0, include_fee=True) == pytest.approx(85.04)


def test_premium_nan_and_series():
    s = pd.Series([0.1, np.nan])
    out = station_premium(s, 100, 0.0)
    assert isinstance(out, pd.Series)
    assert out.iloc[0] == pytest.approx(10.0)
    assert math.isnan(out.iloc[1])


def test_premium_rejects_bad_prob():
    with pytest.raises(ValueError):
        station_premium(1.2, 800, 0.0)
