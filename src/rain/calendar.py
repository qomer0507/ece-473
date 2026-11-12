"""Season calendar per SPEC_v3.

Season: every day from the Friday before Memorial Day through Labor Day, both ends included.
Sensitivity variant: Saturdays and Sundays in that range plus Memorial Day, July 4 and Labor Day.

Memorial Day is the last Monday of May (used for every year, also before the 1971 Uniform Monday Holiday Act,
so that the stand-in calendar is the same rule in all seasons). Labor Day is the first Monday of September.
"""
from __future__ import annotations

import datetime as dt

ALL_DAYS = "all_days"
WEEKEND_HOLIDAY = "weekend_holiday"
VARIANTS = (ALL_DAYS, WEEKEND_HOLIDAY)


def memorial_day(year: int) -> dt.date:
    """Last Monday of May."""
    d = dt.date(year, 5, 31)
    return d - dt.timedelta(days=d.weekday())


def labor_day(year: int) -> dt.date:
    """First Monday of September."""
    d = dt.date(year, 9, 1)
    return d + dt.timedelta(days=(7 - d.weekday()) % 7)


def independence_day(year: int) -> dt.date:
    return dt.date(year, 7, 4)


def season_start(year: int) -> dt.date:
    """The Friday before Memorial Day."""
    return memorial_day(year) - dt.timedelta(days=3)


def season_end(year: int) -> dt.date:
    return labor_day(year)


def holiday_name(day: dt.date) -> str:
    """'memorial_day', 'july_4', 'labor_day' or ''."""
    y = day.year
    if day == memorial_day(y):
        return "memorial_day"
    if day == independence_day(y):
        return "july_4"
    if day == labor_day(y):
        return "labor_day"
    return ""


def is_weekend_or_holiday(day: dt.date) -> bool:
    """Saturday, Sunday, Memorial Day, July 4 or Labor Day."""
    return day.weekday() >= 5 or holiday_name(day) != ""


def season_days(year: int, variant: str = ALL_DAYS) -> list[dt.date]:
    """Season days of `year` in date order.

    variant 'all_days': every day from the Friday before Memorial Day through Labor Day.
    variant 'weekend_holiday': the Saturdays, Sundays and three holidays inside that range.
    """
    if variant not in VARIANTS:
        raise ValueError(f"unknown calendar variant {variant!r}")
    start, end = season_start(year), season_end(year)
    days = [start + dt.timedelta(days=i) for i in range((end - start).days + 1)]
    if variant == WEEKEND_HOLIDAY:
        days = [d for d in days if is_weekend_or_holiday(d)]
    return days
