"""PoP combination, lead matching and carry-forward (src/leadtime/mos_pop.py, hedge_by_lead.py)."""
import math

import numpy as np
import pandas as pd
import pytest

from src.leadtime.mos_pop import (calibration, close_time_utc, combine_independent, day_pop_by_run, pick_lead,
                                  pop_table)
from src.leadtime.hedge_by_lead import available_seasons, pop_with_carry_forward


def test_combine_independent_hand_values():
    assert combine_independent([0.0, 0.0]) == 0.0
    assert combine_independent([1.0, 0.3]) == pytest.approx(1.0)
    assert combine_independent([0.3, 0.4]) == pytest.approx(1 - 0.7 * 0.6)      # 0.58
    assert combine_independent([0.2, 0.2, 0.2, 0.2]) == pytest.approx(1 - 0.8 ** 4)
    assert combine_independent([0.5]) == 0.5


def test_combine_independent_is_at_least_the_max_and_rejects_bad_values():
    assert combine_independent([0.3, 0.6]) >= 0.6
    with pytest.raises(ValueError):
        combine_independent([1.2])


def test_close_time_is_midnight_local_end_of_day_in_utc():
    assert close_time_utc(pd.Timestamp("2025-07-01")) == pd.Timestamp("2025-07-02 04:00")   # EDT
    assert close_time_utc(pd.Timestamp("2025-01-10")) == pd.Timestamp("2025-01-11 05:00")   # EST


def _mos(rows):
    d = pd.DataFrame(rows, columns=["runtime", "ftime", "p06", "p12", "p24"])
    d["runtime"] = pd.to_datetime(d["runtime"])
    d["ftime"] = pd.to_datetime(d["ftime"])
    return d


def test_day_pop_by_run_forms_p12x2_p24_p06x4_with_the_right_windows():
    # target day 2025-07-10: p12 ending 12Z Jul 10 and 00Z Jul 11; p24 ending 00Z Jul 11;
    # p06 ending 12Z, 18Z Jul 10, 00Z, 06Z Jul 11
    rt = "2025-07-08 00:00"
    mos = _mos([
        (rt, "2025-07-10 06:00", 0.10, np.nan, np.nan),      # not in the p06 window (00Z-06Z)
        (rt, "2025-07-10 12:00", 0.20, 0.30, np.nan),
        (rt, "2025-07-10 18:00", 0.20, np.nan, np.nan),
        (rt, "2025-07-11 00:00", 0.20, 0.40, 0.55),
        (rt, "2025-07-11 06:00", 0.20, np.nan, np.nan),
    ])
    t = day_pop_by_run(mos, [pd.Timestamp("2025-07-10")])
    assert len(t) == 1
    r = t.iloc[0]
    assert r["pop_p12"] == pytest.approx(1 - 0.7 * 0.6)
    assert r["pop_p24"] == pytest.approx(0.55)
    assert r["pop"] == pytest.approx(0.55) and r["field"] == "p24"       # p24 wins when present
    assert r["pop_p06"] == pytest.approx(1 - 0.8 ** 4)
    # lead = close (04Z Jul 11) - run (00Z Jul 8) = 3 days + 4 h
    assert r["lead_days"] == pytest.approx(3 + 4 / 24)


def test_day_pop_by_run_falls_back_to_p12x2_and_skips_runs_without_fields():
    mos = _mos([
        ("2025-07-09 00:00", "2025-07-10 12:00", np.nan, 0.5, np.nan),
        ("2025-07-09 00:00", "2025-07-11 00:00", np.nan, 0.5, np.nan),
        ("2025-07-09 12:00", "2025-07-11 00:00", np.nan, 0.9, np.nan),   # no 12Z value: cannot price the day
    ])
    t = day_pop_by_run(mos, [pd.Timestamp("2025-07-10")])
    assert list(t["runtime"]) == [pd.Timestamp("2025-07-09 00:00")]
    assert t.iloc[0]["field"] == "p12x2" and t.iloc[0]["pop"] == pytest.approx(0.75)


def test_pick_lead_takes_the_closest_run_and_breaks_ties_to_the_earlier_run():
    by_run = pd.DataFrame({
        "date": [pd.Timestamp("2025-07-10")] * 4,
        "runtime": pd.to_datetime(["2025-07-08 00:00", "2025-07-08 12:00", "2025-07-09 00:00", "2025-07-09 12:00"]),
        "lead_days": [3.1667, 2.6667, 2.1667, 1.6667],
        "pop": [0.1, 0.2, 0.3, 0.4], "pop_p12": [0.1, 0.2, 0.3, 0.4], "pop_p24": [np.nan] * 4,
        "pop_p06": [np.nan, 0.25, np.nan, np.nan], "field": ["p12x2"] * 4,
    })
    assert pick_lead(by_run, 3.0).iloc[0]["pop"] == 0.1          # 3.1667 is closer than 2.6667
    assert pick_lead(by_run, 2.0).iloc[0]["pop"] == 0.3
    assert pick_lead(by_run, 1.5).iloc[0]["pop"] == 0.4
    # exact tie: 2.9167 would tie between none here; build one: leads 2.75 and 3.25 around 3.0 -> earlier run
    tie = by_run.copy()
    tie["lead_days"] = [3.25, 2.75, 2.1667, 1.6667]
    assert pick_lead(tie, 3.0).iloc[0]["runtime"] == pd.Timestamp("2025-07-08 00:00")
    # a column that only one run has
    assert pick_lead(by_run, 3.0, column="pop_p06").iloc[0]["pop_p06"] == 0.25
    # beyond the tolerance: nothing
    assert pick_lead(by_run, 7.0).empty


def test_pop_table_one_row_per_day_and_lead():
    rows = []
    for d in ("2025-07-10", "2025-07-11"):
        day = pd.Timestamp(d)
        for k in (1, 2, 3):
            rt = (day - pd.Timedelta(days=k)).strftime("%Y-%m-%d 00:00")
            rows.append((rt, (day + pd.Timedelta(hours=12)).strftime("%Y-%m-%d %H:%M"), np.nan, 0.1 * k, np.nan))
            rows.append((rt, (day + pd.Timedelta(days=1)).strftime("%Y-%m-%d %H:%M"), np.nan, 0.1 * k, np.nan))
    t = pop_table(_mos(rows), pd.to_datetime(["2025-07-10", "2025-07-11"]), leads=(1.5, 2, 3))
    assert len(t) == 6
    assert t.groupby(["date", "target_lead"]).size().max() == 1
    # lead 2 -> the run 2 days before the day (lead 2.1667), whose p12 are 0.2 and 0.2
    assert t[t["target_lead"] == 2].iloc[0]["pop"] == pytest.approx(1 - 0.8 * 0.8)


def test_carry_forward_uses_climatology_where_mos_is_missing():
    days = pd.DataFrame({"date": pd.to_datetime(["2010-06-01", "2010-06-02", "2010-07-01"]),
                         "season": [2010, 2010, 2010], "month": [6, 6, 7], "k_s": [1, 0, 1], "c_s": [0, 0, 0],
                         "d_park": [0, 0, 0]})
    pm = {pd.Timestamp("2010-06-01"): 0.8, pd.Timestamp("2010-07-01"): float("nan")}
    pop, used = pop_with_carry_forward(days, pm, {6: 0.3, 7: 0.4, 0: 0.35})
    assert list(pop) == [0.8, 0.3, 0.4]
    assert list(used) == [True, False, False]


def test_available_seasons_rule_90_percent():
    days = pd.DataFrame({"season": [2010] * 10 + [2011] * 10})
    used = np.array([True] * 9 + [False] + [True] * 8 + [False] * 2)
    assert available_seasons(days, used) == [2010]


def test_calibration_bins_group_probabilities():
    c = calibration([0.05, 0.15, 0.95, 1.0], [0, 1, 1, 1])
    assert c["n"].sum() == 4
    assert c.loc[c["bin_lo"] == 0.9, "n"].iloc[0] == 2
    assert math.isclose(c.loc[c["bin_lo"] == 0.9, "rain_share"].iloc[0], 1.0)
