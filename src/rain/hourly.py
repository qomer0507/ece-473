"""Hourly station rain: loading and time mapping.

Input files (written by scripts/p0_rain_analyze.py in Phase 0):
    <probe_dir>/hourly_maysep_<STATION>_<SOURCE>.csv.gz
    columns used: hour_label_utc, present, precip_in, trace, pno      SOURCE is IEM_METAR or NCEI_ISD
Each row is one accumulation hour. The label is the UTC clock hour the accumulation mostly overlaps: label 14:00
is the routine report issued near 14:53, i.e. rain from about 13:53 to 14:53 UTC (:51 to :54 by station; on the
hour before automation). `present` is False when no valid report closed that hour or the gauge was flagged as not
operating. Hours with no row at all are also missing. A trace is stored as 0.00.

Time mapping (the only place local time is computed)
  * local clock time: America/New_York from the tz database, so daylight saving is applied per date.
    Label 14:00 UTC is local hour 10 in summer (EDT, UTC-4) and local hour 9 in winter (EST, UTC-5).
  * NWS climate day: local STANDARD time, UTC-5 all year. In summer the climate day D therefore runs from 01:00
    local clock time on D to 00:59 on D+1. Climate day = date of (UTC label - 5 h).
"""
from __future__ import annotations

import os

import pandas as pd

TZ_NAME = "America/New_York"
LST_OFFSET_HOURS = -5  # Eastern Standard Time, used by the NWS climate day all year
SOURCES = ("IEM_METAR", "NCEI_ISD")
HOURLY_COLUMNS = ["present", "precip_in", "trace", "source"]


def probe_path(probe_dir: str, station: str, source: str) -> str:
    return os.path.join(probe_dir, f"hourly_maysep_{station}_{source}.csv.gz")


def load_source(probe_dir: str, station: str, source: str) -> pd.DataFrame | None:
    """One source's hourly series, indexed by naive UTC hour label. None if the file does not exist or is empty.

    Values are rounded to 0.01 inch. The gauges report hundredths of an inch; the NCEI archive stores tenths of a
    millimetre, so 0.13 in comes back as 0.1299 in. Rounding restores the reported value before any sum.
    Rows that are not present get precip_in = NaN so that they can never enter a total.
    """
    path = probe_path(probe_dir, station, source)
    if not os.path.exists(path):
        return None
    raw = pd.read_csv(path, usecols=["hour_label_utc", "present", "precip_in", "trace"])
    if raw.empty:
        return None
    out = pd.DataFrame(
        {
            "present": raw["present"].astype(bool).to_numpy(),
            "precip_in": raw["precip_in"].astype(float).round(2).to_numpy(),
            "trace": raw["trace"].astype(bool).to_numpy(),
        },
        index=pd.DatetimeIndex(pd.to_datetime(raw["hour_label_utc"]), name="hour_utc"),
    )
    if out.index.has_duplicates:
        raise ValueError(f"duplicate hour labels in {path}")
    out.loc[~out["present"], "precip_in"] = float("nan")
    out["source"] = source
    return out.sort_index()


def add_time_columns(hourly: pd.DataFrame) -> pd.DataFrame:
    """Copy of `hourly` (naive UTC DatetimeIndex) with local_date, local_hour and climate_date columns."""
    out = hourly.copy()
    local = out.index.tz_localize("UTC").tz_convert(TZ_NAME)
    out["local_date"] = local.date
    out["local_hour"] = local.hour
    out["climate_date"] = (out.index + pd.Timedelta(hours=LST_OFFSET_HOURS)).date
    return out


def utc_hours_for_local_window(day, start_hour: int, end_hour: int) -> pd.DatetimeIndex:
    """Naive UTC hour labels for local clock hours start_hour..end_hour-1 on local date `day`."""
    local = pd.date_range(
        pd.Timestamp(day) + pd.Timedelta(hours=start_hour), periods=end_hour - start_hour, freq="h", tz=TZ_NAME
    )
    return local.tz_convert("UTC").tz_localize(None)


def utc_hours_for_climate_day(day) -> pd.DatetimeIndex:
    """The 24 naive UTC hour labels of NWS climate day `day` (05:00 UTC to 04:00 UTC next day)."""
    return pd.date_range(pd.Timestamp(day) - pd.Timedelta(hours=LST_OFFSET_HOURS), periods=24, freq="h")
