# Phase 2 independent replication (log, UTC)

Purpose: recompute the Phase 2 headline numbers from the written rules alone (docs/PHASE2_PREREG.md, SPEC_v3,
phase1_rain.md, phase1_kalshi.md, phase0_rain.md for the hourly-file coding). Not read: src/hedge_eval/,
scripts/hedge_*.py, tests/test_hedge_*.py, data/processed/hedge/, results/phase2/, docs/status/phase2_eval.md.
Not imported: anything under src/. No comparison with the other implementation was made here.

Code: replication/replicate.py (pandas/numpy only; run `python replication/replicate.py`, about 70 s).
Outputs: replication/results.csv, params.csv, per_season_B1.csv, season_compare_phase1.csv, ambiguity_sensitivity.csv.
Weather counts are OBSERVED; all premiums and Kalshi prices are MODELLED.

## Log
- 2026-11-11 (session clock) Read the four documents. Hourly files: an hour is present only if a row exists with
  present = True; present with precip_in 0.0 is a dry hour; trace is already 0.0; absent rows are missing hours.
- Built own calendar (Memorial Day = last Monday of May, season starts the Friday before; Labor Day = first Monday
  of September), opening-hours totals (hours labelled 10..17), usable day (all 8 hours), usable season (>= 90% of
  season-day opening hours), joint alignment (days usable at both stations, seasons usable at both).
- Official daily total: column ghcn_prcp_in of data/processed/rain/daily_{TTN,PHL}.parquet (only that column and date).
- Check against Phase 1 season_counts_{TTN,PHL}.csv (all_days rows): 115 station-seasons (TTN 29, PHL 86),
  loss days, GHCN pay days, usable days and season-usable flag all identical. 0 differ.
- Ran cases A, B1, D (plus D without 1941-47 and D with PNE as stand-in, which has only 6 TRAIN seasons).
- Ran one-at-a-time alternative readings (ambiguity_sensitivity.csv), with the bootstrap interval for HE(3)-HE(2).

## Readings chosen (main run)
1. Source per station-season: the archive with more present opening-hour hours on season days (tie: IEM from 1997,
   NCEI before). Gives NCEI to 1995/96 and IEM after; matches Phase 1 counts exactly.
2. Missing official daily total = Kalshi No (PHL 1945: 73 days).
3. Joint seasons: each station must pass its own 90% rule; days = usable at both.
4. p = share of Kalshi-pay days by calendar month over the case's TRAIN usable season days. rain_today = GHCN flag.
5. Kalshi fee with fractional n: n x round-up-to-cent(0.07 x ask x (1 - ask)), i.e. one-contract-order fee per contract.
6. Unfilled rule: on rain days the order (cost and payout) is scaled by 1 - u, u = 0.0833.
7. Edges: e_k = smallest observed count v with TRAIN share(C <= v) >= k/6; bucket j = (e_{j-1}, e_j]; top bucket
   above e5; a tied edge is moved up by one to keep six buckets (never needed in A, B1, D).
8. Ties in the TRAIN argmax: smallest n, smallest d (no ties occurred).
9. Strategy 4: d chosen again for strategy 4 itself.
10. Strategy 5: n contracts every usable day at (1 + loading) x p_month, no fee, every order filled, n chosen on
    TRAIN from the same grid.
11. Bootstrap: REPORT seasons resampled with replacement, numpy default_rng(473), 2,000 draws, TRAIN reference
    level and all TRAIN-chosen parameters held fixed, percentile interval.

## Results (main run)
TRAIN-chosen parameters
| Case | n (strat 2) | edges | m_j | d (3) | h_j | q_j | premium 3 | d (4) | premium 4 | n (5) |
|---|---|---|---|---|---|---|---|---|---|---|
| A | 0.05 | 2,4,5,6,8 | 1.75, 3.667, 5, 6, 8, 12 | 3 | 0, 0.667, 2, 3, 5, 9 | .237 .184 .132 .184 .132 .132 | 3.337 | 2 | 4.125 | 0.05 |
| B1 | 0.05 | 2,4,5,6,8 | 1.75, 3.667, 5, 6, 7.5, 11.5 | 8 | 0, 0, 0, 0, 0, 3.5 | .237 .184 .184 .132 .132 .132 | 0.553 | 8 | 0.525 | 0.05 |
| D | 0.05 | 2,4,5,6,8 | 1.111, 3.4, 5, 6, 7.5, 9.5 | 3 | 0, 0.4, 2, 3, 4.5, 6.5 | .179 .198 .179 .160 .198 .085 | 2.835 | 3 | 2.808 | 0.05 |

n = 0.05 is the bottom of the grid in every case (TRAIN HE of strategy 2 is negative for every n and falls with n).
In B1 d = 8 is the top of the grid (TRAIN HE of strategy 3 is negative for every d; best is -0.010).

Hedge effectiveness (TRAIN reference level)
| Case | Window | 2 | 3 | 4 | 5 | HE(3) - HE(2) [95%] |
|---|---|---|---|---|---|---|
| A | TRAIN | -0.160 | 0.885 | 0.918 | 0.009 | |
| A | REPORT | -0.682 | 0.585 | 0.603 | -0.294 | 1.267 [0.117, 1.573] |
| B1 | TRAIN | -0.330 | -0.010 | 0.024 | -0.114 | |
| B1 | REPORT | -0.334 | -0.373 | -0.352 | -0.140 | -0.039 [-0.126, -0.002] |
| D | TRAIN | -0.415 | 0.778 | 0.827 | -0.175 | |
| D | REPORT | -0.246 | 0.646 | 0.875 | -0.068 | 0.892 [0.704, 1.163] |

Extra: D without 1941-47: REPORT 2/3/4/5 = -0.245 / 0.638 / 0.892 / -0.073. D with PNE stand-in (6 TRAIN, 30 REPORT
seasons): -0.294 / 0.647 / 0.751 / -0.106, difference 0.942 [0.765, 1.089].
Mean net cost and total premium: replication/results.csv. In B1 the bucketed contract pays nothing in any REPORT
season (largest C_S is 8, the top bucket starts at 9), so strategy 3 there is the premium alone.

## Ambiguities in the pre-registration and their effect (B1 REPORT, HE(3) - HE(2); main = -0.039 [-0.126, -0.002])
1. Fee for a fractional number of contracts. Literal "round up to the cent per order" with n = 0.05 charges one
   cent on 5 cents of exposure: HE(2) -1.101, difference +0.729 [0.573, 1.240]. No rounding: HE(2) -0.309,
   difference -0.064 [-0.166, -0.023]. The sign of the headline depends on this reading.
2. Bucket edge quantile and which side a tied value falls. Linear-interpolated quantile floored, or tied seasons
   put in the bucket above: edges 2,4,5,6,7 (B1) and HE(3) -0.241, difference +0.093 [-0.055, 0.466]. Rounded or
   ceiling: same as main. The sign depends on this too (the contract then pays in 2019).
3. Which seasons count in a two-station case. If a season needs >= 90% of days usable at both stations (instead
   of each station passing its own rule): 11 TRAIN / 11 REPORT seasons, HE(3) -0.066, difference +0.308 [-0.091, 0.485].
4. Source choice hour by hour instead of per season: difference -0.032 [-0.110, 0.003].
5. Unfilled-order rule off (u = 0): HE(2) -0.309, difference -0.064.
6. Missing official total dropped instead of No: no effect on A, B1; D HE(3) 0.631 (edges 2,4,5,6,7, d = 2).
7. Strategy 4 deductible copied from strategy 3: only A changes (HE(4) 0.537 instead of 0.603).
8. Strategy 5 priced as a flat seasonal premium (1 + loading) x n x TRAIN mean K_S: B1 HE(5) -0.033 (main -0.140);
   A HE(5) -0.572 with n = 0.15.
9. Tie-break in the argmax: no effect. n = 0 is not in the grid, so strategy 2 cannot choose "no hedge".
10. "Same set of days": C_S in B1 is counted on days usable at both stations, so it is not the count the oracle
    would report (which uses Trenton's own usable days). Not varied.
11. Pre-registered sensitivities (not ambiguities): a = 0.068 gives difference -0.092 [-0.208, -0.046]; loading
    0.10 gives -0.005 [-0.070, 0.024]; loading 0.30 gives -0.074 [-0.184, -0.029].

## Not done
- Strategy 1 is computed (results.csv) but was not asked for; cases B2, C, E and the secondary metrics other than
  mean net cost, total premium, mean payout and standard deviation were not replicated.
- No comparison with the registered implementation (left to the lead).
