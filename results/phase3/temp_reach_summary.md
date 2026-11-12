# Temperature reach (Phase 3, Question 1) - EXPLORATORY

Observed weather (TMAX panel, 84 exposure stations, 2015-2025). Modelled premiums (1.2 x TRAIN mean payout). Rules: docs/PHASE3_PREREG.md and the reading choices in docs/status/phase3_temp.md.

## Pairs
- 992 ordered pairs (settlement station S with a climate report, exposure gauge G, <= 200 km), including the 40 same-station pairs. 40 settlement stations, 84 gauges.
- Every pair has 11 usable seasons: TRAIN 2015-2020 (6), REPORT 2021-2025 (5). 0 pairs fail the usable rule.
- HE defined for 951 pairs; undefined for 41 (no REPORT season above the TRAIN reference; listed in data/processed/reach/temp_pairs.csv with status he_undefined).
- TRAIN-chosen deductible d: d=0: 129, d=1: 29, d=2: 6, d=3: 16, d=4: 14, d=5: 11, d=6: 20, d=7: 34, d=8: 733. d = 8 is the grid maximum and is chosen for 733 of 992 pairs.
- HE over pairs: median -0.81, mean -6.28, min -244, max 1.00; 291 pairs above 0. Same-station pairs: median 0.74, 27 of 40 above 0.
- Daily trigger agreement: median 0.909 over pairs; same station 1.0. Seasonal count correlation: median 0.54.

## Reach (registered definition: the largest 10 km bin whose lower 95% band edge is above 0)
- pair bootstrap: reach = NONE; 0 of 21 bins have a lower edge above 0.
- gauge bootstrap: reach = NONE; 0 of 21 bins have a lower edge above 0.
- Same-station bin: mean HE -0.92, median 0.74, pair band [-2.62, 0.34], gauge band [-2.44, 0.31].
- So the temperature reach cannot be resolved: no bin, including the settlement station itself, has a lower band edge above zero. In plain words, the registered contract did not hedge the 2021-2025 hot-day counts even where the exposure sits on the settlement station.

### Curve table (registered)
| bin | pairs with HE | mean HE | median HE | pair band | gauge band |
|---|---|---|---|---|---|
| same station | 37 | -0.92 | 0.74 | [-2.62, 0.34] | [-2.44, 0.31] |
| (0,10] | 3 | -3.53 | -3.21 | [-5.33, -2.05] | [-5.33, -2.05] |
| (10,20] | 9 | -11.13 | -0.69 | [-25.95, -0.69] | [-24.34, 0.26] |
| (20,30] | 18 | -0.72 | 0.29 | [-1.86, 0.18] | [-1.89, 0.18] |
| (30,40] | 21 | -5.23 | -0.33 | [-12.51, -0.58] | [-12.79, -0.59] |
| (40,50] | 26 | -3.61 | -1.00 | [-6.57, -1.46] | [-6.37, -1.47] |
| (50,60] | 24 | -11.04 | -0.44 | [-34.13, -0.33] | [-37.44, -0.31] |
| (60,70] | 23 | -2.35 | -0.60 | [-4.64, -0.51] | [-4.88, -0.51] |
| (70,80] | 43 | -3.05 | -0.77 | [-5.19, -1.30] | [-5.14, -1.24] |
| (80,90] | 39 | -6.62 | -1.02 | [-13.61, -2.25] | [-13.89, -2.27] |
| (90,100] | 71 | -4.27 | -1.12 | [-6.82, -2.15] | [-7.10, -2.09] |
| (100,110] | 60 | -4.72 | -0.85 | [-9.44, -1.77] | [-9.51, -1.52] |
| (110,120] | 52 | -6.93 | -1.30 | [-11.35, -3.14] | [-11.11, -3.36] |
| (120,130] | 68 | -6.74 | -0.45 | [-12.09, -2.74] | [-13.60, -1.74] |
| (130,140] | 57 | -11.41 | -1.63 | [-18.96, -5.65] | [-20.91, -4.87] |
| (140,150] | 73 | -7.86 | -0.85 | [-13.55, -3.57] | [-13.50, -3.41] |
| (150,160] | 55 | -4.98 | -1.11 | [-9.50, -2.06] | [-9.60, -1.96] |
| (160,170] | 69 | -7.24 | -0.65 | [-10.98, -3.99] | [-11.67, -3.11] |
| (170,180] | 62 | -10.76 | -1.88 | [-17.50, -5.52] | [-17.80, -4.84] |
| (180,190] | 75 | -4.69 | -1.29 | [-7.95, -2.28] | [-8.11, -2.19] |
| (190,200] | 66 | -7.26 | -0.69 | [-14.30, -2.52] | [-14.28, -2.39] |

## Why the same-station hedge fails (read from the pair table, not a new rule)
- For a same-station pair the net cost is C - max(C - d, 0) + premium. With d = 8 and TRAIN mean counts of 20-40 hot days, the contract pays nearly every season, the premium is 20-40 loss-days, and net cost sits at a constant 8 + premium = reference + 0.2 x (reference - 8), which is ABOVE the reference every season. The hedged semi-variance is then the square of the loading; it beats the unhedged semi-variance only when REPORT seasons are far hotter than TRAIN. 2021-2025 was not far hotter than 2015-2020 at most stations.
- HE is unbounded below. A pair whose REPORT seasons barely exceed the reference has a tiny unhedged semi-variance and an HE like -244. Bin means are dragged by such pairs; the medians are shown as a labelled extra and are also at or below zero beyond the same-station bin.
- The d grid {0..8} was written for rain counts (Phase 2) and carried into the temperature rule by the pre-registration ('same d and premium rule'). It is run as registered.

## Labelled sensitivity (NOT registered): d grid widened to {0..40}
- pair bootstrap: reach = NONE; 0 bins above 0.
- gauge bootstrap: reach = NONE; 0 bins above 0.
- Same-station bin: mean 0.31, median 0.90, pair band [-0.24, 0.76], gauge band [-0.22, 0.74]. 32 of 40 same-station pairs above 0; d chosen: median 21, 88 pairs at the new grid maximum.
- Over all pairs: median HE 0.00, 367 of 951 above 0. The wider grid lifts the same-station bin but no bin's band clears zero. Reach is unresolved under this reading too.

## Regression of HE on distance, elevation difference and coast (registered)
OLS, pairs with defined HE. Classical SE treats pairs as independent, which is false (pairs share gauges); read the gauge-bootstrap interval. coast = 1 if the exposure gauge is within 25 km of the shoreline.

all_pairs (n = 951, 80 gauges, R2 = 0.042)

| term | coef | classical SE | gauge 95% |
|---|---|---|---|
| intercept | -0.193 | 1.631 | [-2.471, 1.557] |
| dist_100km | -1.120 | 1.183 | [-4.219, 2.814] |
| abs_elev_diff_100m | -2.316 | 0.429 | [-6.729, 1.092] |
| coast | -5.348 | 1.294 | [-10.156, -1.605] |

excluding_same_station (n = 914, 80 gauges, R2 = 0.039)

| term | coef | classical SE | gauge 95% |
|---|---|---|---|
| intercept | -0.442 | 1.910 | [-3.335, 1.749] |
| dist_100km | -0.902 | 1.345 | [-4.195, 3.421] |
| abs_elev_diff_100m | -2.324 | 0.439 | [-6.724, 1.072] |
| coast | -5.501 | 1.350 | [-10.453, -1.622] |

- Distance: -1.12 HE per 100 km, gauge interval [-4.22, 2.81]: spans zero. Elevation difference: -2.32 per 100 m [-6.73, 1.09]: spans zero. Coast: -5.35 [-10.16, -1.60]: below zero under the gauge bootstrap. R2 is 0.04; the regression explains almost nothing of HE because HE's spread is dominated by its lower tail.
- Sensitivity grid: distance 1.54 [-0.59, 5.28], elevation -2.69 [-7.27, 0.18], coast -0.12 [-1.05, 0.88]. The coast effect does not survive the wider grid.

## Listing map (results/phase3/temp_listing_map.png)
- Each exposure gauge coloured by the HE of the pair (nearest settlement station, gauge). 45 of 84 gauges above 0; 4 undefined. Nearest-station distance: median 16 km, max 101 km.
- By state: CT: median HE -3.26, 12% above 0 (n=8); DE: median HE 0.30, 100% above 0 (n=2); MD: median HE -1.40, 0% above 0 (n=8); NJ: median HE 0.11, 64% above 0 (n=11); NY: median HE 0.80, 74% above 0 (n=31); PA: median HE 0.21, 50% above 0 (n=24).
- Poorly served areas: Maryland and the Delmarva shore (0 of 8 above 0), coastal Connecticut (1 of 8), and the hot corridor of south-eastern Pennsylvania and central New Jersey show orange; upstate New York and the northern tier show blue, but there the counts are small (often d = 0 on a station with one or two hot days a season), so a blue dot there says little about a hedge anyone would buy.

## Caveats
- Five REPORT seasons per pair. HE on five seasons is a rough number; the bands reflect pair and gauge sampling, not season sampling.
- Every pair shares the same 11 seasons, so the bins are not independent of one another: one hot or mild summer moves the whole curve. The pre-registered bootstrap resamples pairs (and, here, gauges), not seasons.
- The gauge bootstrap and the pair bootstrap give almost the same bands, because the dominant spread is between pairs within the same bin, not between gauges.
- 41 pairs with undefined HE are left out of the curve; they are mostly far pairs where the gauge's REPORT counts never exceeded its TRAIN mean.
- Coast indicator uses a low-resolution shoreline and ignores the Great Lakes (Phase 1).
- Teterboro 2023-2025 is suspect (docs/status/qasim.md); it is in the panel as SPEC says.
- Nothing was dropped after seeing results. The d-grid sensitivity and the median curve were added after seeing the registered result and are labelled as such everywhere.
