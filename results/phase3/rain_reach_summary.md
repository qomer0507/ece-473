# Phase 3, Question 1: how far does a rain hedge reach? (EXPLORATORY)

Observed weather, modelled premiums. Pre-registration: docs/PHASE3_PREREG.md. Reading choices and the log: docs/status/phase3_rain.md. Every number here is read from the CSVs beside this file.

## Stations and pairs

- Candidates: 121 ASOS/AWOS stations in NJ, NY, PA, CT, DE, MD with an IEM archive beginning by 2005. Kept (>= 20 usable seasons): 82, of which 39 have an NWS daily climate report and can settle a contract.
- Not kept: 39 ({'usable_seasons<20': 39}). Listed with their season counts in data/processed/reach/rain_stations.csv.
- Usable seasons per kept station: median 28, range 20-85; 43 stations have seasons from the NCEI archive (before 1997).
- Kept stations with a usable season whose opening-hours rain total is 0.00 in (gauge silent, not caught by the 90% rule): 8: ELM (1), ERI (2), SYR (1), PIT (1), MIV (1), ART (1), ITH (2), UNV (15).
- Pairs within 200 km (S with climate report, G any kept station, plus S = G): 956. Scored under the main rule (>= 20 joint usable seasons): 926, HE defined for 916. Excluded: {'few_joint_seasons': 30} (data/processed/reach/rain_pairs_excluded.csv). Exposure gauges scored: 81; settlement stations: 39.
- Same-station ceiling: 39 pairs, mean HE 0.82 (band 0.65 to 0.92).

## Reach

- pairs resampled: reach 0 km (registered definition: largest 10-km bin whose lower band edge is above 0); contiguous reach 0 km.
- exposure gauges resampled: reach 0 km (registered definition: largest 10-km bin whose lower band edge is above 0); contiguous reach 0 km.
- Sensitivity, pairs with fewer than 20 joint seasons included (pairs resampled): reach 0 km, contiguous 0 km.
- Sensitivity, pairs with fewer than 20 joint seasons included (gauges resampled): reach 0 km, contiguous 0 km.
- Sensitivity, zero-rain seasons treated as unusable (80 stations, 911 pairs; dropped ['ITH', 'UNV']; pairs resampled): reach 0 km, contiguous 0 km.
- Sensitivity, zero-rain seasons treated as unusable (80 stations, 911 pairs; dropped ['ITH', 'UNV']; gauges resampled): reach 0 km, contiguous 0 km.

| bin km | pairs | gauges | mean HE | median HE | 95% band (pairs) | 95% band (gauges) | mean r | mean daily agreement |
|---|---|---|---|---|---|---|---|---|
| 0 (S = G) | 39 of 39 | 39 | 0.82 | 0.94 | 0.65 to 0.92 | 0.65 to 0.92 | 1.00 | 1.000 |
| 0-10 | 3 of 3 | 3 | -0.60 | -0.74 | -1.53 to 0.48 | -1.53 to 0.48 | 0.68 | 0.973 |
| 10-20 | 9 of 9 | 8 | 0.04 | -0.14 | -0.31 to 0.41 | -0.31 to 0.48 | 0.65 | 0.962 |
| 20-30 | 17 of 17 | 15 | 0.00 | -0.03 | -0.30 to 0.29 | -0.26 to 0.28 | 0.64 | 0.956 |
| 30-40 | 22 of 22 | 19 | -0.02 | -0.02 | -0.24 to 0.19 | -0.24 to 0.23 | 0.50 | 0.950 |
| 40-50 | 26 of 26 | 21 | -0.09 | 0.10 | -0.44 to 0.17 | -0.44 to 0.18 | 0.53 | 0.944 |
| 50-60 | 23 of 23 | 19 | -0.01 | 0.09 | -0.23 to 0.22 | -0.23 to 0.25 | 0.55 | 0.943 |
| 60-70 | 20 of 20 | 16 | -0.21 | -0.22 | -0.48 to 0.03 | -0.41 to -0.02 | 0.45 | 0.937 |
| 70-80 | 44 of 45 | 37 | -0.10 | 0.12 | -0.54 to 0.17 | -0.55 to 0.20 | 0.40 | 0.936 |
| 80-90 | 37 of 38 | 27 | -0.18 | -0.07 | -0.55 to 0.08 | -0.52 to 0.10 | 0.39 | 0.934 |
| 90-100 | 66 of 67 | 46 | -2.17 | -0.07 | -6.65 to -0.12 | -6.43 to -0.08 | 0.41 | 0.930 |
| 100-110 | 64 of 65 | 45 | 0.04 | 0.16 | -0.16 to 0.20 | -0.13 to 0.20 | 0.45 | 0.930 |
| 110-120 | 37 of 38 | 29 | -0.21 | -0.01 | -0.49 to 0.02 | -0.52 to 0.04 | 0.44 | 0.925 |
| 120-130 | 73 of 75 | 50 | -0.00 | 0.06 | -0.16 to 0.13 | -0.13 to 0.11 | 0.37 | 0.923 |
| 130-140 | 60 of 61 | 43 | 0.05 | 0.11 | -0.11 to 0.20 | -0.11 to 0.21 | 0.38 | 0.921 |
| 140-150 | 65 of 65 | 44 | -0.06 | 0.02 | -0.20 to 0.07 | -0.19 to 0.07 | 0.35 | 0.922 |
| 150-160 | 52 of 52 | 34 | -0.02 | 0.03 | -0.17 to 0.12 | -0.16 to 0.11 | 0.35 | 0.921 |
| 160-170 | 64 of 65 | 45 | 0.06 | 0.06 | -0.04 to 0.16 | -0.04 to 0.15 | 0.38 | 0.917 |
| 170-180 | 62 of 62 | 42 | -0.10 | -0.04 | -0.24 to 0.03 | -0.25 to 0.03 | 0.28 | 0.920 |
| 180-190 | 76 of 77 | 45 | 0.03 | -0.00 | -0.06 to 0.11 | -0.06 to 0.11 | 0.31 | 0.916 |
| 190-200 | 57 of 57 | 43 | -0.06 | 0.00 | -0.28 to 0.10 | -0.27 to 0.09 | 0.30 | 0.916 |

HE has no lower bound: 51 of 916 pairs are below -1 (worst POU-LGA, 94 km, HE -125: a contract that paid in TRAIN-like seasons and then charged its premium in REPORT seasons where the gauge was dry). The registered bin mean is pulled down by such pairs (the 90-100 km bin most of all); the median beside it is the more stable summary. Over all pairs with S != G the median HE is 0.02 and 52% of them are above 0, so the hedge beyond the station is a coin flip around zero, not a slow decay.

## Regression of HE on distance, elevation difference and coast

| model | term | coefficient | classical SE | 95% gauge-bootstrap interval |
|---|---|---|---|---|
| all_pairs (n = 916, R2 0.01) | intercept | 0.069 | 0.359 | -0.215 to 0.306 |
| all_pairs (n = 916, R2 0.01) | dist_100km | -0.001 | 0.272 | -0.176 to 0.212 |
| all_pairs (n = 916, R2 0.01) | elev_diff_100m | -0.045 | 0.097 | -0.094 to 0.007 |
| all_pairs (n = 916, R2 0.01) | coast_g | -0.785 | 0.344 | -2.307 to -0.045 |
| without_same_station (n = 877, R2 0.01) | intercept | -0.253 | 0.427 | -0.680 to 0.083 |
| without_same_station (n = 877, R2 0.01) | dist_100km | 0.215 | 0.312 | -0.028 to 0.542 |
| without_same_station (n = 877, R2 0.01) | elev_diff_100m | -0.038 | 0.099 | -0.088 to 0.013 |
| without_same_station (n = 877, R2 0.01) | coast_g | -0.768 | 0.360 | -2.331 to -0.012 |

Units: distance per 100 km, |elevation difference| per 100 m, coast = 1 when the exposure gauge is within 15 km of the Atlantic Ocean or Long Island Sound (GSHHS shoreline, bays masked; src/reach/rain_geo.py).

## Trenton-PNE

- S = TTN, G = PNE, 27.7 km. Joint usable seasons 28 (1999-2026; TRAIN 16, REPORT 12). d = 8, premium 0.53. REPORT HE -0.35; daily agreement 0.951; count correlation 0.66. Status: ok.
- Its bin (20-30 km): mean HE 0.00, band -0.30 to 0.29 over 17 pairs. The point sits inside the band: Trenton-PNE is a typical pair at that distance, not an unlucky one.
- Phase 2 (case B1, strategy 4, windows 1999-2014 / 2015-2026) gave HE(4) -0.35 [-0.58, -0.27]; the 60/40 split here lands on the same 16 / 12 seasons, so the number is the same.

## Station-level table (results/phase3/rain_station_table.csv)

- 81 exposure gauges, 39 of them climate-report stations (their nearest settlement station is themselves, HE = the same-station ceiling).
- The 42 gauges without a climate report: nearest climate-report station at a median 40 km, HE median 0.11 (mean 0.14), above 0 for 25 of 41. 'Best' settlement station (highest REPORT HE among up to 21 candidates): median 0.71, above 0 for 41; median distance 107 km.
- The 'best' column is a maximum over many noisy REPORT HEs and is chosen on REPORT seasons, so it overstates what a buyer could know in advance (several 'best' stations are 100-190 km away). It says how good the luckiest pairing looks, not which station to list.

## Caveats, plain language

- Exploratory: the question was chosen after Phase 2. Nothing here is a confirmatory test.
- Pairs share stations. Each settlement station appears in many pairs and each gauge in many pairs, so the pairs are not independent draws. The pair bootstrap treats them as if they were and its band is too narrow. The gauge bootstrap resamples exposure gauges and carries each gauge's whole set of pairs along, which respects one of the two sharing structures (gauges) but not the other (settlement stations). Both bands are reported; the gauge band is the one to trust more.
- Each pair's HE rests on its REPORT seasons (8 to 34 per pair); HE of a single pair is noisy, and pairs with few seasons scatter widely. Pairs with fewer than 20 joint seasons were excluded by a rule fixed before results; the sensitivity curve puts them back.
- Bins at long distance hold pairs from different sub-regions (coast, Appalachians, lake shore); the mean over a bin is not the HE any one park would see.
- Premiums are modelled (1.2 x TRAIN mean payout); nobody sells this contract. Weather is observed.
- Gauge quality differs between stations and decades (Phase 0 and 1 found dew tips and silent gauge failures). Hourly data before 1997 is from the NCEI archive at first-order stations; the sources are never mixed inside a season but can differ between TRAIN and REPORT of one pair.
- The coast indicator is coarse (nearest vertex of a low-resolution shoreline).
