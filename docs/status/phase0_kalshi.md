# Phase 0: Kalshi rain-market probe (question 2)

All times UTC. Raw Kalshi rows stay in data/raw/kalshi/ (git-ignored). Only aggregates appear here and in data/processed/kalshi_rain_probe/.
Scripts: scripts/p0_kalshi_series.py, p0_kalshi_markets.py, p0_kalshi_candle_sample.py, p0_kalshi_rain_summary.py. API calls used: about 150.

## Answer to question 2

| City | Daily rain market? | Since | Rule now | Real price history |
|---|---|---|---|---|
| NYC | Yes | 2021-09-08 (KXRAINNYC, with no market from 2022-08-23 to 2025-01-03); KXRAIN-NYC from 2026-07-15 | precipitation at CLINYC strictly greater than 0 inches; trace and missing = 0 | Summer 2025 complete (153 days), summer 2026 complete (76 + 73 days, two rule sets), 57 days of 2022, 15 days of Sep 2021. None for 2023 or 2024. |
| Philadelphia | Yes | 2026-07-15 (KXRAIN-PHIL) | same, at CLIPHL | 73 May-Sep days (2026-07-15 to 09-30) |
| Trenton | Yes | 2026-08-27 (KXRAIN-TTN) | same, at CLITTN | 35 May-Sep days (2026-08-27 to 09-30) |
| Newark | Yes | 2026-08-27 (KXRAIN-EWR) | same, at CLIEWR | 35 May-Sep days (2026-08-27 to 09-30) |
| Pittsburgh | Yes | 2026-09-23 (KXRAIN-PIT) | same, at CLIPIT | 8 May-Sep days |
| Allentown, other NJ/PA/NY | Not found | - | - | - |

Trenton and Newark do have a daily rain market, but not under their own series: they are city markets inside the generic series KXRAIN ("Where will it rain daily"), one event per day, one yes/no market per city (40 city codes seen, 20 of them from the first day). No series ticker or title contains TTN, EWR, TRENTON or NEWARK except the monthly KXRAINTTNM and KXRAINEWRM. All are still listed today (markets for 2026-11-11 and 11-12 are active).

## a) Series
- 79 rain series in "Climate and Weather" (505 series in the category): 33 daily, 26 monthly, 18 custom, 2 weekly. Full table: data/processed/kalshi_rain_probe/rain_series.csv.
- Daily coverage (daily_coverage.csv). May-Sep events by year:

| Series / city | Events | First | Last | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|
| KXRAINNYC (NYC; includes RAINNYC- tickers) | 869 | 2021-09-08 | 2026-07-15 | 15 | 105 | 0 | 0 | 153 | 76 |
| KXRAIN NYC | 116 | 2026-07-15 | 2026-11-12 | | | | | | 73 |
| KXRAIN PHIL | 116 | 2026-07-15 | 2026-11-12 | | | | | | 73 |
| KXRAIN TTN | 78 | 2026-08-27 | 2026-11-12 | | | | | | 35 |
| KXRAIN EWR | 78 | 2026-08-27 | 2026-11-12 | | | | | | 35 |
| KXRAIN PIT | 51 | 2026-09-23 | 2026-11-12 | | | | | | 8 |
| KXRAINDNYC (named days only) | 5 | 2026-09-19 | 2026-12-31 | | | | | | 1 |
| KXRAINDPHIL (named day) | 1 | 2026-11-22 | 2026-11-22 | | | | | | 0 |
| KXRAINDPIT (named day) | 1 | 2026-11-21 | 2026-11-21 | | | | | | 0 |

- KXRAINNYC by calendar year: 2021 = 101, 2022 = 217, 2023 = 0, 2024 = 0, 2025 = 355, 2026 = 196. Of the 105 May-Sep 2022 events only 57 carry a 0-inch strike (the rest carried one other strike, such as 0.05 or 0.1 inch); the last 2022 event is 08-22.
- KXRAIND ("Rain Daily") and RAINNYC return no markets under their own series ticker. KXRAINDNYC, KXRAINDPHIL, KXRAINDPIT are not daily in practice: they list a handful of named days (Halloween, Thanksgiving, New Year's Eve) that open several days ahead.

## b) Contract rule
Every daily rain market checked is a single yes/no on "strictly greater than 0 inches". It is not a ladder of amounts (KXRAINNYC: one market on 855 of 869 events; 14 events in 2021-22 had 2 to 5 strikes).

Current rule (KXRAIN; NYC and Philadelphia from the 2026-07-15 event, Trenton and Newark from 2026-08-27, same wording for each city with its own station code):
> "If the total precipitation at CLITTN in Trenton in Aug 27, 2026 is strictly greater than 0 inches, then the market resolves to Yes." ... "the official and final value used to determine this market as reported by the Weather Company." ... "Data for CLITTN can be found at https://weather.com/kalshi. "Trace" amounts (T) and missing daily precipitation values are counted as 0 inches."

In plain words: Yes if the day's reported total at the city's NWS climate station (CLINYC = Central Park, CLIPHL = Philadelphia airport, CLITTN = Trenton, CLIEWR = Newark airport) is 0.01 inch or more. A trace or a missing value is No. The named source is The Weather Company's page, which republishes the daily climate report. Only the order of the sentences changed on 2026-08-23; the terms did not.

Old NYC rule (KXRAINNYC, 2021-09-08 to 2026-07-15):
> "If the number of inches of precipitation recorded at Central Park, New York on <date> is strictly greater than 0, then the market resolves to Yes." ... "If the Expiration Value is T (when the target is 0) for Trace or R for Record ..., then the market resolves to Yes."

In plain words: same station and threshold, source the NWS Daily Climate Report (the filed terms and the series settlement source name it; the market text itself names it only on the 2022-03-05 to 2022-06-12 events), but a trace counted as Yes. This is the one material rule change: trace = Yes up to 2026-07-15, trace = No after. From 2025-03-05 the rules added a fallback to the NWS hourly time series for KNYC if the climate report was inconclusive.

Checks against the NWS climate report (IEM copy; kxrain_result_vs_cli.csv, result_vs_cli_check.csv): KXRAINNYC May-Sep results fit "measurable or trace = Yes" on 299 of 299 days. KXRAIN results fit "measurable only" on 114/114 (NYC), 114/114 (Philadelphia), 76/76 (Newark), 76/76 (Trenton); the 8, 12, 10 and 6 trace days all resolved No. No missing values occurred.

Day definition: not stated in the market rules or in the contract terms (the terms say only "<time period> ... as specified by the Exchange"). Kalshi's help page says NWS climate reports use local standard time, so during daylight time the day runs 1:00 AM to 12:59 AM local clock time; that statement is written for temperature markets. The exact match with the climate report above is consistent with the same day for rain. Trading stops at 11:59 PM ET (KXRAINNYC) or midnight ET (KXRAIN), which in summer is one hour before the climate day ends. Markets open only about 36 to 44 hours before the close.

Named-day markets differ: KXRAINDNYC from the 2026-10-31 event and KXRAINDPHIL name "Central Park (KNYC)" / "Philadelphia, PA (KPHL)", link to weather.gov and cite "the corresponding TWC Report (Daily)"; KXRAINDPIT says total precipitation "includes rainfall and the liquid equivalent of snow, sleet, and hail".

## c) Monthly series (monthly_structure.csv)
- KXRAINNYCM (NYC): 35 monthly events, Feb 2024 to Dec 2026. A ladder of "total precipitation at Central Park strictly greater than X inches" markets, 4 to 14 strikes per month, strikes 1 to 13 inches (half-inch steps in the Jul 2024 event, whole inches in Jul 2025 and Jul 2026).
- KXRAINPHILM, KXRAINEWRM, KXRAINTTNM: one event each so far (Nov 2026, all active), 7 strikes each: above 1, 2, 3, 4, 5, 6, 7 inches at CLIPHL / CLIEWR / CLITTN. Settled on the first NWS climate report that covers the whole month.

## d) Price history
- Retrieval works on both tiers through the existing client. 29 of 29 sampled markets returned hourly candles with yes_bid and yes_ask (candle_sample_summary.csv; the per-market table stays in data/raw/kalshi/rain/).
- Hours covered: KXRAIN Jul-Sep 2026 markets have a candle for nearly every hour of their 36 to 44 hour life (median 44 candles). KXRAINNYC 2026: 26 to 38 of 38 hours. KXRAINNYC 2025: 11 to 38 (median 22). 2022: 10 and 16. Hours without activity have no candle and must be carried forward. On the daily markets the earliest quote is 29 to 43 hours before close.
- A quote within half an hour of 24 hours before close exists on 25 of 29 sampled markets.
- Spread (median over a market's hours, then median over markets): 0.03 overall; KXRAIN Aug-Oct 2026 0.01 to 0.03; KXRAINNYC 2026 0.10; 2025 0.07 (but 0.31 when only hours with a real two-sided book are counted); two KXRAIN markets in the first week (July 2026) 0.25.
- Prior cache (prior_cache_ask24.csv), NYC May-Sep: 2023 and 2024 have no days (no market existed). 2025: an ask 24 hours before close on 86.3% of 153 days, an ask below $1.00 on 68.0%, median spread 0.11. 2026 (May 1 to Jun 30, 61 days): 100%, 90.2%, 0.06.
- Full pull estimate for NYC, Philadelphia, Trenton, Newark May-Sep: 301 KXRAINNYC 0-inch markets (15 + 57 + 153 + 76) plus 216 KXRAIN markets, of which 80 are on the live tier (events from 2026-09-11) and can go in about 4 batch calls. About 440 single calls. At the rate seen today (10 s per market, 68% of calls answered 429) that is about 75 minutes; at the 0.7 to 1 market per second logged earlier in docs/status/ehfaz.md it is about 10 minutes. Plan for up to 1.5 hours.

## e) Liquidity (liquidity_last30.csv, open_interest_active_snapshot.csv)
Volume in contracts ($1 each), last 30 settled events (2026-10-12 to 2026-11-10):

| City | Median | Min | Max |
|---|---|---|---|
| NYC | 11,132 | 1,006 | 131,565 |
| Philadelphia | 5,670 | 482 | 92,021 |
| Newark | 2,680 | 95 | 48,747 |
| Trenton | 2,643 | 3 | 74,687 |

May-Sep 2026 medians were higher: NYC 21,552, Philadelphia 15,090, Newark 9,703, Trenton 9,229. KXRAINNYC May-Sep medians: 1,147 (2022), 1,170 (2025), 7,422 (2026).
Open interest: the listing shows 0 for settled markets, so a 30-event series is not available without candles. Two open markets per city today: NYC 187 to 9,034, Philadelphia 734 to 1,577, Newark 658 to 1,067, Trenton 559 to 1,659. Peak open interest from the candle sample, eight KXRAIN markets of Sep 2026: median 13,582, range 5,479 to 81,025.

## f) Position limits
- RAINGLOBALPERIOD (terms for KXRAIN and the KXRAIND* series; filed 2026-06-04): "The Position Accountability Level for the Contract shall be $25,000 per strike, per Member." No hard limit stated.
- RAINNYC (terms for KXRAINNYC; filed 2021-09-02): "The Position Limit for the $1 referred Contract shall be $25,000 per Member" (defined in the cover letter as maximum loss exposure).
- RAINM (monthly; filed 2026-02-04): accountability level $25,000 per strike, per Member.
- Sources: https://assets.kalshi.com/regulatory/product-certifications/RAINGLOBALPERIOD.pdf, .../RAINNYC.pdf, .../RAINM.pdf. Read through WebFetch only; the shell could not download them (403), so no local copy was checked.

## g) NYC base rate, May-Sep (base_rate_nyc.csv)
| Year | Kalshi results | Station data (NWS climate report, not Kalshi) |
|---|---|---|
| 2023 | no market | 35.3% measurable; 48.4% with trace |
| 2024 | no market | 32.7% measurable; 46.4% with trace |
| 2025 | 46.4% Yes (71 of 153; trace = Yes) | 34.4% measurable; 47.0% with trace (151 days in the copy) |
| 2022 (extra) | 29.8% Yes (17 of 57 days with a 0-inch market, May 1 to Aug 12) | 31.4% measurable; 41.2% with trace |
| 2026 (extra) | 51.3% (39 of 76, to Jul 15, trace = Yes); 45.2% (33 of 73, from Jul 15, trace = No) | 42.5% measurable; 51.6% with trace |

## Consequences for the project
- Baseline city. Trenton is listed directly, at the Trenton station (CLITTN), so a park near Trenton has an exact Kalshi baseline contract going forward. But real Trenton prices cover 35 summer days, and Philadelphia 73. Neither has one full summer.
- Only NYC has real summer prices over more than one season: 2025 and 2026 complete, plus 57 days of 2022. That is two summers, not three, and 2023-2024 cannot be recovered because no market existed. The trace rule differs between the two halves of 2026.
- The 40+ season metric therefore cannot use real Kalshi prices. The baseline cost per day has to be modelled (for example fair probability plus a spread and fee) and calibrated on NYC 2025-2026 and on the four-city overlap of Jul-Sep 2026.
- The Kalshi contract pays on any measurable rain (0.01 inch or more) over the whole climate day. The project's bad day is 0.25 inch or more between 10am and 6pm. Under the current rule Kalshi would pay on 31 to 43% of May-Sep days in NYC (station data, 2021-2026), so the baseline hedge has large basis risk. That is useful for the comparison but must be stated.
- The market opens about a day and a half before the day ends, so a park cannot buy the season in advance; it must buy day by day. The accountability level is $25,000 per strike per member, and typical daily volume at Trenton is a few thousand contracts.

## Caveats
- The day window for rain is inferred (exact match with the climate report), not quoted from a rule.
- Position terms were read through a summarising fetcher, not from a local PDF.
- Open interest history needs candles; only a snapshot and a sample are reported.
- Spread figures come from 29 markets; the prior cache covers only KXRAINNYC from 2025-01-04 to 2026-06-30.
- IEM's copy of the climate report lacks 2 days in June 2025.
- The volume fields are contract counts as reported by the API; early-2026 NYC markets show a few very large values (up to 5.4 million on one January day) that were not investigated.

## What a Phase 1 pull needs
1. Hourly candles for about 520 markets (list above), about 440 single calls and 4 batch calls, 10 to 90 minutes, resumable with the existing client. Listings are already cached in data/raw/kalshi/rain/.
2. Forward-fill of hours without candles, and a rule for one-sided books (ask = 1.00 or bid = 0.00).
3. Hourly station rain for the 10am-6pm window from the rain workstream, to measure the gap between the Kalshi day rule and the park's bad-day rule.
4. A fee model (series fee type "quadratic", multiplier 1) for the cost of buying day by day.
5. A decision on which trace rule the modelled baseline uses; the current rule (trace = No) is the one a park would face.

## Blocked
- assets.kalshi.com from the shell: HTTP 403 at the proxy (PDFs read through WebFetch instead, as the task allowed).
- weather.com/kalshi does not state the day window or show station data to a fetcher.

## Progress log
- 2026-11-12 01:22: Read docs/PHASE0.md, src/kalshi/client.py (imported, not edited), docs/status/ehfaz.md. Inspected the prior cache data/raw/kalshi/ladder_quotes_prior_repo.parquet: 15,850 rows, of which 536 are KXRAINNYC (one market per event, strike_type "greater", floor_strike 0; events 2025-01-04 to 2026-06-30). The 2023-01-01 start in the file belongs to the temperature rows, not to rain. So the prior cache holds no rain prices for summers 2023 or 2024.
- 2026-11-12 01:23: Series list pulled (1 call, cached data/raw/kalshi/rain/series_list_climate.json): 505 series in "Climate and Weather", 79 rain series (33 daily, 26 monthly, 18 custom, 2 weekly). Table: data/processed/kalshi_rain_probe/rain_series.csv. No ticker or title contains TTN/EWR/TRENTON/NEWARK among the daily series; only the monthly KXRAINTTNM and KXRAINEWRM do.
- 2026-11-12 01:24: Market listings pulled for 11 series (38 requests, 13 HTTP 429, all retried). KXRAINNYC: 895 finalized markets (344 with RAINNYC- event tickers, 551 with KXRAINNYC-), closes 2021-09-09 to 2026-07-16, then nothing. KXRAIN: 3,050 markets, one event per day with one market per city (ticker suffix = city code, includes TTN), closes from 2026-07-16. KXRAINDNYC 5 markets, KXRAINDPHIL 1, KXRAINDPIT 1 (occasional named days only). KXRAIND and RAINNYC return no markets under their own series ticker.
- 2026-11-12 01:25: KXRAINNYC coverage checked two ways (895 markets from /historical/markets; 869 events from /events): 2021 = 101 events, 2022 = 217, 2023 = 0, 2024 = 0, 2025 = 355, 2026 = 196. Gap from 2022-08-22 to 2025-01-04. Direct lookups of RAINNYC-/KXRAINNYC- 23JUL15 and 24JUL15 tickers return 404 on both tiers. There was no NYC daily rain market in summers 2023 and 2024.
- 2026-11-12 01:25: Trace rule: under KXRAINNYC the rules say trace (T) resolves Yes when the strike is 0; all 42 markets with expiration value "T" and all 34 with value 0.00 that settled Yes confirm this. Under KXRAIN (from the 2026-07-15 event) trace and missing count as 0 inches (No).
- 2026-11-12 01:26: Contract terms: assets.kalshi.com is refused from the shell (curl: CONNECT tunnel failed, 403), recorded and not routed around. The three PDFs were read through WebFetch (a summarising reader, so quotes are as returned by it, not from a local copy): RAINNYC.pdf, RAINGLOBALPERIOD.pdf, RAINM.pdf.
- 2026-11-12 01:32: Candle test (01:27 to 01:32) on 29 markets (scripts/p0_kalshi_candle_sample.py): 87 requests, 59 HTTP 429, 291 s, all 29 retrieved (both tiers work through the client). About 10 s per market at a 1 s base gap.
- 2026-11-12 01:33: Aggregates written by scripts/p0_kalshi_rain_summary.py (no network). KXRAIN results equal the NWS CLI value with trace counted as No on every settled day: NYC 114/114, Philadelphia 114/114, Newark 76/76, Trenton 76/76. KXRAINNYC May-Sep results equal CLI with trace counted as Yes on 299/299 days.
- 2026-11-12 01:35: Per-market candle table moved to data/raw/kalshi/rain/ (git-ignored); only the grouped summary is in data/processed/. Status file completed.
