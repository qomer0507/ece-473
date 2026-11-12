# Phase 3 temperature-reach workstream

Binding document: docs/PHASE3_PREREG.md, Question 1 (temperature part and the combined analysis). EXPLORATORY.
Weather is observed. Every premium is modelled. All times UTC.

## How to rerun
1. `python scripts/reach_temp_run.py` (pairs, curve, regression CSVs; about a minute)
2. `python scripts/reach_temp_report.py` (figures and results/phase3/temp_reach_summary.md from the CSVs)
3. `python scripts/reach_combined.py` (needs the rain workstream's rain_pairs.csv and rain_reach_curve.csv)
4. `python -m pytest tests/test_reach_temp_*.py -q`

## Reading choices, fixed BEFORE any pair result was computed (2026-11-12 21:40 UTC)
Where the pre-registration leaves a rule open, the literal reading is used.
1. Pairs: G = the 84 exposure stations; S = the 40 exposure stations with has_cli. Every ordered (S, G) with
   haversine distance <= 200 km, plus S = G at distance 0. Station coordinates and elevations from stations.csv.
2. Season = May 1 to Sep 30 (SPEC_v2), years 2015-2025 (the panel). A pair's usable season needs TMAX present
   at BOTH stations on at least 90% of the 153 season days (>= 138 joint days). Counts use joint-present days only.
   Days are dropped, never imputed.
3. Exposure count at G: joint days with TMAX_G >= 90. Contract count at S: joint days with TMAX_S >= 90.
   The exposure's loss costs 1 per hot day (L = 1), as in Phase 2.
4. TRAIN = the first floor(0.6 x N) joint usable seasons in calendar order, REPORT = the rest (N = 11 for a pair
   with every season usable: TRAIN 2015-2020, REPORT 2021-2025). A pair with fewer than 2 TRAIN or 2 REPORT seasons
   is listed as failing the usable rule and gets no HE.
5. Contract (Phase 2 strategy 4): payout max(C_S - d, 0); d in {0..8} with the highest TRAIN HE, ties to the
   smallest d (hedge_eval.strategies.argmax_first); premium = 1.2 x TRAIN mean payout, charged every season.
6. HE = hedge_eval.metrics.hedge_effectiveness on REPORT seasons, reference = TRAIN mean of the unhedged cost.
   HE is NaN when no REPORT season is above the reference; such pairs are listed and left out of the curve.
7. Daily trigger agreement = share of joint days (all usable seasons) with 1{TMAX_G >= 90} = 1{TMAX_S >= 90}.
   Count correlation = Pearson r of the seasonal counts over all usable seasons (NaN if either has no variance).
8. Bins: same-station pairs form their own bin at 0 km; then (0,10], (10,20], ..., (190,200]. Bin mean = mean HE
   of the pairs with defined HE. Bootstrap A resamples pairs with replacement; bootstrap B resamples exposure
   gauges G with replacement and keeps every pair of each drawn gauge (multiplicity kept). 2,000 draws each,
   numpy default_rng(473). A bin empty in a draw is left out of that bin's interval and counted.
9. Reach = the largest bin whose 2.5th-percentile band edge is above 0, reported as the bin's upper edge in km,
   once per bootstrap scheme. Also reported (labelled, not the registered definition): the contiguous reach, the
   upper edge of the last bin before the first bin whose lower edge is not above 0.
10. Regression: OLS of HE on distance (per 100 km), absolute elevation difference |elev_G - elev_S| (per 100 m)
    and a coast indicator = 1 if the exposure gauge G is within 25 km of the GSHHS low-resolution shoreline
    (coast_km as computed in Phase 1, results/part1/location_geography.csv). Classical SEs are reported, and a
    95% interval from the gauge bootstrap (B) of the coefficients, because pairs sharing a gauge are not independent.
    Same-station pairs are included; a labelled variant leaves them out.
11. Listing map: each exposure gauge is coloured by the HE of the pair (nearest CLI station, G). The nearest CLI
    station of a CLI gauge is itself (distance 0).

## Progress log (UTC)
- 2026-11-12 21:37 Read PHASE3_PREREG, phase2_eval.md, qasim.md, SPEC_v2, src/hedge_eval, src/panel/hedge.py.
  Panel: 84 exposure stations, 40 with CLI, 11 seasons 2015-2025, 153 days each. 992 pairs within 200 km
  including the 40 same-station pairs (counted from coordinates only, before any TMAX was read).
