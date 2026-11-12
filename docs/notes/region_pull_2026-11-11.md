# Regional TMAX pull (2026-11-11 UTC)

Script: scripts/pull_region_tmax.py. Source: NCEI Access Data Service, daily-summaries, units=standard (deg F).
Output: data/raw/region/ (stations_region.csv, tmax/{ID}.csv, pull_log.csv). Coverage table: data/manifests/region_coverage.csv.

- 334 stations pulled, 0 errors. States NY NJ PA CT DE MD. Period 2015-01-01 to 2025-12-31.
- May-Sep coverage (1,683 possible days): 221 stations >= 98%, 254 >= 95%, 276 >= 90%, 297 >= 80%.
- Of the 276 at >= 90%: PA 103, NY 99, NJ 30, MD 24, CT 17, DE 3. 84 are USW (airport/first-order), 192 are USC (cooperative observer).
- 72 of the 276 lie inside the NYC-Philadelphia box (39.3-41.6N, 76.2-72.5W).
- 90F days per season among the 276: median 9.4, range 0.1 to 49.6.

## Checks
- Against the Milestone I dataset: 8 of 9 stations match on every day compared.
- Teterboro (USW00094741): 14 of 1,661 days differ, all 2025-09-14 to 2025-09-29, new values 1-6F lower on 13 of them. Two days change the 90F trigger. The new pull is NOAA's current record; the old cache was pulled 2026-09-30. Cause not established.

## Caveat to resolve before Part 1
USC (cooperative) stations often record at a morning observation time. Their "daily max" can then be the previous afternoon's high, logged a day late. Comparing them day by day against airport stations (midnight to midnight) would inflate mismatch. Options: restrict to the 84 USW stations, or check each USC station's observation time and shift or drop morning observers.
