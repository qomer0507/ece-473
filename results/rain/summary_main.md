# Rain workstream: loss days vs Kalshi-pay days (observed station data)

Main case per SPEC_v3: every day from the Friday before Memorial Day through Labor Day; loss day = at least
0.25 inch between 10:00 and 18:00 local clock time; Kalshi pays when the climate-day total is at least 0.01 inch.
Usable seasons only; unusable days are dropped and counted. Shares are pooled over seasons.

| Station | Seasons | N | Loss days per season: mean (min-max) | Kalshi-pay days per season: mean (min-max) | Kalshi-pay days that are not loss days | Loss days Kalshi pays on | Days dropped |
|---|---|---|---|---|---|---|---|
| TTN | all usable seasons, 1999-2026 | 28 | 5.36 (1-12) | 36.43 (22-60) | 85.3% | 100.0% | 132 of 2884 |
| TTN | train (to 2014), 1999-2014 | 16 | 5.38 (1-12) | 37.44 (24-60) | 85.6% | 100.0% | 99 of 1639 |
| TTN | report (2015-2026), 2015-2026 | 12 | 5.33 (1-8) | 35.08 (22-41) | 84.8% | 100.0% | 33 of 1245 |
| TTN | 1999-2026 (Trenton's seasons), 1999-2026 | 28 | 5.36 (1-12) | 36.43 (22-60) | 85.3% | 100.0% | 132 of 2884 |
| PHL | all usable seasons, 1941-2026 | 85 | 5.02 (0-14) | 31.26 (19-50) | 83.9% | 100.0% | 108 of 8761 |
| PHL | train (to 2014), 1941-2014 | 73 | 5.03 (0-14) | 30.75 (19-50) | 83.7% | 100.0% | 93 of 7516 |
| PHL | report (2015-2026), 2015-2026 | 12 | 5.00 (2-8) | 34.33 (25-40) | 85.4% | 100.0% | 15 of 1245 |
| PHL | 1999-2026 (Trenton's seasons), 1999-2026 | 28 | 5.32 (1-14) | 32.11 (19-50) | 83.4% | 100.0% | 94 of 2884 |
| ABE | all usable seasons, 1948-2026 | 70 | 5.63 (0-11) | 34.20 (15-50) | 83.5% | 100.0% | 202 of 7217 |
| ABE | train (to 2014), 1948-2014 | 58 | 5.41 (0-10) | 33.97 (15-50) | 84.1% | 100.0% | 157 of 5972 |
| ABE | report (2015-2026), 2015-2026 | 12 | 6.67 (3-11) | 35.33 (22-41) | 81.1% | 100.0% | 45 of 1245 |
| ABE | 1999-2026 (Trenton's seasons), 1999-2026 | 28 | 6.00 (1-11) | 35.50 (15-50) | 83.1% | 100.0% | 122 of 2884 |

Reference check (not the SPEC flag): the same rule applied to the GHCN-Daily total instead of the hourly sum.

| Station | Seasons | Kalshi-pay days per season, hourly rule | Same, GHCN-Daily total | Pay days not loss days, GHCN | Loss days paid, GHCN | Usable days without a GHCN value |
|---|---|---|---|---|---|---|
| TTN | 1999-2026 | 36.43 | 34.54 | 84.5% | 100.0% | 0 |
| PHL | 1941-2026 | 31.26 | 31.11 | 84.3% | 97.4% | 73 |
| ABE | 1948-2026 | 34.20 | 33.84 | 83.4% | 100.0% | 0 |

Sensitivity cases (all usable seasons): see summary_by_case.csv. Extract:

| Station | Calendar | Threshold | Window | Loss days: mean (min-max) | Kalshi-pay days: mean | Pay days not loss days | Loss days paid |
|---|---|---|---|---|---|---|---|
| TTN | all_days | 0.10 | 10:00-16:00 | 5.75 (1-12) | 36.64 | 84.3% | 100.0% |
| TTN | all_days | 0.10 | 10:00-18:00 | 8.75 (2-19) | 36.43 | 76.0% | 100.0% |
| TTN | all_days | 0.10 | 10:00-20:00 | 11.54 (2-19) | 35.93 | 67.9% | 100.0% |
| TTN | all_days | 0.25 | 10:00-16:00 | 3.11 (0-9) | 36.64 | 91.5% | 100.0% |
| TTN | all_days | 0.25 | 10:00-18:00 | 5.36 (1-12) | 36.43 | 85.3% | 100.0% |
| TTN | all_days | 0.25 | 10:00-20:00 | 7.14 (1-12) | 35.93 | 80.1% | 100.0% |
| TTN | all_days | 0.50 | 10:00-16:00 | 1.43 (0-5) | 36.64 | 96.1% | 100.0% |
| TTN | all_days | 0.50 | 10:00-18:00 | 2.71 (0-8) | 36.43 | 92.5% | 100.0% |
| TTN | all_days | 0.50 | 10:00-20:00 | 3.71 (0-9) | 35.93 | 89.7% | 100.0% |
| TTN | weekend_holiday | 0.10 | 10:00-16:00 | 2.14 (0-6) | 11.04 | 80.6% | 100.0% |
| TTN | weekend_holiday | 0.10 | 10:00-18:00 | 2.96 (0-7) | 11.00 | 73.0% | 100.0% |
| TTN | weekend_holiday | 0.10 | 10:00-20:00 | 3.71 (0-9) | 10.89 | 65.9% | 100.0% |
| TTN | weekend_holiday | 0.25 | 10:00-16:00 | 1.14 (0-4) | 11.04 | 89.6% | 100.0% |
| TTN | weekend_holiday | 0.25 | 10:00-18:00 | 1.93 (0-5) | 11.00 | 82.5% | 100.0% |
| TTN | weekend_holiday | 0.25 | 10:00-20:00 | 2.46 (0-6) | 10.89 | 77.4% | 100.0% |
| TTN | weekend_holiday | 0.50 | 10:00-16:00 | 0.54 (0-3) | 11.04 | 95.2% | 100.0% |
| TTN | weekend_holiday | 0.50 | 10:00-18:00 | 0.82 (0-4) | 11.00 | 92.5% | 100.0% |
| TTN | weekend_holiday | 0.50 | 10:00-20:00 | 1.14 (0-5) | 10.89 | 89.5% | 100.0% |
| PHL | all_days | 0.10 | 10:00-16:00 | 5.39 (0-14) | 31.32 | 82.8% | 100.0% |
| PHL | all_days | 0.10 | 10:00-18:00 | 7.99 (1-17) | 31.26 | 74.4% | 100.0% |
| PHL | all_days | 0.10 | 10:00-20:00 | 10.49 (2-19) | 31.12 | 66.3% | 100.0% |
| PHL | all_days | 0.25 | 10:00-16:00 | 3.34 (0-10) | 31.32 | 89.3% | 100.0% |
| PHL | all_days | 0.25 | 10:00-18:00 | 5.02 (0-14) | 31.26 | 83.9% | 100.0% |
| PHL | all_days | 0.25 | 10:00-20:00 | 6.75 (1-16) | 31.12 | 78.3% | 100.0% |
| PHL | all_days | 0.50 | 10:00-16:00 | 1.58 (0-8) | 31.32 | 95.0% | 100.0% |
| PHL | all_days | 0.50 | 10:00-18:00 | 2.62 (0-11) | 31.26 | 91.6% | 100.0% |
| PHL | all_days | 0.50 | 10:00-20:00 | 3.59 (0-11) | 31.12 | 88.5% | 100.0% |
| PHL | weekend_holiday | 0.10 | 10:00-16:00 | 1.94 (0-6) | 10.31 | 81.2% | 100.0% |
| PHL | weekend_holiday | 0.10 | 10:00-18:00 | 2.86 (0-7) | 10.31 | 72.3% | 100.0% |
| PHL | weekend_holiday | 0.10 | 10:00-20:00 | 3.64 (0-9) | 10.27 | 64.6% | 100.0% |
| PHL | weekend_holiday | 0.25 | 10:00-16:00 | 1.22 (0-4) | 10.31 | 88.1% | 100.0% |
| PHL | weekend_holiday | 0.25 | 10:00-18:00 | 1.76 (0-5) | 10.31 | 82.9% | 100.0% |
| PHL | weekend_holiday | 0.25 | 10:00-20:00 | 2.39 (0-6) | 10.27 | 76.8% | 100.0% |
| PHL | weekend_holiday | 0.50 | 10:00-16:00 | 0.45 (0-2) | 10.31 | 95.7% | 100.0% |
| PHL | weekend_holiday | 0.50 | 10:00-18:00 | 0.75 (0-3) | 10.31 | 92.7% | 100.0% |
| PHL | weekend_holiday | 0.50 | 10:00-20:00 | 1.11 (0-4) | 10.27 | 89.2% | 100.0% |
| ABE | all_days | 0.10 | 10:00-16:00 | 6.57 (0-14) | 34.37 | 80.9% | 100.0% |
| ABE | all_days | 0.10 | 10:00-18:00 | 9.54 (1-17) | 34.20 | 72.1% | 100.0% |
| ABE | all_days | 0.10 | 10:00-20:00 | 12.11 (3-20) | 33.86 | 64.2% | 100.0% |
| ABE | all_days | 0.25 | 10:00-16:00 | 3.44 (0-7) | 34.37 | 90.0% | 100.0% |
| ABE | all_days | 0.25 | 10:00-18:00 | 5.63 (0-11) | 34.20 | 83.5% | 100.0% |
| ABE | all_days | 0.25 | 10:00-20:00 | 7.57 (0-16) | 33.86 | 77.6% | 100.0% |
| ABE | all_days | 0.50 | 10:00-16:00 | 1.64 (0-4) | 34.37 | 95.2% | 100.0% |
| ABE | all_days | 0.50 | 10:00-18:00 | 2.87 (0-6) | 34.20 | 91.6% | 100.0% |
| ABE | all_days | 0.50 | 10:00-20:00 | 3.83 (0-10) | 33.86 | 88.7% | 100.0% |
| ABE | weekend_holiday | 0.10 | 10:00-16:00 | 2.21 (0-6) | 10.90 | 79.7% | 100.0% |
| ABE | weekend_holiday | 0.10 | 10:00-18:00 | 2.99 (0-7) | 10.86 | 72.5% | 100.0% |
| ABE | weekend_holiday | 0.10 | 10:00-20:00 | 3.79 (0-7) | 10.77 | 64.8% | 100.0% |
| ABE | weekend_holiday | 0.25 | 10:00-16:00 | 1.13 (0-4) | 10.90 | 89.6% | 100.0% |
| ABE | weekend_holiday | 0.25 | 10:00-18:00 | 1.79 (0-5) | 10.86 | 83.5% | 100.0% |
| ABE | weekend_holiday | 0.25 | 10:00-20:00 | 2.34 (0-5) | 10.77 | 78.2% | 100.0% |
| ABE | weekend_holiday | 0.50 | 10:00-16:00 | 0.59 (0-3) | 10.90 | 94.6% | 100.0% |
| ABE | weekend_holiday | 0.50 | 10:00-18:00 | 0.93 (0-3) | 10.86 | 91.5% | 100.0% |
| ABE | weekend_holiday | 0.50 | 10:00-20:00 | 1.11 (0-3) | 10.77 | 89.7% | 100.0% |
