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

## Reading choices, fixed BEFORE any pair result was computed
(filled in below as the work goes; see the dated lines)

## Progress log (UTC)
- 2026-11-12 22:55 Read PHASE3_PREREG, SPEC_v3, phase1_rain.md, phase2_eval.md, phase3_temp.md (temperature
  workstream, for matching column names), src/rain, src/hedge_eval, scripts/p0_rain_*.py. The earlier attempt
  left scripts/reach_rain_stations.py (run once: 121 candidate stations, 40 with a climate report) and
  scripts/reach_rain_fetch.py (never run). Both reused after reading. IEM and NCEI reachable (HTTP 200).
