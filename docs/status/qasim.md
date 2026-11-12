# Qasim workstream log (weather data, Part 1 Study A)

All times UTC.

- 2026-11-11 22:55 Read SPEC_v2 and region pull note. Started.
- 2026-11-11 22:57 IEM NWSCLI geojson reachable (200). IEM cli.py for KTEB 2025 returns zero rows: Teterboro has no CLI product.
- 2026-11-11 23:05 Teterboro: IEM ASOS daily (network NJ_ASOS, station TEB) reachable. First look: on the 14 differing days the new pull equals IEM on 12; the old pull equals IEM on 0.
- 2026-11-11 23:10 github.com raw file (state outlines) refused with 403 "repository not enabled". www2.census.gov refused (CONNECT 403). Not retried. State and coast outlines taken instead from the PyPI package basemap-data (GSHHS/GMT data), which is an allowed host.
- 2026-11-11 23:20 stations.csv built. 334 stations, 95 USW, 84 exposure locations (NY 31, PA 24, NJ 11, MD 8, CT 8, DE 2). 41 IEM CLI sites in the six states, all matched within 2 km (max 1.74 km). 40 exposure locations have a CLI, 36 are candidates (not listed).
- 2026-11-11 23:20 One ambiguous CLI match: KPBG Plattsburgh. Two GHCN records lie within 2 km (USW00004742 at 0.15 km, only 2024-25 data; USW00064776 at about 1.3 km, full record). IEM lists USW00064776 for the site. Rule applied: take IEM's id when it is one of the stations within 2 km. Flagged in cli_mapping.csv.
- 2026-11-11 23:20 Eleven USW stations fail coverage (mostly military fields with no data 2015-2022, plus Maryland Science Center). IEM connection reset once mid-run; retry with pause succeeded.
- 2026-11-11 23:40 Teterboro check extended. IEM ASOS daily for TEB is not an independent official record: in 2015-2022 it equals NCEI on every season day; in 2023 to Aug 2025 it equals NCEI on only about 30% of days and NCEI is 1.3 F higher on average. Pulled raw METARs for TEB (May-Sep 2025) and read the station's own 24-hour maximum group. On the 14 differing days the OLD pull equals the METAR 24-h max on 14 of 14; the NEW pull on 0 of 14. The new pull equals IEM's daily value (highest hourly reading) on 12 of 14. From 2025-08-27 the new pull is below the METAR 24-h max on 10 of 16 further days (mean 1.3 F). KTEB has no CLI. The METARs carry the maintenance flag ($) on 82-86% of reports in Jul-Sep 2025.
- 2026-11-11 23:40 Spot check vs IEM CLI, 20 random season days each, seed 473: Albany 20/20, Hagerstown 20/20, LaGuardia 19/20 (2016-07-19: NCEI 85, CLI 88).
- 2026-11-11 23:45 Panel built: 84 stations (all four listed stations are exposure locations), 140,224 station-days, 99.19% of possible. One value dropped as impossible: Patuxent River NAS 2017-07-16, 130 F (listed in dropped_values.csv). Suspect but kept: Lancaster AP 2025-07-27, 107 F (regional median 86 F).
- 2026-11-11 23:50 src/panel/hedge.py and tests written. 31 tests pass.
- 2026-11-12 00:10 Study A run. Results in results/part1/. Map and scatter opened and checked: legible.

## Final section (2026-11-12 UTC)

### What was built
- `scripts/panel_build_stations.py` -> `data/processed/panel/stations.csv`, `cli_mapping.csv`
- `scripts/panel_build_panel.py` -> `data/processed/panel/tmax_panel.parquet`, `dropped_values.csv`
- `scripts/panel_iem_checks.py` -> `results/part1/teterboro_check.csv`, `iem_spotcheck.csv`
- `scripts/panel_fetch_outlines.py` -> `data/processed/panel/outlines.csv` (state borders, coastline, Great Lakes)
- `src/panel/hedge.py` (library), `src/panel/__init__.py`
- `tests/test_panel_hedge.py`, `tests/test_panel_bootstrap.py`, `tests/test_panel_data.py` (31 tests, all pass)
- `scripts/panel_study_a.py` -> `results/part1/`: `per_location.csv`, `per_location_long.csv`, `summary.csv`,
  `improve_counts.csv`, `distance_test.csv`, `distance_regression.csv`, `distance_bins_Lnow_REPORT_baseline.csv`,
  `location_geography.csv`, `study_a_summary.md`, `mismatch_map.png`, `distance_scatter.png`
- IEM downloads are cached in `data/processed/panel/iem_cache/`.

### Stations
- 334 stations, 95 USW. 84 exposure locations (NY 31, PA 24, NJ 11, MD 8, CT 8, DE 2). All four listed stations qualify.
- Philadelphia Intl (USW00013739) is in the data with 100% coverage. Kalshi's Philadelphia station is INFERRED, not confirmed. Column `station_inferred` flags it.
- has_cli method: IEM NWSCLI network list, 41 sites in the six states. Each site matched to the nearest of our 334 stations by haversine distance, limit 2 km. All 41 match (median 0.29 km, max 1.74 km). Each site also returned CLI rows for the 2025 season (150 or 151 days). IEM's own GHCN id for the site agrees with the coordinate match at 40 of 41.
- Ambiguous: KPBG Plattsburgh (two GHCN records within 2 km; took USW00064776, the id IEM lists; the nearer record USW00004742 has data for 2024-25 only). KNAK Annapolis: IEM lists two different ids (USC00180193 and USW00013752); the coordinate match is USW00013752, 0 km.
- 40 exposure locations have a CLI. 36 are candidate new markets (CLI, not listed).

### Study A, REPORT 2023-2025 (80 exposure locations that are not one of the four listed stations)
| | mean R | pooled miss rate | pooled false-payout rate |
|---|---|---|---|
| L_pre baseline | 0.1020 [0.0781, 0.1228] | 0.237 | 0.536 |
| L_pre adjusted | 0.0537 [0.0400, 0.0633] | 0.416 | 0.227 |
| L_now baseline | 0.1039 [0.0802, 0.1246] | 0.228 | 0.541 |
| L_now adjusted | 0.0545 [0.0416, 0.0637] | 0.393 | 0.252 |
- Adjusted minus baseline, mean R: L_pre -0.0483 [-0.0595, -0.0381]; L_now -0.0495 [-0.0610, -0.0386].
- L_now minus L_pre over these 80: baseline +0.0020, adjusted +0.0008. Adding Newark and Trenton did not lower mean mismatch at the other locations. It raised it slightly.
- Over all 84 (Newark and Trenton drop to zero under L_now): baseline 0.0994 -> 0.0990, adjusted 0.0524 -> 0.0519. Difference intervals include zero.
- Adjusted vs baseline by location (80, L_now, REPORT): 60 improve, 8 unchanged, 12 worsen. L_pre: 63 / 8 / 9. SELECT: L_now 57 / 9 / 14, L_pre 59 / 8 / 13.
- No hedge at all has mean R 0.0913 (the hot-day share). The baseline hedge is worse than no hedge on average and beats it at only 32 of 80 locations (L_now). The adjusted hedge beats it at 63 of 80.
- The adjusted hedge lowers R by raising the strike (median 94, range 89-99). It cuts false payouts and misses more hot days: pooled miss rate 0.23 -> 0.39. Beyond 300 km it misses 339 of 395 hot days.
- SELECT 2020-2022 (80): L_pre 0.1339 -> 0.0665; L_now 0.1351 -> 0.0702.
- Dropping Teterboro changes mean R in the fourth decimal.

### Distance
- Baseline hedge: mismatch rises with distance to the hedge station. L_now, REPORT: Pearson r = +0.58 (year-bootstrap 95% +0.37 to +0.68), Spearman +0.64, n = 80. L_pre: r = +0.63. Same sign in SELECT and over 2015-2025. OLS: +0.019 R per 100 km (R2 0.34). Miss rate also rises (r = +0.51, 70 locations with at least 10 hot days).
- With elevation difference and the coast proxy added, distance keeps its coefficient for R (+0.018 per 100 km, p 0.007) and elevation difference adds +0.012 per 100 m. For miss rate, distance is no longer significant once elevation and coast distance are in.
- Adjusted hedge: R does not rise with distance (r = -0.13 on REPORT, interval spans zero), but miss rate rises strongly (r = +0.80). Far locations have few hot days and get a high strike, so the hedge rarely pays.
- So this agrees with the outside paper for the plain nearest-station hedge. The earlier 7-station sample covered only short distances.
- p-values treat locations as independent, which is false. Read them as too small.

### Teterboro (USW00094741)
- The two pulls differ on 14 days, 2025-09-14 to 2025-09-29.
- New pull = IEM ASOS daily value on 12 of 14. Old pull = IEM on 0 of 14.
- But IEM's daily value for TEB in 2023-2025 is the highest hourly reading, not an official daily maximum. There is no CLI for KTEB.
- The station's own 24-hour maximum in the raw METARs equals the OLD pull on 14 of 14 days and the new pull on 0 of 14.
- Verdict: the new pull (NOAA's current record) matches the hourly readings; the old pull matched what the station itself reported as its daily maximum. NOAA appears to have replaced the late-August to September 2025 values with hourly-based ones. Cause not established. Two 90 F days (Sep 14, Sep 28) exist in the old pull only.
- The sensor carried the maintenance flag on most reports in Jul-Sep 2025, and its daily maxima in 2023-2025 run 1.3 F above its own hourly readings on average (3 F or more on about 15% of days; Newark about 1%). Teterboro 2023-2025 is suspect either way.
- The panel uses the new pull, as SPEC says.

### Caveats
- REPORT and SELECT have three summers each. The bootstrap has only 10 distinct year mixes. Intervals are rough.
- One reading dropped as impossible (Patuxent River NAS, 2017-07-16, 130 F). This screen (> 111 F) is not in SPEC. Lancaster AP 2025-07-27 at 107 F looks wrong but is kept.
- The pull has no NCEI quality flags, so flagged values were not filtered.
- Spot check vs CLI: 59 of 60 match. LaGuardia 2016-07-19: NCEI 85, CLI 88.
- Tie rule added beyond SPEC: if strikes 90-d and 90+d tie on the same station, the lower strike is taken.
- Coast distance uses a low-resolution shoreline and ignores the Great Lakes.
- USC stations are not in the panel. No USC sensitivity run was done.

### Blocked
- github.com raw file: 403 (repository not enabled). www2.census.gov: CONNECT 403. Neither retried.

### Open questions
- Minimum mismatch rewards hedges that almost never pay where hot days are rare. Should Part 2 rank on R alone, or also report miss rate, or limit locations to those with enough hot days?
- Should Teterboro 2023-2025 stay in the exposure set?
- KPBG: accept USW00064776 as the CLI station?
- Should Part 2 count the candidate station itself as a location (it drops to zero when listed)?

### Rerun
```
cd /home/claude/ece473-ceraunic
python scripts/panel_build_stations.py        # add --refresh to re-download IEM files
python scripts/panel_build_panel.py
python scripts/panel_fetch_outlines.py        # needs PyPI
python scripts/panel_iem_checks.py
python -m pytest tests/test_panel_*.py -q
python scripts/panel_study_a.py
```
