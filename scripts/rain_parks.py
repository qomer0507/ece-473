"""Park table and operating calendars against the SPEC_v3 season and opening window.

    python scripts/rain_parks.py

Reads   data/processed/rain/park_calendar_transcribed.txt   day-level reading of queue-times.com month pages
        data/processed/rain_probe/parks.csv, park_station_distances.csv   (Phase 0: coordinates, distances)
Writes  data/processed/rain/parks.csv                  one row per park: coordinates, settlement station, sources
        data/processed/rain/park_calendar_days.csv     one row per park-day that was read
        data/processed/rain/park_calendar_vs_spec.csv  per park and season: SPEC season days, days read, open days, hours
The calendar is third-party data read by an LLM fetch tool. It is evidence about the stand-in calendar, not an input
to any rain count.
"""
import calendar as pycal
import datetime as dt
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from rain import calendar as cal  # noqa: E402

OUT = os.path.join(ROOT, "data", "processed", "rain")
PROBE = os.path.join(ROOT, "data", "processed", "rain_probe")
QT_ID = {"sesame_place": 29, "dorney_park": 69, "great_adventure": 37}
STATION = {  # settlement station per SPEC_v3 / Phase 0 verdict
    "sesame_place": ("TTN", "lead case; Kalshi daily rain market at Trenton since 2026-08-27"),
    "dorney_park": ("ABE", "'should be listed' case; no Kalshi rain market at Allentown"),
    "great_adventure": ("TTN", "no usable nearby station (Phase 0); Trenton is the practical choice, not a SPEC case"),
}
SPEC_OPEN, SPEC_CLOSE = 10.0, 18.0


def hhmm(text):
    h, m = text.split(":")
    return int(h) + int(m) / 60


def parse_transcription(path):
    days, months = [], []
    for line in open(path):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        park, ym, status, runs = line.split("|")
        year, month = int(ym[:4]), int(ym[5:])
        months.append(dict(park_id=park, year=year, month=month, status=status))
        seen = set()
        for run in filter(None, runs.split(";")):
            span, value = run.split("=")
            a, b = (span.split("-") + [span])[:2] if "-" in span else (span, span)
            for day in range(int(a), int(b) + 1):
                if day in seen:
                    raise ValueError(f"{park} {ym}: day {day} given twice")
                seen.add(day)
                rec = dict(park_id=park, date=dt.date(year, month, day), open=value != "C", open_time="", close_time="")
                if value != "C":
                    rec["open_time"], rec["close_time"] = value.split("-")
                days.append(rec)
        if status == "ok" and len(seen) != pycal.monthrange(year, month)[1]:
            raise ValueError(f"{park} {ym}: {len(seen)} days transcribed, month has {pycal.monthrange(year, month)[1]}")
    return pd.DataFrame(days), pd.DataFrame(months)


def season_table(days, months):
    rows = []
    for (park, year), _ in months.groupby(["park_id", "year"]):
        season = cal.season_days(year)
        d = days[(days.park_id == park) & days.date.isin(season)]
        o = d[d.open]
        m = months[(months.park_id == park) & (months.year == year)]
        r = dict(
            park_id=park, season=year, spec_first_day=season[0], spec_last_day=season[-1], spec_season_days=len(season),
            days_read=len(d), days_not_read=len(season) - len(d), open_days=len(o), closed_days=int((~d.open).sum()),
            share_of_read_days_open=round(len(o) / len(d), 3) if len(d) else None,
            closed_dates="; ".join(str(x) for x in d[~d.open].date),
            months_not_read=", ".join(f"{x.month:02d} ({x.status})" for x in m.itertuples() if x.status != "ok"),
        )
        if len(o):
            ot, ct = o.open_time.map(hhmm), o.close_time.map(hhmm)
            r.update(
                usual_open_time=o.open_time.mode().iloc[0], usual_close_time=o.close_time.mode().iloc[0],
                earliest_close=o.close_time.min(), latest_close=o.close_time.max(),
                open_days_opening_by_10=int((ot <= SPEC_OPEN).sum()), open_days_opening_after_10=int((ot > SPEC_OPEN).sum()),
                open_days_closing_before_18=int((ct < SPEC_CLOSE).sum()), open_days_closing_at_18=int((ct == SPEC_CLOSE).sum()),
                open_days_closing_after_18=int((ct > SPEC_CLOSE).sum()),
                mean_open_hours_per_day=round((ct - ot).mean(), 2),
                share_of_open_hours_inside_10_18=round(
                    ((ct.clip(upper=SPEC_CLOSE) - ot.clip(lower=SPEC_OPEN)).clip(lower=0)).sum() / (ct - ot).sum(), 3),
                weekend_holiday_days_read=int(d.date.map(cal.is_weekend_or_holiday).sum()),
                weekend_holiday_days_open=int(o.date.map(cal.is_weekend_or_holiday).sum()),
            )
        rows.append(r)
    return pd.DataFrame(rows)


def park_table():
    p = pd.read_csv(os.path.join(PROBE, "parks.csv"))
    dist = pd.read_csv(os.path.join(PROBE, "park_station_distances.csv"))
    p = p[p.park_id.isin(QT_ID)].copy()
    p["settlement_station"] = p.park_id.map(lambda k: STATION[k][0])
    p["role"] = p.park_id.map(lambda k: STATION[k][1])
    look = {(r.park_id, r.asos_id): r.distance_km for r in dist.itertuples()}
    p["station_distance_km"] = [look.get((a, b)) for a, b in zip(p.park_id, p.settlement_station)]
    p["queue_times_id"] = p.park_id.map(QT_ID)
    p["calendar_source"] = p.queue_times_id.map(lambda i: f"https://queue-times.com/parks/{i}/calendar/YYYY/MM")
    p["spec_season"] = "Friday before Memorial Day through Labor Day"
    p["spec_opening_window"] = "10:00-18:00"
    return p


if __name__ == "__main__":
    days, months = parse_transcription(os.path.join(OUT, "park_calendar_transcribed.txt"))
    days.sort_values(["park_id", "date"]).to_csv(os.path.join(OUT, "park_calendar_days.csv"), index=False)
    t = season_table(days, months)
    t.to_csv(os.path.join(OUT, "park_calendar_vs_spec.csv"), index=False)
    park_table().to_csv(os.path.join(OUT, "parks.csv"), index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
    print(t.drop(columns=["closed_dates", "spec_first_day", "spec_last_day"]).to_string(index=False))
    print(t[["park_id", "season", "closed_dates"]].to_string(index=False))
    print(pd.read_csv(os.path.join(OUT, "parks.csv")).to_string(index=False))
