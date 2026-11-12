# Risk check for the "hedgeability map" version (2026-11-11 UTC)

## 1. Which nearby cities Kalshi lists (daily high temp)
Source: https://api.elections.kalshi.com/trade-api/v2/series?category=Climate%20and%20Weather (read via WebFetch 2026-11-11)
- NYC: KXHIGHNY (The Weather Company; older HIGHNY series settled on NWS)
- Newark, NJ (EWR): KXHIGHTEWR, first event 2026-08-26 (77 settled events to 2026-11-10)
- Trenton, NJ: KXHIGHTTTN, first event 2026-08-26
- Philadelphia: KXHIGHPHIL, historical markets go back to at least 2026-03-28; earlier start not confirmed
- Further away: Washington DC (KXHIGHTDC), Boston (KXHIGHTBOS)
- Settlement station for PHIL and EWR not confirmed from rules (EWR title names "EWR").

Takeaway: NYC, Newark, Trenton and Philadelphia are all listed now, so multi-contract baskets are feasible. Newark and Trenton were added on the same day in Aug 2026, which is a natural test for a "which contract to list next" model.

## 2. Price history
- NYC: real hourly bid/ask snapshots (12/24/30 h before close) for every May-Sep day of 2023, 2024 and 2025, plus 2026 through June 30. In the prior Ceraunic repo: data/cache/elasticity/ladder_quotes.parquet (15,850 rows; also Chicago and NYC rain). Built from Kalshi hourly candlesticks (src/wi/elasticity/ladder_shim.py).
- NYC 2022 markets exist under HIGHNY (e.g. HIGHNY-22JUL15, 4 brackets).
- Kalshi historical candlesticks with yes_bid/yes_ask are available: /historical/markets/{ticker}/candlesticks?period_interval=60 (checked on KXHIGHNY-25JUL15-B86.5: 35 hourly candles).
- Newark, Trenton: prices only from 2026-08-26 (late summer and fall). Philadelphia: at least Mar 2026 onward, so summer 2026.
- Limitation: WebFetch summarizes and will not return raw data verbatim, so bulk pulls need a normal HTTP client (laptop).

## 3. Bulk weather and business data
- Blocked from the cloud shell: NCEI, NOAA S3 mirror, Iowa Mesonet, Census API.
- BigQuery public GHCN-D reachable via bq CLI, but needs a GCP project (none configured).
- Cached already: 25 GHCN-D TMAX stations (about 15 in NY/NJ/PA), plus 26 IEM ASOS stations 2023-2026.
- Hundreds of stations and Census business counts need a laptop pull (scripts/pull_ghcnd.py pattern).
