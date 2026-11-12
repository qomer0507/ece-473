"""Daily rain measures per SPEC_v3: opening-hours totals, loss days, the Kalshi rule, usable days and seasons.

Definitions
  opening window   local clock hours start..end-1 (America/New_York). Main case 10:00-18:00 = hours 10..17.
  usable day       every hour of the opening window is present. Otherwise the day's total and loss flags are
                   missing (NaN / <NA>); the day is dropped from counts and reported as unusable. Never imputed.
  loss day         opening-window total >= threshold (inches), equality included. Main threshold 0.25.
  climate day      NWS climate day, local standard time (see rain.hourly).
  Kalshi rule      pays when the climate-day total is >= 0.01 inch. Trace counts as zero. A climate day with no
                   measured rain in the hours that are present is No, also when hours are missing ("missing = No").
                   climate_hours_present says how many of the 24 hours were there.
  usable season    at least 90% of the main-window opening-hour hours of the season's days are present.

Totals are rounded to 0.01 inch before any comparison, so 0.10 + 0.15 is a loss day at 0.25.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import calendar as cal
from .hourly import add_time_columns

THRESHOLDS = (0.10, 0.25, 0.50)
WINDOWS = ((10, 16), (10, 18), (10, 20))
MAIN_THRESHOLD = 0.25
MAIN_WINDOW = (10, 18)
KALSHI_THRESHOLD = 0.01
USABLE_SEASON_SHARE = 0.90
SOURCE_PREFERENCE = ("IEM_METAR", "NCEI_ISD")  # tie-break order when two sources cover a season equally


def threshold_tag(threshold: float) -> str:
    """0.25 -> '0p25'."""
    return f"{threshold:.2f}".replace(".", "p")


def window_tag(window: tuple[int, int]) -> str:
    """(10, 18) -> '10_18'."""
    return f"{window[0]:02d}_{window[1]:02d}"


def loss_column(threshold: float, window: tuple[int, int]) -> str:
    return f"loss_{threshold_tag(threshold)}_{window_tag(window)}"


def window_totals(hourly_t: pd.DataFrame, start_hour: int, end_hour: int) -> pd.DataFrame:
    """Per local date: hours_present and rain_in for local clock hours start_hour..end_hour-1.

    `hourly_t` must carry the columns of rain.hourly.add_time_columns. rain_in is NaN unless every hour of the
    window is present. Dates with no row in the window do not appear (treat as 0 hours present).
    """
    n_hours = end_hour - start_hour
    w = hourly_t[(hourly_t["local_hour"] >= start_hour) & (hourly_t["local_hour"] < end_hour) & hourly_t["present"]]
    g = w.groupby("local_date").agg(hours_present=("present", "size"), rain_in=("precip_in", "sum"))
    g["rain_in"] = g["rain_in"].round(2).where(g["hours_present"] == n_hours)
    return g


def climate_day_totals(hourly_t: pd.DataFrame) -> pd.DataFrame:
    """Per climate date: hours_present (0-24) and total_in, the sum over the hours that are present."""
    p = hourly_t[hourly_t["present"]]
    g = p.groupby("climate_date").agg(hours_present=("present", "size"), total_in=("precip_in", "sum"))
    g["total_in"] = g["total_in"].round(2)
    return g


def loss_flag(total_in: pd.Series, threshold: float) -> pd.Series:
    """Nullable boolean: total >= threshold; <NA> where the total is missing (unusable day)."""
    t = pd.to_numeric(total_in, errors="coerce")
    flag = (t.round(2) >= round(threshold, 2)).astype("boolean")
    return flag.mask(t.isna())


def kalshi_flag(climate_total_in: pd.Series) -> pd.Series:
    """Plain boolean: climate-day total >= 0.01 inch. Missing total = False (the 'missing = No' rule)."""
    t = pd.to_numeric(climate_total_in, errors="coerce")
    return (t.round(2) >= KALSHI_THRESHOLD).fillna(False).astype(bool)


def choose_source(per_source: dict[str, pd.DataFrame], days: list, window: tuple[int, int] = MAIN_WINDOW) -> str | None:
    """Source with the most present opening-window hours over `days`. Ties go by SOURCE_PREFERENCE.

    `per_source` maps source name to an hourly frame with time columns. None if no source has a present hour.
    """
    day_set = set(days)
    best, best_n = None, 0
    for name in [s for s in SOURCE_PREFERENCE if s in per_source] + [s for s in per_source if s not in SOURCE_PREFERENCE]:
        h = per_source[name]
        m = h["present"] & (h["local_hour"] >= window[0]) & (h["local_hour"] < window[1]) & h["local_date"].isin(day_set)
        n = int(m.sum())
        if n > best_n:
            best, best_n = name, n
    return best


def build_daily(per_source: dict[str, pd.DataFrame], station: str, seasons: list[int]) -> pd.DataFrame:
    """One row per season day (all-days calendar) for each season in `seasons`.

    `per_source` maps source name to that source's hourly frame (naive UTC index; columns present, precip_in,
    trace), as returned by rain.hourly.load_source. One source is used per season (choose_source); sources are
    never mixed inside a season. A season with no present hour in any source still gets rows, all unusable.
    """
    timed = {k: add_time_columns(v) for k, v in per_source.items() if v is not None and len(v)}
    frames = []
    for season in seasons:
        days = cal.season_days(season, cal.ALL_DAYS)
        source = choose_source(timed, days)
        d = pd.DataFrame({"date": days})
        d.insert(0, "station", station)
        d["season"] = season
        d["source"] = source if source else ""
        d["weekend_or_holiday"] = [cal.is_weekend_or_holiday(x) for x in days]
        d["holiday"] = [cal.holiday_name(x) for x in days]
        h = timed[source] if source else None
        for window in WINDOWS:
            tag = window_tag(window)
            if h is not None:
                wt = window_totals(h, *window).reindex(days)
                present = wt["hours_present"].fillna(0).astype(int).to_numpy()
                rain = wt["rain_in"].to_numpy()
            else:
                present, rain = np.zeros(len(days), dtype=int), np.full(len(days), np.nan)
            d[f"hours_present_{tag}"] = present
            d[f"usable_{tag}"] = present == (window[1] - window[0])
            d[f"rain_in_{tag}"] = rain
            for thr in THRESHOLDS:
                d[loss_column(thr, window)] = loss_flag(d[f"rain_in_{tag}"], thr)
        if h is not None:
            ct = climate_day_totals(h).reindex(days)
            d["climate_hours_present"] = ct["hours_present"].fillna(0).astype(int).to_numpy()
            d["climate_day_total_in"] = ct["total_in"].to_numpy()
        else:
            d["climate_hours_present"] = 0
            d["climate_day_total_in"] = np.nan
        d["kalshi_pays"] = kalshi_flag(d["climate_day_total_in"])
        frames.append(d)
    out = pd.concat(frames, ignore_index=True)
    main = window_tag(MAIN_WINDOW)
    out["usable"] = out[f"usable_{main}"]
    out["open_hours_rain_in"] = out[f"rain_in_{main}"]
    share = season_hour_share(out)
    out["season_usable"] = out["season"].map(share >= USABLE_SEASON_SHARE)
    return out


def season_hour_share(daily: pd.DataFrame, window: tuple[int, int] = MAIN_WINDOW) -> pd.Series:
    """Per season: present opening-window hours / expected opening-window hours over all season days."""
    col = f"hours_present_{window_tag(window)}"
    g = daily.groupby("season")[col].agg(["sum", "size"])
    return g["sum"] / (g["size"] * (window[1] - window[0]))


def usable_seasons(daily: pd.DataFrame) -> list[int]:
    """Seasons with >= 90% of main-window opening-hour hours present."""
    share = season_hour_share(daily)
    return [int(s) for s in share.index[share >= USABLE_SEASON_SHARE]]


def season_counts(
    daily: pd.DataFrame,
    threshold: float = MAIN_THRESHOLD,
    window: tuple[int, int] = MAIN_WINDOW,
    variant: str = cal.ALL_DAYS,
) -> pd.DataFrame:
    """Per season: days, usable days, loss days, Kalshi-pay days and the three overlap counts.

    Counts are over usable days only (window complete). Unusable days are reported in days_unusable.
    If `daily` has a ghcn_prcp_in column, ref_* columns give the Kalshi rule applied to the GHCN-Daily total
    (reference only; a missing GHCN value counts as No and is counted in ref_usable_days_ghcn_missing).
    season_usable and share_open_hours_present always refer to the main window on the all-days calendar.
    """
    if variant not in cal.VARIANTS:
        raise ValueError(f"unknown calendar variant {variant!r}")
    d = daily if variant == cal.ALL_DAYS else daily[daily["weekend_or_holiday"]]
    usable = d[f"usable_{window_tag(window)}"].to_numpy(dtype=bool)
    loss = d[loss_column(threshold, window)].fillna(False).to_numpy(dtype=bool) & usable
    paid = d["kalshi_pays"].to_numpy(dtype=bool) & usable
    t = pd.DataFrame(
        {
            "season": d["season"].to_numpy(),
            "days": 1,
            "usable_days": usable,
            "days_unusable": ~usable,
            "loss_days": loss,
            "kalshi_pay_days": paid,
            "loss_and_paid": loss & paid,
            "loss_not_paid": loss & ~paid,
            "paid_not_loss": paid & ~loss,
            "usable_days_climate_day_incomplete": usable & (d["climate_hours_present"].to_numpy() < 24),
        }
    )
    if "ghcn_prcp_in" in d.columns:
        # Reference only: the same rule applied to the GHCN-Daily total instead of the hourly sum.
        ghcn_paid = (d["ghcn_prcp_in"].to_numpy(dtype=float) >= KALSHI_THRESHOLD) & usable
        t["ref_ghcn_pay_days"] = ghcn_paid
        t["ref_ghcn_paid_not_loss"] = ghcn_paid & ~loss
        t["ref_loss_and_ghcn_paid"] = ghcn_paid & loss
        t["ref_usable_days_ghcn_missing"] = usable & d["ghcn_prcp_in"].isna().to_numpy()
    out = t.groupby("season").sum().astype(int).reset_index()
    share = season_hour_share(daily)
    out["share_open_hours_present"] = out["season"].map(share).round(4)
    out["season_usable"] = out["season"].map(share >= USABLE_SEASON_SHARE)
    out.insert(1, "calendar", variant)
    out.insert(2, "threshold_in", threshold)
    out.insert(3, "window", f"{window[0]:02d}:00-{window[1]:02d}:00")
    return out
