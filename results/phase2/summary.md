# Phase 2 results: seasonal rain-count contract versus Kalshi's daily rain contract

Pre-registration: docs/PHASE2_PREREG.md. Nothing was tuned after results were seen. Reading choices made before the first run are listed in docs/status/phase2_eval.md.

**Labels.** Rain counts (D_park, C_S, K_S) are OBSERVED station data. Every price and premium is MODELLED. Units: one loss day costs 1 (L = 1). HE = hedge effectiveness against the fixed TRAIN mean. Brackets are 95% intervals from 2,000 bootstrap draws of whole REPORT seasons (seed 473).

## The registered verdict

1. **The claim "the seasonal contract beats Kalshi's" is NOT made.** In B1 on REPORT seasons HE(3) - HE(2) = -0.039 [-0.126, -0.002]. The interval excludes zero, but on the negative side: the seasonal contract did slightly worse than the sized Kalshi position. In case D with the stand-in the difference is 0.94 [0.77, 1.09], the opposite sign. The two conditions are not both met.
2. **HE(3) is not above zero in case B.** B1: -0.37 [-0.62, -0.28]. B2: -0.58 [-4.06, -0.41]. In the pre-registration's words: the product does not hedge a park 11-30 km away, and location basis is the finding. Here the stand-in gauges are 27.7 km (PNE) and 26.7 km (DYL) from Trenton.
3. **Strategy 5 (shape versus timing and markup).** In B1 no contract shape helps: HE(5) = -0.14 [-0.23, -0.09], also below zero. Where the seasonal contract does work (D with stand-in), the gap HE(3) - HE(2) = 0.94 [0.77, 1.09] splits into 0.75 [0.54, 0.90] from contract shape (HE(3) - HE(5)) and 0.19 [0.15, 0.27] from timing and markup (HE(5) - HE(2)).

In B1 both hedges are close to empty positions. The TRAIN rule chose the smallest allowed Kalshi size (n = 0.05) and the largest allowed deductible (d = 8), because no choice gave a positive TRAIN hedge effectiveness. The seasonal contract then paid in 0 of 12 REPORT seasons. The B1 difference compares two premium drags. It does not show that Kalshi's contract hedges the park.

## Headline table (REPORT seasons; observed weather, modelled prices)

| Case | REPORT seasons | HE 1 | HE 2 | HE 3 | HE 4 | HE 5 | HE(3) - HE(2) |
|---|---|---|---|---|---|---|---|
| A | 12 | -89.67 [-327.21, -49.24] | -0.68 [-1.26, -0.49] | 0.58 [-1.16, 0.83] | 0.60 [-0.62, 0.79] | -0.29 [-0.61, -0.18] | 1.27 [0.12, 1.57] |
| B1 | 12 | -23.65 [-62.58, -15.35] | -0.33 [-0.53, -0.27] | -0.37 [-0.62, -0.28] | -0.35 [-0.58, -0.27] | -0.14 [-0.23, -0.09] | -0.04 [-0.13, -0.00] |
| B2 | 11 | -153.74 [-8486.79, -65.02] | -0.73 [-7.45, -0.53] | -0.58 [-4.06, -0.41] | -0.55 [-3.84, -0.39] | -0.31 [-5.61, -0.12] | 0.16 [0.01, 3.38] |
| D-same | 35 | -26.95 [-95.05, -13.14] | -0.25 [-0.51, -0.16] | 0.65 [0.29, 0.78] | 0.88 [0.53, 0.94] | -0.07 [-0.20, -0.01] | 0.89 [0.70, 1.16] |
| D-PNE | 30 | -22.98 [-41.06, -15.15] | -0.29 [-0.41, -0.24] | 0.65 [0.44, 0.77] | 0.75 [0.52, 0.88] | -0.11 [-0.19, -0.05] | 0.94 [0.77, 1.09] |

Strategies: 1 Kalshi daily, one contract per day. 2 Kalshi daily, sized n. 3 seasonal, six buckets (the product). 4 seasonal, exact payout (benchmark). 5 Kalshi daily at the fair-comparison price, sized n. A is circular by construction (a ceiling). The stand-in gauge is not the park.

## TRAIN-chosen parameters, headline case B1 (TRAIN 1999-2014, 16 seasons)

| Parameter | Value | Label |
|---|---|---|
| Reference level (TRAIN mean of D_park) | 4.875 | observed |
| n, strategy 2 | 0.05 | chosen on TRAIN; smallest value in the grid |
| n, strategy 5 | 0.05 | chosen on TRAIN; smallest value in the grid |
| Bucket upper edges e1..e5 | [2, 4, 5, 6, 8] | observed TRAIN counts; no repair needed |
| m_j | [1.75, 3.667, 5.0, 6.0, 7.5, 11.5] | observed |
| TRAIN seasons per bucket | [4, 3, 3, 2, 2, 2] | observed |
| q_j (add-half) | [0.2368, 0.1842, 0.1842, 0.1316, 0.1316, 0.1316] | modelled |
| d, strategy 3 | 8 | chosen on TRAIN; largest value in the grid |
| h_j | [0.0, 0.0, 0.0, 0.0, 0.0, 3.5] | holding |
| Premium, strategy 3 (loading 0.20) | 0.5526 per season | modelled |
| d and premium, strategy 4 | 8; 0.5250 | modelled |
| Monthly p (May..Sep) | {"5": 0.396, "6": 0.3933, "7": 0.3362, "8": 0.3016, "9": 0.24} | observed TRAIN frequency |
| TRAIN HE, in-sample | {"1": -31.7975, "2": -0.3299, "3": -0.0102, "4": 0.024, "5n": -19.1878, "5": -0.1144} | in-sample |

All cases and variants: results/phase2/train_params.csv.

## Case B1 in money terms (REPORT 2015-2026, 12 seasons; observed weather, modelled prices)

| Strategy | Mean net cost | Mean premium | Mean payout | Premium per $1 useful payout | Mean cost, worst 3 seasons | SD of net cost | Share of seasons with lower cost |
|---|---|---|---|---|---|---|---|
| No hedge | 5.83 [4.42, 7.17] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | no hedge | 8.67 [7.00, 10.00] | 2.59 [1.73, 3.09] | 0.00 [0.00, 0.00] |
| 2 Kalshi daily, sized | 6.35 [4.96, 7.69] | 2.13 [2.03, 2.22] | 1.61 [1.47, 1.73] | 1.32 [1.28, 1.38] | 9.19 [7.43, 10.59] | 2.55 [1.70, 3.08] | 0.00 [0.00, 0.00] |
| 3 Seasonal, six buckets | 6.39 [4.97, 7.72] | 0.55 [0.55, 0.55] | 0.00 [0.00, 0.00] | undefined (premium 6.63, useful payout 0) | 9.22 [7.55, 10.55] | 2.59 [1.73, 3.09] | 0.00 [0.00, 0.00] |
| 4 Seasonal, exact (benchmark) | 6.36 [4.94, 7.69] | 0.53 [0.53, 0.53] | 0.00 [0.00, 0.00] | undefined (premium 6.30, useful payout 0) | 9.19 [7.53, 10.53] | 2.59 [1.73, 3.09] | 0.00 [0.00, 0.00] |
| 5 Kalshi daily, fair-comparison price | 6.12 [4.75, 7.45] | 2.04 [1.98, 2.10] | 1.75 [1.61, 1.88] | 1.16 [1.10, 1.25] | 8.90 [7.10, 10.36] | 2.50 [1.66, 3.02] | 0.08 [0.00, 0.25] |

Per-season values: results/phase2/season_net_cost.csv. Figure: results/phase2/fig_b1_net_cost_by_season.png.

## Shape versus timing and markup (strategy 5; REPORT seasons)

| Case | HE(3) - HE(2), total gap | HE(3) - HE(5), contract shape | HE(5) - HE(2), timing and markup | HE(3) - HE(4), cost of bucketing |
|---|---|---|---|---|
| A | 1.27 [0.12, 1.57] | 0.88 [-0.57, 1.14] | 0.39 [0.30, 0.68] | -0.02 [-0.47, 0.18] |
| B1 | -0.04 [-0.13, -0.00] | -0.23 [-0.46, -0.14] | 0.19 [0.14, 0.34] | -0.02 [-0.04, -0.02] |
| B2 | 0.16 [0.01, 3.38] | -0.27 [-1.49, 1.55] | 0.42 [0.28, 2.93] | -0.03 [-0.22, -0.02] |
| D-same | 0.89 [0.70, 1.16] | 0.71 [0.41, 0.92] | 0.18 [0.11, 0.39] | -0.23 [-0.34, -0.03] |
| D-PNE | 0.94 [0.77, 1.09] | 0.75 [0.54, 0.90] | 0.19 [0.15, 0.27] | -0.10 [-0.14, -0.04] |

Removing the market's forecast information, spread and fees lifts the Kalshi position by about 0.2 to 0.4 in every case, but it stays below zero everywhere. Away from B, most of the gap is contract shape.

## Misspecification (case C; REPORT seasons; contract stays at 0.25 inch, 10:00-18:00, all days)

| Case | Park's true loss day | Where | HE 3 on TRAIN (in-sample) | HE 2 | HE 3 | HE(3) - HE(2) |
|---|---|---|---|---|---|---|
| C-c1-TTN | >= 0.10 inch | Trenton same station | 0.63 | -0.40 [-0.64, -0.31] | -0.09 [-1.05, 0.44] | 0.31 [-0.53, 0.89] |
| C-c1-B1 | >= 0.10 inch | B1 stand-in (PNE) | 0.33 | -0.17 [-0.25, -0.15] | -0.04 [-0.52, 0.34] | 0.13 [-0.34, 0.55] |
| C-c2-TTN | >= 0.50 inch | Trenton same station | 0.70 | -0.67 [-4.59, -0.41] | -0.58 [-5.44, -0.10] | 0.09 [-2.29, 0.59] |
| C-c2-B1 | >= 0.50 inch | B1 stand-in (PNE) | -0.30 | -0.41 [-0.65, -0.36] | -0.48 [-0.82, -0.39] | -0.06 [-0.16, -0.04] |
| C-c3-TTN | 10:00-20:00 | Trenton same station | 0.75 | -0.38 [-0.60, -0.29] | -0.00 [-0.77, 0.41] | 0.38 [-0.24, 0.81] |
| C-c3-B1 | 10:00-20:00 | B1 stand-in (PNE) | 0.01 | -0.22 [-0.39, -0.18] | -0.25 [-0.44, -0.19] | -0.02 [-0.08, -0.00] |
| C-c4-TTN | 10:00-16:00 | Trenton same station | 0.68 | -0.90 [-2.91, -0.71] | -0.50 [-8.07, 0.01] | 0.41 [-4.98, 0.80] |
| C-c4-B1 | 10:00-16:00 | B1 stand-in (PNE) | -0.09 | -0.34 [-3.33, -0.29] | -0.35 [-4.12, -0.26] | -0.00 [-0.79, 0.02] |
| C-c5-TTN | weekends and holidays only | Trenton same station | -0.24 | -2.29 [-2.80, -1.61] | -16.98 [-24.99, -11.10] | -14.70 [-22.60, -9.23] |
| C-c5-B1 | weekends and holidays only | B1 stand-in (PNE) | -1.16 | -5.71 [-6.31, -5.17] | -6.66 [-6.66, -6.66] | -0.95 [-1.49, -0.36] |

HE(3) is above zero in 0 of 10 misspecification runs on REPORT seasons. At Trenton itself the in-sample values are high (0.63 to 0.75 for c1-c4) and the REPORT values are not. With 12 REPORT seasons the intervals are very wide. The weekend-only park (c5) is hurt badly by an all-days contract: it pays a premium for rain on days it does not lose money.

## Case E, Allentown same station (no Kalshi market; strategies 0, 3, 4)

| Run | TRAIN / REPORT seasons | HE 3 | HE 4 | Mean net cost: none / 3 | Premium per $1 useful payout, 3 |
|---|---|---|---|---|---|
| E | 35 / 35 | 0.79 [0.65, 0.86] | 0.86 [0.71, 0.92] | 5.77 [5.03, 6.49] / 5.92 [5.64, 6.17] | 1.07 [0.85, 1.45] |
| E-trenton-windows | 16 / 12 | 0.82 [0.56, 0.87] | 0.91 [0.69, 0.96] | 6.67 [5.58, 7.75] / 6.28 [6.03, 6.53] | 0.86 [0.65, 1.25] |

The pre-registration names no window for E. E uses the Philadelphia windows (TRAIN 1948-1990, REPORT 1991-2026). E-trenton-windows is a sensitivity, not a registered case. E is same-station, so it is a ceiling like A.

## Registered sensitivities (REPORT seasons)

| Case | Variant | n (2) | Edges | d (3) | HE 2 | HE 3 | HE(3) - HE(2) |
|---|---|---|---|---|---|---|---|
| A | main | 0.05 | [2, 4, 5, 6, 8] | 3 | -0.68 [-1.26, -0.49] | 0.58 [-1.16, 0.83] | 1.27 [0.12, 1.57] |
| A | loading_0.10 | 0.05 | [2, 4, 5, 6, 8] | 2 | -0.68 [-1.26, -0.49] | 0.86 [0.28, 0.94] | 1.54 [1.30, 1.83] |
| A | loading_0.30 | 0.05 | [2, 4, 5, 6, 8] | 3 | -0.68 [-1.26, -0.49] | 0.30 [-2.64, 0.71] | 0.98 [-1.31, 1.40] |
| A | markup_0.068 | 0.05 | [2, 4, 5, 6, 8] | 3 | -0.56 [-1.02, -0.40] | 0.58 [-1.16, 0.83] | 1.14 [-0.12, 1.43] |
| A | edges_linear_floor | 0.05 | [2, 4, 5, 6, 8] | 3 | -0.68 [-1.26, -0.49] | 0.58 [-1.16, 0.83] | 1.27 [0.12, 1.57] |
| B1 | main | 0.05 | [2, 4, 5, 6, 8] | 8 | -0.33 [-0.53, -0.27] | -0.37 [-0.62, -0.28] | -0.04 [-0.13, -0.00] |
| B1 | loading_0.10 | 0.05 | [2, 4, 5, 6, 8] | 8 | -0.33 [-0.53, -0.27] | -0.34 [-0.56, -0.26] | -0.01 [-0.07, 0.02] |
| B1 | loading_0.30 | 0.05 | [2, 4, 5, 6, 8] | 8 | -0.33 [-0.53, -0.27] | -0.41 [-0.68, -0.31] | -0.07 [-0.18, -0.03] |
| B1 | markup_0.068 | 0.05 | [2, 4, 5, 6, 8] | 8 | -0.27 [-0.43, -0.23] | -0.37 [-0.62, -0.28] | -0.10 [-0.22, -0.05] |
| B1 | edges_linear_floor | 0.05 | [2, 4, 5, 6, 7] | 8 | -0.33 [-0.53, -0.27] | -0.24 [-0.54, 0.02] | 0.09 [-0.05, 0.47] |
| B2 | main | 0.05 | [2, 3, 5, 6, 8] | 8 | -0.73 [-7.45, -0.53] | -0.58 [-4.06, -0.41] | 0.16 [0.01, 3.38] |
| B2 | loading_0.10 | 0.05 | [2, 3, 5, 6, 8] | 8 | -0.73 [-7.45, -0.53] | -0.52 [-3.60, -0.37] | 0.21 [0.09, 3.84] |
| B2 | loading_0.30 | 0.05 | [2, 3, 5, 6, 8] | 8 | -0.73 [-7.45, -0.53] | -0.63 [-4.54, -0.45] | 0.10 [-0.07, 2.90] |
| B2 | markup_0.068 | 0.05 | [2, 3, 5, 6, 8] | 8 | -0.58 [-5.95, -0.43] | -0.58 [-4.06, -0.41] | 0.00 [-0.19, 1.88] |
| B2 | edges_linear_floor | 0.05 | [2, 3, 5, 6, 8] | 8 | -0.73 [-7.45, -0.53] | -0.58 [-4.06, -0.41] | 0.16 [0.01, 3.38] |
| D-same | main | 0.05 | [2, 4, 5, 6, 8] | 3 | -0.25 [-0.51, -0.16] | 0.65 [0.29, 0.78] | 0.89 [0.70, 1.16] |
| D-same | loading_0.10 | 0.05 | [2, 4, 5, 6, 8] | 2 | -0.25 [-0.51, -0.16] | 0.75 [0.63, 0.89] | 1.00 [0.85, 1.29] |
| D-same | loading_0.30 | 0.05 | [2, 4, 5, 6, 8] | 4 | -0.25 [-0.51, -0.16] | 0.57 [0.15, 0.70] | 0.82 [0.60, 1.06] |
| D-same | markup_0.068 | 0.05 | [2, 4, 5, 6, 8] | 3 | -0.20 [-0.41, -0.13] | 0.65 [0.29, 0.78] | 0.84 [0.64, 1.09] |
| D-same | edges_linear_floor | 0.05 | [2, 4, 5, 6, 7] | 3 | -0.25 [-0.51, -0.16] | 0.62 [0.38, 0.82] | 0.86 [0.65, 1.21] |
| D-PNE | main | 0.05 | [1, 2, 3, 4, 5] | 3 | -0.29 [-0.41, -0.24] | 0.65 [0.44, 0.77] | 0.94 [0.77, 1.09] |
| D-PNE | loading_0.10 | 0.05 | [1, 2, 3, 4, 5] | 2 | -0.29 [-0.41, -0.24] | 0.72 [0.52, 0.84] | 1.01 [0.84, 1.16] |
| D-PNE | loading_0.30 | 0.05 | [1, 2, 3, 4, 5] | 3 | -0.29 [-0.41, -0.24] | 0.61 [0.39, 0.75] | 0.91 [0.72, 1.06] |
| D-PNE | markup_0.068 | 0.05 | [1, 2, 3, 4, 5] | 3 | -0.24 [-0.34, -0.19] | 0.65 [0.44, 0.77] | 0.89 [0.71, 1.03] |
| D-PNE | edges_linear_floor | 0.05 | [1, 2, 3, 4, 5] | 3 | -0.29 [-0.41, -0.24] | 0.65 [0.44, 0.77] | 0.94 [0.77, 1.09] |

loading_0.10 and loading_0.30 change strategies 3, 4, 5. markup_0.068 changes strategies 1 and 2. edges_linear_floor is the alternative reading of the quantile rule (not registered wording; shown because the rule was ambiguous). Under it the B1 difference is 0.09 [-0.05, 0.47]: the sign flips and the interval includes zero. HE(3) in B1 is below zero in every variant. Philadelphia without the doubtful seasons 1941-47: HE(3) = 0.64 [0.45, 0.84], HE(3) - HE(2) = 0.88 [0.69, 1.21].

## Stand-in gauges (observed coordinates)

| Gauge | km to Sesame Place | km to Trenton (TTN) | km to Philadelphia Intl (PHL) |
|---|---|---|---|
| PNE (PHILADELPHIA NE) | 16.8 | 27.7 | 29.2 |
| DYL (DOYLESTOWN AIRPORT) | 26.9 | 26.7 | 51.9 |
| TTN (TRENTON/MERCER CO.) | 11.3 | 0.0 | 56.9 |

The stand-in is not the park. Sesame Place is 11.3 km from Trenton; the stand-ins are 27 to 28 km from Trenton. Usable seasons: PNE 36 (1974, 1977-79, 1987-88, 1997-2026); DYL 26 (2000-2024, 2026). File: results/phase2/standin_distances.csv.

## Things a sceptical reader should know

1. **Small sample.** Trenton cases have 12 REPORT seasons (B2 has 11) and 16 TRAIN seasons (B2 15). The ceiling case A has HE(3) = 0.58 [-1.16, 0.83]: the interval runs from clearly harmful to very good. Only the Philadelphia and Allentown cases (30 to 35 REPORT seasons) have strategy 3 intervals that stay above zero.
2. **B1 compares two near-empty hedges.** n = 0.05 is the bottom of the registered grid (zero was not allowed) and d = 8 is the top. On TRAIN the best seasonal contract had HE = -0.01, so the product failed for this gauge even in-sample. The seasonal contract paid nothing in 2015-2026, so its premium per $1 of useful payout is undefined (premium paid 6.63, payout 0). The B1 difference of -0.039 is the difference between two small premiums, measured against a fixed reference.
3. **Why the stand-in fails.** Season counts at Trenton and at PNE correlate 0.67 on TRAIN and 0.70 on REPORT (Doylestown: 0.67 and 0.60). That is too weak for a count contract with a 20% loading to pay for itself. Also, PNE had more loss days in REPORT (mean 5.83) than in TRAIN (4.88); with the reference fixed at the TRAIN mean, any premium is punished harder in REPORT.
4. **What the stand-in does and does not prove.** It shows that rain counts 27-28 km apart differ enough to defeat this contract. It does not measure the park: Sesame Place is 11.3 km from Trenton, closer than either stand-in, and no gauge at the park was available. The true basis for the park is probably smaller than in B1 and B2, but it is unmeasured. The result is a warning, not a measurement of the park's hedge.
5. **Case D with the stand-in rests on 6 TRAIN seasons.** PNE has only 1974, 1977-79 and 1987-88 before 1991. Edges from six seasons needed the tie repair (raw quantiles [1, 1, 3, 3, 5] became [1, 2, 3, 4, 5]). HE(3) = 0.65 [0.44, 0.77]. A non-registered sensitivity that takes the buckets from all 50 Philadelphia TRAIN seasons (and so picks d = 6) gives HE(3) = 0.08 [-0.30, 0.32] and HE(3) - HE(2) = 0.37 [0.06, 0.60]. The positive D stand-in result is fragile. It depends on the deductible, which six seasons chose. Its premium was also set from those six seasons (1.27 a season) and came out below the mean REPORT payout (1.87), so part of its score is a premium that turned out too low.
6. **Timing and markup versus shape.** Pricing Kalshi's contract like the seasonal one (strategy 5) recovers 0.19 [0.14, 0.34] of HE in B1, 0.39 [0.30, 0.68] in A and 0.19 [0.15, 0.27] in D with stand-in. The rest of the gap is shape: a daily 0.01-inch contract pays on about 35 days a season of which about 5 are loss days. Even at a fair-comparison price it is below zero in every case.
7. **Kalshi daily is never a hedge here.** One contract per day (strategy 1) costs about 43 a season in modelled premium against about 5.8 loss days; HE is -20 or worse. The TRAIN rule always shrinks it to the smallest size. The Kalshi price is modelled from 381 real quotes in 2025-2026, not observed for these seasons; the model probably still overstates Kalshi's seasonal protection (docs/status/phase1_kalshi.md, limit 3).
8. **Misspecification.** The conclusion that the seasonal contract helps does not survive it on Trenton REPORT seasons: HE(3) is above zero in 0 of 10 runs. The conclusion that the Kalshi daily contract does not help survives everywhere: HE(2) is below zero in all 10 runs. HE(3) - HE(2) is positive at Trenton same-station for c1-c4 but every interval includes zero.
9. **The metric is harsh on premiums by design.** The reference is the TRAIN mean of unhedged cost. A hedge with a steady premium must pay out in bad seasons to score above zero. Mean net cost is higher under every hedge in every Trenton case, as expected with a positive loading.
10. **Bootstrap limits.** Seasons are resampled as independent. Some draws have no season above the reference; those draws are dropped and counted (column n_boot_valid). TRAIN-window numbers are in-sample and have no interval.

## Files

- metrics_tidy.csv: every case x variant x strategy x window x metric with its interval.
- train_params.csv: TRAIN-chosen parameters per case and variant.
- season_net_cost.csv: per-season counts, payout, premium, net cost.
- headline_table.csv, standin_distances.csv.
- fig_b1_net_cost_by_season.png, fig_hedge_effectiveness.png.

## Deviations from the pre-registration

None forced. Additions that are not registered and are labelled as such: runs E-trenton-windows and D-PNE-phl-buckets; variant edges_linear_floor; strategy 5n; the differences HE(3) - HE(5), HE(5) - HE(2), HE(3) - HE(4).
