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
- 2026-11-12 22:05 src/reach_temp/{contract,curve,regress}.py and scripts/reach_temp_run.py written. 24 tests in
  tests/test_reach_temp_{pairs,curve}.py pass (pair sets, 60/40 split, hand HE, leak test, gauge bootstrap keeps
  whole gauges, planted regression slope). No real pair result looked at yet.
- 2026-11-12 22:12 scripts/reach_temp_run.py run (8 s). 992 pairs: 951 with HE, 41 with HE undefined (no REPORT
  season above the TRAIN reference), 0 failing the usable rule (every pair has 11 usable seasons, TRAIN 2015-2020,
  REPORT 2021-2025). REGISTERED RESULT: no 10 km bin, including the same-station bin, has a lower band edge above
  0 under either bootstrap. Same-station bin mean HE -0.92, pair band [-2.62, 0.34], gauge band [-2.44, 0.31].
  d = 8 (the grid maximum) is chosen for 733 of 992 pairs: stations with 20-40 hot days a season cannot get a
  deductible near their mean count, so the contract pays nearly every season and the 20% loading on a premium of
  20-40 loss-days alone drives net cost above the reference. Decided at this point (not registered, labelled):
  one sensitivity with the d grid widened to {0..40}, and a median curve beside the registered mean curve.
  The registered mean curve and reach stay the headline. No other rule changed.
- 2026-11-12 22:20 Rerun with the labelled sensitivity (d grid {0..40}; files *_sens_dgrid40.csv). Registered run
  unchanged. Sensitivity: same-station bin mean HE 0.31, median 0.90, bands [-0.24, 0.76] (pair) and
  [-0.22, 0.74] (gauge); still no bin with a lower band edge above 0, so reach is unresolved under both rules.
  Registered regression (951 pairs, 80 gauges, R2 0.04): distance -1.12 per 100 km, gauge band [-4.22, 2.81];
  |elev diff| -2.32 per 100 m [-6.73, 1.09]; coast -5.35 [-10.16, -1.60]. HE is unbounded below (minimum -244),
  so the means are dragged by pairs whose REPORT seasons barely exceed the reference. Next: figures and summary.
- 2026-11-12 22:35 scripts/reach_temp_report.py: temp_reach.png, temp_listing_map.png, temp_reach_summary.md.
  Both figures opened and checked. Fixed: legend sat on the band (moved below the axes); footnote ran off the
  right edge (wrapped). Listing map: 45 of 84 gauges above 0; MD 0 of 8, CT 1 of 8; blue in upstate NY is
  mostly stations with one or two hot days a season.
