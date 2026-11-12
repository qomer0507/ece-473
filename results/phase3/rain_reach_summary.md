# Phase 3, Question 1: how far does a rain hedge reach? (EXPLORATORY)

Observed weather, modelled premiums. Pre-registration: docs/PHASE3_PREREG.md. Reading choices and the log: docs/status/phase3_rain.md. Every number here is read from the CSVs beside this file.

## Stations and pairs

- Candidates: 121 ASOS/AWOS stations in NJ, NY, PA, CT, DE, MD with an IEM archive beginning by 2005. Kept (>= 20 usable seasons): 30, of which 19 have an NWS daily climate report and can settle a contract.
- Not kept: 91 ({'no_present_hour': 85, 'usable_seasons<20': 6}). Listed with their season counts in data/processed/reach/rain_stations.csv.
- Usable seasons per kept station: median 30, range 20-85; 7 stations have seasons from the NCEI archive (before 1997).
- Pairs within 200 km (S with climate report, G any kept station, plus S = G): 222. Scored under the main rule (>= 20 joint usable seasons): 222, HE defined for 221. Excluded: {} (data/processed/reach/rain_pairs_excluded.csv). Exposure gauges scored: 30; settlement stations: 19.
- Same-station ceiling: 19 pairs, mean HE 0.83 (band 0.71 to 0.92).

## Reach

- pairs resampled: reach 80 km (registered definition: largest 10-km bin whose lower band edge is above 0); contiguous reach 0 km.
- exposure gauges resampled: reach 80 km (registered definition: largest 10-km bin whose lower band edge is above 0); contiguous reach 0 km.
- Sensitivity, pairs with fewer than 20 joint seasons included (pairs resampled): reach 80 km, contiguous 0 km.
- Sensitivity, pairs with fewer than 20 joint seasons included (gauges resampled): reach 80 km, contiguous 0 km.

| bin km | pairs | gauges | mean HE | 95% band (pairs) | 95% band (gauges) | mean r | mean daily agreement |
|---|---|---|---|---|---|---|---|
| 0 (S = G) | 19 of 19 | 19 | 0.83 | 0.71 to 0.92 | 0.71 to 0.92 | 1.00 | 1.000 |
| 0-10 | 3 of 3 | 3 | -0.59 | -1.53 to 0.49 | -1.53 to 0.49 | 0.67 | 0.972 |
| 10-20 | 4 of 4 | 4 | -0.27 | -0.54 to 0.02 | -0.53 to 0.02 | 0.52 | 0.961 |
| 20-30 | 8 of 8 | 7 | -0.22 | -0.63 to 0.22 | -0.65 to 0.14 | 0.66 | 0.956 |
| 30-40 | 4 of 4 | 3 | 0.23 | -0.10 to 0.63 | 0.06 to 0.31 | 0.55 | 0.958 |
| 40-50 | 2 of 2 | 2 | -0.48 | -0.96 to 0.00 | -0.96 to 0.00 | 0.47 | 0.940 |
| 50-60 | 8 of 8 | 8 | 0.01 | -0.46 to 0.49 | -0.47 to 0.47 | 0.62 | 0.944 |
| 60-70 | 3 of 3 | 3 | -0.11 | -0.38 to 0.33 | -0.38 to 0.33 | 0.52 | 0.933 |
| 70-80 | 14 of 14 | 13 | 0.29 | 0.15 to 0.44 | 0.17 to 0.45 | 0.46 | 0.938 |
| 80-90 | 11 of 11 | 10 | 0.08 | -0.17 to 0.31 | -0.15 to 0.30 | 0.41 | 0.936 |
| 90-100 | 13 of 13 | 10 | -0.65 | -1.42 to 0.03 | -1.17 to 0.07 | 0.49 | 0.936 |
| 100-110 | 12 of 12 | 10 | -0.03 | -0.44 to 0.27 | -0.48 to 0.27 | 0.41 | 0.928 |
| 110-120 | 10 of 10 | 7 | -0.24 | -1.23 to 0.38 | -1.37 to 0.40 | 0.46 | 0.921 |
| 120-130 | 20 of 20 | 17 | 0.03 | -0.15 to 0.21 | -0.15 to 0.21 | 0.37 | 0.921 |
| 130-140 | 7 of 7 | 7 | -0.06 | -0.26 to 0.18 | -0.27 to 0.17 | 0.39 | 0.918 |
| 140-150 | 20 of 20 | 15 | 0.14 | -0.02 to 0.33 | -0.00 to 0.31 | 0.38 | 0.920 |
| 150-160 | 16 of 16 | 13 | -0.10 | -0.45 to 0.18 | -0.41 to 0.19 | 0.39 | 0.924 |
| 160-170 | 12 of 12 | 8 | -0.08 | -0.31 to 0.10 | -0.34 to 0.14 | 0.22 | 0.919 |
| 170-180 | 12 of 12 | 12 | -0.02 | -0.22 to 0.20 | -0.22 to 0.19 | 0.31 | 0.923 |
| 180-190 | 14 of 15 | 12 | 0.04 | -0.09 to 0.20 | -0.09 to 0.17 | 0.20 | 0.917 |
| 190-200 | 9 of 9 | 9 | -0.04 | -0.35 to 0.16 | -0.31 to 0.15 | 0.45 | 0.917 |

## Regression of HE on distance, elevation difference and coast

| model | term | coefficient | classical SE | 95% gauge-bootstrap interval |
|---|---|---|---|---|
| all_pairs (n = 221, R2 0.05) | intercept | 0.333 | 0.102 | 0.125 to 0.562 |
| all_pairs (n = 221, R2 0.05) | dist_100km | -0.185 | 0.082 | -0.356 to -0.037 |
| all_pairs (n = 221, R2 0.05) | elev_diff_100m | -0.062 | 0.069 | -0.175 to 0.104 |
| all_pairs (n = 221, R2 0.05) | coast_g | -0.218 | 0.094 | -0.496 to 0.014 |
| without_same_station (n = 202, R2 0.02) | intercept | -0.074 | 0.130 | -0.341 to 0.232 |
| without_same_station (n = 202, R2 0.02) | dist_100km | 0.077 | 0.096 | -0.135 to 0.250 |
| without_same_station (n = 202, R2 0.02) | elev_diff_100m | -0.034 | 0.068 | -0.145 to 0.142 |
| without_same_station (n = 202, R2 0.02) | coast_g | -0.146 | 0.097 | -0.437 to 0.092 |

Units: distance per 100 km, |elevation difference| per 100 m, coast = 1 when the exposure gauge is within 15 km of the Atlantic Ocean or Long Island Sound (GSHHS shoreline, bays masked; src/reach/rain_geo.py).

## Trenton-PNE

- S = TTN, G = PNE, 27.7 km. Joint usable seasons 28 (1999-2026; TRAIN 16, REPORT 12). d = 8, premium 0.53. REPORT HE -0.35; daily agreement 0.951; count correlation 0.66. Status: ok.
- Its bin (20-30 km): mean HE -0.22, band -0.63 to 0.22 over 8.0 pairs.

## Station-level table (results/phase3/rain_station_table.csv)

- 30 exposure gauges. Best available settlement station: mean HE 0.78; it is the gauge itself for 16 gauges. Nearest climate-report station: mean HE 0.61 (median distance 0 km); HE above 0 for 24 of 30 gauges with a defined HE.

## Caveats, plain language

- Exploratory: the question was chosen after Phase 2. Nothing here is a confirmatory test.
- Pairs share stations. Each settlement station appears in many pairs and each gauge in many pairs, so the pairs are not independent draws. The pair bootstrap treats them as if they were and its band is too narrow. The gauge bootstrap resamples exposure gauges and carries each gauge's whole set of pairs along, which respects one of the two sharing structures (gauges) but not the other (settlement stations). Both bands are reported; the gauge band is the one to trust more.
- Each pair's HE rests on its REPORT seasons (8 to 34 per pair); HE of a single pair is noisy, and pairs with few seasons scatter widely. Pairs with fewer than 20 joint seasons were excluded by a rule fixed before results; the sensitivity curve puts them back.
- Bins at long distance hold pairs from different sub-regions (coast, Appalachians, lake shore); the mean over a bin is not the HE any one park would see.
- Premiums are modelled (1.2 x TRAIN mean payout); nobody sells this contract. Weather is observed.
- Gauge quality differs between stations and decades (Phase 0 and 1 found dew tips and silent gauge failures). Hourly data before 1997 is from the NCEI archive at first-order stations; the sources are never mixed inside a season but can differ between TRAIN and REPORT of one pair.
- The coast indicator is coarse (nearest vertex of a low-resolution shoreline).
