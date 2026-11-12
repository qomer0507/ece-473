"""Kalshi rain quotes: carry-forward, staleness, one-sided books, fee rounding, calibration bins."""
import math

import pytest

from src.kalshi.rain_quotes import (brier, calibration_table, candle_quotes, market_row, quote_at, side_close,
                                    taker_fee, taker_fee_per_contract)

CLOSE = 1_000_000 * 3600  # an exact hour, in seconds
H = 3600


def q(hours_before_close, bid, ask):
    return (CLOSE - int(hours_before_close * H), bid, ask)


# ---- carry-forward and staleness
def test_carry_forward_uses_last_candle_at_or_before_decision_time():
    quotes = [q(30, 0.40, 0.44), q(26, 0.50, 0.54), q(23, 0.70, 0.74)]
    r = quote_at(quotes, CLOSE, 24)
    assert (r["bid"], r["ask"]) == (0.50, 0.54)
    assert r["age_hours"] == pytest.approx(2.0)
    assert r["has_quote"] and not r["stale"] and r["buyable"] and r["two_sided"]
    assert r["spread"] == pytest.approx(0.04) and r["mid"] == pytest.approx(0.52)


def test_candle_ending_after_decision_time_is_never_used():
    r = quote_at([q(23.99, 0.70, 0.74)], CLOSE, 24)
    assert not r["has_quote"] and r["ask"] is None and not r["buyable"]


def test_candle_ending_exactly_at_decision_time_is_used():
    r = quote_at([q(24, 0.30, 0.33)], CLOSE, 24)
    assert r["has_quote"] and r["age_hours"] == 0 and r["ask"] == 0.33


def test_stale_boundary_six_hours():
    fresh = quote_at([q(30, 0.30, 0.33)], CLOSE, 24)       # exactly 6 h old: still usable
    stale = quote_at([q(30.5, 0.30, 0.33)], CLOSE, 24)     # 6.5 h old: stale
    assert fresh["age_hours"] == pytest.approx(6.0) and not fresh["stale"] and fresh["two_sided"]
    assert stale["has_quote"] and stale["stale"] and not stale["buyable"] and not stale["two_sided"]
    assert stale["spread"] is None and stale["mid"] is None


def test_candles_without_both_sides_are_skipped_when_carrying():
    r = quote_at([q(27, 0.20, 0.25), q(25, None, 0.30)], CLOSE, 24)
    assert (r["bid"], r["ask"]) == (0.20, 0.25) and r["age_hours"] == pytest.approx(3.0)


def test_each_decision_time_gets_its_own_quote():
    quotes = [q(37, 0.10, 0.15), q(25, 0.20, 0.25), q(13, 0.60, 0.65), q(3, 0.90, 0.95)]
    got = [quote_at(quotes, CLOSE, h)["ask"] for h in (36, 24, 12, 2)]
    assert got == [0.15, 0.25, 0.65, 0.95]


# ---- one-sided books
def test_ask_of_one_dollar_is_not_buyable():
    r = quote_at([q(25, 0.60, 1.00)], CLOSE, 24)
    assert r["has_quote"] and r["ask_is_1"] and not r["buyable"] and not r["two_sided"] and r["mid"] is None


def test_bid_of_zero_is_buyable_but_not_two_sided():
    r = quote_at([q(25, 0.00, 0.22)], CLOSE, 24)
    assert r["bid_is_0"] and r["buyable"] and not r["two_sided"] and r["spread"] is None


def test_empty_book_both_flags():
    r = quote_at([q(25, 0.00, 1.00)], CLOSE, 24)
    assert r["ask_is_1"] and r["bid_is_0"] and not r["buyable"]


# ---- candle parsing and the market row
def test_side_close_formats():
    assert side_close({"close": "0.5500"}) == 0.55
    assert side_close({"close_dollars": "0.07"}) == 0.07
    assert side_close({"close": 55}) == 0.55          # integer cents
    assert side_close({"close": None}) is None and side_close(None) is None


def test_market_row_end_to_end():
    m = {"_series": "KXRAIN", "_city": "TTN", "_date": "2026-09-02", "_group": "KXRAIN-TTN-2026",
         "ticker": "X", "result": "yes", "open_time": "2026-09-01T09:00:00Z", "close_time": "2026-09-03T04:00:00Z"}
    from src.kalshi.client import parse_ts
    close = parse_ts(m["close_time"])
    candles = [{"end_period_ts": close - 25 * H, "yes_bid": {"close": "0.3000"}, "yes_ask": {"close": "0.3400"}},
               {"end_period_ts": close - 40 * H, "yes_bid": {"close": "0.0000"}, "yes_ask": {"close": "1.0000"}}]
    assert [t for t, _, _ in candle_quotes(candles)] == sorted(t for t, _, _ in candle_quotes(candles))
    r = market_row(m, candles)
    assert r["result"] == 1 and r["pulled"] and r["n_candles"] == 2 and r["life_hours"] == 43.0
    assert r["ask_24"] == 0.34 and r["two_sided_24"] and r["spread_24"] == pytest.approx(0.04)
    assert r["has_quote_36"] and r["ask_is_1_36"] and not r["buyable_36"]
    assert r["stale_12"] and not r["buyable_12"]          # 13 h old at the 12-hour time
    assert market_row(m, None)["pulled"] is False


# ---- fee
@pytest.mark.parametrize("price,contracts,fee", [
    (0.50, 1, 0.02),      # 1.75 cents rounds up to 2 (fee schedule table)
    (0.50, 100, 1.75),    # exact, must not round up to 1.76
    (0.10, 800, 5.04),    # worked example in docs/contract_spec.md
    (0.50, 800, 14.00),
    (0.30, 1, 0.02),      # 1.47 cents -> 2
    (0.05, 1, 0.01),      # 0.3325 cents -> 1
    (0.99, 1, 0.01),
    (0.0, 5, 0.0), (1.0, 5, 0.0),
])
def test_fee_rounding(price, contracts, fee):
    assert taker_fee(price, contracts) == pytest.approx(fee, abs=1e-9)


def test_fee_properties():
    for c in (1, 3, 100):
        for i in range(1, 100):
            p = i / 100
            f = taker_fee(p, c)
            exact = 0.07 * c * p * (1 - p)
            assert exact - 1e-9 <= f < exact + 0.01 + 1e-9       # rounded up, by less than a cent
            assert abs(f * 100 - round(f * 100)) < 1e-9           # whole cents
            assert taker_fee(1 - p, c) == pytest.approx(f)        # symmetric
    assert taker_fee_per_contract(0.5, 100) == pytest.approx(0.0175)
    with pytest.raises(ValueError):
        taker_fee(1.2)


# ---- calibration bins
def test_calibration_hand_made_example():
    prices = [0.05, 0.25, 0.29, 0.30, 0.35, 0.90, 1.00]
    result = [0,    0,    1,    1,    0,    1,    1]
    t = calibration_table(prices, result)
    assert len(t) == 10 and sum(b["n"] for b in t) == 7
    b0, b2, b3, b9 = t[0], t[2], t[3], t[9]
    assert (b0["n"], b0["yes_share"]) == (1, 0.0)
    assert b2["n"] == 2 and b2["mean_price"] == pytest.approx(0.27) and b2["yes_share"] == 0.5
    assert b3["n"] == 2 and b3["mean_price"] == pytest.approx(0.325) and b3["yes_share"] == 0.5   # 0.30 opens the bin
    assert b9["n"] == 2 and b9["yes_share"] == 1.0                                               # 1.00 is in the last bin
    assert t[5]["n"] == 0 and t[5]["yes_share"] is None and t[5]["mean_price"] is None


def test_calibration_edge_values_and_errors():
    t = calibration_table([0.1, 0.2, 0.7], [1, 0, 1])          # floating edges land in the upper bin
    assert [b["n"] for b in t] == [0, 1, 1, 0, 0, 0, 0, 1, 0, 0]
    with pytest.raises(ValueError):
        calibration_table([0.5], [1, 0])
    with pytest.raises(ValueError):
        calibration_table([1.5], [1])
    with pytest.raises(ValueError):
        calibration_table([float("nan")], [1])


def test_brier():
    assert brier([0.3, 0.3], [1, 0]) == pytest.approx((0.49 + 0.09) / 2)
    assert brier([1.0, 0.0], [1, 0]) == 0.0
    assert math.isnan(brier([], []))
