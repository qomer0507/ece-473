"""Hand-checked cases: opening-hours totals, threshold equality, missing hours, Kalshi rule, usable rules, counts."""
import datetime as dt
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from rain import calendar as cal  # noqa: E402
from rain import daily as rd  # noqa: E402
from rain import hourly as rh  # noqa: E402

D = dt.date
YEAR = 2024  # season 24 May - 2 Sep 2024, 102 days


def season_hours(year=YEAR):
    """Every UTC hour label needed for the season: from the first climate day through the last one."""
    days = cal.season_days(year)
    start = rh.utc_hours_for_climate_day(days[0])[0]
    end = rh.utc_hours_for_climate_day(days[-1])[-1]
    return pd.date_range(start, end, freq="h")


def synthetic(rain=None, missing=(), year=YEAR, source="IEM_METAR"):
    """Dry, complete season; `rain` maps UTC label -> inches; `missing` lists UTC labels that are not present."""
    idx = season_hours(year)
    h = pd.DataFrame({"present": True, "precip_in": 0.0, "trace": False, "source": source}, index=idx)
    h.index.name = "hour_utc"
    for label, value in (rain or {}).items():
        h.loc[pd.Timestamp(label), "precip_in"] = value
    for label in missing:
        h.loc[pd.Timestamp(label), ["present", "precip_in"]] = [False, np.nan]
    return h


def local(day, hour):
    """UTC label of local clock hour `hour` on local date `day`."""
    return rh.utc_hours_for_local_window(day, hour, hour + 1)[0]


def build(rain=None, missing=(), year=YEAR):
    d = rd.build_daily({"IEM_METAR": synthetic(rain, missing, year)}, "XXX", [year])
    return d.set_index("date")


DAY = D(2024, 7, 10)


def test_dry_complete_season():
    d = build()
    assert len(d) == 102
    assert d["usable"].all() and d["season_usable"].all()
    assert (d["open_hours_rain_in"] == 0).all()
    assert not d["kalshi_pays"].any()
    assert not d[rd.loss_column(0.25, (10, 18))].any()
    assert (d["climate_hours_present"] == 24).all()


def test_threshold_equality_counts_as_loss():
    # 0.10 + 0.15 = 0.25 exactly (a float sum of 0.25000000000000006 or 0.24999999999999997 must still count)
    d = build({local(DAY, 10): 0.10, local(DAY, 17): 0.15})
    r = d.loc[DAY]
    assert r["open_hours_rain_in"] == 0.25
    assert r["loss_0p25_10_18"] is True or r["loss_0p25_10_18"] == True  # noqa: E712
    assert r["loss_0p10_10_18"] == True and r["loss_0p50_10_18"] == False  # noqa: E712
    assert d["loss_0p25_10_18"].sum() == 1


def test_just_below_threshold_is_not_a_loss():
    d = build({local(DAY, 12): 0.24})
    assert d.loc[DAY, "loss_0p25_10_18"] == False  # noqa: E712
    assert d.loc[DAY, "loss_0p10_10_18"] == True  # noqa: E712


@pytest.mark.parametrize("thr,total,expected", [(0.10, 0.10, True), (0.10, 0.09, False), (0.50, 0.50, True),
                                                (0.50, 0.49, False), (0.25, 0.26, True)])
def test_loss_flag_edges(thr, total, expected):
    assert bool(rd.loss_flag(pd.Series([total]), thr).iloc[0]) is expected


def test_loss_flag_sum_of_hundredths():
    total = pd.Series([sum([0.01] * 25)])  # float sum is 0.25000000000000006
    assert bool(rd.loss_flag(total, 0.25).iloc[0])
    total = pd.Series([0.1 + 0.2 + 0.2])  # 0.5000000000000001
    assert bool(rd.loss_flag(total, 0.50).iloc[0])


def test_loss_flag_missing_is_na():
    f = rd.loss_flag(pd.Series([np.nan, 0.3]), 0.25)
    assert f.isna().iloc[0] and bool(f.iloc[1])


def test_window_edges_10_to_18():
    # Rain at local 09:00 and 18:00 is outside 10:00-18:00; 18:00 is inside 10:00-20:00.
    d = build({local(DAY, 9): 0.30, local(DAY, 18): 0.40})
    r = d.loc[DAY]
    assert r["open_hours_rain_in"] == 0.0 and r["loss_0p25_10_18"] == False  # noqa: E712
    assert r["rain_in_10_16"] == 0.0
    assert r["rain_in_10_20"] == 0.40 and r["loss_0p25_10_20"] == True  # noqa: E712
    assert r["climate_day_total_in"] == 0.70 and r["kalshi_pays"]


def test_window_10_16_excludes_hour_16():
    d = build({local(DAY, 15): 0.25, local(DAY, 16): 0.25})
    r = d.loc[DAY]
    assert r["rain_in_10_16"] == 0.25 and r["open_hours_rain_in"] == 0.50
    assert r["loss_0p50_10_16"] == False and r["loss_0p50_10_18"] == True  # noqa: E712


def test_missing_opening_hour_makes_day_unusable_not_dry():
    d = build({local(DAY, 11): 0.60}, missing=[local(DAY, 14)])
    r = d.loc[DAY]
    assert not r["usable"] and r["hours_present_10_18"] == 7
    assert np.isnan(r["open_hours_rain_in"])
    assert pd.isna(r["loss_0p25_10_18"])
    # the shorter window does not need hour 14? it does (10..15), so it is unusable too; 10-20 as well
    assert not r["usable_10_16"] and not r["usable_10_20"]
    assert d["usable"].sum() == 101
    c = rd.season_counts(d.reset_index()).iloc[0]
    assert c["days"] == 102 and c["usable_days"] == 101 and c["days_unusable"] == 1
    assert c["loss_days"] == 0  # the unusable day is dropped, not counted as a loss and not as a dry day


def test_missing_hour_outside_main_window_only_affects_wider_window():
    d = build(missing=[local(DAY, 19)])
    r = d.loc[DAY]
    assert r["usable"] and r["usable_10_16"] and not r["usable_10_20"]
    assert pd.isna(r["loss_0p25_10_20"]) and r["loss_0p25_10_18"] == False  # noqa: E712


def test_kalshi_rule_threshold_trace_and_missing():
    h = synthetic({local(D(2024, 7, 1), 3): 0.01})          # 0.01 in at 03:00: pays, not a loss day
    h.loc[local(D(2024, 7, 2), 12), "trace"] = True          # trace only (stored as 0.00): No
    d = rd.build_daily({"IEM_METAR": h}, "XXX", [YEAR]).set_index("date")
    assert d.loc[D(2024, 7, 1), "kalshi_pays"] and d.loc[D(2024, 7, 1), "loss_0p10_10_18"] == False  # noqa: E712
    assert not d.loc[D(2024, 7, 2), "kalshi_pays"]
    assert rd.kalshi_flag(pd.Series([np.nan, 0.0, 0.01, 0.004])).tolist() == [False, False, True, False]


def test_kalshi_rule_uses_climate_day_not_local_day():
    # 0.20 in at 00:00 local clock on 11 July belongs to climate day 10 July (23:00 standard time).
    d = build({local(D(2024, 7, 11), 0): 0.20})
    assert d.loc[D(2024, 7, 10), "kalshi_pays"] and d.loc[D(2024, 7, 10), "climate_day_total_in"] == 0.20
    assert not d.loc[D(2024, 7, 11), "kalshi_pays"]


def test_climate_day_with_missing_hours_and_no_rain_is_no():
    night = [local(DAY, h) for h in (1, 2, 3, 4)]
    d = build(missing=night)
    r = d.loc[DAY]
    assert r["usable"] and r["climate_hours_present"] == 20 and not r["kalshi_pays"]
    c = rd.season_counts(d.reset_index()).iloc[0]
    assert c["usable_days_climate_day_incomplete"] == 1


def test_usable_season_rule_at_90_percent():
    days = cal.season_days(YEAR)  # 102 days x 8 hours = 816 opening hours; 10% = 81.6
    def drop(n_hours):
        labels = []
        for day in days:
            for hour in range(10, 18):
                if len(labels) < n_hours:
                    labels.append(local(day, hour))
        return build(missing=labels)
    ok = drop(81)    # 735 / 816 = 0.9007
    bad = drop(82)   # 734 / 816 = 0.8995
    assert ok["season_usable"].all() and rd.usable_seasons(ok.reset_index()) == [YEAR]
    assert not bad["season_usable"].any() and rd.usable_seasons(bad.reset_index()) == []
    assert abs(rd.season_hour_share(ok.reset_index()).iloc[0] - 735 / 816) < 1e-12
    # unusable days are counted: 81 missing hours = 10 full days + 1 hour of an 11th day
    assert (~ok["usable"]).sum() == 11


def test_season_with_no_data_has_rows_and_is_unusable():
    d = rd.build_daily({"IEM_METAR": synthetic(year=2024)}, "XXX", [2023, 2024])
    a = d[d.season == 2023]
    assert len(a) == 102 and not a["usable"].any() and not a["season_usable"].any()
    assert a["open_hours_rain_in"].isna().all() and not a["kalshi_pays"].any()
    assert d[d.season == 2024]["season_usable"].all()


def test_source_choice_per_season_takes_better_coverage():
    good = synthetic({local(DAY, 12): 0.30}, source="NCEI_ISD")
    poor = synthetic(missing=[local(d, 12) for d in cal.season_days(YEAR)[:30]], source="IEM_METAR")
    d = rd.build_daily({"IEM_METAR": poor, "NCEI_ISD": good}, "XXX", [YEAR])
    assert set(d["source"]) == {"NCEI_ISD"} and d["usable"].all()
    tie = rd.build_daily({"NCEI_ISD": synthetic(source="NCEI_ISD"), "IEM_METAR": synthetic()}, "XXX", [YEAR])
    assert set(tie["source"]) == {"IEM_METAR"}  # equal coverage: documented preference


def test_season_counts_and_overlaps():
    rain = {
        local(D(2024, 6, 3), 12): 0.30,   # Monday: loss and paid
        local(D(2024, 6, 8), 13): 0.25,   # Saturday: loss (equality) and paid
        local(D(2024, 6, 9), 22): 0.50,   # Sunday evening: paid, not a loss
        local(D(2024, 6, 12), 4): 0.02,   # Wednesday night: paid, not a loss
        local(D(2024, 7, 4), 11): 0.10,   # Thursday 4 July: paid; loss only at the 0.10 threshold
    }
    d = build(rain).reset_index()
    c = rd.season_counts(d).iloc[0]
    assert (c["loss_days"], c["kalshi_pay_days"]) == (2, 5)
    assert (c["loss_and_paid"], c["loss_not_paid"], c["paid_not_loss"]) == (2, 0, 3)
    assert c["usable_days"] == 102 and bool(c["season_usable"])
    low = rd.season_counts(d, threshold=0.10).iloc[0]
    assert (low["loss_days"], low["paid_not_loss"]) == (3, 2)
    w = rd.season_counts(d, variant=cal.WEEKEND_HOLIDAY).iloc[0]
    assert w["days"] == 33
    assert (w["loss_days"], w["kalshi_pay_days"], w["paid_not_loss"]) == (1, 3, 2)  # 8 Jun; 8, 9 Jun and 4 Jul


def test_season_counts_reference_ghcn_columns():
    d = build({local(DAY, 12): 0.30}).reset_index()
    d["ghcn_prcp_in"] = 0.0
    d.loc[d["date"] == DAY, "ghcn_prcp_in"] = 0.31
    d.loc[d["date"] == D(2024, 7, 11), "ghcn_prcp_in"] = np.nan
    c = rd.season_counts(d).iloc[0]
    assert c["ref_ghcn_pay_days"] == 1 and c["ref_loss_and_ghcn_paid"] == 1 and c["ref_ghcn_paid_not_loss"] == 0
    assert c["ref_usable_days_ghcn_missing"] == 1


def test_tags():
    assert rd.loss_column(0.25, (10, 18)) == "loss_0p25_10_18"
    assert rd.threshold_tag(0.1) == "0p10" and rd.window_tag((10, 20)) == "10_20"
