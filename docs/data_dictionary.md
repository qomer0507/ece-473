# Data dictionary (Qasim workstream)

All dates are ISO `YYYY-MM-DD`. A date is the GHCN-Daily observation day. For these first-order (USW) stations that is midnight to midnight local standard time (LST), which is also the NWS climate-report day. Dates are not shifted to UTC; the file timestamps and logs are UTC.
Temperatures are whole °F.

## data/manifests/stations.csv
One row per (station, reference pairing). Built by `scripts/pull_station_meta.py`.

| column | meaning |
|---|---|
| station_id | GHCN-Daily id (e.g. USW00094728) |
| name | GHCN-D station name |
| lat, lon, elev_m | as returned by NCEI with `includeStationLocation=1` (decimal degrees, metres) |
| city | NYC or Trenton |
| role | `reference` (contract settlement station) or `local` (stand-in for a business location) |
| reference_id | reference station for this row |
| distance_km | great-circle (haversine) distance to the reference, R = 6371.0088 km |
| coord_source | file under data/raw/ncei_spotcheck/ that holds the NCEI response with these coordinates |
| source_url | NCEI GHCN-D by_station file for this station |

## data/raw/ghcnd_tmax_from_ceraunic_cache.csv
Long table, 2010-01-01 to 2025-12-31, the nine stations in stations.csv. Built by `scripts/pull_ceraunic_cache.py`.

| column | meaning |
|---|---|
| date | observation day |
| station_id | GHCN-D id |
| tmax_f | daily maximum temperature, whole °F |

Provenance: derived cache from the prior Ceraunic repo (github.com/ehfuzzz/ceraunic, commit f65163c, `data/cache/eval04/ghcnd_tmax.parquet`). Original source: NOAA NCEI GHCN-Daily by_station files, pulled 2026-09-30 UTC. GHCN stores TMAX in tenths of °C. The prior code converts with floor(C × 9/5 + 32 + 0.5) and drops values with a non-blank quality flag. Missing days are absent rows. Details in `data/manifests/raw_provenance.csv`.

## data/raw/ghcnd_tmax_ncei.csv (not present yet)
Written by `scripts/pull_ghcnd.py` on a machine that can reach NCEI. Same columns plus `qflag` (GHCN quality flag; blank = passed). `src/load_weather.py` prefers this file when it exists. Quality-flagged values become NaN.

## data/raw/ncei_spotcheck/*.csv
Verbatim NCEI Access Data Service responses (44 station-days). Used only to verify the cache and to get coordinates. See SOURCE.md in that folder.

## data/processed/aligned_daily.csv
One row per (date, local station). Every day of May–Sep, 2015-05-01 to 2025-09-30 (1,683 days per pair, 7 pairs, 11,781 rows). Built by `python -m src.load_weather`.

| column | meaning |
|---|---|
| date | observation day |
| city | NYC or Trenton |
| local_station_id | local station GHCN id |
| ref_station_id | reference station GHCN id |
| local_tmax_f | local TMAX °F; empty if missing |
| ref_tmax_f | reference TMAX °F; empty if missing |
| data_quality | `ok`, `missing_local`, `missing_ref`, or `missing_both`. Nothing is imputed. |

## results/tables/basis_risk_prelim.csv
One row per (pair, k) for k = 85, 90, 95. Only `ok` days are used. Built by `python -m src.basis_risk`.

| column | meaning |
|---|---|
| distance_km | local-to-reference distance |
| days_in_window, days_ok, coverage_pct | season days in the window, days with both values, share in % |
| heat_days_ref, heat_days_local | days with TMAX >= k at reference / local |
| both_heat | both >= k |
| local_heat_ref_not | local >= k, reference < k (station contract does not pay, business is hot: shortfall day) |
| ref_heat_local_not | reference >= k, local < k (contract pays, business not hot: overhedge day) |
| p_local_heat_ref_not, p_ref_heat_local_not | above counts / days_ok |
| mismatch_rate | sum of the two / days_ok |
| miss_rate_given_local_heat | local_heat_ref_not / heat_days_local |
| false_rate_given_ref_heat | ref_heat_local_not / heat_days_ref |
| mean_diff_f, sd_diff_f, mae_f, p05_diff_f, p95_diff_f | stats of local − reference TMAX, °F |
| corr | Pearson correlation of local and reference TMAX (May–Sep days) |
