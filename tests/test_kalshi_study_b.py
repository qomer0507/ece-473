"""Tests for src/kalshi/study_b.py and client helpers. Synthetic inputs only; no network, no Kalshi data."""
from datetime import date

import pytest

from src.kalshi.client import event_date_from_ticker, parse_ts
from src.kalshi.study_b import (Bracket, Quote, Replication, achievable_thresholds, bounds_from_rules,
                                bracket_bounds, bracket_from_market, hedge_day, nearest_threshold,
                                price_replication, quote_at, replication_error, replications,
                                taker_fee_cents, to_cents, year_block_bootstrap)


# ---------------- bracket semantics ----------------
def test_between_is_inclusive_both_ends():
    lo, hi = bracket_bounds("between", 89, 90)
    b = Bracket("B", lo, hi)
    assert [b.pays(t) for t in (88, 89, 90, 91)] == [False, True, True, False]


def test_greater_means_floor_plus_one():
    lo, hi = bracket_bounds("greater", floor_strike=90)
    assert (lo, hi) == (91, None)
    b = Bracket("T", lo, hi)
    assert not b.pays(90) and b.pays(91) and b.pays(120)


def test_less_means_cap_minus_one():
    lo, hi = bracket_bounds("less", cap_strike=85)
    assert (lo, hi) == (None, 84)
    b = Bracket("T", lo, hi)
    assert b.pays(84) and not b.pays(85) and b.pays(-10)


def test_float_strikes_and_bad_inputs():
    assert bracket_bounds("between", 41.0, 42.0) == (41, 42)
    with pytest.raises(ValueError):
        bracket_bounds("between", 41.5, 42.5)
    with pytest.raises(ValueError):
        bracket_bounds("between", 43, 42)
    with pytest.raises(ValueError):
        bracket_bounds("sideways", 1, 2)


@pytest.mark.parametrize("text,expected", [
    ("If the highest temperature recorded in Central Park, New York on August 8, 2021 is strictly greater than 77°F, then", (78, None)),
    ("for July 15, 2022 as reported by the NWS, is between 85-86°, then the market resolves to Yes.", (85, 86)),
    ("for Jul 15, 2022, is less than 85°, then the market", (None, 84)),
    ("for July 24, 2022 as reported, is above 95°, then", (96, None)),
    ("at Newark (CLIEWR) for Nov 8, 2026, is between 63-64° fahrenheit according to", (63, 64)),
    ("for Jan 15, 2025, is strictly less than 30°, then", (None, 29)),
])
def test_bounds_from_rules_text(text, expected):
    assert bounds_from_rules(text) == expected


def test_bounds_from_rules_unparseable():
    with pytest.raises(ValueError):
        bounds_from_rules("Will it be hot?")


def test_bracket_from_market_prefers_strike_fields_then_rules():
    m = {"ticker": "X-T90", "strike_type": "greater", "floor_strike": 90, "rules_primary": "is greater than 50°"}
    assert bracket_from_market(m) == Bracket("X-T90", 91, None)
    m2 = {"ticker": "X-B85.5", "rules_primary": "is between 85-86°, then"}
    assert bracket_from_market(m2) == Bracket("X-B85.5", 85, 86)


def test_event_date_and_ts_parsing():
    assert event_date_from_ticker("KXHIGHNY-26AUG14") == date(2026, 8, 14)
    assert event_date_from_ticker("HIGHNY-21AUG06") == date(2021, 8, 6)
    with pytest.raises(ValueError):
        event_date_from_ticker("KXHIGHNY-BAD")
    assert parse_ts("1970-01-02T00:00:00Z") == 86400


# ---------------- ladder -> threshold replication ----------------
def ladder_even():
    """<=85 | 86-87 | 88-89 | 90-91 | 92-93 | >=94 : boundary at 90."""
    return [Bracket("L", None, 85), Bracket("B86", 86, 87), Bracket("B88", 88, 89),
            Bracket("B90", 90, 91), Bracket("B92", 92, 93), Bracket("H", 94, None)]


def ladder_odd():
    """<=84 | 85-86 | 87-88 | 89-90 | 91-92 | >=93 : 90 is inside a bracket."""
    return [Bracket("L", None, 84), Bracket("B85", 85, 86), Bracket("B87", 87, 88),
            Bracket("B89", 89, 90), Bracket("B91", 91, 92), Bracket("H", 93, None)]


def test_exact_replication_both_routes():
    reps = [r for r in replications(ladder_even()) if r.threshold == 90]
    assert Replication(90, "yes", ("B90", "B92", "H")) in reps
    assert Replication(90, "no", ("B88", "B86", "L")) in reps
    assert len(reps) == 2


def test_replication_payout_is_the_indicator():
    br = {b.ticker: b for b in ladder_even()}
    for r in replications(ladder_even()):
        for t in range(70, 110):
            hits = sum(br[x].pays(t) for x in r.tickers)
            if r.side == "yes":
                payoff = hits
            else:  # NO legs pay 1 each unless hit; subtract the sure constant n-1
                payoff = (len(r.tickers) - hits) - (len(r.tickers) - 1)
            assert payoff == int(t >= r.threshold)


def test_achievable_thresholds():
    assert achievable_thresholds(ladder_even()) == [86, 88, 90, 92, 94]
    assert achievable_thresholds(ladder_odd()) == [85, 87, 89, 91, 93]
    assert achievable_thresholds([]) == []


def test_single_threshold_markets():
    # old-style day: one "greater than 89" market; top tail alone gives >= 90 exactly
    assert achievable_thresholds([Bracket("T89", 90, None)]) == [90]
    # bottom tail alone: NO on "<= 89" also gives >= 90
    r = replications([Bracket("T90", None, 89)])
    assert r == [Replication(90, "no", ("T90",))]


def test_gap_in_ladder_blocks_chain():
    br = [Bracket("B88", 88, 89), Bracket("H", 94, None)]  # nothing covers 90..93
    assert achievable_thresholds(br) == [94]


def test_nearest_threshold_and_tie_goes_low():
    assert nearest_threshold([85, 87, 89, 91, 93], 90) == 89
    assert nearest_threshold([86, 88, 90], 90) == 90
    assert nearest_threshold([70, 72], 90) == 72
    assert nearest_threshold([], 90) is None


def q(ask, bid=None, age=0):
    return Quote(ask, bid, age)


def test_hedge_day_exact_picks_cheapest_route():
    quotes = {"L": q(60, 55), "B86": q(15, 12), "B88": q(12, 9), "B90": q(8, 5), "B92": q(4, 2), "H": q(3, 1)}
    h = hedge_day(ladder_even(), quotes, 90, contracts=100)
    assert h.status == "exact" and h.k_achieved == 90 and h.strike_gap == 0 and h.quoted
    # YES route: 8 + 4 + 3 = 15c + fees ceil(7*.08*.92*100)=52c, ceil(26.88)=27c, ceil(20.37)=21c -> 1.00c/contract
    assert h.priced.rep.side == "yes"
    assert h.priced.premium_per_dollar == pytest.approx(0.15)
    assert h.priced.fee_per_dollar == pytest.approx((52 + 27 + 21) / 10000)
    # NO route would be 1 - (55 + 12 + 9)/100 = 0.24 before fees: dearer
    yes_only = hedge_day(ladder_even(), quotes, 90, contracts=100, allow_no=False)
    assert yes_only.priced.cost_per_dollar == h.priced.cost_per_dollar


def test_hedge_day_no_route_when_cheaper():
    quotes = {"L": q(90, 88), "B86": q(5, 3), "B88": q(4, 2), "B90": q(6, 1), "B92": q(5, 1), "H": q(5, 1)}
    h = hedge_day(ladder_even(), quotes, 90, contracts=100)
    assert h.priced.rep.side == "no"
    # 3 NO legs at 12, 97, 98 cents; constant 2 dollars comes back: net premium = 3.07 - 2 = 0.07
    assert h.priced.premium_per_dollar == pytest.approx(0.07)


def test_hedge_day_inexact_records_nearest_and_gap():
    quotes = {b.ticker: q(10, 5) for b in ladder_odd()}
    h = hedge_day(ladder_odd(), quotes, 90)
    assert h.status == "inexact" and h.k_achieved == 89 and h.strike_gap == -1
    assert replication_error(89, 90, 89) == 1     # hedge pays, target does not
    assert replication_error(90, 90, 89) == 0
    assert replication_error(88, 90, 89) == 0
    assert replication_error(90, 90, 91) == -1    # shortfall


def test_hedge_day_cool_day_far_threshold():
    br = [Bracket("L", None, 71), Bracket("B72", 72, 73), Bracket("H", 74, None)]
    h = hedge_day(br, {}, 90)
    assert h.status == "inexact" and h.k_achieved == 74 and h.strike_gap == -16 and not h.quoted


# ---------------- no-quote handling ----------------
def test_no_quote_when_a_leg_is_missing():
    quotes = {"B90": q(8, 5), "B92": q(4, 2), "H": None, "L": None, "B86": q(15, 12), "B88": q(12, 9)}
    h = hedge_day(ladder_even(), quotes, 90)
    assert h.status == "exact" and h.priced is None and not h.quoted


def test_no_quote_when_ask_side_empty_but_no_route_can_still_price():
    quotes = {"B90": q(None, 5), "B92": q(4, 2), "H": q(3, 1), "L": q(60, 55), "B86": q(15, 12), "B88": q(12, 9)}
    assert hedge_day(ladder_even(), quotes, 90, allow_no=False).priced is None
    h = hedge_day(ladder_even(), quotes, 90, allow_no=True)
    assert h.priced is not None and h.priced.rep.side == "no"


def test_no_leg_needs_a_bid():
    rep = Replication(90, "no", ("L",))
    assert price_replication(rep, {"L": q(60, None)}) is None
    assert price_replication(rep, {}) is None


def test_no_ladder():
    h = hedge_day([], {}, 90)
    assert h.status == "no_ladder" and h.k_achieved is None and h.strike_gap is None


# ---------------- fee rounding ----------------
def test_fee_matches_published_examples():
    assert taker_fee_cents(50, 1) == 2          # 0.07*0.25 = 1.75c -> 2c
    assert taker_fee_cents(50, 100) == 175      # exactly $1.75, no rounding
    assert taker_fee_cents(10, 800) == 504      # contract_spec.md worked example: $5.04
    assert taker_fee_cents(50, 800) == 1400     # $14.00


def test_fee_rounds_up_to_next_cent():
    assert taker_fee_cents(5, 1) == 1           # 0.3325c -> 1c
    assert taker_fee_cents(5, 100) == 34        # 33.25c -> 34c
    assert taker_fee_cents(1, 1) == 1           # 0.0693c -> 1c
    assert taker_fee_cents(99, 1) == 1
    assert taker_fee_cents(20, 25) == 28        # exactly 28c: must not round to 29


def test_fee_edges():
    assert taker_fee_cents(0, 10) == 0 and taker_fee_cents(100, 10) == 0 and taker_fee_cents(50, 0) == 0
    with pytest.raises(ValueError):
        taker_fee_cents(101, 1)
    with pytest.raises(ValueError):
        taker_fee_cents(50, -1)


def test_fee_symmetric_in_price():
    for p in range(1, 100):
        assert taker_fee_cents(p, 37) == taker_fee_cents(100 - p, 37)


def test_price_replication_adds_fee_per_leg():
    rep = Replication(90, "yes", ("A", "B"))
    p = price_replication(rep, {"A": q(5), "B": q(5)}, contracts=1)
    assert p.premium_per_dollar == pytest.approx(0.10)
    assert p.fee_per_dollar == pytest.approx(0.02)       # 1c per leg after rounding up
    assert p.cost_per_dollar == pytest.approx(0.12)
    p100 = price_replication(rep, {"A": q(5), "B": q(5)}, contracts=100)
    assert p100.fee_per_dollar == pytest.approx(0.0068)  # 34c per leg per 100 contracts


def test_to_cents():
    assert to_cents("0.2200") == 22 and to_cents(0.07) == 7 and to_cents(None) is None
    assert to_cents(float("nan")) is None


# ---------------- staleness rule ----------------
CLOSE = 1_000_000_000
T0 = CLOSE - 24 * 3600


def candle(end, ask="0.2000", bid="0.1800"):
    return {"end_period_ts": end, "yes_ask": {"close": ask}, "yes_bid": {"close": bid}}


def test_quote_uses_latest_candle_at_or_before_decision_time():
    cs = [candle(T0 - 7200, "0.30"), candle(T0 - 600, "0.25"), candle(T0 + 3000, "0.10")]
    qt = quote_at(cs, CLOSE)
    assert qt.ask_c == 25 and qt.bid_c == 18 and qt.age_s == 600


def test_candle_exactly_at_decision_time_is_used():
    assert quote_at([candle(T0, "0.40")], CLOSE).age_s == 0


def test_six_hour_staleness_boundary():
    assert quote_at([candle(T0 - 6 * 3600)], CLOSE) is not None        # exactly 6 h: allowed
    assert quote_at([candle(T0 - 6 * 3600 - 1)], CLOSE) is None        # one second more: stale
    assert quote_at([candle(T0 + 1)], CLOSE) is None                   # only future candles: no look-ahead
    assert quote_at([], CLOSE) is None


def test_empty_book_sides_are_not_quotes():
    qt = quote_at([candle(T0 - 60, "1.0000", "0.0000")], CLOSE)
    assert qt is not None and qt.ask_c is None and qt.bid_c is None
    qt = quote_at([candle(T0 - 60, "0.9900", "0.0000")], CLOSE)
    assert qt.ask_c == 99 and qt.bid_c is None
    qt = quote_at([{"end_period_ts": T0 - 60, "yes_ask": {"close": None}, "yes_bid": None}], CLOSE)
    assert qt.ask_c is None and qt.bid_c is None


def test_live_tier_candle_keys():
    c = {"end_period_ts": T0 - 60, "yes_ask": {"close_dollars": "0.4200"}, "yes_bid": {"close_dollars": "0.3500"}}
    qt = quote_at([c], CLOSE)
    assert (qt.ask_c, qt.bid_c) == (42, 35)


# ---------------- bootstrap ----------------
def test_year_block_bootstrap_is_seeded_and_bounded():
    vals = {2023: 1.0, 2024: 2.0, 2025: 4.0}
    stat = lambda ys: sum(vals[y] for y in ys) / len(ys)  # noqa: E731
    a = year_block_bootstrap(list(vals), stat)
    b = year_block_bootstrap(list(vals), stat)
    assert a == b and 1.0 <= a[0] <= a[1] <= 4.0


def test_year_block_bootstrap_one_year_gives_nan():
    lo, hi = year_block_bootstrap([2026], lambda ys: 1.0)
    assert lo != lo and hi != hi
