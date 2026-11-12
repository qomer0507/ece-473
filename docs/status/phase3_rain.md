# Phase 3 rain-reach workstream

Binding document: docs/PHASE3_PREREG.md, Question 1 (rain part). EXPLORATORY.
Weather is observed. Every premium is modelled. All times UTC.

## How to rerun (or resume after an interruption)
1. `python scripts/reach_rain_stations.py` (candidate list from the cached IEM network geojson)
2. `python scripts/reach_rain_fetch.py iem` then `python scripts/reach_rain_fetch.py ncei` (cached; skips files
   that exist, so a cut-off run can simply be started again)
3. `python scripts/reach_rain_build.py` (hourly reduction, daily tables, season counts, station table)
4. `python scripts/reach_rain_pairs.py` (pairs, HE, curve, regression, station-level table)
5. `python scripts/reach_rain_report.py` (summary.md and the figure from the CSVs)
6. `python -m pytest tests/test_reach_rain_*.py -q`

## Reading choices, fixed BEFORE any pair result was computed (2026-11-12 23:03 UTC)
Where the pre-registration leaves a rule open, the literal reading is used. Code: src/reach/rain_*.py.
1. Stations: every station of the IEM networks NJ_ASOS, NY_ASOS, PA_ASOS, CT_ASOS, DE_ASOS, MD_ASOS whose IEM
   archive begins on or before 2005-12-31 (121). Hourly precipitation: IEM asos.py (p01i + METAR, 1990-2026) for
   all; NCEI global-hourly (ISD, AA1-AA4) 1941-2005 for stations whose IEM archive begins before 1990 and that have
   a USAF/WBAN id. Same requests and the same hour-coding rules as Phase 0 (src/reach/rain_hourly.py copies
   scripts/p0_rain_analyze.py; checked to reproduce the Phase 0 TTN and PHL hourly files row for row). The 12
   Phase 0 stations use their existing files in data/processed/rain_probe/.
2. Daily tables: src.rain.daily.build_daily unchanged (one source per season, loss day = >= 0.25 in over the
   8 clock hours 10:00-17:59 local, usable day = all 8 hours present, usable season = >= 90% of opening-window
   hours over the Friday-before-Memorial-Day .. Labor Day season). A station is KEPT with >= 20 usable seasons.
3. Climate report: has_cli from data/processed/panel/stations.csv, mapped by cli_id = "K" + IEM sid.
4. Pairs: every ordered (S, G), S kept with has_cli, G kept, haversine distance <= 200 km on IEM coordinates,
   plus S = G at distance 0. Elevation from IEM metadata. Coast indicator: within 15 km of the Atlantic Ocean or
   Long Island Sound, from the GSHHS low-resolution shoreline cached in data/processed/panel/outlines.csv with
   Chesapeake Bay, Delaware Bay and the Hudson masked out (src/reach/rain_geo.py has the exact mask).
5. Joint day: the 10:00-18:00 window is complete at S and at G (Phase 2 reading choice 1). Joint usable season:
   passes the 90% rule at both stations. Counts C_S, C_G and the daily agreement use joint days only.
6. Windows: TRAIN = the first floor(0.6 N) joint usable seasons in calendar order, REPORT = the rest.
7. Contract: payout max(C_S - d, 0), d in {0..8} with the highest TRAIN HE, ties to the smallest d
   (hedge_eval.strategies.argmax_first); premium = 1.2 x TRAIN mean payout (modelled), charged every season.
   Exposure cost = C_G (L = 1). HE = hedge_eval.metrics.hedge_effectiveness on REPORT with the reference fixed at
   the TRAIN mean of C_G. HE is NaN when no REPORT season is above the reference; such pairs stay in the table
   (he_defined = False) and are left out of means and bootstraps.
8. Pair usable rule (main): at least 20 joint usable seasons, the same number the station rule uses (so TRAIN has
   >= 12 and REPORT >= 8 seasons). Pairs with fewer are listed in rain_pairs_excluded.csv with their numbers.
   Labelled sensitivity: every pair with >= 2 TRAIN and >= 2 REPORT seasons (rain_reach_curve_sensitivity.csv).
9. Bins: same-station pairs form their own bin at 0 km; then (0,10], (10,20], ..., (190,200]. Bin mean = mean HE
   of pairs with a defined HE. Bootstrap A resamples pairs; bootstrap B resamples exposure gauges G and keeps every
   pair of each drawn gauge (multiplicity kept). 2,000 draws each, numpy default_rng(473). A bin empty in a draw
   is left out of that bin's interval and counted. The same for the mean count correlation (pair bootstrap).
10. Reach = the largest distance bin whose 2.5th-percentile band edge is above 0, as the bin's upper edge in km,
    once per bootstrap scheme (registered). Also reported, labelled: the contiguous reach (upper edge of the last
    bin before the first bin whose lower edge is not above 0).
11. Regression: OLS of HE on distance (per 100 km), |elev_G - elev_S| (per 100 m) and the coast indicator of G.
    Classical SEs and a 95% interval from the gauge bootstrap of the coefficients. Same-station pairs included;
    a labelled variant leaves them out.
12. Station-level table: per exposure gauge G, the settlement station with the highest REPORT HE (ties to the
    nearer one) and the nearest climate-report station (G itself when it has one).
13. Trenton-PNE: the (TTN, PNE) pair of this analysis (its own windows), plotted and labelled.
14. (added 2026-11-12 23:12, before the full build) A gauge that reports 0.00 every hour passes the 90% rule
    (Phase 0: a failure without PNO cannot be caught). The SPEC rule is kept as the main rule; the station table
    gets n_usable_zero_rain (usable seasons whose opening-hours rain total is 0.00 in) and such stations are
    listed in the summary. Seen in the smoke test: SWF, 12 usable seasons, 0 loss days (not kept anyway).

## Progress log (UTC)
- 2026-11-12 22:55 Read PHASE3_PREREG, SPEC_v3, phase1_rain.md, phase2_eval.md, phase3_temp.md (temperature
  workstream, for matching column names), src/rain, src/hedge_eval, scripts/p0_rain_*.py. The earlier attempt
  left scripts/reach_rain_stations.py (run once: 121 candidate stations, 40 with a climate report) and
  scripts/reach_rain_fetch.py (never run). Both reused after reading. IEM and NCEI reachable (HTTP 200).
- 2026-11-12 22:57 Pull started in the background: `scripts/reach_rain_fetch.py iem` then `ncei`, one request at
  a time, cached under data/raw/rain/reach/ (requests.log per source). IEM answers 429 now and then; the script
  waits 20 s and retries (all retries so far succeeded). About 25 s per station.
- 2026-11-12 23:00 src/reach/rain_hourly.py (Phase 0 reduction rules): reproduces the Phase 0 TTN (IEM) and PHL
  (NCEI) hourly files row for row (0 mismatches in present or precip_in).
- 2026-11-12 23:03 src/reach/{rain_geo,rain_pairs,rain_curve}.py, scripts/reach_rain_{build,pairs,report}.py,
  tests/test_reach_rain_{pairs,curve}.py (13 pass). Reading choices above written down before any pair was scored.
- 2026-11-12 23:07 First pass of scripts/reach_rain_build.py on the 21 stations pulled so far plus the 12 Phase 0
  stations, then reach_rain_pairs.py and reach_rain_report.py, to check that the pipeline runs end to end
  (30 kept stations, 222 pairs). Numbers not read as results; everything is rerun when the pull is complete.
  Figure opened: the Trenton-PNE label sat on the curve; moved below the point. No rule changed.
- 2026-11-12 23:15 The container restarted; the background pull died after 46 IEM stations (the last request, ART,
  got an empty reply). Pull restarted with the same script (cached files are skipped).
- 2026-11-12 23:47 IEM pull complete: 109 stations (all 121 candidates minus the 12 Phase 0 stations), 0 failures,
  requests logged in data/raw/rain/reach/iem_asos/requests.log. NCEI pull running (pre-1990 archive stations).
15. (added 2026-11-12 23:54, after the station table of the full IEM pull was read but before any pair was
    scored on it) UNV has 20 usable seasons of which 15 report 0.00 in over the whole season (silent gauge);
    ELM 1 of 30, ITH 2 of 20. The main rule is unchanged (literal SPEC). Labelled sensitivity added: zero-rain
    seasons are treated as unusable, stations re-kept at >= 20 seasons, pairs rebuilt and rescored
    (rain_pairs_sens_nozero.csv, rain_reach_curve_sens_nozero.csv).
