# Verified findings file (Phase 4, written 2026-11-12 UTC)

Facts and figure captions for the team to write the talk and the report from. Not prose for pasting: the course requires that the team writes every word. Every number names the file it came from. "OBSERVED" = station weather or real Kalshi quotes. "MODELLED" = a price, premium or net cost from a fitted model. "SIMULATED" = the LMSR market experiment. Phase 3 items are marked PENDING where no result file exists yet (results/phase3/ is empty at the time of writing).

Figures: results/talk/fig1..fig8 (1920x1080 PNG), script results/talk/make_figures.py, every printed number in results/talk/figure_numbers.csv.

Labels used below: HE = hedge effectiveness = 1 - (downside semi-variance of hedged net cost) / (downside semi-variance of unhedged cost), both measured above the TRAIN mean of unhedged cost (docs/PHASE2_PREREG.md, Metrics). 1 = all bad-season excess removed; 0 = same as no hedge; below 0 = worse than no hedge. Brackets are 95% percentile intervals from 2,000 bootstrap draws of whole REPORT seasons, seed 473. Units: one loss day costs 1 (L = 1).

---

## PART 1: TALK ORDER (10 minutes: goal 2, results 5, method 2, next 1)

### 1. Goal (2 min)

- Question: can an amusement park hedge its rainy season on a prediction market? (docs/milestone2_facts.md)
- Hypothesis, written before the test: a seasonal rain-day-count contract reduces a park's bad-season losses where Kalshi's existing daily rain contract does not. (docs/PHASE2_PREREG.md, Question)
- The buyer: a park near Trenton (Sesame Place is 11.3 km from Trenton airport, TTN). (results/phase2/standin_distances.csv)
- The risk: a loss day = at least 0.25 inch of rain between 10:00 and 18:00 local, every day from the Friday before Memorial Day through Labor Day. (docs/SPEC_v3.md via results/rain/summary_main.md)
- The baseline that exists today: Kalshi's daily rain contract (KXRAIN) for Trenton, Philadelphia, Newark, NYC. It pays $1 when the official daily total is at least 0.01 inch. (docs/status/phase1_kalshi.md)
- The product we built: a seasonal contract on the count of loss days at the settlement station, six count buckets, sold through a sponsor-funded on-chain LMSR market. (docs/PHASE2_PREREG.md strategy 3; results/market/summary.md)
- Why the pivot from temperature (one sentence if asked): Milestone I feedback said goal and product were unclear; the temperature "local layer" was a product nobody sells and beat its baseline by construction. (docs/milestone2_facts.md)

### 2. Results (5 min), one figure per point

**Fig 1 (fig1_wrong_days.png). Kalshi's rain contract pays on about 6x more days than a park loses.** OBSERVED.
- Trenton, 28 usable seasons 1999-2026: Kalshi-pay days (official daily total >= 0.01 inch) mean 34.5 per season; park loss days mean 5.4. Ratio 6.4. (data/processed/rain/season_counts_TTN.csv, columns ref_ghcn_pay_days, loss_days; results/talk/figure_numbers.csv)
- 84% of Kalshi pay days are not loss days. Kalshi pays on 100% of loss days. (same file)
- Same pattern at Philadelphia over 85 seasons (31.3 vs 5.0) and Allentown over 70 seasons (34.2 vs 5.6), hourly-sum rule. (results/rain/summary_main.md)
- Caption: Trenton 1999-2026, usable seasons, all days; Kalshi-pay days use the GHCN-Daily official total; loss days use hourly ASOS 10:00-18:00. Observed station data; no prices.

**Fig 2 (fig2_forecast_in_price.png). By the time you can buy, the forecast is already in the price.** OBSERVED.
- 517 Kalshi rain markets pulled (4 cities, 2021-2026); 403 market-days with a two-sided book 24 h before close. (docs/status/phase1_kalshi.md sections 1 and 4; data/processed/kalshi_rain/calibration.csv)
- Calibration: mean mid price 0.420, rain on 41.7% of those days. Prices are right on average. (calibration.csv, 24 h, mid, all markets; computed in figure_numbers.csv)
- Split by outcome, held-out 2026 set (four cities, Jul 15-Sep 30, 209 buyable days): mean ask 0.750 on rain days, 0.232 on dry days. (data/processed/kalshi_rain/model_eval.csv, design "hold out C", part "test (held out)", columns obs_mean_ask_rain_days / obs_mean_ask_dry_days)
- From the binned aggregates on all 403 days the same split is 0.77 / 0.26. (calibration.csv; figure_numbers.csv)
- Skill: Brier score of the mid price 0.110 against 0.247 for monthly climatology; skill score 0.55 (24 h, 344 days 2025-2026). (data/processed/kalshi_rain/sharpness.csv, row "all 2025-2026", 24 h)
- Market opens about 1.5 days before the rain day; "24 h before close" is about midnight at the start of the rain day. (docs/status/phase1_kalshi.md, log 03:59)
- A buyer of one contract every day at 24 h lost money in every city and year with real prices: premium per $1 of payout 1.04 to 1.31 (1.07 to 1.35 with fees). Trenton 2026: 1.18 (1.23 with fees), 35 markets. (data/processed/kalshi_rain/strategy_24h.csv; docs/status/phase1_kalshi.md section 6)
- Days with no offer below $1.00 were almost all rain days (2026: 15 of 15 resolved Yes): nobody sells once rain is certain. (docs/status/phase1_kalshi.md section 3)
- Caption: Kalshi ask 24 h before close, 10-cent bins, counts per bin split by the day's outcome; observed quotes, binned aggregates only (no raw rows).

**Fig 3 (fig3_hedge_effectiveness.png). The seasonal contract hedges Philadelphia; nothing hedges a park 28 km from Trenton.** Weather OBSERVED, prices MODELLED.
- All values: REPORT seasons, variant main. (results/phase2/metrics_tidy.csv; results/phase2/summary.md headline table)

| Case | REPORT seasons | HE 2 Kalshi sized | HE 3 seasonal, 6 buckets (product) | HE 4 seasonal, exact | HE 5 Kalshi at fair price | HE(3) - HE(2) |
|---|---|---|---|---|---|---|
| A Trenton same station (ceiling, circular) | 12 | -0.68 [-1.26, -0.49] | 0.58 [-1.16, 0.83] | 0.60 [-0.62, 0.79] | -0.29 [-0.61, -0.18] | 1.27 [0.12, 1.57] |
| B1 Trenton, stand-in PNE 27.7 km (REGISTERED HEADLINE) | 12 | -0.33 [-0.53, -0.27] | -0.37 [-0.62, -0.28] | -0.35 [-0.58, -0.27] | -0.14 [-0.23, -0.09] | -0.04 [-0.13, -0.00] |
| B2 Trenton, stand-in DYL 26.7 km | 11 | -0.73 [-7.45, -0.53] | -0.58 [-4.06, -0.41] | -0.55 [-3.84, -0.39] | -0.31 [-5.61, -0.12] | 0.16 [0.01, 3.38] |
| D-same Philadelphia same station | 35 | -0.25 [-0.51, -0.16] | 0.65 [0.29, 0.78] | 0.88 [0.53, 0.94] | -0.07 [-0.20, -0.01] | 0.89 [0.70, 1.16] |
| D-PNE Philadelphia, stand-in PNE 29.2 km | 30 | -0.29 [-0.41, -0.24] | 0.65 [0.44, 0.77] | 0.75 [0.52, 0.88] | -0.11 [-0.19, -0.05] | 0.94 [0.77, 1.09] |
| E Allentown same station (no Kalshi market) | 35 | n/a | 0.79 [0.65, 0.86] | 0.86 [0.71, 0.92] | n/a | n/a |

- The registered claim ("seasonal beats Kalshi") is NOT made. Its test needed HE(3) - HE(2) above zero in B1 and the same sign in D with stand-in. B1 gave -0.04 [-0.13, -0.00]; D-PNE gave +0.94. Both conditions were not met. (results/phase2/summary.md, "The registered verdict")
- In B1 both hedges are near-empty: TRAIN chose the smallest Kalshi size (n = 0.05, bottom of the grid) and the largest deductible (d = 8, top of the grid); the seasonal contract paid in 0 of 12 REPORT seasons. The B1 difference compares two premium drags. (results/phase2/summary.md; results/phase2/train_params.csv)
- Kalshi's daily contract is below zero in every case and every misspecification run (10 of 10). (results/phase2/summary.md, points 7 and 8)
- One Kalshi contract per day (strategy 1) costs 39 to 44 in modelled premium per season against about 5 to 6 loss days; HE -23 to -154. (metrics_tidy.csv strategy 1 mean_premium; summary.md headline table)
- Shape vs timing: pricing Kalshi's contract like the seasonal one (strategy 5) recovers 0.19 [0.14, 0.34] of HE in B1 and 0.19 [0.15, 0.27] in D-PNE but stays below zero; where the seasonal contract works, 0.75 [0.54, 0.90] of the 0.94 gap is contract shape. (results/phase2/summary.md, shape table)
- Caption: hedge effectiveness on held-out seasons, four strategies, 95% bootstrap intervals; rain counts observed, every premium and Kalshi price modelled (Phase 1 "skill" price model, loading 0.20); the red band marks the failed registered case; A's intervals are wide (12 seasons) and A is circular by construction.

**Fig 4 (fig4_net_cost_philadelphia.png). At Philadelphia the seasonal contract removes two-thirds of bad-season cost.** Weather OBSERVED, prices MODELLED.
- D-same, 35 REPORT seasons 1991-2026, terms fixed on TRAIN 1941-1990 (50 seasons). HE(3) = 0.65 [0.29, 0.78]. (results/phase2/metrics_tidy.csv; train_params.csv)
- Worst 10% of seasons, mean cost: 10.0 unhedged; 6.8 with the seasonal contract; 10.5 with Kalshi sized. (metrics_tidy.csv, worst_mean_unhedged / worst_mean_hedged)
- Mean net cost: 5.06 no hedge; 5.59 Kalshi sized; 5.78 seasonal. The premium (2.83 a season) raises the mean; every season pays to protect the bad ones. (metrics_tidy.csv mean_net_cost; train_params.csv premium_strategy3)
- Standard deviation of net cost: 2.70 unhedged, 1.06 seasonal. (metrics_tidy.csv sd_net_cost)
- Share of seasons where the seasonal hedge reduced cost: 34%. (metrics_tidy.csv share_seasons_reduced)
- Premium per $1 of useful payout: seasonal 1.34 [1.00, 1.93]; Kalshi sized 1.38 [1.31, 1.46]. (metrics_tidy.csv premium_per_useful_payout)
- "Two-thirds" means the HE: 65% of the downside semi-variance above the reference level is removed. It is not a two-thirds cut in mean cost (mean cost rises) and not a two-thirds cut in the worst seasons (10.0 to 6.8 is 32%). Say which one.
- Reference level 5.0 loss days (1941-1990 mean). (train_params.csv train_reference_mean_D_park)
- Caption: per-season net cost (loss days minus payout plus premium) for no hedge, Kalshi daily sized, and the seasonal count contract; Philadelphia Intl; observed loss days, modelled premiums.

**Fig 5 (fig5_market_price.png). A sponsor-funded market prices the hedge near fair value once funding is about 10x the hedge.** SIMULATED.
- LMSR cost rule, six buckets, registered edges [2, 4, 5, 6, 8] from Trenton TRAIN counts; q_j = 0.237, 0.184, 0.132, 0.184, 0.132, 0.132. (results/market/registered_buckets.csv)
- Shown: deductible d = 3 (the value TRAIN chose for the same-station cases A and D-same; B1 chose d = 8). (results/phase2/train_params.csv)
- Price per $1 of expected payout, informed start: 3.20 at b = 0.05x hedge size; 1.17 at 10x; 1.03 at 50x; 1.00 at 500x. Uniform start (hedger trades first): 1.36 at 10x, flattening at 1.18 because every bucket opens at 1/6. (results/market/hedge_pricing.csv; figure_numbers.csv)
- Informed-start price equals the registered modelled premium (1.20 x expected payout) at b = 8.5x the hedge size (d = 3; 7.8x for d = 2, 9.5x for d = 4). (results/market/break_even.csv)
- Sponsor's worst-case loss is b ln 6 = 1.79 b. Sponsor's expected loss to an informed trader is 0.0268 b. (results/market/summary.md)
- Contract: 162 passing tests in contracts/ (local Hardhat EVM), run end to end on the real 2025 Trenton count (5); not deployed to Sepolia. Gas: registered basket as first trade 354,120; deploy 3,776,901. (docs/status/phase2_market.md; results/market/gas_report.json)
- Caption: simulation of the LMSR cost rule, no real traders, no real money; "fair" means fair under the TRAIN bucket probabilities.

**Fig 6 (fig6_reach.png). How far does a weather hedge reach?** PENDING. Placeholder slide written. Expected: HE against distance for every (settlement station, exposure gauge) pair, rain and temperature, binned mean with 95% band; reach = largest bin whose lower band edge is above 0; the Trenton-PNE pair plotted as a labelled point. Source when it exists: results/phase3/*reach_curve.csv (docs/PHASE3_PREREG.md Question 1; docs/status/phase3_temp.md has the reading choices for the temperature part, fixed 2026-11-12 21:40 UTC).
- Known so far (Phase 2): the contract works at 0 km (A, D-same, E) and at 29 km from Philadelphia (D-PNE, 0.65) but not at 27-28 km from Trenton (B1 -0.37, B2 -0.58). Season counts at Trenton and PNE correlate 0.67 (TRAIN) and 0.70 (REPORT); DYL 0.67 and 0.60. (results/phase2/summary.md points 3 and 5)

**Fig 7 (fig7_leadtime.png). When must a daily contract be listed to work?** PENDING. Placeholder slide written. Expected: HE and premium per $1 of payout for buying the daily contract every day, priced at the GFS MOS probability of precipitation at leads of 1 to 7 days and at climatology, Trenton and Philadelphia same-station. Source when it exists: results/phase3/leadtime_he_by_lead.csv (docs/PHASE3_PREREG.md Question 2).
- Known so far: Kalshi lists about 1.5 days ahead; observed asks at 36/24/12/2 h exist in the Phase 1 aggregates (two-sided count 201/199/104/46 of 216 KXRAIN markets). Strategy 5 (no forecast in the price) is still below zero in every Phase 2 case, which the pre-registration says would mean shape, not timing, is the binding problem. (docs/status/phase1_kalshi.md section 3; results/phase2/summary.md)

### 3. Method (2 min)

**Fig 8 (fig8_method.png).** Boxes and arrows: pre-registered rules -> TRAIN seasons choose terms -> REPORT seasons score -> two implementations agree.
- Pre-registration written 2026-11-12 UTC before any hedge evaluation was run; no deviations were forced. (docs/PHASE2_PREREG.md; results/phase2/summary.md "Deviations")
- Windows: Trenton TRAIN 1999-2014 (16 seasons), REPORT 2015-2026 (12); Philadelphia TRAIN 1941-1990 (50), REPORT 1991-2026 (35). (results/phase2/train_params.csv)
- Chosen on TRAIN only: bucket edges (1/6..5/6 quantiles of the count), bucket means, deductible d from {0..8}, Kalshi size n from {0.05..1.0}, premium = 1.20 x expected payout, reference level. (docs/PHASE2_PREREG.md)
- Kalshi price model: ask = clamp(p + 0.504 (rain today - p) + 0.085) plus fee, fitted on 381 real quotes from 2025-2026; held-out mean cost error +0.003 per contract; it reproduces 0.73 / 0.24 on rain / dry days against observed 0.75 / 0.23. Labelled MODELLED everywhere. (docs/status/phase1_kalshi.md section 7; data/processed/kalshi_rain/model_eval.csv)
- Two independent implementations: src/hedge_eval (registered) and replication/replicate.py (written from the rules alone, no shared code). 300 of 300 shared numbers agree to 1e-6 (5 cases x 6 strategies x 5 metrics x 2 windows); 120 of them are the registered cases A, B1, D with strategies 2-5. (replication/results.csv vs results/phase2/metrics_tidy.csv; count made for this file, see docs/status/phase4_figures.md)
- Rain data check: 115 station-seasons of counts identical between the two implementations. (docs/status/phase2_replication.md)
- Tests: 138 rain tests, 43 hedge tests, 39 Kalshi tests, 61 LMSR simulation tests, 162 contract tests pass. (docs/status/phase2_market.md; phase2_eval.md; phase1_kalshi.md)

### 4. Next (1 min)

- Phase 3 reach and lead-time results (pending; see Future directions).
- Sepolia deployment and recorded demo (guide written: docs/deploy_sepolia.md; not deployed). (docs/status/phase2_market.md)
- A gauge at the park. The stand-in is 27.7 km from Trenton; the park is 11.3 km. The park's own basis is unmeasured. (results/phase2/standin_distances.csv)

---

## PART 2: REPORT ORDER (four pages, results first)

### Page 1. Goal and main result

- Goal and hypothesis: as in Part 1, section 1.
- Main result in three sentences of fact:
  1. Kalshi's daily rain contract does not hedge the park in any case tested: HE below zero in all 5 registered cases and all 10 misspecification runs; a buyer of one contract a day pays 1.04-1.31 per $1 received on real prices. (results/phase2/summary.md; data/processed/kalshi_rain/strategy_24h.csv)
  2. The seasonal count contract hedges a park whose rain matches the settlement station: HE 0.65 [0.29, 0.78] at Philadelphia over 35 held-out seasons; 0.79 [0.65, 0.86] at Allentown; 0.65 [0.44, 0.77] for a stand-in 29 km from Philadelphia. (results/phase2/metrics_tidy.csv)
  3. It failed for the registered Trenton case with a stand-in 28 km away: HE -0.37 [-0.62, -0.28]; the registered claim is not made. Location basis is the finding. (results/phase2/summary.md)
- Fig 3 is the page-1 figure.

### Page 2. Evidence: why the daily contract fails

- Fig 1 and Fig 2 numbers (Part 1, section 2).
- Decomposition (strategy 5): of the gap between the seasonal and the Kalshi hedge where the seasonal one works (D-PNE, 0.94 [0.77, 1.09]), 0.75 [0.54, 0.90] is contract shape and 0.19 [0.15, 0.27] is market timing and markup. (results/phase2/summary.md, shape table)
- Fee: Kalshi taker fee round_up_to_cent(0.07 x C x P x (1 - P)); 1.3-1.5 cents per one-contract order; whether rounding is per order or per fill is unverified. (docs/status/phase1_kalshi.md section 5; docs/contract_spec.md)
- Price model biases to state: no forecast beyond the day's own outcome; deterministic; probably still overstates Kalshi's seasonal protection (city-month slope 0.33 observed vs 0.43 modelled, 18 city-months). Sensitivity a = 0.068 changes HE(2) by about +0.05 and does not change any sign. (docs/status/phase1_kalshi.md section 7; results/phase2/summary.md sensitivities)

### Page 3. Evidence continued: the seasonal contract and the market

- Fig 4 numbers (Part 1).
- Sensitivities, D-same HE(3): loading 0.10 -> 0.75 [0.63, 0.89]; loading 0.30 -> 0.57 [0.15, 0.70]; alternative edge reading -> 0.62 [0.38, 0.82]; without doubtful seasons 1941-47 -> 0.64 [0.45, 0.84]. (results/phase2/summary.md, registered sensitivities)
- Cost of bucketing (HE(3) - HE(4)): -0.23 [-0.34, -0.03] at D-same; -0.10 [-0.14, -0.04] at D-PNE. (results/phase2/summary.md, shape table)
- D-PNE is fragile: its buckets and d rest on 6 TRAIN seasons; with Philadelphia's 50 TRAIN seasons for the buckets, HE(3) = 0.08 [-0.30, 0.32]; its premium (1.27) came out below mean REPORT payout (1.87). (results/phase2/summary.md point 5)
- Misspecification (case C, Trenton): HE(3) above zero in 0 of 10 runs on REPORT seasons; in-sample values 0.63-0.75 for c1-c4 at Trenton did not hold out; weekend-only park (c5) is hurt badly by an all-days contract (HE(3) -16.98). (results/phase2/summary.md, case C table)
- Fig 5 numbers and the contract facts (Part 1). Break-even fee: with no hedger, 11.3% of the informed trader's cost; 0% where b is below about 12-14x the hedge (the hedger's impact pays the sponsor). (results/market/summary.md; results/market/break_even.csv)
- Fig 6 / Fig 7: PENDING; insert when results/phase3 is written.

### Page 4. Conclusion, limitations, next

Conclusion facts (choose from): the hypothesis is half supported. The daily contract never hedges (robust: every case, every run). The seasonal contract hedges only where the park's rain matches the station's; 27-28 km of basis at Trenton defeated it on 12 seasons; the Trenton case is also the small-sample case.

**Limitations** (each is stated in a results file; cite it)
1. Prices are modelled. Real Kalshi prices exist for 35 Trenton market-days (2026) and 517 markets in all; the 28-season comparison uses a price model fitted on 381 real quotes. The model probably overstates Kalshi's seasonal protection. (docs/status/phase1_kalshi.md section 7; results/phase2/summary.md point 7)
2. The stand-in gauge is not the park. PNE is 16.8 km from Sesame Place and 27.7 km from Trenton; the park is 11.3 km from Trenton; no gauge at the park. The B1 result is a warning, not a measurement of the park's hedge. (results/phase2/standin_distances.csv; summary.md point 4)
3. Twelve Trenton REPORT seasons. Intervals are wide: A's HE(3) runs from -1.16 to 0.83. Only Philadelphia and Allentown (30-35 REPORT seasons) give intervals above zero. (results/phase2/summary.md point 1)
4. No real traders. The LMSR is a pricing rule; it finds a fair price only if informed traders show up; one hedger per market; buy only, no selling; the fee is hypothetical. Nothing deployed beyond a local EVM. (results/market/summary.md, Limits)
5. Single reporter oracle. SeasonCountOracle has one reporter (setReporter), a report window and a void function; no dispute mechanism. (results/market/summary.md gas table; docs/deploy_sepolia.md)
6. MOS is one forecast system. The Phase 3 lead-time study prices the contract at GFS MOS probabilities only. (docs/PHASE3_PREREG.md Question 2) PENDING.
7. Also: the metric is harsh on premiums by design (fixed TRAIN reference); seasons bootstrapped as independent; two seasons of Kalshi data from one region; the 2021-2025 NYC data used the old trace rule; fee rounding per order vs per fill unverified; the registered quantile rule was ambiguous and a different reading flips the sign of the B1 difference (0.09 [-0.05, 0.47]). (results/phase2/summary.md points 9-10 and sensitivities; docs/status/phase2_replication.md ambiguities 1-2)

**Future directions**
1. Finish Phase 3: reach in km for rain and temperature with a band (Question 1); the lead time at which the daily contract's HE first exceeds zero, or that it never does (Question 2). (docs/PHASE3_PREREG.md)
2. Measure the park's own basis: a gauge at the park, or the nearest gauge inside 11 km, for at least one season.
3. Deploy to Sepolia, replay the 2025 Trenton season, record the demo. (docs/deploy_sepolia.md)
4. Price the seasonal contract with real counterparties: who sponsors b of 8-10x the hedge, and at what fee.
5. Contract design for the Trenton case: a lower loading, a deductible chosen with more seasons, or a weekend-only index (c5 shows an all-days contract hurts a weekend park).
6. A multi-reporter or dispute-capable oracle.
7. Replace the deterministic Kalshi price model with one that follows wet spells day by day (the known bias direction).

---

## Figure captions (one line each, for the slides and the report)

- Fig 1: Trenton 1999-2026, 28 usable seasons: days Kalshi's contract pays (official daily total >= 0.01 in) vs days a park loses (>= 0.25 in, 10:00-18:00). Observed station data.
- Fig 2: Kalshi ask 24 h before close, 403 two-sided market-days 2021-2026, split by whether it rained; mean ask 0.75 on rain days, 0.23 on dry days (held-out 2026 set). Observed quotes, binned aggregates.
- Fig 3: Hedge effectiveness on held-out seasons for four strategies in four cases, 95% bootstrap intervals; the registered headline case (B1) failed. Weather observed, prices modelled.
- Fig 4: Philadelphia, 35 held-out seasons: net cost per season with no hedge, Kalshi daily sized, and the seasonal count contract; HE 0.65; worst-10% seasons 10.0 -> 6.8. Weather observed, prices modelled.
- Fig 5: LMSR market, d = 3: price per $1 of expected payout against sponsor funding as a multiple of the hedge, uniform vs informed start; crosses the registered 1.20 at 8.5x. Simulation.
- Fig 6: PENDING (Phase 3 reach curve). Placeholder slide.
- Fig 7: PENDING (Phase 3 lead time). Placeholder slide.
- Fig 8: Evaluation design: pre-registered rules, TRAIN chooses terms, REPORT scores, two independent implementations agree on 300 of 300 shared numbers.
