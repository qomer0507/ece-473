# Phase 1: Kalshi rain workstream log

All times UTC. Raw Kalshi rows stay in data/raw/kalshi/ (git-ignored). Only aggregates appear here and in data/processed/kalshi_rain/.
"Observed" = real Kalshi quotes or results. "Modelled" = output of src/kalshi/rain_price_model.py.

## How to continue if interrupted
1. `python scripts/kalshi_rain_pull.py` is resumable: it skips every market whose candle file exists in data/raw/kalshi/candles/<series>/. Its log is data/raw/kalshi/rain/pull_log.csv; `--status` prints what is and is not cached without touching the network.
2. `python scripts/kalshi_rain_quotes.py` builds the per-market quote table (data/raw/kalshi/rain/quote_table.csv) from the cache (no network).
3. `python scripts/kalshi_rain_aggregates.py` writes the aggregates, the fitted price model and the figure (no network).
4. `python -m pytest tests/test_kalshi_rain_*.py -q`

## Progress log
- 2026-11-12 03:44: Read SPEC_v3, phase0_kalshi.md, phase0_verdict.md, client.py, fee section of docs/contract_spec.md. Cache at start: 16 KXRAIN and 10 KXRAINNYC candle files from the Phase 0 sample. API reachable (HTTP 200 on /historical/cutoff).
- 2026-11-12 03:47: Wrote src/kalshi/rain_quotes.py (scope, carry-forward, fee, calibration bins) and scripts/kalshi_rain_pull.py. Scope = 517 markets (Phase 0 estimated about 520): KXRAIN TTN 35, PHIL 73, EWR 35, NYC 73; KXRAINNYC 0-inch strike 2026 76, 2025 153, 2022 57, 2021 15. 22 were already cached.
- 2026-11-12 03:48: Pull started in the background, 1 s base gap, order TTN, PHIL, EWR, NYC (KXRAIN), then KXRAINNYC 2026, 2025, 2022, 2021. The 80 live-tier markets went through the batch endpoint (4 calls).
- 2026-11-12 03:58: Pull finished. 495 markets pulled in 586 s, 473 requests, 50 HTTP 429 (all retried), 0 errors. All 517 of 517 markets are cached; none is empty. Nothing is missing. Per-attempt log: data/raw/kalshi/rain/pull_log.csv.
- 2026-11-12 03:59: Checked that close_time is the scheduled close, not an early close: KXRAINNYC closes 23:59 ET on the rain day in every market; KXRAIN closes at 04:00Z or 05:00Z, the same for Yes and No markets. So "24 hours before close" is about midnight at the start of the rain day.
- 2026-11-12 04:00: Wrote scripts/kalshi_rain_quotes.py (raw table data/raw/kalshi/rain/quote_table.csv, 517 rows, git-ignored), scripts/kalshi_rain_aggregates.py, src/kalshi/rain_price_model.py and two test files.
- 2026-11-12 04:08: Aggregates, price model, figure written. 39 tests pass (tests/test_kalshi_rain_quotes.py, tests/test_kalshi_rain_price_model.py). Figure results/kalshi_rain/calibration.png opened and checked.

## Results (all from data/processed/kalshi_rain/; "observed" unless marked "modelled")

### 1. Pull (pull_coverage.csv)
| Series | City | Year | Markets | Pulled | Missing |
|---|---|---|---|---|---|
| KXRAIN | Trenton | 2026 (08-27 to 09-30) | 35 | 35 | 0 |
| KXRAIN | Philadelphia | 2026 (07-15 to 09-30) | 73 | 73 | 0 |
| KXRAIN | Newark | 2026 (08-27 to 09-30) | 35 | 35 | 0 |
| KXRAIN | NYC | 2026 (07-15 to 09-30) | 73 | 73 | 0 |
| KXRAINNYC | NYC | 2026 (05-01 to 07-15) | 76 | 76 | 0 |
| KXRAINNYC | NYC | 2025 (05-01 to 09-30) | 153 | 153 | 0 |
| KXRAINNYC | NYC | 2022 (05-01 to 08-12, 0-inch strike days only) | 57 | 57 | 0 |
| KXRAINNYC | NYC | 2021 (09-08 to 09-30) | 15 | 15 | 0 |

Not in scope and not pulled: Pittsburgh, the other KXRAIN cities, months outside May-Sep, the 48 NYC 2022 events with a non-zero strike. 2023 and 2024 have no market.

### 2. Quote rules (src/kalshi/rain_quotes.py)
- Decision times 36, 24, 12, 2 hours before the scheduled close. The quote is the close of the last hourly candle that ended at or before that time. Older than 6 hours = stale = not usable.
- buyable = fresh quote with ask < 1.00. two-sided = buyable and bid > 0.00. Ask = 1.00 or bid = 0.00 is flagged as a one-sided book.
- Station outcome per market: NWS daily climate report (IEM copy), class wet / trace / dry.

### 3. Quote coverage at 24 hours before close (quotes_by_city_year.csv)
| Group | Markets | Two-sided | Buyable (ask < 1) | Ask = 1.00 | Stale or no quote | Mean ask | Mean bid | Share Yes (two-sided days) | Mean spread | Median spread |
|---|---|---|---|---|---|---|---|---|---|---|
| Trenton 2026 | 35 | 33 (94%) | 34 | 1 | 0 | 0.394 | 0.362 | 0.333 | 0.032 | 0.03 |
| Philadelphia 2026 | 73 | 69 (95%) | 72 | 1 | 0 | 0.444 | 0.386 | 0.348 | 0.058 | 0.03 |
| Newark 2026 | 35 | 31 (89%) | 32 | 3 | 0 | 0.382 | 0.350 | 0.355 | 0.032 | 0.03 |
| NYC 2026 KXRAIN | 73 | 66 (90%) | 71 | 2 | 0 | 0.462 | 0.423 | 0.470 | 0.039 | 0.02 |
| NYC 2026 KXRAINNYC | 76 | 68 (89%) | 68 | 8 | 0 | 0.482 | 0.388 | 0.456 | 0.094 | 0.095 |
| NYC 2025 | 153 | 77 (50%) | 104 | 28 | 21 | 0.610 | 0.347 | 0.494 | 0.263 | 0.10 |
| NYC 2022 | 57 | 48 (84%) | 52 | 1 | 4 | 0.372 | 0.269 | 0.333 | 0.103 | 0.04 |
| NYC 2021 | 15 | 11 (73%) | 12 | 2 | 1 | 0.613 | 0.423 | 0.545 | 0.190 | 0.03 |

- Mean ask, bid and spread are over two-sided days. Share Yes over all markets: Trenton 0.343, Philadelphia 0.342, Newark 0.400, NYC KXRAIN 0.452, NYC 2026 KXRAINNYC 0.513, NYC 2025 0.464, 2022 0.298, 2021 0.600.
- Two-sided quotes fall off later in the day because the outcome becomes known: in the four KXRAIN groups the two-sided count is 201 of 216 at 36 h, 199 at 24 h, 104 at 12 h, 46 at 2 h. At 12 h and 2 h the remaining two-sided markets are mostly dry days (share Yes 0.29 and 0.09). The 36-hour time is thin on KXRAINNYC 2025 (37 of 153) because many markets had no quote yet.
- In 2026 every day with ask = 1.00 at 24 h had a bid of 0.98-0.99 and resolved Yes (15 of 15): nobody sells once rain is certain. In 2025 the ask was 1.00 on 28 days with a much lower bid (24 of 27 with a bid rained): a thin book.

### 4. Calibration (calibration.csv, results/kalshi_rain/calibration.png)
- Mid price 24 h before close, 403 two-sided market days, all groups: mean mid 0.420, share Yes 0.417. The price is right on average.
- By bin (price -> realised, n): 0.05 -> 0.02 (111); 0.14 -> 0.08 (40); 0.25 -> 0.18 (34); 0.35 -> 0.27 (26); 0.45 -> 0.52 (29); 0.55 -> 0.58 (24); 0.66 -> 0.83 (23); 0.74 -> 0.74 (39); 0.85 -> 0.89 (28); 0.95 -> 0.98 (49).
- Prices of 10 to 40 cents were too high: mean price 0.23, realised 0.16 (n = 100). Prices above 40 cents were slightly too low. Each single bin's 95% interval still contains the diagonal (23 to 111 days per bin); the pooled 10-to-40-cent gap is about 1.9 standard errors, so it is suggestive, not established.
- Sharpness (sharpness.csv), 24 h, 2025-2026, 344 two-sided days: Brier score of the mid 0.110, of the ask 0.123, of monthly climatology 0.247, of climatology plus yesterday's rain 0.245. Skill score of the mid against climatology 0.55. Mean mid on rain days 0.72, on dry days 0.22. Philadelphia+Trenton+Newark alone: 0.104 vs 0.228. Yesterday's rain adds nothing measurable.

### 5. Fees (docs/contract_spec.md: round_up_to_cent(0.07 * C * P * (1 - P)))
- One contract per order: mean fee 1.3 to 1.5 cents per contract in every group (always 1 or 2 cents). In a 100-contract order: 0.8 to 0.9 cent per contract. Whether Kalshi rounds per order or per fill is unverified (contract_spec.md).

### 6. Cost of buying one contract every day at the 24-hour time, observed prices (strategy_24h.csv)
| Group | Market days | Bought | No offer below $1 (of which rain days) | Premium | Fees | Payout | Net | Premium per $1 payout | Premium + fee per $1 payout |
|---|---|---|---|---|---|---|---|---|---|
| Trenton 2026 (08-27 to 09-30) | 35 | 34 | 1 (1) | 13.02 | 0.47 | 11 | -2.49 | 1.18 | 1.23 |
| Philadelphia 2026 (07-15 to 09-30) | 73 | 72 | 1 (1) | 31.40 | 1.07 | 24 | -8.47 | 1.31 | 1.35 |
| Newark 2026 (08-27 to 09-30) | 35 | 32 | 3 (3) | 11.85 | 0.45 | 11 | -1.30 | 1.08 | 1.12 |
| NYC 2026 KXRAIN (07-15 to 09-30) | 73 | 71 | 2 (2) | 32.10 | 1.01 | 31 | -2.11 | 1.04 | 1.07 |
| NYC 2026 KXRAINNYC (05-01 to 07-15) | 76 | 68 | 8 (8) | 32.78 | 0.91 | 31 | -2.69 | 1.06 | 1.09 |
| NYC 2026, both series | 148 | 138 | 10 (10) | 64.40 | 1.90 | 61 | -5.30 | 1.06 | 1.09 |
| NYC 2025 | 153 | 104 | 49 (30) | 53.91 | 1.43 | 41 | -14.34 | 1.31 | 1.35 |
| NYC 2022 (05-01 to 08-12) | 57 | 52 | 5 (1) | 17.94 | 0.73 | 16 | -2.67 | 1.12 | 1.17 |
| NYC 2021 (09-08 to 09-30) | 15 | 12 | 3 (3) | 7.10 | 0.16 | 6 | -1.26 | 1.18 | 1.21 |
| Four cities, 08-27 to 09-30 2026 | 140 | 133 | 7 (7) | 51.45 | 1.87 | 48 | -5.32 | 1.07 | 1.11 |

Dollars for one $1 contract per day. The buyer lost money in every group: 3 to 14 cents per contract bought. A day with no offer below $1.00 is skipped; almost all of those were rain days, so the buyer misses payouts exactly when rain is certain. NYC 2021, 2022 and 2025 through 2026-07-15 used the old rule (trace = Yes).

### 7. Price model (MODELLED; src/kalshi/rain_price_model.py, price_model.json, model_eval.csv)
Inputs available for all 29 seasons: p = monthly climatological share of measurable-rain days at the station, the day's own outcome, yesterday's outcome. For the fit p comes from GHCN-Daily 1998-2024 (climatology.csv), under each contract's own trace rule. Fit days: 381 days of 2025-2026 with a buyable ask at 24 h.

| Model | Formula | Fitted on all three sets |
|---|---|---|
| clim | ask = clamp(p + a) | a = 0.102 |
| persist | ask = clamp(p + k*(rain yesterday - p) + a), k from station history (Trenton 0.21) | a = 0.092 |
| skill (recommended) | ask = clamp(p + s*(rain today - p) + a) | a = 0.085 (se 0.015), s = 0.504 (se 0.031) |

Cost per contract = ask + taker fee. clamp = whole cents in [0.01, 0.99].

Sets (disjoint): A = NYC 2025 (104 days); B = NYC 2026 to Jul 15, old rule (68); C = four cities Jul 15-Sep 30 2026, current rule (209). Main test: fit on A + B, hold out C.

Held-out set C, mean per contract (observed vs modelled):
| Model | Cost (ask + fee): observed 0.437 | Error | Premium per $1 payout: observed 1.148 | Ask on rain days: observed 0.750 | Ask on dry days: observed 0.232 | Daily RMSE of ask |
|---|---|---|---|---|---|---|
| clim | 0.406 | -0.031 | 1.047 | 0.388 | 0.385 | 0.344 |
| persist | 0.414 | -0.023 | 1.070 | 0.409 | 0.386 | 0.339 |
| skill | 0.440 | +0.003 | 1.140 | 0.731 | 0.239 | 0.237 |

Payout per contract is 0.368 in all three (the models use the real outcome). Trenton alone inside set C (34 days): observed cost 0.397, skill 0.412 (+0.015), clim 0.396.
Other hold-outs (skill, error in mean cost): hold out A: -0.042; hold out B: +0.073; fit on all NYC, test Philadelphia+Trenton+Newark: -0.007. So the mean cost is reproduced to within about 4 to 7 cents per contract on an unseen set, and to under 1 cent on the set that matters most. The markup a alone differs a lot by set (skill fitted on one set: A 0.119, B 0.028, C 0.086); s is stable (0.48, 0.51, 0.51).

Why skill is recommended
- All three reproduce the average premium about equally (it is one fitted number). Only skill reproduces the pattern: observed asks are about 0.75 on rain days and 0.23 on dry days; clim and persist charge about 0.39 on both.
- That pattern decides what the hedge is worth. With climatology pricing a rain day nets about +0.60 and a dry day costs about 0.40. On real prices a rain day nets about +0.24 and a dry day costs about 0.25. The real contract moves about half as much money from dry days to rain days as a climatology price implies (1 - s = 0.50).
- City-month check (retention_by_month.csv, 18 city-months): slope of (payout - premium) on (rain days above climatology) is 0.33 on observed asks, 0.43 with skill, 0.92 with clim, 0.79 with persist. A hedge evaluation run with clim would overstate the baseline's protection by a factor of two to three.

What the model cannot capture (known biases)
1. No forecast. The day's outcome stands in for it. Valid only for buying the same quantity every day; never for choosing days by price.
2. It is deterministic. Real asks scatter around the two levels (residual sd 0.25). Season totals average most of that out.
3. Season-level wetness. A real market follows a wet spell day by day, so its mean price rises fully in a wet season; the model's rises by s. The city-month slope (0.33 observed vs 0.43 modelled) points the same way: the model probably still overstates the baseline's seasonal protection somewhat. 18 city-months is weak evidence.
4. Markup. a = 0.085 reproduces the mean ask on fit days that were wetter than climatology (share Yes 0.39 vs p about 0.36). The observed mean of (ask - result) is 0.068 (a_net_matched in the JSON). In an average season the model charges about 10 cents per contract over fair value including the fee; the observed loss was 8 cents. Run the hedge with a = 0.068 as a sensitivity. a also depends on market depth: 2025 was thin and expensive.
5. No offer on some rain days. Parameter u = share of rain days with ask = 1.00: 0.083 in set C (7 of 84), 0.122 in all of 2026, 0.37 in 2025. modelled_cost() scales the order on rain days by 1 - u. Default u = 0.083 (the current series). Set u = 0 to switch it off.
6. Trace rule. Sets A and B were priced under trace = Yes. The modelled baseline uses trace = No (SPEC). s and a are assumed the same under both rules; set C alone (trace = No) gives s = 0.51, a = 0.086, so this looks safe.
7. Two seasons, one region, cities that share weather on the same day. Standard errors come from a bootstrap over dates.
8. Fees are for one-contract orders rounded up to the cent (1.4 cents). A park buying N contracts in one order pays about 0.9 cent per contract; pass contracts=N.

How to call it
```
from src.kalshi.rain_price_model import modelled_cost, season_cost
modelled_cost(p_clim=0.34, rain_today=1)                 # recommended model and saved parameters
season_cost(p_list, rain_list, contracts=N)              # premium, fee, payout, net for a season (MODELLED)
```
p_clim must come from training seasons only (for example the 1998-2014 share of measurable-rain days in that month at Trenton).

## Blocked
- Nothing was refused in this phase. Only api.elections.kalshi.com was contacted.

## Not done / open
- Rounding of fees per order vs per fill is still unverified.
- The gap between the Kalshi day rule and the park's 10:00-18:00 loss rule needs the rain workstream's hourly data; not done here.
