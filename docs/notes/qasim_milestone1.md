# Qasim — Milestone I notes (2026-10-30 UTC)

## What was done
- Got real daily TMAX for 9 GHCN-Daily stations (2 reference, 7 local), 2010–2025.
- Checked the data against NOAA directly: 44 of 44 station-days fetched from the NCEI Access Data Service match exactly. This check runs as a test.
- Built the aligned table `data/processed/aligned_daily.csv`: May–Sep, 2015-05-01 to 2025-09-30, 7 local–reference pairs, 11,781 rows. Gaps are flagged, never filled.
- Computed preliminary basis-risk numbers at k = 85/90/95 (`results/tables/basis_risk_prelim.csv`) and a scatter figure (`results/figures/local_vs_ref_scatter.png`).
- Code: `src/load_weather.py`, `src/basis_risk.py`, `scripts/pull_ceraunic_cache.py`, `scripts/pull_station_meta.py`, `scripts/pull_ghcnd.py`. Tests: `tests/test_alignment.py` (11 pass).

## Data provenance
- Shell access to NOAA/NCEI, IEM, AWS and GCS is blocked in our sandbox. GitHub works.
- Main path: derived cache from the prior Ceraunic repo (github.com/ehfuzzz/ceraunic, commit f65163c, `data/cache/eval04/ghcnd_tmax.parquet`). Original source: NOAA NCEI GHCN-Daily by_station files, pulled 2026-09-30 UTC. Quality-flagged values were already dropped. Values were converted from tenths of °C to whole °F.
- Independent check: the WebFetch tool can read NCEI Access Data Service CSVs. Four responses (44 station-days, 2019, 2024, 2025) are saved verbatim in `data/raw/ncei_spotcheck/`. All match the cache.
- Station coordinates come from those NCEI responses.
- To re-pull from NOAA on a laptop: `python scripts/pull_ghcnd.py --start 2010-01-01 --end 2025-12-31`. The loader then uses that file automatically.

## Stations and pairs
| city | role | id | name | km to ref |
|---|---|---|---|---|
| NYC | reference | USW00094728 | Central Park | 0 |
| NYC | local | USW00014732 | LaGuardia | 7.5 |
| NYC | local | USW00094741 | Teterboro | 11.5 |
| NYC | local | USW00014734 | Newark | 20.0 |
| NYC | local | USW00094789 | JFK | 23.3 |
| Trenton | reference | USW00014792 | Trenton-Mercer | 0 |
| Trenton | local | USW00054786 | Doylestown | 26.7 |
| Trenton | local | USW00094732 | Philadelphia NE | 27.7 |
| Trenton | local | USW00054785 | Somerville (KSMQ) | 40.6 |

Why these: first-order ASOS stations with long, clean records and the same instruments and day convention as the references. NYC locals span inland (Teterboro, Newark) and coastal (JFK) sites. Trenton has no ASOS closer than about 27 km, so its pairs are farther apart. Philadelphia Intl (USW00013739) is about 57 km away (prior-repo coordinates) and not used. I found no Princeton-area COOP station with a clean TMAX record in the cache.

## Coverage
- References: 100% of 1,683 season days.
- LaGuardia, Newark, JFK: 100%. Teterboro 98.7%. Philadelphia NE 98.9%. Doylestown 97.7%. Somerville 96.9%.
- Gaps cluster: Somerville May–Jun 2015 (35 days) and 2025 (18); Doylestown 2024 (21); Teterboro 2022 (12).

## Preliminary numbers (May–Sep 2015–2025, k = 90°F, ok days only)
| pair | ref heat days | local heat days | P(local heat, ref not) | P(ref heat, local not) | mean local−ref °F | corr |
|---|---|---|---|---|---|---|
| NYC: LaGuardia | 197 | 284 | 5.8% | 0.7% | +1.1 | 0.977 |
| NYC: Teterboro | 196 | 345 | 9.2% | 0.2% | +1.9 | 0.974 |
| NYC: Newark | 197 | 379 | 11.0% | 0.2% | +2.4 | 0.975 |
| NYC: JFK | 197 | 117 | 1.9% | 6.7% | −0.9 | 0.927 |
| Trenton: Doylestown | 260 | 297 | 4.2% | 1.9% | +0.5 | 0.978 |
| Trenton: Philadelphia NE | 263 | 405 | 8.7% | 0.2% | +2.1 | 0.987 |
| Trenton: Somerville | 258 | 315 | 4.6% | 1.1% | +1.1 | 0.979 |

The full table for k = 85 and 95 is in `results/tables/basis_risk_prelim.csv`.

Takeaways:
- Correlation is high (0.93–0.99), yet threshold triggers still disagree on 6–11% of season days. Basis risk sits in a narrow band near k.
- Mismatch is lopsided. Inland locals run hotter than Central Park, so the station contract misses 34–49% of their heat days. Coastal JFK runs cooler, so the contract pays on 57% of Central Park heat days when JFK is not hot.
- Distance alone does not predict mismatch. Doylestown (27 km) mismatches less than Newark (20 km). Siting (sea breeze, urban heat, elevation) matters more.

## Caveats
- Station siting: the local points are airport thermometers, not shops. They stand in for "a nearby location". Central Park is under tree cover and is known to read cool in summer.
- Urban heat and sea breeze drive the sign of the bias. A shop in Midtown may be hotter than any of these stations.
- Day boundary: GHCN-D and the NWS climate report both use the LST day. The prior Ceraunic repo found GHCN TMAX equal to the NWS CLI high on 99.7–100% of days for these references (2025-10 to 2026-08). Kalshi's newer settlement source (The Weather Company, from about 2026-08) is not checked here.
- One station per local point. No PRISM or grid check yet.
- In-sample over 2015–2025. No train/test split yet.
- The cache stores whole °F. A 0.5 °F rounding difference near k could flip a trigger.

## Open questions
1. Which local points does the team want as the "business"? One per city (e.g. LaGuardia and Doylestown) or all?
2. Does Kalshi NYC settle on the NWS CLI value or The Weather Company? (Ehfaz.) This changes which reference series to use after 2026-08.
3. Is a Trenton exchange contract real, or is Trenton a hypothetical reference? (Ehfaz.)
4. Should we add a non-airport local point (a COOP or PRISM cell at a Princeton or Midtown address)?

## Proposed Milestone II tasks (Qasim)
- Re-pull from NCEI on a laptop with `scripts/pull_ghcnd.py`; diff against the cache.
- Add train (2015–2021) / test (2022–2025) splits and bootstrap CIs (by season block) on the mismatch rates.
- Station-only hedge performance per pair: shortfall and overhedge in $ at N = $800, using Ehfaz's payout module.
- PRISM (or nClimGrid) cell at chosen business addresses as a robustness check.
- Plot mismatch rate vs distance and vs mean bias; check by month (June vs August sea breeze).

## Sources
- NOAA NCEI GHCN-Daily, by_station files: https://www.ncei.noaa.gov/pub/data/ghcn/daily/by_station/
- NOAA NCEI Access Data Service (daily-summaries): https://www.ncei.noaa.gov/access/services/data/v1
- GHCN-Daily documentation: https://www.ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-daily
- Prior Ceraunic repo (derived cache, background only): https://github.com/ehfuzzz/ceraunic
