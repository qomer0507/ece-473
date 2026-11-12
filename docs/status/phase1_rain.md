# Phase 1 rain workstream (Qasim)

Status: COMPLETE for Phase 1 (2026-11-12 04:20 UTC). Hedge evaluation not started (Phase 2). Spec: docs/SPEC_v3.md (frozen). Builds on docs/status/phase0_rain.md.


## Results (observed station data)

Main case: every day from the Friday before Memorial Day through Labor Day (102 or 109 days); loss day = at least
0.25 in between 10:00 and 18:00 local clock time; Kalshi pays when the climate-day total is at least 0.01 in.

| Station | Usable seasons | Loss days per season: mean (min-max) | Kalshi-pay days: mean (min-max) | Kalshi-pay days that are not loss days | Loss days Kalshi pays on | Days dropped |
|---|---|---|---|---|---|---|
| TTN | 28 (1999-2026) | 5.36 (1-12) | 36.43 (22-60) | 85.3% | 100% | 132 of 2,884 |
| PHL | 85 (1941-2026, not 1996) | 5.02 (0-14) | 31.26 (19-50) | 83.9% | 100% | 108 of 8,761 |
| ABE | 70 (1948-2026, not 1965-72, 1996) | 5.63 (0-11) | 34.20 (15-50) | 83.5% | 100% | 202 of 7,217 |

- Train / report split at Trenton: 16 seasons to 2014 (loss 5.38, Kalshi 37.44) and 12 seasons 2015-2026 (5.33, 35.08).
- Weekend-plus-holiday calendar (33 or 34 days): TTN loss 1.93 (0-5), Kalshi 11.00, 82.5% not loss days;
  PHL 1.76, 10.31, 82.9%; ABE 1.79, 10.86, 83.5%.
- Thresholds and windows at TTN, all days: loss days 8.75 at 0.10 in, 2.71 at 0.50 in; 3.11 for 10:00-16:00,
  7.14 for 10:00-20:00. Share of pay days that are not loss days ranges 68% to 96%. All 18 cases per station are in
  results/rain/summary_by_case.csv and summary_main.md.
- "Loss days Kalshi pays on" is 100% by construction: the opening window lies inside the same climate day, so a
  loss day always has a climate-day total of at least 0.25 in. With the GHCN-Daily total instead it is 100% at
  TTN and ABE and 97.4% at PHL (pre-1950 days where the daily file disagrees or is missing).

## Doubtful points for the lead

1. **Trenton has 28 usable seasons, not 29.** 1998 has 89.7% of opening-hour hours on the SPEC season days (gauge
   gaps 8-19 August 1998) and fails the 90% rule. SPEC_v3 says 1998-2026 (29). Train seasons become 1999-2014 (16).
   The rule was not changed. Rows for 1998 stay in daily_TTN.parquet with season_usable = False.
2. **The hourly Kalshi flag overcounts at Trenton before 2014.** 56 season days in 2002-2013 have an hourly sum of
   0.01 in (dew on the gauge, early morning) and no measurable rain in the NWS report. That is about 4.7 extra
   pay days per season in those years; 1999-2001 cannot be checked (no CLI) but GHCN suggests the same. Using
   the GHCN-Daily total, Trenton's mean is 34.54 pay days per season (20-49) instead of 36.43, and 33.50 instead of
   37.44 on the train seasons. Report seasons 2015-2026 are not affected (35.92 vs 35.08). The overlap share barely
   moves (84.5% vs 85.3%). Phase 2 may prefer ghcn_prcp_in >= 0.01 as the Kalshi payout; both are in the tables.
   Philadelphia and Allentown do not show this (3 and 11 such days in 25 seasons).
3. **Climate days with missing hours.** A usable day needs the opening hours only. On 175 usable days at TTN (usable seasons) the
   climate day has fewer than 24 hours; where the present hours are dry the flag is No. Against the NWS report
   this gives 21 wrong No answers at TTN in 25 seasons (all season days) (most are gauge outages on wet days in 2006, 2014, 2020, 2022).
4. The hourly sum is 7-9 minutes early (09:53-17:53 at Trenton). Not removable with hourly data.
5. Before 1967 daylight saving in Pennsylvania was set locally; the tz database's New York rules are used.

## Validation

**(a) Hourly Kalshi-rule flag vs NWS climate report (IEM cli.py), SPEC season days, 2002-2026 (25 seasons; the
service has no rows before 2002).** validation_kalshi_vs_cli_summary.csv, _by_season.csv, _disagreements.csv.

| Station | Days | Agree | Hourly Yes, NWS No | Hourly No, NWS Yes | 2002-2013 | 2014-2026 |
|---|---|---|---|---|---|---|
| TTN | 2,578 | 96.7% | 59 | 27 | 94.5% | 98.7% |
| PHL | 2,578 | 99.4% | 3 | 12 | 99.1% | 99.7% |
| ABE | 2,578 | 99.2% | 11 | 10 | 98.8% | 99.6% |

On usable days only: TTN 97.0%, PHL 99.5%, ABE 99.4%. Trace days in the report (246 / 304 / 302) are No on both sides.

**(b) Hourly flag vs Kalshi's settled daily results** (day-level rows read from data/raw/kalshi/rain/, aggregates
only written; validation_kalshi_settled_summary.csv). Trenton: 35 of 35 days agree (27 Aug - 30 Sep 2026; 12 of 12
SPEC season days). Philadelphia: 73 of 73 (15 Jul - 30 Sep 2026; 50 of 50 season days). 41 later settled days per
city have no hourly data here (the hourly files end 30 Sep).

**(c) Hourly climate-day sum vs GHCN-Daily PRCP, usable seasons, days with 24 hours** (validation_hourly_vs_ghcn_*).

| Station | Seasons | Days | Within 0.02 in | Wet/dry flag agrees | Hourly total / GHCN total | Worst season |
|---|---|---|---|---|---|---|
| TTN | 28 | 2,577 | 98.4% | 96.8% | 0.998 | 2014: 91.2%, total 8.38 vs 9.54 in |
| PHL | 85 | 8,419 | 97.8% | 99.4% | 1.000 | 1941: 70.6% |
| ABE | 70 | 6,701 | 99.4% | 99.6% | 1.001 | 2001: 93.9% |

Philadelphia 1941-1947 is weak day by day (71-79% within 0.02 in; season totals differ by up to 31% in 1947).
The two archives appear to split days differently in those years. From 1948 on PHL is fine. Season totals differ
by more than 5% in 3 TTN seasons and 6 PHL seasons, no ABE season.

## Park calendars against the SPEC season and window

Source: queue-times.com month pages read with the fetch tool (an LLM reads the page; third-party data).
Tables: data/processed/rain/parks.csv, park_calendar_days.csv, park_calendar_vs_spec.csv; the day-level reading
is in park_calendar_transcribed.txt. Only May-September pages were read, so first and last operating dates of
the whole year were not collected. Sesame Place is open year-round on a reduced schedule; Dorney and Great
Adventure open on weekends from early May (first open day read: 4 May 2024, 9 May 2025 at Dorney; 1 May 2026 at
Great Adventure) and stay on weekends after Labor Day.

| Park, season | SPEC season days | Days read | Open | Closed | Usual hours | Opens after 10:00 | Closes before / at / after 18:00 | Open hours inside 10:00-18:00 |
|---|---|---|---|---|---|---|---|---|
| Sesame Place 2022 | 102 | 97 | 97 | 0 | 10:00-20:00 | 0 days | 18 / 18 / 61 | 86% |
| Sesame Place 2023 | 102 | 98 | 98 | 0 | 10:00-19:00 | 1 day | 22 / 14 / 62 | 89% |
| Sesame Place 2024 | 102 | 71 | 71 | 0 | 10:00-17:00 | 0 days | 25 / 14 / 32 | 91% |
| Sesame Place 2025 | 102 | 32 | 32 | 0 | 10:00-19:00 | 0 days | 5 / 5 / 22 | 88% |
| Sesame Place 2026 | 109 | 0 | | | not read | | | |
| Dorney Park 2024 | 102 | 102 | 98 | 4 (26-29 Aug) | 10:30-21:00 | 77 days | 0 / 7 / 91 | 73% |
| Dorney Park 2025 | 102 | 102 | 95 | 7 (28 May, 4 and 11 Jun, 25-28 Aug) | 11:00-21:00 | 70 days | 0 / 5 / 90 | 73% |
| Great Adventure 2026 | 109 | 109 | 109 | 0 | 10:30-20:00 | 109 days | 0 / 0 / 109 | 76% |

What this says about the SPEC:
- **Season.** Sesame Place was open on every SPEC season day that could be read (298 of 298). Dorney was open on
  98 and 95 of 102 days; it closes Monday to Thursday in the week before Labor Day. Great Adventure 2026: 109 of
  109. The every-day season fits. All weekend and holiday days read were open at all three parks.
- **Window.** 10:00 opening fits Sesame Place exactly. Its closing time varies: 17:00 on weekdays in early June
  and late August (so the last SPEC hour is after closing on 16-35% of days), 19:00-21:00 in July and August.
  About 88% of its open hours fall inside 10:00-18:00. Dorney opens 10:30 or 11:00 on three days in four and
  closes 19:00-23:00; Great Adventure opens 10:30 and closes 19:00-22:00. For those two about a quarter of open
  hours are after 18:00, so the 10:00-20:00 sensitivity window is the closer match.
- The evidence covers 2022-2026 only. Applying the calendar to earlier decades is an assumption.

## Blocked or not read

- Shell: queue-times.com not reachable (no connection). Not routed around.
- Fetch tool refused (permission request not answered; not retried):
  https://queue-times.com/parks ; https://queue-times.com/parks/29/calendar/2024/07 ;
  https://queue-times.com/parks/29/calendar/2025/05 to /09 and /2026/05 to /09 ;
  https://queue-times.com/en-US/parks/29/calendar/2025/05, /06, /07 and /2026/05 to /09.
  So Sesame Place July 2024, May-July 2025 and all of 2026 are missing.
- Read but empty: Sesame Place May 2022 (only closed days 2-6 and 23-26 had text) and September 2023 (no grid).
- Not attempted for lack of a linked path: Dorney 2022, 2023, 2026; Great Adventure 2022-2025.
- NWS climate report before 2002: IEM returns no rows (KTTN 1995-2001 checked).
- A page read by an LLM can be wrong on single days. No second reading was made.

## Files

- Library: src/rain/__init__.py, calendar.py, hourly.py, daily.py, reference.py
- Scripts: scripts/rain_build_daily.py, rain_fetch_cli.py, rain_validate.py, rain_parks.py, rain_summary.py
  (run in that order; fetch is skipped when the cache exists)
- Tests: tests/test_rain_calendar.py, test_rain_hourly.py, test_rain_daily.py (138 tests)
- Data: data/processed/rain/daily_{TTN,PHL,ABE}.parquet, season_counts_<SID>.csv (main case, both calendars),
  season_counts_cases_<SID>.csv (18 cases), validation_*.csv (6 files), parks.csv, park_calendar_*.{csv,txt}
- Raw cache (git-ignored): data/raw/rain/iem_cli/ (NWS climate report json, KTTN/KPHL/KABE)
- Results: results/rain/summary_by_case.csv, summary_main.md, loss_vs_kalshi_days.png

## Column notes for daily_<SID>.parquet

date, station, season, source (hourly archive used for that season), weekend_or_holiday, holiday;
hours_present_<win>, usable_<win>, rain_in_<win>, loss_<thr>_<win> for windows 10_16, 10_18, 10_20 and thresholds
0p10, 0p25, 0p50 (loss flags are <NA> on days whose window is incomplete); usable and open_hours_rain_in (main
window 10_18); climate_hours_present, climate_day_total_in, kalshi_pays; season_usable; ghcn_prcp_in (reference).

## Progress log (UTC)

- 2026-11-12 03:47 Read SPEC_v3, phase0_rain.md, phase0_verdict.md, scripts/p0_rain_*.py. Inputs to reuse:
  data/processed/rain_probe/hourly_maysep_<SID>_<SOURCE>.csv.gz (hourly, UTC labels, May-Sep), cached GHCN-Daily in
  data/raw/rain/ncei_daily/, cached NWS CLI JSON for KTTN/KPHL 2021-2026 in data/raw/kalshi/iem_cli/.
  No new hourly downloads planned.
- 2026-11-12 03:47 Shell cannot reach queue-times.com (curl: no connection, HTTP 000). Not routed around; park
  calendars go through the WebFetch tool.
- 2026-11-12 03:50 Plan: src/rain/{calendar,hourly,daily,reference}.py; scripts/rain_build_daily.py,
  rain_fetch_cli.py, rain_validate.py, rain_summary.py; tests/test_rain_*.py.
- 2026-11-12 03:53 scripts/rain_fetch_cli.py done: NWS CLI json cached in data/raw/rain/iem_cli/ for KTTN, KPHL, KABE
  1995-2026 (years already cached by the Kalshi workstream in data/raw/kalshi/iem_cli/ were not fetched again).
  KTTN 1995-1998 returned 0 rows; first year with rows to be reported by the validation script.
- 2026-11-12 03:55 src/rain/{calendar,hourly,daily,reference}.py written. scripts/rain_build_daily.py run: wrote
  data/processed/rain/daily_<SID>.parquet, season_counts_<SID>.csv, season_counts_cases_<SID>.csv.
  FINDING: Trenton 1998 has 89.7% of opening-hour hours on the SPEC season days (gauge gaps 8-19 Aug 1998), so it
  fails the 90% rule. Trenton usable seasons = 28 (1999-2026), not the 29 in SPEC_v3. Phase 0 measured coverage
  over all of May-Sep, which is why it passed there. Rule not changed; reported to the lead.
- 2026-11-12 04:00 Park calendars: WebFetch reads queue-times month pages (ids: Sesame Place 29, Dorney 69, Great
  Adventure 37). Day-level transcription kept in data/processed/rain/park_calendar_transcribed.txt as I go.
  Blocked by the fetch tool (permission not answered, told not to retry): https://queue-times.com/parks (index),
  https://queue-times.com/parks/29/calendar/2024/07. Unreadable (days came back "unknown"): Sesame 2022-05, 2023-09.
- 2026-11-12 04:05 scripts/rain_validate.py written and run (three checks, tables in data/processed/rain/validation_*).
  FINDING: at Trenton 2002-2013 the hourly sum is 0.01 in on 56 season days where the NWS report has no measurable
  rain. Raw METARs show one P0001 group near 03:00-07:00 local with calm wind, clear sky, temperature = dew point
  (e.g. 2002-06-20 08:53Z, 2003-07-15 06:53Z): the gauge tipped on dew and the daily summary removed it. None after
  2013. Rule not changed. Added reference columns (ref_ghcn_*) so the size of the effect is visible.
- 2026-11-12 04:10 tests/test_rain_calendar.py, test_rain_hourly.py, test_rain_daily.py: 138 pass.
- 2026-11-12 04:12 Park calendars: after the first unanswered permission request the fetch tool refused every URL
  that was not a real link on a page already read. Walked month to month through each page's "previous month"
  link. Refused URLs were not retried. scripts/rain_parks.py written and run.
- 2026-11-12 04:18 scripts/rain_summary.py: results/rain/summary_by_case.csv, summary_main.md,
  loss_vs_kalshi_days.png (opened and checked: labels readable, mean lines clear of text).
- 2026-11-12 04:20 Status file completed.
