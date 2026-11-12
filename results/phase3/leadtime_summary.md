# Phase 3, Question 2: when must the daily contract be listed to work as a hedge?

EXPLORATORY (docs/PHASE3_PREREG.md). Weather observed. Kalshi prices observed to 1.5 days before close; every price beyond that is MODELLED (MOS probability + Phase 1 markup + fee). Rules: docs/status/phase3_leadtime.md.

Finding: Daily rain contract: HE stays below zero at every lead from 1 day to climatology (modelled); shape, not timing, is the limit.

## Lead at which HE first exceeds zero (REPORT seasons, strategy-2 sizing, 95% season bootstrap)

- A (Trenton same-station), markup main: never (point estimate below zero at every lead; highest HE -0.64 at lead inf (same seasons as GFS leads))
- A (Trenton same-station), markup markup_0.068: never (point estimate below zero at every lead; highest HE -0.54 at lead inf (same seasons as GFS leads))
- D-same (Philadelphia same-station), markup main: never (point estimate below zero at every lead; highest HE -0.23 at lead inf (all seasons))
- D-same (Philadelphia same-station), markup markup_0.068: never (point estimate below zero at every lead; highest HE -0.18 at lead inf (all seasons))

Per the pre-registration: if HE stays below zero at every lead, the daily contract's shape, not its timing, is the binding problem. That is the outcome here.

## HE and cost by lead (main markup a = 0.085; MODELLED prices)

| case | lead (days) | price source | windows | TRAIN / REPORT seasons | n per day | HE [95%] | mean net cost | premium per $1 useful payout | premium per $1 payout | mean ask | carry-forward days |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A (Trenton same-station) | 1 (p06x4) | GFS | Phase 2 windows restricted to MOS seasons | 11 / 12 (2015-2026) | 0.05 | -1.28 [-2.65, -0.90] | 6.18 [5.11, 7.17] | 1.52 | 1.52 | 0.504 | 1 |
| A (Trenton same-station) | 1.5 | GFS | Phase 2 windows restricted to MOS seasons | 11 / 12 (2015-2026) | 0.05 | -1.29 [-2.50, -0.96] | 6.15 [5.08, 7.16] | 1.50 | 1.50 | 0.496 | 0 |
| A (Trenton same-station) | 2 | GFS | Phase 2 windows restricted to MOS seasons | 11 / 12 (2015-2026) | 0.05 | -1.31 [-2.56, -0.95] | 6.16 [5.08, 7.17] | 1.51 | 1.50 | 0.496 | 0 |
| A (Trenton same-station) | 3 | GFS | Phase 2 windows restricted to MOS seasons | 11 / 12 (2015-2026) | 0.05 | -1.24 [-2.60, -0.84] | 6.14 [5.07, 7.14] | 1.50 | 1.49 | 0.491 | 0 |
| A (Trenton same-station) | 4 | MEX | all MOS seasons are REPORT; n and reference from GFS lead 3 (Phase 2 windows restricted to MOS seasons) | 0 / 6 (2021-2026) | 0.05 | -1.58 [-5.45, -1.19] | 5.50 [3.90, 6.72] | 1.44 | 1.42 | 0.456 | 0 |
| A (Trenton same-station) | 5 | MEX | all MOS seasons are REPORT; n and reference from GFS lead 3 (Phase 2 windows restricted to MOS seasons) | 0 / 6 (2021-2026) | 0.05 | -1.54 [-5.43, -1.15] | 5.54 [3.97, 6.72] | 1.46 | 1.45 | 0.459 | 0 |
| A (Trenton same-station) | 6 | MEX | all MOS seasons are REPORT; n and reference from GFS lead 3 (Phase 2 windows restricted to MOS seasons) | 0 / 6 (2021-2026) | 0.05 | -1.71 [-5.77, -1.33] | 5.59 [4.04, 6.78] | 1.50 | 1.48 | 0.468 | 0 |
| A (Trenton same-station) | 7 | MEX | all MOS seasons are REPORT; n and reference from GFS lead 3 (Phase 2 windows restricted to MOS seasons) | 0 / 6 (2021-2026) | 0.05 | -1.44 [-4.66, -1.12] | 5.52 [3.96, 6.68] | 1.45 | 1.43 | 0.452 | 0 |
| A (Trenton same-station) | inf (all seasons) | climatology (TRAIN monthly) | Phase 2 windows 1999-2014 / 2015-2026 | 16 / 12 (2015-2026) | 0.05 | -0.69 [-1.36, -0.47] | 5.90 [4.88, 6.87] | 1.35 | 1.35 | 0.432 | 0 |
| A (Trenton same-station) | inf (same seasons as GFS leads) | climatology (TRAIN monthly) | Phase 2 windows restricted to MOS seasons | 11 / 12 (2015-2026) | 0.05 | -0.64 [-1.29, -0.43] | 5.86 [4.83, 6.83] | 1.33 | 1.32 | 0.424 | 0 |
| A (Trenton same-station) | inf (same seasons as MEX leads) | climatology (TRAIN monthly) | all MOS seasons are REPORT; n and reference from GFS lead 3 (Phase 2 windows restricted to MOS seasons) | 0 / 6 (2021-2026) | 0.05 | -1.19 [-3.58, -0.91] | 5.39 [3.88, 6.56] | 1.37 | 1.35 | 0.423 | 0 |
| D-same (Philadelphia same-station) | 1 (p06x4) | GFS | 60/40 split of MOS seasons (Phase 2 TRAIN window has no MOS season) | 13 / 10 (2017-2026) | 0.05 | -1.45 [-9.15, -1.08] | 6.39 [5.38, 7.45] | 1.54 | 1.54 | 0.505 | 1 |
| D-same (Philadelphia same-station) | 1.5 | GFS | 60/40 split of MOS seasons (Phase 2 TRAIN window has no MOS season) | 13 / 10 (2017-2026) | 0.05 | -1.49 [-8.51, -1.20] | 6.39 [5.39, 7.46] | 1.54 | 1.54 | 0.503 | 0 |
| D-same (Philadelphia same-station) | 2 | GFS | 60/40 split of MOS seasons (Phase 2 TRAIN window has no MOS season) | 13 / 10 (2017-2026) | 0.05 | -1.49 [-8.31, -1.23] | 6.38 [5.37, 7.47] | 1.54 | 1.54 | 0.501 | 0 |
| D-same (Philadelphia same-station) | 3 | GFS | 60/40 split of MOS seasons (Phase 2 TRAIN window has no MOS season) | 13 / 10 (2017-2026) | 0.05 | -1.49 [-8.38, -1.16] | 6.38 [5.36, 7.45] | 1.54 | 1.54 | 0.499 | 0 |
| D-same (Philadelphia same-station) | 4 | MEX | all MOS seasons are REPORT; n and reference from GFS lead 3 (60/40 split of MOS seasons (Phase 2 TRAIN window has no MOS season)) | 0 / 6 (2021-2026) | 0.05 | -1.07 [-7.99, -0.82] | 6.08 [4.81, 7.30] | 1.48 | 1.48 | 0.457 | 0 |
| D-same (Philadelphia same-station) | 5 | MEX | all MOS seasons are REPORT; n and reference from GFS lead 3 (60/40 split of MOS seasons (Phase 2 TRAIN window has no MOS season)) | 0 / 6 (2021-2026) | 0.05 | -1.09 [-8.21, -0.81] | 6.10 [4.83, 7.33] | 1.49 | 1.49 | 0.458 | 0 |
| D-same (Philadelphia same-station) | 6 | MEX | all MOS seasons are REPORT; n and reference from GFS lead 3 (60/40 split of MOS seasons (Phase 2 TRAIN window has no MOS season)) | 0 / 6 (2021-2026) | 0.05 | -1.16 [-8.26, -0.88] | 6.16 [4.91, 7.37] | 1.53 | 1.53 | 0.466 | 0 |
| D-same (Philadelphia same-station) | 7 | MEX | all MOS seasons are REPORT; n and reference from GFS lead 3 (60/40 split of MOS seasons (Phase 2 TRAIN window has no MOS season)) | 0 / 6 (2021-2026) | 0.05 | -1.02 [-6.78, -0.75] | 6.07 [4.81, 7.28] | 1.47 | 1.47 | 0.448 | 0 |
| D-same (Philadelphia same-station) | inf (all seasons) | climatology (TRAIN monthly) | Phase 2 windows 1941-1990 / 1991-2026 | 50 / 35 (1991-2026) | 0.05 | -0.23 [-0.51, -0.14] | 5.60 [4.78, 6.51] | 1.39 | 1.38 | 0.386 | 0 |
| D-same (Philadelphia same-station) | inf (same seasons as GFS leads) | climatology (TRAIN monthly) | 60/40 split of MOS seasons (Phase 2 TRAIN window has no MOS season) | 13 / 10 (2017-2026) | 0.05 | -0.52 [-2.65, -0.44] | 5.84 [4.88, 6.84] | 1.21 | 1.21 | 0.380 | 0 |
| D-same (Philadelphia same-station) | inf (same seasons as MEX leads) | climatology (TRAIN monthly) | all MOS seasons are REPORT; n and reference from GFS lead 3 (60/40 split of MOS seasons (Phase 2 TRAIN window has no MOS season)) | 0 / 6 (2021-2026) | 0.05 | -0.53 [-3.47, -0.41] | 5.75 [4.50, 6.95] | 1.26 | 1.26 | 0.381 | 0 |

Sensitivity a = 0.068 (markup_0.068 rows of results/phase3/leadtime_he_by_lead.csv): HE is higher by 0.1-0.3 at every lead and still below zero everywhere.

## Observed decision-time table (Phase 1 quote table, aggregates; one contract per market day)

| group | hours before close | lead (days) | market days | share with a usable ask | premium + fee per $1 payout | share of rain days with no offer | Brier of mid (n two-sided) | mean ask, rain days | mean ask, dry days |
|---|---|---|---|---|---|---|---|---|---|
| four cities, all years | 36 | 1.50 | 517 | 0.72 | 1.20 | 0.35 | 0.126 (335) | 0.71 | 0.28 |
| four cities, all years | 24 | 1.00 | 517 | 0.86 | 1.21 | 0.22 | 0.108 (403) | 0.77 | 0.25 |
| four cities, all years | 12 | 0.50 | 517 | 0.69 | 1.38 | 0.66 | 0.099 (248) | 0.72 | 0.16 |
| four cities, all years | 2 | 0.08 | 517 | 0.60 | 2.60 | 0.92 | 0.071 (140) | 0.71 | 0.11 |
| NYC alone, all years | 36 | 1.50 | 374 | 0.62 | 1.22 | 0.45 | 0.137 (200) | 0.72 | 0.31 |
| NYC alone, all years | 24 | 1.00 | 374 | 0.82 | 1.18 | 0.26 | 0.110 (270) | 0.77 | 0.26 |
| NYC alone, all years | 12 | 0.50 | 374 | 0.67 | 1.34 | 0.65 | 0.103 (177) | 0.74 | 0.17 |
| NYC alone, all years | 2 | 0.08 | 374 | 0.57 | 2.54 | 0.91 | 0.060 (109) | 0.76 | 0.12 |
| four cities, KXRAIN 2026 | 36 | 1.50 | 216 | 0.95 | 1.10 | 0.07 | 0.113 (201) | 0.68 | 0.23 |
| four cities, KXRAIN 2026 | 24 | 1.00 | 216 | 0.97 | 1.19 | 0.08 | 0.104 (199) | 0.75 | 0.23 |
| four cities, KXRAIN 2026 | 12 | 0.50 | 216 | 0.75 | 1.29 | 0.64 | 0.099 (104) | 0.66 | 0.13 |
| four cities, KXRAIN 2026 | 2 | 0.08 | 216 | 0.63 | 2.81 | 0.95 | 0.078 (46) | 0.49 | 0.06 |
| four cities, 2025-2026 | 36 | 1.50 | 445 | 0.76 | 1.21 | 0.32 | 0.122 (308) | 0.73 | 0.28 |
| four cities, 2025-2026 | 24 | 1.00 | 445 | 0.86 | 1.21 | 0.23 | 0.110 (344) | 0.77 | 0.26 |
| four cities, 2025-2026 | 12 | 0.50 | 445 | 0.70 | 1.40 | 0.66 | 0.102 (208) | 0.73 | 0.16 |
| four cities, 2025-2026 | 2 | 0.08 | 445 | 0.59 | 3.15 | 0.94 | 0.076 (104) | 0.70 | 0.11 |

## Forecast skill by lead (MOS archive vs the station's official daily total >= 0.01 inch; park-season days)

| station | line | field | target lead | mean lead | days | seasons | mean PoP | rain share | Brier | Brier of climatology (same days, leave-one-season-out monthly) | skill vs climatology |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TTN | GFS | p12x2 | 1.5 | 1.42 | 2374 | 23 (2004-2026) | 0.407 | 0.355 | 0.131 | 0.228 | 0.43 |
| TTN | GFS | p12x2 | 2.0 | 1.92 | 2374 | 23 (2004-2026) | 0.406 | 0.355 | 0.139 | 0.228 | 0.39 |
| TTN | GFS | p12x2 | 3.0 | 2.92 | 2374 | 23 (2004-2026) | 0.413 | 0.355 | 0.155 | 0.228 | 0.32 |
| TTN | GFS-p06x4 | pop_p06 | 1.0 | 1.17 | 2373 | 23 (2004-2026) | 0.414 | 0.355 | 0.115 | 0.228 | 0.50 |
| TTN | GFS-p06x4 | pop_p06 | 1.5 | 1.42 | 2374 | 23 (2004-2026) | 0.411 | 0.355 | 0.118 | 0.228 | 0.48 |
| TTN | GFS-p06x4 | pop_p06 | 2.0 | 1.92 | 2374 | 23 (2004-2026) | 0.421 | 0.355 | 0.129 | 0.228 | 0.43 |
| TTN | GFS-p06x4 | pop_p06 | 3.0 | 2.92 | 2374 | 23 (2004-2026) | 0.443 | 0.355 | 0.152 | 0.228 | 0.33 |
| TTN | AVN | p12x2 | 1.5 | 1.50 | 305 | 3 (2001-2003) | 0.380 | 0.370 | 0.129 | 0.233 | 0.45 |
| TTN | AVN | p12x2 | 2.0 | 2.00 | 306 | 3 (2001-2003) | 0.386 | 0.372 | 0.145 | 0.233 | 0.38 |
| TTN | AVN | p12x2 | 3.0 | 3.00 | 306 | 3 (2001-2003) | 0.386 | 0.372 | 0.158 | 0.233 | 0.32 |
| TTN | AVN-p06x4 | pop_p06 | 1.0 | 1.17 | 306 | 3 (2001-2003) | 0.384 | 0.372 | 0.117 | 0.233 | 0.50 |
| TTN | AVN-p06x4 | pop_p06 | 1.5 | 1.50 | 306 | 3 (2001-2003) | 0.389 | 0.372 | 0.126 | 0.233 | 0.46 |
| TTN | AVN-p06x4 | pop_p06 | 2.0 | 2.00 | 306 | 3 (2001-2003) | 0.392 | 0.372 | 0.145 | 0.233 | 0.38 |
| TTN | AVN-p06x4 | pop_p06 | 3.0 | 2.83 | 305 | 3 (2001-2003) | 0.409 | 0.370 | 0.158 | 0.233 | 0.32 |
| TTN | MEX | p24 | 1.5 | 1.67 | 675 | 7 (2020-2026) | 0.386 | 0.348 | 0.135 | 0.228 | 0.41 |
| TTN | MEX | p24 | 2.0 | 2.16 | 677 | 7 (2020-2026) | 0.384 | 0.347 | 0.141 | 0.228 | 0.38 |
| TTN | MEX | p24 | 3.0 | 3.16 | 676 | 7 (2020-2026) | 0.376 | 0.346 | 0.158 | 0.228 | 0.31 |
| TTN | MEX | p24 | 4.0 | 4.16 | 675 | 7 (2020-2026) | 0.373 | 0.345 | 0.172 | 0.228 | 0.25 |
| TTN | MEX | p24 | 5.0 | 5.16 | 674 | 7 (2020-2026) | 0.374 | 0.346 | 0.184 | 0.228 | 0.19 |
| TTN | MEX | p24 | 6.0 | 6.16 | 673 | 7 (2020-2026) | 0.380 | 0.346 | 0.198 | 0.228 | 0.13 |
| TTN | MEX | p24 | 7.0 | 7.16 | 672 | 7 (2020-2026) | 0.363 | 0.347 | 0.206 | 0.228 | 0.10 |
| TTN | MEX-p12x2 | pop_p12 | 1.5 | 1.67 | 675 | 7 (2020-2026) | 0.406 | 0.348 | 0.137 | 0.228 | 0.40 |
| TTN | MEX-p12x2 | pop_p12 | 2.0 | 2.16 | 677 | 7 (2020-2026) | 0.403 | 0.347 | 0.144 | 0.228 | 0.37 |
| TTN | MEX-p12x2 | pop_p12 | 3.0 | 3.16 | 676 | 7 (2020-2026) | 0.403 | 0.346 | 0.161 | 0.228 | 0.29 |
| TTN | MEX-p12x2 | pop_p12 | 4.0 | 4.16 | 675 | 7 (2020-2026) | 0.410 | 0.345 | 0.174 | 0.228 | 0.24 |
| TTN | MEX-p12x2 | pop_p12 | 5.0 | 5.16 | 674 | 7 (2020-2026) | 0.434 | 0.346 | 0.191 | 0.228 | 0.16 |
| TTN | MEX-p12x2 | pop_p12 | 6.0 | 6.16 | 673 | 7 (2020-2026) | 0.429 | 0.346 | 0.203 | 0.228 | 0.11 |
| TTN | MEX-p12x2 | pop_p12 | 7.0 | 7.16 | 672 | 7 (2020-2026) | 0.423 | 0.347 | 0.213 | 0.228 | 0.07 |
| TTN | NBS | p12x2 | 1.5 | 1.57 | 830 | 8 (2019-2026) | 0.404 | 0.353 | 0.133 | 0.229 | 0.42 |
| TTN | NBS | p12x2 | 2.0 | 2.07 | 830 | 8 (2019-2026) | 0.406 | 0.353 | 0.138 | 0.229 | 0.40 |
| TTN | NBS | p12x2 | 3.0 | 3.07 | 830 | 8 (2019-2026) | 0.398 | 0.353 | 0.151 | 0.229 | 0.34 |
| TTN | NBS-p06x4 | pop_p06 | 1.0 | 1.10 | 829 | 8 (2019-2026) | 0.411 | 0.353 | 0.106 | 0.229 | 0.53 |
| TTN | NBS-p06x4 | pop_p06 | 1.5 | 1.57 | 830 | 8 (2019-2026) | 0.411 | 0.353 | 0.116 | 0.229 | 0.49 |
| TTN | NBS-p06x4 | pop_p06 | 2.0 | 2.07 | 830 | 8 (2019-2026) | 0.418 | 0.353 | 0.126 | 0.229 | 0.45 |
| TTN | NBS-p06x4 | pop_p06 | 3.0 | 2.85 | 830 | 8 (2019-2026) | 0.430 | 0.353 | 0.143 | 0.229 | 0.38 |
| TTN | NBE | p12x2 | 1.5 | 1.63 | 629 | 7 (2020-2026) | 0.398 | 0.345 | 0.139 | 0.228 | 0.39 |
| TTN | NBE | p12x2 | 2.0 | 2.13 | 629 | 7 (2020-2026) | 0.400 | 0.345 | 0.145 | 0.228 | 0.36 |
| TTN | NBE | p12x2 | 3.0 | 3.13 | 628 | 7 (2020-2026) | 0.394 | 0.344 | 0.156 | 0.228 | 0.32 |
| TTN | NBE | p12x2 | 4.0 | 4.13 | 627 | 7 (2020-2026) | 0.391 | 0.344 | 0.172 | 0.228 | 0.24 |
| TTN | NBE | p12x2 | 5.0 | 5.13 | 626 | 7 (2020-2026) | 0.390 | 0.344 | 0.181 | 0.228 | 0.21 |
| TTN | NBE | p12x2 | 6.0 | 6.13 | 625 | 7 (2020-2026) | 0.398 | 0.344 | 0.191 | 0.228 | 0.16 |
| TTN | NBE | p12x2 | 7.0 | 7.13 | 624 | 7 (2020-2026) | 0.397 | 0.343 | 0.199 | 0.228 | 0.13 |
| PHL | GFS | p12x2 | 1.5 | 1.42 | 2374 | 23 (2004-2026) | 0.407 | 0.328 | 0.144 | 0.220 | 0.34 |
| PHL | GFS | p12x2 | 2.0 | 1.92 | 2374 | 23 (2004-2026) | 0.407 | 0.328 | 0.151 | 0.220 | 0.31 |
| PHL | GFS | p12x2 | 3.0 | 2.92 | 2374 | 23 (2004-2026) | 0.414 | 0.328 | 0.166 | 0.220 | 0.25 |
| PHL | GFS-p06x4 | pop_p06 | 1.0 | 1.17 | 2373 | 23 (2004-2026) | 0.414 | 0.328 | 0.121 | 0.220 | 0.45 |
| PHL | GFS-p06x4 | pop_p06 | 1.5 | 1.42 | 2374 | 23 (2004-2026) | 0.412 | 0.328 | 0.127 | 0.220 | 0.42 |
| PHL | GFS-p06x4 | pop_p06 | 2.0 | 1.92 | 2374 | 23 (2004-2026) | 0.419 | 0.328 | 0.137 | 0.220 | 0.38 |
| PHL | GFS-p06x4 | pop_p06 | 3.0 | 2.92 | 2374 | 23 (2004-2026) | 0.443 | 0.328 | 0.158 | 0.220 | 0.28 |
| PHL | AVN | p12x2 | 1.5 | 1.50 | 305 | 3 (2001-2003) | 0.379 | 0.351 | 0.122 | 0.229 | 0.47 |
| PHL | AVN | p12x2 | 2.0 | 2.00 | 306 | 3 (2001-2003) | 0.386 | 0.353 | 0.143 | 0.229 | 0.37 |
| PHL | AVN | p12x2 | 3.0 | 3.00 | 306 | 3 (2001-2003) | 0.385 | 0.353 | 0.154 | 0.229 | 0.33 |
| PHL | AVN-p06x4 | pop_p06 | 1.0 | 1.17 | 306 | 3 (2001-2003) | 0.381 | 0.353 | 0.106 | 0.229 | 0.54 |
| PHL | AVN-p06x4 | pop_p06 | 1.5 | 1.50 | 306 | 3 (2001-2003) | 0.390 | 0.353 | 0.115 | 0.229 | 0.50 |
| PHL | AVN-p06x4 | pop_p06 | 2.0 | 2.00 | 306 | 3 (2001-2003) | 0.395 | 0.353 | 0.138 | 0.229 | 0.40 |
| PHL | AVN-p06x4 | pop_p06 | 3.0 | 2.83 | 305 | 3 (2001-2003) | 0.412 | 0.351 | 0.152 | 0.229 | 0.34 |
| PHL | MEX | p24 | 1.5 | 1.67 | 675 | 7 (2020-2026) | 0.392 | 0.341 | 0.145 | 0.223 | 0.35 |
| PHL | MEX | p24 | 2.0 | 2.16 | 677 | 7 (2020-2026) | 0.392 | 0.340 | 0.150 | 0.223 | 0.33 |
| PHL | MEX | p24 | 3.0 | 3.16 | 676 | 7 (2020-2026) | 0.380 | 0.339 | 0.164 | 0.223 | 0.26 |
| PHL | MEX | p24 | 4.0 | 4.16 | 675 | 7 (2020-2026) | 0.375 | 0.338 | 0.171 | 0.223 | 0.23 |
| PHL | MEX | p24 | 5.0 | 5.16 | 674 | 7 (2020-2026) | 0.374 | 0.338 | 0.188 | 0.223 | 0.16 |
| PHL | MEX | p24 | 6.0 | 6.16 | 673 | 7 (2020-2026) | 0.379 | 0.339 | 0.196 | 0.223 | 0.12 |
| PHL | MEX | p24 | 7.0 | 7.16 | 672 | 7 (2020-2026) | 0.361 | 0.339 | 0.199 | 0.223 | 0.11 |
| PHL | MEX-p12x2 | pop_p12 | 1.5 | 1.67 | 675 | 7 (2020-2026) | 0.412 | 0.341 | 0.148 | 0.223 | 0.34 |
| PHL | MEX-p12x2 | pop_p12 | 2.0 | 2.16 | 677 | 7 (2020-2026) | 0.411 | 0.340 | 0.154 | 0.223 | 0.31 |
| PHL | MEX-p12x2 | pop_p12 | 3.0 | 3.16 | 676 | 7 (2020-2026) | 0.404 | 0.339 | 0.169 | 0.223 | 0.24 |
| PHL | MEX-p12x2 | pop_p12 | 4.0 | 4.16 | 675 | 7 (2020-2026) | 0.412 | 0.338 | 0.175 | 0.223 | 0.22 |
| PHL | MEX-p12x2 | pop_p12 | 5.0 | 5.16 | 674 | 7 (2020-2026) | 0.432 | 0.338 | 0.197 | 0.223 | 0.12 |
| PHL | MEX-p12x2 | pop_p12 | 6.0 | 6.16 | 673 | 7 (2020-2026) | 0.427 | 0.339 | 0.199 | 0.223 | 0.11 |
| PHL | MEX-p12x2 | pop_p12 | 7.0 | 7.16 | 672 | 7 (2020-2026) | 0.419 | 0.339 | 0.205 | 0.223 | 0.08 |
| PHL | NBS | p12x2 | 1.5 | 1.57 | 830 | 8 (2019-2026) | 0.400 | 0.343 | 0.150 | 0.227 | 0.34 |
| PHL | NBS | p12x2 | 2.0 | 2.07 | 830 | 8 (2019-2026) | 0.404 | 0.343 | 0.154 | 0.227 | 0.32 |
| PHL | NBS | p12x2 | 3.0 | 3.07 | 830 | 8 (2019-2026) | 0.400 | 0.343 | 0.166 | 0.227 | 0.27 |
| PHL | NBS-p06x4 | pop_p06 | 1.0 | 1.10 | 829 | 8 (2019-2026) | 0.410 | 0.344 | 0.114 | 0.227 | 0.50 |
| PHL | NBS-p06x4 | pop_p06 | 1.5 | 1.57 | 830 | 8 (2019-2026) | 0.409 | 0.343 | 0.126 | 0.227 | 0.44 |
| PHL | NBS-p06x4 | pop_p06 | 2.0 | 2.07 | 830 | 8 (2019-2026) | 0.416 | 0.343 | 0.137 | 0.227 | 0.40 |
| PHL | NBS-p06x4 | pop_p06 | 3.0 | 2.85 | 830 | 8 (2019-2026) | 0.430 | 0.343 | 0.155 | 0.227 | 0.31 |
| PHL | NBE | p12x2 | 1.5 | 1.63 | 629 | 7 (2020-2026) | 0.396 | 0.339 | 0.150 | 0.223 | 0.33 |
| PHL | NBE | p12x2 | 2.0 | 2.13 | 629 | 7 (2020-2026) | 0.397 | 0.339 | 0.154 | 0.223 | 0.31 |
| PHL | NBE | p12x2 | 3.0 | 3.13 | 628 | 7 (2020-2026) | 0.393 | 0.338 | 0.166 | 0.223 | 0.26 |
| PHL | NBE | p12x2 | 4.0 | 4.13 | 627 | 7 (2020-2026) | 0.391 | 0.338 | 0.182 | 0.223 | 0.19 |
| PHL | NBE | p12x2 | 5.0 | 5.13 | 626 | 7 (2020-2026) | 0.390 | 0.337 | 0.188 | 0.223 | 0.16 |
| PHL | NBE | p12x2 | 6.0 | 6.13 | 625 | 7 (2020-2026) | 0.398 | 0.338 | 0.195 | 0.223 | 0.13 |
| PHL | NBE | p12x2 | 7.0 | 7.13 | 624 | 7 (2020-2026) | 0.398 | 0.337 | 0.196 | 0.223 | 0.12 |

Calibration tables per lead: results/phase3/leadtime_calibration_by_lead.csv.

## Model check at the observed end (modelled ask at lead 1.5 vs the real 36-hour ask on the same days)

| city | line | target lead | markup | days | years | mean observed ask | mean modelled ask | difference (modelled - observed) | daily RMSE | daily corr | Brier of observed ask | Brier of PoP |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TTN | GFS | 1.5 | main | 35 | 2026 | 0.372 | 0.498 | +0.126 | 0.187 | 0.92 | 0.070 | 0.085 |
| TTN | GFS | 1.5 | markup_0.068 | 35 | 2026 | 0.372 | 0.483 | +0.111 | 0.177 | 0.92 | 0.070 | 0.085 |
| TTN | GFS-p06x4 | 1.0 | main | 35 | 2026 | 0.372 | 0.511 | +0.138 | 0.216 | 0.89 | 0.070 | 0.099 |
| TTN | GFS-p06x4 | 1.0 | markup_0.068 | 35 | 2026 | 0.372 | 0.495 | +0.123 | 0.205 | 0.89 | 0.070 | 0.099 |
| TTN | GFS-p06x4 | 1.5 | main | 35 | 2026 | 0.372 | 0.501 | +0.128 | 0.210 | 0.89 | 0.070 | 0.093 |
| TTN | GFS-p06x4 | 1.5 | markup_0.068 | 35 | 2026 | 0.372 | 0.487 | +0.115 | 0.202 | 0.89 | 0.070 | 0.093 |
| TTN | MEX | 1.5 | main | 35 | 2026 | 0.372 | 0.499 | +0.127 | 0.179 | 0.93 | 0.070 | 0.078 |
| TTN | MEX | 1.5 | markup_0.068 | 35 | 2026 | 0.372 | 0.482 | +0.109 | 0.166 | 0.93 | 0.070 | 0.078 |
| TTN | MEX-p12x2 | 1.5 | main | 35 | 2026 | 0.372 | 0.517 | +0.145 | 0.199 | 0.92 | 0.070 | 0.077 |
| TTN | MEX-p12x2 | 1.5 | markup_0.068 | 35 | 2026 | 0.372 | 0.505 | +0.132 | 0.188 | 0.92 | 0.070 | 0.077 |
| TTN | NBS | 1.5 | main | 35 | 2026 | 0.372 | 0.457 | +0.085 | 0.147 | 0.94 | 0.070 | 0.070 |
| TTN | NBS | 1.5 | markup_0.068 | 35 | 2026 | 0.372 | 0.442 | +0.069 | 0.140 | 0.94 | 0.070 | 0.070 |
| TTN | NBS-p06x4 | 1.0 | main | 35 | 2026 | 0.372 | 0.477 | +0.105 | 0.155 | 0.95 | 0.070 | 0.052 |
| TTN | NBS-p06x4 | 1.0 | markup_0.068 | 35 | 2026 | 0.372 | 0.462 | +0.090 | 0.144 | 0.95 | 0.070 | 0.052 |
| PHIL | GFS | 1.5 | main | 69 | 2026 | 0.425 | 0.511 | +0.085 | 0.261 | 0.71 | 0.164 | 0.128 |
| PHIL | GFS | 1.5 | markup_0.068 | 69 | 2026 | 0.425 | 0.495 | +0.070 | 0.255 | 0.72 | 0.164 | 0.128 |
| PHIL | GFS-p06x4 | 1.0 | main | 69 | 2026 | 0.425 | 0.502 | +0.077 | 0.260 | 0.73 | 0.164 | 0.110 |
| PHIL | GFS-p06x4 | 1.0 | markup_0.068 | 69 | 2026 | 0.425 | 0.487 | +0.062 | 0.256 | 0.73 | 0.164 | 0.110 |
| PHIL | GFS-p06x4 | 1.5 | main | 69 | 2026 | 0.425 | 0.494 | +0.068 | 0.259 | 0.73 | 0.164 | 0.108 |
| PHIL | GFS-p06x4 | 1.5 | markup_0.068 | 69 | 2026 | 0.425 | 0.480 | +0.054 | 0.255 | 0.73 | 0.164 | 0.108 |
| PHIL | MEX | 1.5 | main | 69 | 2026 | 0.425 | 0.508 | +0.083 | 0.257 | 0.72 | 0.164 | 0.141 |
| PHIL | MEX | 1.5 | markup_0.068 | 69 | 2026 | 0.425 | 0.490 | +0.065 | 0.252 | 0.72 | 0.164 | 0.141 |
| PHIL | MEX-p12x2 | 1.5 | main | 69 | 2026 | 0.425 | 0.527 | +0.101 | 0.266 | 0.72 | 0.164 | 0.145 |
| PHIL | MEX-p12x2 | 1.5 | markup_0.068 | 69 | 2026 | 0.425 | 0.513 | +0.087 | 0.259 | 0.73 | 0.164 | 0.145 |
| PHIL | NBS | 1.5 | main | 69 | 2026 | 0.425 | 0.482 | +0.056 | 0.244 | 0.74 | 0.164 | 0.156 |
| PHIL | NBS | 1.5 | markup_0.068 | 69 | 2026 | 0.425 | 0.466 | +0.041 | 0.243 | 0.74 | 0.164 | 0.156 |
| PHIL | NBS-p06x4 | 1.0 | main | 69 | 2026 | 0.425 | 0.469 | +0.043 | 0.238 | 0.75 | 0.164 | 0.104 |
| PHIL | NBS-p06x4 | 1.0 | markup_0.068 | 69 | 2026 | 0.425 | 0.454 | +0.029 | 0.236 | 0.75 | 0.164 | 0.104 |
| EWR | GFS | 1.5 | main | 34 | 2026 | 0.361 | 0.478 | +0.116 | 0.182 | 0.91 | 0.098 | 0.085 |
| EWR | GFS | 1.5 | markup_0.068 | 34 | 2026 | 0.361 | 0.464 | +0.102 | 0.173 | 0.91 | 0.098 | 0.085 |
| EWR | GFS-p06x4 | 1.0 | main | 34 | 2026 | 0.361 | 0.490 | +0.129 | 0.202 | 0.89 | 0.098 | 0.074 |
| EWR | GFS-p06x4 | 1.0 | markup_0.068 | 34 | 2026 | 0.361 | 0.476 | +0.115 | 0.194 | 0.89 | 0.098 | 0.074 |
| EWR | GFS-p06x4 | 1.5 | main | 34 | 2026 | 0.361 | 0.485 | +0.123 | 0.204 | 0.89 | 0.098 | 0.076 |
| EWR | GFS-p06x4 | 1.5 | markup_0.068 | 34 | 2026 | 0.361 | 0.470 | +0.108 | 0.194 | 0.89 | 0.098 | 0.076 |
| EWR | MEX | 1.5 | main | 34 | 2026 | 0.361 | 0.481 | +0.120 | 0.179 | 0.92 | 0.098 | 0.083 |
| EWR | MEX | 1.5 | markup_0.068 | 34 | 2026 | 0.361 | 0.464 | +0.102 | 0.166 | 0.92 | 0.098 | 0.083 |
| EWR | MEX-p12x2 | 1.5 | main | 34 | 2026 | 0.361 | 0.498 | +0.136 | 0.201 | 0.90 | 0.098 | 0.081 |
| EWR | MEX-p12x2 | 1.5 | markup_0.068 | 34 | 2026 | 0.361 | 0.484 | +0.123 | 0.191 | 0.90 | 0.098 | 0.081 |
| EWR | NBS | 1.5 | main | 34 | 2026 | 0.361 | 0.424 | +0.063 | 0.135 | 0.94 | 0.098 | 0.092 |
| EWR | NBS | 1.5 | markup_0.068 | 34 | 2026 | 0.361 | 0.409 | +0.047 | 0.129 | 0.94 | 0.098 | 0.092 |
| EWR | NBS-p06x4 | 1.0 | main | 34 | 2026 | 0.361 | 0.449 | +0.087 | 0.134 | 0.95 | 0.098 | 0.090 |
| EWR | NBS-p06x4 | 1.0 | markup_0.068 | 34 | 2026 | 0.361 | 0.434 | +0.073 | 0.124 | 0.96 | 0.098 | 0.090 |
| NYC | GFS | 1.5 | main | 202 | 2025+2026 | 0.491 | 0.401 | -0.089 | 0.292 | 0.64 | 0.158 | 0.141 |
| NYC | GFS | 1.5 | markup_0.068 | 202 | 2025+2026 | 0.491 | 0.386 | -0.105 | 0.298 | 0.64 | 0.158 | 0.141 |
| NYC | GFS-p06x4 | 1.0 | main | 202 | 2025+2026 | 0.491 | 0.414 | -0.077 | 0.293 | 0.64 | 0.158 | 0.109 |
| NYC | GFS-p06x4 | 1.0 | markup_0.068 | 202 | 2025+2026 | 0.491 | 0.398 | -0.093 | 0.298 | 0.64 | 0.158 | 0.109 |
| NYC | GFS-p06x4 | 1.5 | main | 202 | 2025+2026 | 0.491 | 0.401 | -0.089 | 0.300 | 0.63 | 0.158 | 0.117 |
| NYC | GFS-p06x4 | 1.5 | markup_0.068 | 202 | 2025+2026 | 0.491 | 0.386 | -0.105 | 0.307 | 0.63 | 0.158 | 0.117 |
| NYC | MEX | 1.5 | main | 202 | 2025+2026 | 0.491 | 0.406 | -0.084 | 0.298 | 0.62 | 0.158 | 0.140 |
| NYC | MEX | 1.5 | markup_0.068 | 202 | 2025+2026 | 0.491 | 0.388 | -0.103 | 0.305 | 0.62 | 0.158 | 0.140 |
| NYC | MEX-p12x2 | 1.5 | main | 202 | 2025+2026 | 0.491 | 0.419 | -0.072 | 0.296 | 0.62 | 0.158 | 0.135 |
| NYC | MEX-p12x2 | 1.5 | markup_0.068 | 202 | 2025+2026 | 0.491 | 0.404 | -0.087 | 0.300 | 0.62 | 0.158 | 0.135 |
| NYC | NBS | 1.5 | main | 202 | 2025+2026 | 0.491 | 0.384 | -0.106 | 0.297 | 0.65 | 0.158 | 0.142 |
| NYC | NBS | 1.5 | markup_0.068 | 202 | 2025+2026 | 0.491 | 0.369 | -0.122 | 0.304 | 0.65 | 0.158 | 0.142 |
| NYC | NBS-p06x4 | 1.0 | main | 202 | 2025+2026 | 0.491 | 0.398 | -0.093 | 0.284 | 0.67 | 0.158 | 0.104 |
| NYC | NBS-p06x4 | 1.0 | markup_0.068 | 202 | 2025+2026 | 0.491 | 0.383 | -0.108 | 0.290 | 0.67 | 0.158 | 0.104 |

## Caveats

1. Modelled prices are a deterministic markup over a MOS probability; real asks scatter, thin out and go to 1.00 on some rain days. The model is checked only at 1.5 days: the mean modelled ask minus the observed 36-h ask is TTN +0.13 (n = 35), PHIL +0.09 (n = 69), EWR +0.12 (n = 34), NYC -0.09 (n = 202). At Trenton, Philadelphia and Newark (2026 KXRAIN) the model is too dear by 8-13 cents, so the modelled premium curve sits above what the observed end shows (1.50 vs 1.21 per $1 of payout); NYC (2025-2026, thin 2025 book and the old trace rule) goes the other way. A dearer model lowers HE, but HE is also below zero at lead = infinity, where no forecast enters the price.
2. The MOS 24-h window is 00Z-00Z (20:00-20:00 local), four hours before the climate day. The p12x2 and p06x4 fields assume independent periods and overstate the probability on persistent-rain days (see calibration).
3. MEX leads 4-7 exist only from 2021 (6 seasons); their n and reference level come from the station's GFS lead-3 TRAIN choice, and their REPORT bands are wide.
4. Philadelphia GFS leads use a 60/40 split of 2004-2026 because the Phase 2 TRAIN window (1941-1990) predates the archive.
5. The strategy-2 grid has no n = 0; TRAIN prefers the smallest n at every lead, as in Phase 2.
6. Leads are measured from the model run time; MOS text is issued 2-4 h later.
7. Two cases, same-station, circular by construction (Phase 2 case A is a ceiling). Location basis (Phase 2 case B) is not added here.
