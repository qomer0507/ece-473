# Phase 2 evaluation workstream (Qasim)

Binding document: docs/PHASE2_PREREG.md. Weather is observed. Every price and premium is modelled.

## How to continue if interrupted
1. `python scripts/hedge_build_standins.py` (stand-in gauges PNE, DYL; a few seconds)
2. `python -m pytest tests/test_hedge_*.py -q`
3. `python scripts/hedge_run.py` (all cases and sensitivities; writes results/phase2/*.csv and data/processed/hedge/)
4. `python scripts/hedge_report.py` (figures and results/phase2/summary.md from the CSVs; no new computation)

## Reading choices, fixed BEFORE any hedge result was computed (2026-11-12 04:45 UTC)
Where the pre-registration leaves a rule open, the literal reading is used. Alternatives are run as labelled sensitivities.
1. Joint usable days: a day counts if the 10:00-18:00 window is complete at S and at the park gauge. For c3 (park
   window 10:00-20:00) the park's own window must also be complete at the park gauge, or D_park is undefined.
   A season counts if it passes the Phase 1 90% rule at both locations.
2. K_S uses ghcn_prcp_in >= 0.01 at S. A missing daily total is No (Philadelphia 1945 has 73 such days).
3. Monthly p: share of TRAIN joint-usable days with K = 1, per calendar month, at S.
4. Kalshi market price (strategies 1, 2): modelled_cost(p, "skill", fitted a, s, u), one-contract order, cost = ask + fee,
   order and payout scaled by 1 - u on rain days. n contracts scale premium, fee and payout linearly.
   "Premium" of strategies 1 and 2 includes the fee.
5. Markup sensitivity uses a = 0.068 as written (the JSON holds 0.0684).
6. Ties when maximising TRAIN hedge effectiveness go to the smallest n and the smallest d.
7. Bucket edges: e_k = smallest TRAIN count x with at least k/6 of TRAIN seasons <= x (the ceil(kN/6)-th smallest).
   Bucket j is e_(j-1) < C <= e_j. "Ties merged upward": an edge not above the previous one becomes previous + 1.
   Sensitivity: floor of the linearly interpolated quantile ("edges_linear_floor").
8. Empty-bucket midpoint: middle of the bucket's integer range (bucket 1 starts at 0).
9. d depends on the loading (the premium is in the net cost), so d is re-chosen on TRAIN in the loading sensitivities.
10. Strategy 4 "same d rule": d chosen on TRAIN for strategy 4 itself (not copied from strategy 3).
11. Strategy 5: price per contract-day = (1 + loading) * monthly p. No fee, every order filled. "5n" = 1 contract
    (variant of strategy 1), "5" = n re-chosen on TRAIN at this price (variant of strategy 2). Tables that say
    "strategy 5" mean the sized one.
12. Worst seasons: 3 for Trenton cases; ceil(10% of N) for Philadelphia and Allentown cases. Ranked by unhedged cost,
    ties to the earlier season. Recomputed inside each bootstrap draw.
13. Bootstrap: numpy default_rng(473).integers, one set of 2,000 season draws per case, shared by all strategies
    (paired). The TRAIN reference level stays fixed. Draws where a metric is undefined (no season above the
    reference) are left out and counted. TRAIN-window metrics are in-sample and carry no interval.
14. Case E names no window. Philadelphia windows are used (TRAIN to 1990, REPORT 1991-2026). Sensitivity: Trenton windows.
15. B2 runs: Doylestown has 15 TRAIN (2000-2014) and 11 REPORT seasons (2015-2026 without 2025) usable at both.
16. D with PNE: only 6 joint TRAIN seasons exist (1974, 1977-79, 1987-88); 30 REPORT seasons (1997-2026). Run as
    registered. Sensitivity "D-PNE-phl-buckets": edges, m_j, q_j from all Philadelphia TRAIN seasons.
17. sd of net cost uses N - 1. "Share of seasons where the hedge reduced net cost" = net cost strictly below unhedged.

## Progress log (UTC)
- 2026-11-12 04:31 Read PHASE2_PREREG, SPEC_v3, phase1_rain.md, phase1_kalshi.md, rain_price_model.py, price_model.json.
- 2026-11-12 04:36 scripts/hedge_build_standins.py written and run with src/rain unchanged. PNE: 36 usable seasons
  (1974, 1977-79, 1987-88, 1997-2026). DYL: 26 (2000-2024, 2026). Table: data/processed/hedge/standin_seasons.csv.
- 2026-11-12 04:45 src/hedge_eval/{data,metrics,strategies,bootstrap,cases}.py written. Season counts per case
  checked (alignment only, no hedge numbers looked at): A 16/12, B1 16/12, B2 15/11, D-same 50/35, D-PNE 6/30, E 35/35.
  Reading choices above written down at this point.
- 2026-11-12 04:52 tests/test_hedge_metrics.py, test_hedge_strategies.py, test_hedge_alignment.py: 43 pass
  (hand examples, joint alignment, leak test on synthetic and real tables).
- 2026-11-12 04:58 scripts/hedge_run.py run (74 s): 17 registered runs + 2 labelled sensitivity runs, 5 variants each.
  Outputs: results/phase2/metrics_tidy.csv, train_params.csv, season_net_cost.csv, standin_distances.csv;
  data/processed/hedge/season_aggregates.csv. No rule was changed after this point.
- 2026-11-12 05:10 scripts/hedge_report.py: summary.md, headline_table.csv, two figures. Both figures opened and
  checked. Fixed: reference-line label overlapped bars; legend overlapped axis labels; second title overstated case A.
- 2026-11-12 05:12 Status: COMPLETE.

## Results in brief (REPORT seasons; observed weather, modelled prices; details in results/phase2/summary.md)
- B1 (headline): HE(2) -0.33 [-0.53, -0.27], HE(3) -0.37 [-0.62, -0.28], HE(3) - HE(2) -0.039 [-0.126, -0.002].
  TRAIN chose n = 0.05 (grid minimum) and d = 8 (grid maximum); the seasonal contract paid in 0 of 12 seasons.
- B2: HE(3) -0.58 [-4.06, -0.41]. D-PNE: HE(3) 0.65 [0.44, 0.77], HE(3) - HE(2) 0.94 [0.77, 1.09] (6 TRAIN seasons).
- A (ceiling): HE(3) 0.58 [-1.16, 0.83]. D-same: 0.65 [0.29, 0.78]. E: 0.79 [0.65, 0.86].
- Registered verdict: the claim "the seasonal contract beats Kalshi's" is NOT made. HE(3) is not above zero in
  case B: location basis is the finding. HE(3) is above zero in 0 of 10 misspecification runs.

## Deviations
None forced. Not registered, labelled wherever shown: runs E-trenton-windows and D-PNE-phl-buckets; variant
edges_linear_floor; strategy 5n; differences HE(3) - HE(5), HE(5) - HE(2), HE(3) - HE(4).
docs/PHASE2_PREREG.md was not edited (outside this workstream's files).

## Doubtful points for the lead
1. The pre-registration is dated 2026-11-12; this log uses the machine clock (UTC), which matches.
2. B1's difference is between two near-empty positions. Its sign flips under the alternative quantile reading
   (edges [2,4,5,6,7]: +0.09 [-0.05, 0.47]). HE(3) < 0 in B1 under every variant.
3. D-PNE has 6 TRAIN seasons. With Philadelphia-wide buckets HE(3) falls to 0.08 [-0.30, 0.32].
4. Case E had no registered window; Philadelphia windows used.
5. The stand-ins are 27-28 km from Trenton; Sesame Place is 11.3 km. The park's own basis is unmeasured.
6. The Kalshi grid has no n = 0, so strategy 2 is forced to hold 0.05 contracts although TRAIN prefers none.
