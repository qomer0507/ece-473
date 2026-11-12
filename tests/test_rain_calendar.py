"""Hand-checked cases for the season calendar (SPEC_v3)."""
import datetime as dt
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from rain import calendar as cal  # noqa: E402

D = dt.date

# Checked against printed calendars: (year, Memorial Day, Labor Day)
HOLIDAYS = [
    (1998, D(1998, 5, 25), D(1998, 9, 7)),
    (2004, D(2004, 5, 31), D(2004, 9, 6)),
    (2015, D(2015, 5, 25), D(2015, 9, 7)),
    (2019, D(2019, 5, 27), D(2019, 9, 2)),
    (2021, D(2021, 5, 31), D(2021, 9, 6)),
    (2024, D(2024, 5, 27), D(2024, 9, 2)),
    (2025, D(2025, 5, 26), D(2025, 9, 1)),
    (2026, D(2026, 5, 25), D(2026, 9, 7)),
]


@pytest.mark.parametrize("year,mem,lab", HOLIDAYS)
def test_memorial_and_labor_day(year, mem, lab):
    assert cal.memorial_day(year) == mem
    assert cal.labor_day(year) == lab
    assert mem.weekday() == 0 and lab.weekday() == 0


def test_labor_day_when_september_first_is_monday():
    assert cal.labor_day(2025) == D(2025, 9, 1)  # 1 Sep 2025 is a Monday
    assert cal.labor_day(2014) == D(2014, 9, 1)


def test_memorial_day_when_may_31_is_monday():
    assert cal.memorial_day(2021) == D(2021, 5, 31)
    assert cal.memorial_day(2010) == D(2010, 5, 31)


def test_season_2024_ends_and_length():
    days = cal.season_days(2024)
    assert days[0] == D(2024, 5, 24) and days[0].weekday() == 4  # Friday before Memorial Day
    assert days[-1] == D(2024, 9, 2)
    assert len(days) == 102  # 8 in May + 30 + 31 + 31 + 2 in Sep
    assert days == sorted(set(days))


def test_season_2026_is_109_days():
    days = cal.season_days(2026)
    assert days[0] == D(2026, 5, 22) and days[-1] == D(2026, 9, 7)
    assert len(days) == 109  # 10 in May + 30 + 31 + 31 + 7 in Sep


@pytest.mark.parametrize("year", range(1941, 2027))
def test_season_length_is_102_or_109(year):
    n = len(cal.season_days(year))
    assert n in (102, 109)
    assert cal.season_start(year).weekday() == 4


def test_weekend_holiday_variant_2024():
    days = cal.season_days(2024, cal.WEEKEND_HOLIDAY)
    # 15 weekends (25 May .. 1 Sep) = 30 days, plus Memorial Day, Thursday 4 July, Labor Day
    assert len(days) == 33
    assert D(2024, 5, 24) not in days  # the opening Friday is a weekday
    assert D(2024, 5, 27) in days and D(2024, 7, 4) in days and D(2024, 9, 2) in days
    assert D(2024, 7, 3) not in days
    assert all(d.weekday() >= 5 or cal.holiday_name(d) for d in days)


def test_weekend_holiday_variant_when_july_4_is_saturday():
    days = cal.season_days(2026, cal.WEEKEND_HOLIDAY)  # 4 July 2026 is a Saturday: not counted twice
    assert len(days) == 34  # 16 weekends (23 May .. 6 Sep) = 32, plus Memorial Day and Labor Day
    assert len(set(days)) == len(days)


def test_holiday_names_and_flag():
    assert cal.holiday_name(D(2024, 7, 4)) == "july_4"
    assert cal.holiday_name(D(2024, 5, 27)) == "memorial_day"
    assert cal.holiday_name(D(2024, 9, 2)) == "labor_day"
    assert cal.holiday_name(D(2024, 7, 5)) == ""
    assert cal.is_weekend_or_holiday(D(2024, 7, 4)) and not cal.is_weekend_or_holiday(D(2024, 7, 5))
    assert cal.is_weekend_or_holiday(D(2024, 7, 6))


def test_unknown_variant_raises():
    with pytest.raises(ValueError):
        cal.season_days(2024, "weekdays")
