# Phase 0 rain-data and parks probe (questions 1 and 3)

Status: COMPLETE for Phase 0 (2026-11-12 03:40 UTC). Answers first, then tables, caveats, and the progress log.

## Question 1: can we support "0.25 inch during 10am-6pm" over 40+ seasons?

**At Trenton: no.** Hourly rain at Trenton-Mercer (TTN) exists only from the 1998 season, when the automated
station started reporting it. That gives 29 seasons (1998-2026), all with at least 90% of opening-hour hours.
Before 1998 neither IEM (304,960 reports 1930-1989, every one without a precipitation value) nor NCEI's hourly
archive (no 1-hour groups; 6-hour totals only in the 1980s) has hourly rain for Trenton. Trenton's daily record
is just as short: GHCN-Daily PRCP for USW00014792 covers 1945 and then 1998-2026.

**At Philadelphia, Newark, Allentown, JFK and LaGuardia: yes**, by joining NCEI's hourly archive (before 1997)
to IEM's METAR archive (1997 on). Seasons (May-Sep) with at least 90% of the 10:00-18:00 local hours present:

| Station | First hourly season | Seasons >= 90% | Of those, 1980-2026 | Seasons below 90% | Daily PRCP first year | Daily seasons >= 90% |
|---|---|---|---|---|---|---|
| TTN Trenton-Mercer | 1998 | **29** | 29 | none since 1998 | 1945, then 1998 | 30 |
| PHL Philadelphia Intl | 1941 | **85** | 46 | 1996 | 1940 | 85 |
| EWR Newark | 1948 | **75** | 46 | 1967-69, 1996 | 1865 (see caveat 7) | 152 |
| ABE Allentown | 1948 | **70** | 46 | 1965-72, 1996 | 1948 | 79 |
| LGA LaGuardia | 1948 | **67** | 45 | 1948, 1965-72, 1996, 2011 | 1940 | 87 |
| JFK | 1949 | **55** | 46 | 1950, 1965-66, 1969, 1971-72, 1996; no hourly data 1951-64, 1967-68 | 1948 | 69 |
| PNE Philadelphia NE | 1973 | **34** | 31 | most of 1973-87, 1996, 2003; no hourly data 1989-95 | 1945 | 51 |
| NYC Central Park | 1965 (3-hourly), 1996 hourly | **31** | 31 | most seasons before 1996 (3-hourly), 1996 | 1869 | 158 |
| DYL Doylestown | 1999 | **26** | 26 | 1999, 2025 | 1999 | 24 |
| WRI McGuire AFB | 2000 | **19** | 19 | 2000-2006, 2009 | 1949 (ends 1970) | 22 |
| BLM Belmar/Monmouth | 1992 | **11** | 11 | 1992-2011, 2021, 2024-2026 | none usable | 0 |
| NEL Lakehurst | 2000 | **1** | 1 | nearly all | 1945 (ends 1988) | 42 |

Source: data/processed/rain_probe/coverage_summary.csv, hourly_coverage_by_season.csv, hourly_coverage_best_source.csv.
Every station loses 1996 (about half the season is missing in both archives, the year the report format changed).
1965-72 at ABE, LGA, NYC (and the JFK years present) and 1968-69 at EWR are 3-hourly only (share 0.375 = 3 of 8 hours).

**Can missing be told from zero? It depends on the product.**
- IEM `hourlyprecip.py`: **no** before 2012. Dry hours are simply absent (TTN May-Sep 2005: 189 rows, none zero),
  so a dry hour and a missing hour look the same. From 2012 it writes one row per hour with 0.0.
- Raw METAR from IEM `asos.py` (what this probe uses): **yes, mostly.** An hour counts as present when the routine
  report exists, is from an automated AO2 station, and does not carry the PNO remark (rain gauge not operating);
  no P-group then means zero. What it cannot catch is a gauge that failed without raising PNO.
  At TTN that happened on 12 of 3,916 compared days (daily total >= 0.03 in, hourly sum 0.00), e.g. 2014-05-22
  (daily 1.47 in, hourly 0.00).
- NCEI hourly archive before 1997: zeros are explicit ("01,0000") and the daily check below supports them.

**What the hourly value means (IEM).** The value labelled HH:00 is the P-group of the routine METAR issued near
HH:53 (TTN :53, PHL :54, ABE/EWR/NYC/JFK/LGA :51), i.e. rain from about (HH-1):53 to HH:53. Times are UTC unless
`tz=` is passed. Trace is 0.0001 in hourlyprecip.py (T in asos.py with `trace=T`). Special reports within the hour
are already reduced to one value per hour in hourlyprecip.py; asos.py returns every report, and this probe takes
the maximum in the hour. "10:00-18:00" here is the 8 hours labelled 10..17 America/New_York, which is 09:53-17:53
at Trenton: a 7-9 minute offset that cannot be removed with hourly data.

**Hourly sum vs daily PRCP** (days with all 24 hours, local-standard-time day; hourly_vs_daily_summary.csv):

| Station, period | Days | Within 0.02 in | Wet days within 0.02 in | Hourly lower / higher | Largest gap |
|---|---|---|---|---|---|
| TTN 2021-2025 | 709 | **97.7%** | 93.4% | 12 / 4 | 0.53 in |
| PHL 2021-2025 | 746 | **98.9%** | 96.8% | 5 / 3 | 0.25 in |
| TTN 1998-2026 | 3,916 | 98.2% | 95.0% | 43 / 29 | 1.47 in |
| PHL 1997-2026 | 4,157 | 98.7% | 95.8% | 35 / 21 | 1.46 in |
| PHL 1941-1995 (NCEI hourly) | 8,262 | 97.6% | 92.5% | 114 / 81 | 2.26 in |
| EWR 1948-1995 (NCEI hourly) | 6,553 | 99.8% | 99.3% | 11 / 5 | 0.72 in |
| ABE 1948-1995 (NCEI hourly) | 5,861 | 99.9% | 99.8% | 1 / 2 | 0.07 in |

Disagreements are of three kinds: the hourly sum is zero or far too low while the daily total is not (gauge
outage, daily total later filled in; clusters in 2009 and 2014 at TTN); pairs of adjacent days where rain near
midnight is split differently (2011-08-03/04: -0.49 then +0.49); and small differences of 0.03-0.07 in.
Season totals agree within 0.5% (TTN 1998-2026: 502.29 in hourly vs 504.61 in daily).

**Preliminary first look (not a result).** Per season, Saturday before Memorial Day through Labor Day.
"Any rain" = daily PRCP > 0; "opening-hours" = >= 0.25 in in the 8 opening hours. prelim_counts_summary.csv.

| Station | Seasons | Day set | Days | Any-rain days: mean (min-max) | Opening-hours days: mean (min-max) | Any-rain days that are not opening-hours days |
|---|---|---|---|---|---|---|
| TTN | 29 (1998-2026) | weekends + 3 holidays | 33 | 10.1 (5-18) | 1.9 (0-5) | **80.8%** |
| TTN | 29 | every day | 102 | 33.8 (20-48) | 5.3 (1-12) | 84.4% |
| PHL | 85 (1941-2026) | weekends + 3 holidays | 33 | 10.3 (4-18) | 1.7 (0-5) | 83.3% |
| PHL | 85 | every day | 102 | 30.8 (15-49) | 4.9 (0-14) | 84.3% |
| ABE | 70 (1948-2026) | weekends + 3 holidays | 33 | 10.8 (2-18) | 1.8 (0-5) | 83.4% |
| EWR | 75 (1948-2026) | weekends + 3 holidays | 33 | 10.2 (4-16) | 1.5 (0-6) | 85.6% |

Days dropped for incomplete opening hours or missing daily: TTN 50 of 957 weekend/holiday days (10 of them in 1998,
7 in 2011). The per-season table for TTN is data/processed/rain_probe/prelim_counts_TTN.csv (also PHL, ABE, EWR).

## Question 3: parks

**Past operating calendars are public only for recent seasons, and only from a third party.** queue-times.com
keeps dated open/closed calendars with hours: Great Adventure from March 2018, Dorney Park from June 2019,
Sesame Place from January 2022. Luna Park is not listed there. Nothing older was found: the parks' own sites show
the current season only, web.archive.org is blocked for the fetch tool, and thrill-data.com and lunaparknyc.com
returned errors. So for 40+ seasons a stand-in rule is unavoidable.

**The weekend-and-holiday rule is not what these parks do in summer.** Every month checked shows daily operation
from Memorial Day weekend to Labor Day:

| Park | Evidence (queue-times.com unless noted) | Typical hours | Season outside summer |
|---|---|---|---|
| Great Adventure | open every day Jun 2024 and Jul 2019; daily from Thu 23 May 2024; closed Tue-Thu after Labor Day 2023 | 10:30 to 19:00-22:00 | Fri-Sun in May; Wikipedia gives March to December |
| Dorney Park | open every day Jun 2019 (one closure) and Jul 2024; daily from Fri 24 May 2024; weekends only after Labor Day 2024 | 10:00/10:30 to 20:00-22:00; 11:00 in May and Sep | Wikipedia: May through October; 2021 opened 22 May |
| Sesame Place | open every day Jul 2023; daily from Fri 26 May 2023; Sat-Sun after Labor Day 2023 | 10:00 to 19:00-20:00 | year-round since 2021 (Wikipedia); water rides Memorial Day to Labor Day |
| Luna Park | Time Out: "open daily for the season starting Friday, May 24" 2024; 6sqft: opened 29 Mar 2025 at 11 a.m., Fri-Sun until Memorial Day weekend | 11:00 opening; closing time not found | Wikipedia: April-October; closing date not found |

**Proposed stand-in.** Operating days = every day from the Friday before Memorial Day through Labor Day
(about 102 days). Report the weekends-plus-holidays set (33 days) as the revenue-weighted alternative, since
weekends carry the crowds. Opening hours 10:00-18:00 fit Sesame Place exactly; Great Adventure and Dorney open
10:30 and close 19:00-22:00, Luna Park opens 11:00, so the window misses their evenings. The evidence covers
2018-2025 only; applying the rule to earlier decades is an assumption.

**Coordinates and distances** (parks.csv, park_station_distances.csv; coordinates from each park's Wikipedia
page, stations from IEM metadata, haversine):

| Park | Lat, lon | Nearest stations, km (NWS daily climate report?) |
|---|---|---|
| Sesame Place | 40.18500, -74.87194 | TTN 11.3 (yes), PNE 16.8 (no), DYL 26.9 (no), WRI 30.4 (no), PHL 46.0 (yes) |
| Great Adventure | 40.13750, -74.44000 | NEL 13.7 (no), WRI 18.7 (no), MJX 26.5 (not in stations.csv), BLM 26.8 (not in stations.csv), TTN 35.5 (yes) |
| Dorney Park | 40.57794, -75.53153 | XLL 3.7 (AWOS, not in stations.csv), ABE 10.7 (yes), DYL 44.1 (no) |
| Luna Park | 40.57397, -73.97848 | JFK 19.6 (yes), EWR 20.1 (yes), NYC 22.8 (yes), LGA 24.3 (yes) |

## Recommendation

- **Lead with Dorney Park and Allentown (ABE).** It is the only pairing with a station 10.7 km away that has a
  daily climate report, 70 seasons of opening-hours rain, and 99.9% hourly-daily agreement before 1996.
- **Sesame Place and Trenton** is the closest pairing (11.3 km) and Trenton is a Kalshi city, but it gives 29
  seasons, not 40+. If Sesame Place must lead, Philadelphia (PHL, 46 km, 85 seasons) is the long-history proxy
  and 1998-2026 can measure how well PHL stands in for TTN.
- **Great Adventure has no usable nearby station**: Lakehurst has 1 good season, McGuire 19, and neither has a
  climate report. Trenton at 35.5 km is the practical choice.
- Luna Park has four long stations within 25 km but no calendar archive.

## Caveats

1. The 40+ season claim rests on NCEI's hourly archive before 1997, pulled with a simple parser (1-hour groups,
   quality codes 3 and 7 dropped). It was checked against daily totals at PHL, EWR and ABE only.
2. 1996 is unusable everywhere; 1965-72 is unusable at ABE, LGA, JFK, NYC; JFK has no hourly rain 1951-64.
3. A failed gauge without a PNO remark reads as zero rain. About 0.3% of days at TTN.
4. The opening window is offset 7-9 minutes early (09:53-17:53 at TTN).
5. The daily comparison uses the local-standard-time day; in summer that is 01:00 to 01:00 on the clock.
6. Traces count as zero in both the hourly sums and the any-rain rule.
7. EWR's daily file starts in 1865 with flagged rows that predate the airport; treat anything before 1931 as a
   different site until checked. NEL daily ends 1988 and WRI daily ends 1970.
8. Preliminary counts use daily PRCP for "any rain"; Kalshi's exact rule is the other probe's question.
9. Calendar evidence is from an LLM reading of queue-times pages, a few months per park, not a full scrape.

## Blocked or not found

- thrill-data.com, lunaparknyc.com: client error from the fetch tool. web.archive.org: blocked.
- Park calendars before 2018 (Great Adventure), 2019 (Dorney), 2022 (Sesame Place), any year (Luna Park): not found.
- Luna Park closing time and last operating date: not found.

## Files

- Scripts: scripts/p0_rain_fetch_iem.py, p0_rain_fetch_ncei_daily.py, p0_rain_fetch_ncei_hourly.py,
  p0_rain_analyze.py, p0_rain_prelim.py, p0_rain_parks.py
- Raw (133 MB): data/raw/rain/iem_asos/, ncei_global_hourly/, ncei_daily/, iem_hourlyprecip/, iem_meta/, iem_help/
- Processed: data/processed/rain_probe/ (coverage tables, hourly_maysep_<station>_<source>.csv.gz, comparison and
  preliminary count tables, parks.csv, park_station_distances.csv)

## Progress log (UTC)

- 2026-11-12 01:22 Read docs/PHASE0.md. Created data/raw/rain/, data/processed/rain_probe/.
- 2026-11-12 01:25 Saved IEM help pages (data/raw/rain/iem_help/). hourlyprecip.py reads IEM table `hourly`
  (source read from github.com/akrherz/iem pylib/iemweb/request/hourlyprecip.py).
- 2026-11-12 01:30 First findings from samples at TTN:
  - hourlyprecip.py returns nothing before about 1997, only wet hours for 2000-2010 (dry hours are simply absent),
    and one row per hour (0.0 for dry) from about 2012. So in that product "missing" and "zero" look the same before ~2012.
  - asos.py (raw METAR): pre-ASOS observations (tagged IEM_DS3505 / IEM_GHCNH) carry p01i = M for every report sampled.
  - Hourly value labelled HH:00 = the P-group of the routine METAR issued at about HH:53 (e.g. valid 19:00Z <- 19:53Z METAR).
- 2026-11-12 01:35 Saved IEM network metadata (data/raw/rain/iem_meta/*.geojson). Starting full pulls with asos.py.
- 2026-11-12 01:40 scripts/p0_rain_fetch_iem.py running (asos.py, 2 requests per station, 3 s apart, cached .csv.gz).
  scripts/p0_rain_fetch_ncei_daily.py done for 12 stations (GHCN-Daily PRCP).
- 2026-11-12 01:45 TTN profile: 304,960 IEM reports 1930-1989, every p01i = M. First P-group in a TTN METAR is 1998.
  So IEM has no hourly rain at Trenton before ASOS. Probed NCEI global-hourly (ISD): TTN 1975 has no AA1 group,
  1985 only 6-hour groups; PHL 1975 and 1985 have 1-hour groups with explicit zeros. Wrote
  scripts/p0_rain_fetch_ncei_hourly.py to pull ISD AA1-AA4 1941-2005 for the stations (5-year blocks).
- 2026-11-12 01:55 Parks: coordinates from Wikipedia; queue-times.com has dated open/closed calendars with hours
  (Great Adventure from 2018-03, Dorney from 2019-06, Sesame Place from 2022-01; Luna Park not listed).
  thrill-data.com and lunaparknyc.com fetches failed (client error); web.archive.org blocked for WebFetch.
- 2026-11-12 02:05 scripts/p0_rain_analyze.py and scripts/p0_rain_parks.py written; first run on partial downloads.
- 2026-11-12 02:15 IEM pulls finished for all 12 stations (24 requests, one retry after a connection reset on EWR).
  Cross-checked my hourly reduction against IEM's own hourlyprecip.py for TTN 2005/2012/2024 and PHL 2024:
  1-2 hours per season differ by more than 0.005 in.
- 2026-11-12 02:20 Work paused (usage limit). Resumed 03:24.
- 2026-11-12 03:27 NCEI hourly pull had stopped at NEL 1991-1995 with a truncated file; refetched, pull complete (130 files).
- 2026-11-12 03:30 Fixed a bug: hours with the PNO remark were counted present from 2012 on (IEM writes 0.00 there). Reran.
- 2026-11-12 03:33 scripts/p0_rain_prelim.py: hourly-vs-daily check and preliminary counts written.
- 2026-11-12 03:40 Status file completed.
