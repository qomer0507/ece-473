"""Hand-checked tests for src/panel/hedge.py (SPEC_v2 definitions). All data here is synthetic test input."""
import math

import numpy as np
import pandas as pd
import pytest

from src.panel import hedge as H

NAN = float("nan")


def stations3():
    # A at origin; S1 about 11 km east; S2 about 111 km north.
    return pd.DataFrame({"id": ["A", "S1", "S2"], "lat": [40.0, 40.0, 41.0], "lon": [-75.0, -74.87, -75.0]})


def wide(cols, dates):
    return pd.DataFrame(cols, index=pd.to_datetime(dates))


# ---------------------------------------------------------------- metrics
def test_metrics_hand_case():
    # day:   1   2   3   4   5   6
    loc = [91, 89, 90, 95, 80, 92]
    ref = [90, 90, 89, 96, 70, 85]
    # H:     1   0   1   1   0   1      P (k=90): 1 1 0 1 0 0
    # FN days: 3, 6 -> 2.   FP days: 2 -> 1.   hot = 4, pay = 3, n = 6.
    m = H.mismatch_metrics(loc, ref, strike=90)
    assert (m["n"], m["n_hot"], m["n_pay"], m["fn_days"], m["fp_days"]) == (6, 4, 3, 2, 1)
    assert m["R"] == pytest.approx(3 / 6)
    assert m["FN"] == pytest.approx(2 / 6)
    assert m["FP"] == pytest.approx(1 / 6)
    assert m["miss_rate"] == pytest.approx(2 / 4)
    assert m["false_payout_rate"] == pytest.approx(1 / 3)
    assert m["R"] == pytest.approx(m["FN"] + m["FP"])


def test_threshold_and_strike_equality_count_as_events():
    # exactly 90 is a heat event; exactly k pays; one below does neither.
    m = H.mismatch_metrics([90, 89], [90, 89], strike=90)
    assert (m["n_hot"], m["n_pay"], m["fn_days"], m["fp_days"]) == (1, 1, 0, 0)
    m = H.mismatch_metrics([90, 90], [87, 86], strike=87)
    assert (m["n_pay"], m["fn_days"]) == (1, 1)  # 87 >= 87 pays, 86 does not
    m = H.mismatch_metrics([89, 89], [93, 92], strike=93)
    assert (m["n_pay"], m["fp_days"]) == (1, 1)


def test_missing_days_are_dropped_not_filled():
    loc = [95, NAN, 95, 70, NAN]
    ref = [95, 95, NAN, 70, NAN]
    m = H.mismatch_metrics(loc, ref)
    assert m["n"] == 2 and m["n_hot"] == 1 and m["n_pay"] == 1 and m["R"] == 0.0


def test_undefined_ratios_are_nan():
    m = H.mismatch_metrics([70, 71], [70, 71])
    assert m["R"] == 0.0 and math.isnan(m["miss_rate"]) and math.isnan(m["false_payout_rate"])
    m = H.mismatch_metrics([NAN], [NAN])
    assert m["n"] == 0 and math.isnan(m["R"])


def test_length_mismatch_raises():
    with pytest.raises(ValueError):
        H.mismatch_counts([1, 2], [1])


# ---------------------------------------------------------------- helpers
def test_season_and_window_masks():
    d = ["2019-04-30", "2019-05-01", "2019-09-30", "2019-10-01", "2020-07-01", "2023-07-01"]
    assert H.season_mask(d).tolist() == [False, True, True, False, True, True]
    assert H.window_mask(d, "FIT").tolist() == [True, True, True, True, False, False]
    assert H.window_mask(d, "SELECT").tolist() == [False] * 4 + [True, False]
    assert H.window_mask(d, "REPORT").tolist() == [False] * 5 + [True]
    assert H.WINDOWS == {"FIT": (2015, 2019), "SELECT": (2020, 2022), "REPORT": (2023, 2025)}


def test_haversine_known_values():
    assert H.haversine_km(40, -75, 40, -75) == pytest.approx(0.0)
    assert H.haversine_km(40, -75, 41, -75) == pytest.approx(111.195, abs=0.01)  # one degree of latitude
    # Central Park to Newark: about 19.9 km (manifest value 19.96 uses slightly different coordinates)
    assert H.haversine_km(40.77898, -73.96925, 40.68275, -74.16927) == pytest.approx(19.96, abs=0.1)


def test_to_wide_keeps_gaps_and_drops_off_season():
    long = pd.DataFrame({"date": ["2019-07-01", "2019-07-02", "2019-07-02", "2019-12-25"],
                         "id": ["A", "A", "B", "A"], "tmax_f": [90.0, 91.0, 80.0, 30.0]})
    w = H.to_wide(long)
    assert list(w.index.strftime("%Y-%m-%d")) == ["2019-07-01", "2019-07-02"]
    assert math.isnan(w.loc["2019-07-01", "B"]) and w.loc["2019-07-02", "B"] == 80.0
    with pytest.raises(ValueError):
        H.to_wide(pd.concat([long, long.iloc[:1]]))


# ---------------------------------------------------------------- hedges
def test_baseline_is_nearest_station_at_90():
    st = stations3()
    b = H.baseline_hedge("A", ["S2", "S1"], st)
    assert (b.station, b.strike, b.kind) == ("S1", 90, "baseline")
    assert b.dist_km == pytest.approx(H.haversine_km(40, -75, 40, -74.87))
    assert H.baseline_hedge("A", ["S2"], st).station == "S2"
    assert H.baseline_hedge("S1", ["S2", "S1"], st).dist_km == 0.0


def test_adjusted_picks_lowest_fit_mismatch_strike():
    # S1 reads exactly 3 F below A. A's 90 F event is S1 >= 87. Strike 87 gives zero FIT mismatch.
    d = pd.date_range("2016-07-01", periods=8)
    a = np.array([85, 88, 89, 90, 91, 93, 95, 70.0])
    w = wide({"A": a, "S1": a - 3, "S2": a + 20}, d)
    h = H.adjusted_hedge("A", ["S1", "S2"], w, stations3())
    assert (h.station, h.strike, h.fit_R, h.fit_n) == ("S1", 87, 0.0, 8)
    # baseline (k = 90 on S1) misses days with A in 90..92: values 90, 91 -> 2 of 8
    assert H.evaluate_hedge(w, "A", H.baseline_hedge("A", ["S1", "S2"], stations3()), "FIT")["R"] == pytest.approx(2 / 8)


def test_adjusted_tie_goes_to_strike_closest_to_90():
    # A hot on 2 of 4 days. S1 = [80, 80, 95, 95]: every strike 81..95 separates perfectly (R = 0).
    d = pd.date_range("2016-07-01", periods=4)
    w = wide({"A": [70, 70, 95, 95.0], "S1": [80, 80, 95, 95.0], "S2": [0, 0, 0, 0.0]}, d)
    h = H.adjusted_hedge("A", ["S1", "S2"], w, stations3())
    assert (h.station, h.strike, h.fit_R) == ("S1", 90, 0.0)
    # S1 = [80, 80, 86, 86]: strikes 81..86 give R = 0; closest to 90 is 86.
    w["S1"] = [80, 80, 86, 86.0]
    assert H.adjusted_hedge("A", ["S1", "S2"], w, stations3()).strike == 86


def test_adjusted_tie_then_goes_to_nearest_station():
    d = pd.date_range("2016-07-01", periods=4)
    same = [80, 80, 95, 95.0]
    w = wide({"A": [70, 70, 95, 95.0], "S1": same, "S2": same}, d)
    for order in (["S1", "S2"], ["S2", "S1"]):
        h = H.adjusted_hedge("A", order, w, stations3())
        assert (h.station, h.strike) == ("S1", 90)  # S1 is 11 km away, S2 is 111 km away


def test_adjusted_prefers_lower_mismatch_over_distance_and_strike():
    # Near station S1 is useless (constant). Far station S2 at strike 95 is perfect.
    d = pd.date_range("2016-07-01", periods=4)
    w = wide({"A": [70, 89, 90, 95.0], "S1": [85, 85, 85, 85.0], "S2": [80, 94, 95, 99.0]}, d)
    h = H.adjusted_hedge("A", ["S1", "S2"], w, stations3())
    assert (h.station, h.strike, h.fit_R) == ("S2", 95, 0.0)


def test_adjusted_symmetric_strike_tie_takes_lower_strike():
    # A never hot. S1 always 50: every strike gives R = 0... closest to 90 is 90 itself.
    # To force an 89-vs-91 tie: A hot on day 1 only; S1 = [90, 89]. k=90: R=0. So build a real tie instead:
    # A = [hot, cold, cold], S1 = [89, 91, 70]. k=89: P=[1,1,0] R=1/3. k=90: P=[0,1,0] R=2/3. k=91: same 2/3.
    # k=92: P=[0,0,0] R=1/3. Best R=1/3 at k in {71..89} and {92..100}; closest to 90 is 89 (distance 1).
    d = pd.date_range("2016-07-01", periods=3)
    w = wide({"A": [95, 70, 70.0], "S1": [89, 91, 70.0], "S2": [NAN, NAN, NAN]}, d)
    assert H.adjusted_hedge("A", ["S1", "S2"], w, stations3()).strike == 89
    # exact 88-vs-92 tie: S1 = [88, 91, 70]: k<=88 R=1/3 ; k=89,90,91 R=2/3 ; k>=92 R=1/3 -> 88 and 92 tie, lower wins
    w["S1"] = [88, 91, 70.0]
    assert H.adjusted_hedge("A", ["S1", "S2"], w, stations3()).strike == 88


def test_adjusted_skips_station_with_no_fit_overlap_and_falls_back():
    d = pd.date_range("2016-07-01", periods=3)
    w = wide({"A": [95, 70, 70.0], "S1": [NAN] * 3, "S2": [95, 70, 70.0]}, d)
    assert H.adjusted_hedge("A", ["S1", "S2"], w, stations3()).station == "S2"
    w["S2"] = [NAN] * 3
    h = H.adjusted_hedge("A", ["S1", "S2"], w, stations3())
    assert (h.station, h.strike, h.kind, h.fit_n) == ("S1", 90, "adjusted", 0)


def test_strikes_limited_to_80_100():
    assert H.STRIKES == tuple(range(80, 101))
    # A's event lines up with S1 >= 70, outside the strike range: the best allowed strike is 80.
    d = pd.date_range("2016-07-01", periods=4)
    w = wide({"A": [95, 95, 60, 60.0], "S1": [75, 72, 65, 60.0], "S2": [NAN] * 4}, d)
    h = H.adjusted_hedge("A", ["S1", "S2"], w, stations3())
    assert h.strike == 90 and h.fit_R == pytest.approx(0.5)  # all strikes tie at 2/4, so 90


# ---------------------------------------------------------------- window separation
def leak_panel():
    """FIT: S1 = A - 3 exactly. SELECT and REPORT: relation reversed (S1 = A + 5)."""
    parts = []
    for y in range(2015, 2026):
        d = pd.date_range(f"{y}-07-01", periods=6)
        a = np.array([84, 88, 90, 92, 96, 70.0])
        s1 = a - 3 if y <= 2019 else a + 5
        parts.append(wide({"A": a, "S1": s1, "S2": a * 0 + 50}, d))
    return pd.concat(parts)


def test_adjusted_hedge_uses_fit_years_only():
    w = leak_panel()
    st = stations3()
    h = H.adjusted_hedge("A", ["S1", "S2"], w, st)
    assert (h.station, h.strike, h.fit_n) == ("S1", 87, 5 * 6)
    # Changing or deleting everything after 2019 must not change the fitted hedge.
    w2 = w.copy()
    w2.loc[w2.index.year >= 2020, :] = 999.0
    w3 = w[w.index.year <= 2019]
    w4 = w.copy()
    w4.loc[w4.index.year >= 2020, :] = np.nan
    for other in (w2, w3, w4):
        assert H.adjusted_hedge("A", ["S1", "S2"], other, st) == h
    # A hedge fitted on SELECT instead would be different, so the test has power. There S1 = A + 5 =
    # [89, 93, 95, 97, 101, 75]; strikes 94 and 95 both separate perfectly; 94 is closer to 90.
    assert H.adjusted_hedge("A", ["S1", "S2"], w, st, fit_window="SELECT").strike == 94


def test_evaluation_windows_do_not_mix_years():
    w = leak_panel()
    st = stations3()
    h = H.adjusted_hedge("A", ["S1", "S2"], w, st)
    fit = H.evaluate_hedge(w, "A", h, "FIT")
    sel = H.evaluate_hedge(w, "A", h, "SELECT")
    rep = H.evaluate_hedge(w, "A", h, "REPORT")
    assert (fit["n"], sel["n"], rep["n"]) == (30, 18, 18)
    assert fit["R"] == 0.0
    # After 2019: S1 = A + 5, strike 87 -> P = 1 when A >= 82: A in {84, 88} are false payouts: 2 of 6 days.
    assert sel["R"] == pytest.approx(2 / 6) and sel["fp_days"] == 6 and sel["fn_days"] == 0
    assert rep["false_payout_rate"] == pytest.approx(2 / 5)
    yc = H.yearly_counts(w, "A", h, "REPORT")
    assert list(yc.index) == [2023, 2024, 2025] and yc["n"].tolist() == [6, 6, 6]


def test_mismatch_under_listed_set_table():
    w = leak_panel()
    st = stations3()
    res, yearly = H.mismatch_under_listed_set(["S1", "S2"], w, st, location_ids=["A", "S1"], return_yearly=True)
    assert len(res) == 2 * 2 * 2  # locations x hedge kinds x windows
    assert set(res["window"]) == {"SELECT", "REPORT"}
    r = res.set_index(["location_id", "hedge", "window"])
    assert r.loc[("A", "baseline", "SELECT"), "hedge_station"] == "S1"
    assert r.loc[("A", "baseline", "SELECT"), "strike"] == 90
    # baseline after 2019: S1 = A + 5 >= 90 when A >= 85: A = 88 is a false payout: 1 of 6 days
    assert r.loc[("A", "baseline", "REPORT"), "R"] == pytest.approx(1 / 6)
    assert r.loc[("A", "adjusted", "REPORT"), "strike"] == 87
    assert r.loc[("A", "adjusted", "REPORT"), "R"] == pytest.approx(2 / 6)
    # a listed station hedges itself perfectly and is flagged
    assert r.loc[("S1", "adjusted", "REPORT"), "R"] == 0.0
    assert bool(r.loc[("S1", "baseline", "REPORT"), "in_listed_set"]) is True
    assert r.loc[("S1", "baseline", "REPORT"), "dist_km"] == 0.0
    assert set(yearly["year"]) == set(range(2020, 2026))
    with pytest.raises(KeyError):
        H.mismatch_under_listed_set(["S1", "NOPE"], w, st, location_ids=["A"])


def test_default_locations_use_is_exposure_column():
    w = leak_panel()
    st = stations3().assign(is_exposure=[True, False, False])
    res = H.mismatch_under_listed_set(["S1"], w, st)
    assert set(res["location_id"]) == {"A"}


def test_adding_a_station_cannot_raise_fit_mismatch():
    rng = np.random.default_rng(1)
    d = pd.date_range("2015-05-01", "2019-09-30")
    d = d[H.season_mask(d)]
    w = wide({"A": rng.integers(70, 100, len(d)).astype(float), "S1": rng.integers(70, 100, len(d)).astype(float),
              "S2": rng.integers(70, 100, len(d)).astype(float)}, d)
    one = H.adjusted_hedge("A", ["S1"], w, stations3())
    two = H.adjusted_hedge("A", ["S1", "S2"], w, stations3())
    assert two.fit_R <= one.fit_R
