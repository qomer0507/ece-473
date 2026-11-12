"""Hand-checked cases: daylight-saving hour mapping, the climate-day boundary, loading and rounding."""
import datetime as dt
import gzip
import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from rain import hourly as rh  # noqa: E402

D = dt.date


def frame(labels):
    idx = pd.DatetimeIndex(pd.to_datetime(labels), name="hour_utc")
    return pd.DataFrame({"present": True, "precip_in": 0.0, "trace": False, "source": "TEST"}, index=idx)


def test_summer_utc_14_is_local_10():
    t = rh.add_time_columns(frame(["2024-07-10 14:00"]))  # EDT = UTC-4
    assert t["local_hour"].iloc[0] == 10 and t["local_date"].iloc[0] == D(2024, 7, 10)


def test_winter_utc_14_is_local_9():
    t = rh.add_time_columns(frame(["2024-01-10 14:00"]))  # EST = UTC-5
    assert t["local_hour"].iloc[0] == 9


def test_spring_forward_day_2024():
    # 10 March 2024: clocks go 01:59 EST -> 03:00 EDT. 06:00 UTC is 01:00 EST, 07:00 UTC is 03:00 EDT.
    t = rh.add_time_columns(frame(["2024-03-10 06:00", "2024-03-10 07:00"]))
    assert list(t["local_hour"]) == [1, 3]


def test_fall_back_day_2024():
    # 3 November 2024: 05:00 UTC is 01:00 EDT, 06:00 UTC is 01:00 EST (the repeated hour), 15:00 UTC is 10:00 EST.
    t = rh.add_time_columns(frame(["2024-11-03 05:00", "2024-11-03 06:00", "2024-11-03 15:00"]))
    assert list(t["local_hour"]) == [1, 1, 10]


def test_opening_window_utc_hours_summer_and_winter():
    summer = rh.utc_hours_for_local_window(D(2024, 7, 10), 10, 18)
    assert len(summer) == 8
    assert summer[0] == pd.Timestamp("2024-07-10 14:00") and summer[-1] == pd.Timestamp("2024-07-10 21:00")
    winter = rh.utc_hours_for_local_window(D(2024, 1, 10), 10, 18)
    assert winter[0] == pd.Timestamp("2024-01-10 15:00") and winter[-1] == pd.Timestamp("2024-01-10 22:00")


def test_war_time_1943_is_daylight_time():
    # Year-round "war time" (UTC-4) was in force in summer 1943; the tz database knows it.
    t = rh.add_time_columns(frame(["1943-07-10 14:00"]))
    assert t["local_hour"].iloc[0] == 10


def test_climate_day_boundary_in_summer():
    # In summer the climate day (standard time) runs 01:00 to 00:59 on the local clock.
    labels = [
        "2024-07-10 04:00",  # 00:00 EDT 10 Jul = 23:00 EST 9 Jul  -> climate day 9 Jul
        "2024-07-10 05:00",  # 01:00 EDT 10 Jul = 00:00 EST 10 Jul -> climate day 10 Jul
        "2024-07-11 03:00",  # 23:00 EDT 10 Jul                    -> climate day 10 Jul
        "2024-07-11 04:00",  # 00:00 EDT 11 Jul = 23:00 EST 10 Jul -> climate day 10 Jul, local date 11 Jul
        "2024-07-11 05:00",  # 01:00 EDT 11 Jul                    -> climate day 11 Jul
    ]
    t = rh.add_time_columns(frame(labels))
    assert list(t["climate_date"]) == [D(2024, 7, 9), D(2024, 7, 10), D(2024, 7, 10), D(2024, 7, 10), D(2024, 7, 11)]
    assert list(t["local_date"]) == [D(2024, 7, 10), D(2024, 7, 10), D(2024, 7, 10), D(2024, 7, 11), D(2024, 7, 11)]
    assert list(t["local_hour"]) == [0, 1, 23, 0, 1]


def test_climate_day_equals_local_day_in_winter():
    t = rh.add_time_columns(frame(["2024-01-10 05:00", "2024-01-11 04:00"]))  # 00:00 and 23:00 EST on 10 Jan
    assert list(t["climate_date"]) == [D(2024, 1, 10), D(2024, 1, 10)]
    assert list(t["local_date"]) == [D(2024, 1, 10), D(2024, 1, 10)]


def test_climate_day_utc_hours():
    h = rh.utc_hours_for_climate_day(D(2024, 7, 10))
    assert len(h) == 24 and h[0] == pd.Timestamp("2024-07-10 05:00") and h[-1] == pd.Timestamp("2024-07-11 04:00")
    t = rh.add_time_columns(frame(h))
    assert set(t["climate_date"]) == {D(2024, 7, 10)}
    assert t["local_hour"].iloc[0] == 1 and t["local_hour"].iloc[-1] == 0


def test_opening_window_lies_inside_the_same_climate_day():
    for day in (D(2024, 5, 24), D(2024, 9, 2)):
        win = rh.utc_hours_for_local_window(day, 10, 20)
        t = rh.add_time_columns(frame(win))
        assert set(t["climate_date"]) == {day}


def write_probe(tmp_path, station, source, rows):
    path = tmp_path / f"hourly_maysep_{station}_{source}.csv.gz"
    with gzip.open(path, "wt") as fh:
        fh.write("hour_label_utc,source,ldate,lhour,lst_date,present,precip_in,trace,pno\n")
        for label, present, value, trace in rows:
            fh.write(f"{label},{source},x,0,x,{present},{value},{trace},False\n")
    return str(tmp_path)


def test_load_source_rounds_and_masks(tmp_path):
    folder = write_probe(
        tmp_path, "XXX", "NCEI_ISD",
        [("2000-07-01 14:00:00", True, 0.1299, False),   # 3.3 mm in the archive = 0.13 in reported
         ("2000-07-01 15:00:00", True, 0.0118, False),   # 0.3 mm = 0.01 in
         ("2000-07-01 16:00:00", False, 0.0, False),     # not present: value must not be usable
         ("2000-07-01 17:00:00", True, 0.0, True)],      # trace = 0
    )
    h = rh.load_source(folder, "XXX", "NCEI_ISD")
    assert list(h["precip_in"].iloc[[0, 1, 3]]) == [0.13, 0.01, 0.0]
    assert pd.isna(h["precip_in"].iloc[2]) and not h["present"].iloc[2]
    assert h["trace"].iloc[3]


def test_load_source_missing_file_returns_none(tmp_path):
    assert rh.load_source(str(tmp_path), "XXX", "IEM_METAR") is None


def test_load_source_rejects_duplicate_hours(tmp_path):
    folder = write_probe(tmp_path, "XXX", "IEM_METAR",
                         [("2000-07-01 14:00:00", True, 0.0, False), ("2000-07-01 14:00:00", True, 0.1, False)])
    with pytest.raises(ValueError):
        rh.load_source(folder, "XXX", "IEM_METAR")
