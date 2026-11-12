# Contract specification: the rain-count contract and the Kalshi daily rain contract

Rewritten 2026-11-12 UTC for the rain project (docs/SPEC_v3.md, docs/PHASE2_PREREG.md).
Part A is the contract we build. Part B is the contract that exists today and that we compare with.
Part C puts them side by side. The earlier temperature specification is kept, unchanged, at the end.

Labels used here: **OBSERVED** = station data or Kalshi's own rules and results. **MODELLED** = a price we compute.
**SIMULATED** = from the LMSR rule, no real orders. **LOCAL EVM** = run in the Hardhat test chain, not on Sepolia.

---

## A. The rain-count contract (ours)

### A1. What is counted

| Item | Definition | Source |
|---|---|---|
| Station | Trenton-Mercer airport (ASOS TTN; NWS climate report CLITTN). 11.3 km from Sesame Place. | SPEC_v3 |
| Season | Every day from the Friday before Memorial Day through Labor Day. 102 days, or 109 in some years. | SPEC_v3 |
| Loss day | A day with at least 0.25 inch of rain between 10:00 and 18:00 local clock time at the station. | SPEC_v3 |
| Index C | The number of loss days in the season. A whole number from 0 to the number of season days. | PHASE2_PREREG |
| Unusable days | Days with incomplete opening-hour data are dropped and counted, never filled in. | SPEC_v3 |

The contract pays on the **count for the whole season**. It does not pay day by day.

### A2. Buckets (registered, from the training seasons)

OBSERVED loss-day counts at Trenton in the 16 training seasons 1999-2014:
2, 6, 6, 4, 8, 5, 5, 8, 2, 4, 12, 2, 1, 6, 12, 3 (data/processed/rain/season_counts_TTN.csv).
The five edges are the 1/6, 2/6, 3/6, 4/6 and 5/6 quantiles of these counts: **2, 4, 5, 6, 8**.
The five quantiles are all different, so there are six distinct buckets and nothing was merged.

| Bucket j | 0 | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| Loss days in the season | 0-2 | 3-4 | 5 | 6 | 7-8 | 9 or more |
| Training seasons n_j | 4 | 3 | 2 | 3 | 2 | 2 |
| Mean training count m_j | 1.75 | 3.667 | 5 | 6 | 8 | 12 |
| Smoothed probability q_j = (n_j + 0.5) / 19 | 0.2368 | 0.1842 | 0.1316 | 0.1842 | 0.1316 | 0.1316 |

Full record: results/market/registered_buckets.csv. Each count is in exactly one bucket. An edge is the last count of its bucket.

### A3. What the buyer holds and what it pays

- A buyer holds a number of shares of each bucket. One share of the bucket that contains the season's count pays one unit. The other buckets pay nothing.
- The registered hedge is stepped: per unit of hedge size the park holds **h_j = max(m_j - d, 0)** shares of bucket j.
- d is the deductible: the loss days the park carries itself. d is chosen on the training seasons from 0 to 8. **It is not chosen yet.**
- Payout for a season = h_j of the bucket that contains C. Example with d = 3: holdings 0, 0.667, 2, 3, 5, 9. A season with 5 loss days pays 2 units; a season with 12 pays 9 units.
- One unit stands for L, the park's loss per loss day. L is a scenario parameter, not a measured loss.
- Shares are whole numbers on chain. All h_j are multiples of 1/12, so a payout unit of L/12 (or a hedge size that is a multiple of 3 or 12) gives whole shares.

### A4. Price

| Price | Rule | Label |
|---|---|---|
| Registered premium | 1.20 x expected payout, expected payout = sum of h_j x q_j. Sensitivity 1.10 and 1.30. | MODELLED |
| LMSR market price | Cost C(q) = b ln(sum of exp(q_j / b)). A buy is charged C(after) - C(before). All six prices start at 1/6. | SIMULATED (sim/experiment.py), and LOCAL EVM for the contract |

Nobody has quoted either price. See results/market/summary.md for what the LMSR rule charges for the registered hedge.

### A5. How it runs on chain (contracts/RainCountLMSR.sol, contracts/SeasonCountOracle.sol)

| Step | Who | Rule |
|---|---|---|
| Open the season | oracle owner | Station, season, start, end, number of days. Once per season. Can not be changed. |
| Deploy and fund | sponsor | Sends at least b x ln(6) x unit. This is the most the sponsor can lose. Edges, b and unit are fixed for ever. |
| Buy | anyone | `buy` one bucket or `buyBasket` six quantities in one transaction, until tradingClose. tradingClose is at or before the first season day. Buy only: no selling. |
| Report | reporter | One count per (station, season). Refused before the season end. Refused if above the number of season days. |
| Settle | anyone | Needs a valid report that is at least disputeDelay seconds old. Final. |
| Redeem | buyer | Shares of the winning bucket x unit. |
| Withdraw | sponsor | Everything not owed to buyers, after settle or cancel. |
| No valid report by the deadline | anyone | `cancelAfterDeadline`: every buyer gets back exactly what they paid; the sponsor gets the funding back. |
| Emergency | sponsor | `emergencyCancel`, only while trading is open. Same refunds. |
| Unclaimed money | sponsor | `sweepUnclaimed` after the claim period (7 days or more). |

Trust, stated plainly:

- One reporter decides the count. The contract checks who reports and when. It can not check that the count is true.
- The sponsor and the reporter must be different people. The contract can not enforce it.
- During the dispute delay the oracle owner can void a report; the market then refunds everybody after the deadline.
- Testnet only. Not audited. Tested in the local EVM (`npm test` in contracts/); not deployed anywhere by us.

Student guide: docs/deploy_sepolia.md.

---

## B. The Kalshi daily rain contract (what exists today)

All facts in this part are as recorded in docs/status/phase0_kalshi.md (Kalshi public API and contract terms, read 2026-11-12 UTC). OBSERVED unless marked.

| Item | Rule | Notes |
|---|---|---|
| Series | KXRAIN ("Where will it rain daily"). One event per day, one yes/no market per city. Trenton is the city code TTN. | Trenton listed since 2026-08-27; Philadelphia and NYC (under KXRAIN) since 2026-07-15. No Allentown market found. |
| Question | "If the total precipitation at CLITTN in Trenton in <date> is strictly greater than 0 inches, then the market resolves to Yes." | One yes/no market. Not a ladder of amounts. |
| In plain words | Yes if the day's official total at the station is 0.01 inch or more. | |
| Trace and missing | "Trace" amounts (T) and missing daily values count as 0 inches: No. | The rule since the 2026-07-15 event. The old NYC series KXRAINNYC (2021-09-08 to 2026-07-15) counted a trace as Yes. |
| Source | "the official and final value ... as reported by the Weather Company" (weather.com/kalshi), which republishes the NWS daily climate report for the station. | Results matched the NWS climate report with trace = No on 76 of 76 settled Trenton days. |
| Station | CLITTN = Trenton. CLIPHL = Philadelphia airport. CLINYC = Central Park. CLIEWR = Newark airport. | |
| Day | Not stated in the rules. Inferred: the climate-report day, local standard time, so 1:00 AM to 12:59 AM clock time in summer. | Inferred from the exact match with the climate report. |
| Payout | $1 per contract if Yes, $0 if No. | |
| Listing | Each market opens about 36 to 44 hours before it closes. Trading stops at midnight ET. | A park can not buy a season in advance. It must buy day by day. |
| Size | Position accountability level $25,000 per strike per member. No hard limit stated. | Read through a summarising fetcher, not from a local PDF. |
| Liquidity at Trenton | Median 2,643 contracts per day over the last 30 settled events (range 3 to 74,687). May-Sep 2026 median 9,229. | |
| Fee | Series fee type "quadratic", multiplier 1. Formula in the fee schedule: see "Earlier temperature study", section 3. | |
| Real prices at Trenton | 35 summer days (2026-08-27 to 09-30). | So every season-long Kalshi price in this project is MODELLED (src/kalshi/rain_price_model.py). |

Not verified: the exact day window for rain; the position terms from a local copy; open-interest history.

---

## C. Side by side

| | Rain-count contract (ours) | Kalshi daily rain contract |
|---|---|---|
| Station | Trenton (TTN) | Trenton (CLITTN), the same station |
| What triggers | The season's number of days with at least 0.25 inch between 10:00 and 18:00 | Each day's official total of 0.01 inch or more, any hour |
| Period | One season, about 102 days | One day |
| When you can buy | Before the season starts, once | About a day and a half before each day, about 102 times |
| Payout | Stepped in the count: h_j = max(m_j - d, 0) units for the bucket that contains the count | $1 per contract on each Yes day |
| Days that pay at Trenton, OBSERVED 1999-2026 | Loss days: 5.4 per season on average (1 to 12) | Pay days: 34.5 per season on average (20 to 49) |
| Overlap, OBSERVED 1999-2026 | Every loss day is also a Kalshi-pay day | 84% of Kalshi-pay days are not loss days |
| Price | MODELLED: 1.20 x expected payout. SIMULATED: LMSR market | MODELLED for whole seasons; real prices for 35 Trenton summer days |
| Who takes the other side | A sponsor who funds b ln 6 and can lose at most that | Other traders on an order book |
| Settlement source | One reporter enters the count (trusted, disclosed) | The Weather Company's copy of the NWS daily climate report |
| Status | Class project, local tests, testnet guide. Does not exist as a market. | Live, regulated exchange |

Pay-day figures: data/processed/rain/season_counts_TTN.csv, usable seasons, official daily total (column ref_ghcn_pay_days);
chart results/rain/loss_vs_kalshi_days.png.

What the comparison can and can not say: both contracts settle at the station, not at the park. Whether either one
cuts a park's bad-season cost is the Phase 2 evaluation (docs/PHASE2_PREREG.md). It is not answered in this file.

---

## Earlier temperature study

**Everything below this line is the earlier temperature (heat-day) specification, written for Milestone I and
compiled 2026-10-30 UTC. It is kept unchanged for the record, with its headings moved one level down. It does not
describe the rain contract.** Original title: "Contract specification (Ehfaz, Milestone I)".

Compiled 2026-10-30 UTC. Each fact is marked **VERIFIED** (with the URL we read) or **UNVERIFIED**.
Kalshi API pages were read with a web-fetch tool between about 2026-10-30T02:30Z and 03:05Z. API responses are live and can change. Market snapshots below are single observations, not a price history.

Base URL for Kalshi API reads below: `https://api.elections.kalshi.com/trade-api/v2` (public, read-only, no account).

---

### 1. Kalshi NYC daily high: series KXHIGHNY

| Fact | Status | Source |
|---|---|---|
| Series title "Highest temperature in NYC", frequency daily, category Climate and Weather. | VERIFIED | `/series/KXHIGHNY` |
| Series-level settlement source is **The Weather Company** (weather.com/kalshi). Series last updated 2026-10-22. | VERIFIED | `/series/KXHIGHNY` |
| Fee type "quadratic", fee multiplier 1. | VERIFIED | `/series/KXHIGHNY` |
| Contract terms document is the generic GLOBALTEMPERATURE terms. Source agencies in order: The Weather Company, then NWS, then the local national weather service. | VERIFIED | https://assets.kalshi.com/contract_terms/GLOBALTEMPERATURE.pdf |
| Settlement value $1.00 per contract. Minimum tick $0.01. Position accountability level $25,000 per strike per member. | VERIFIED | GLOBALTEMPERATURE.pdf above |
| Only the first official non-preliminary report is used. Later revisions are ignored. Kalshi may hold expiration if the first publication has a material error. | VERIFIED | GLOBALTEMPERATURE.pdf; `/series/KXHIGHNY` product_metadata |
| Strike semantics: "between" is inclusive on both ends; "greater" and "less" are strict. | VERIFIED | GLOBALTEMPERATURE.pdf; tickers in `/markets?series_ticker=KXHIGHNY` |
| Each daily event is a **ladder of 6 markets**: two tails plus four 2°F brackets. Example for 2026-10-15: "63° or below" (T64, less than 64), 64–65, 66–67, 68–69, 70–71, "72° or above" (T71, greater than 71). | VERIFIED | `/markets?series_ticker=KXHIGHNY&limit=8` |
| Bracket placement shifts day to day around the forecast. Lower bracket bounds were even on 2026-08-16 (78, 80, 82, 84) and odd on 2026-08-10 (a 91–92 bracket). So a fixed threshold such as 90°F is not always a bracket edge. | VERIFIED | `/markets?event_ticker=KXHIGHNY-26AUG16`, `/markets?event_ticker=KXHIGHNY-26AUG10` |
| Timing (example event 2026-10-15): opens 2026-10-14T14:00Z (10:00 ET the day before), closes 2026-10-16T05:00Z (01:00 EDT, which is midnight EST, so the end of the local-standard-time day), latest expiration 2026-10-22T14:00Z. | VERIFIED | `/markets?series_ticker=KXHIGHNY&limit=8` |
| Settled markets resolve next morning: 2026-08-13 event settled 2026-08-14T12:04Z; 2026-08-17 event settled 2026-08-18T11:19Z. | VERIFIED | `/markets?event_ticker=KXHIGHNY-26AUG13`, `/markets?event_ticker=KXHIGHNY-26AUG17` |
| NWS climate reports use **local standard time**. In daylight time the day runs 1:00 AM to 12:59 AM local clock time. | VERIFIED | https://help.kalshi.com/markets/popular-markets/weather-markets |
| Trading is 24/7 except scheduled maintenance Thursdays 03:00–05:00 ET. | VERIFIED | https://help.kalshi.com/trading/what-are-trading-hours (page dated 2026-08-23) |
| Markets list only about 1.5 days ahead. You cannot buy a season of heat-day protection up front on Kalshi. | VERIFIED (open/close times above); the "cannot buy a season" part is our inference | as above |

#### 1a. Settlement source and station: what changed and when

| Event date (local) | Source named in market rules | Station wording | Status | Source |
|---|---|---|---|---|
| 2026-08-10 | NWS "Climatological Report (Daily)" | "Central Park, New York" | VERIFIED | `/markets?event_ticker=KXHIGHNY-26AUG10` |
| 2026-08-12 | NWS Climatological Report (Daily) | Central Park, New York | VERIFIED | `/markets?event_ticker=KXHIGHNY-26AUG12` |
| 2026-08-13 | NWS Climatological Report (Daily) | Central Park, New York | VERIFIED | `/markets?event_ticker=KXHIGHNY-26AUG13` |
| 2026-08-14 | The Weather Company | "New York City"; Central Park named in secondary rules | VERIFIED (one read) | `/historical/markets?event_ticker=KXHIGHNY-26AUG14` |
| 2026-08-15 to 2026-08-18 | The Weather Company | "New York City (CLINYC)" | VERIFIED | `/markets?event_ticker=KXHIGHNY-26AUG15` ... `26AUG18` |
| 2026-10-15 (current) | The Weather Company | New York City (CLINYC) | VERIFIED | `/markets?series_ticker=KXHIGHNY&limit=8` |

Findings:
- The switch from NWS to The Weather Company happened between the 2026-08-13 and 2026-08-14 events. Our project records said "about 2026-08-17". The API shows **2026-08-14** is the first event naming The Weather Company. We did not find a Kalshi announcement of the change.
- **CLINYC** is the NWS product ID for the Central Park daily climate report, issued by NWS New York (KOKX). VERIFIED: https://mesonet.agron.iastate.edu/wx/afos/p.php?pil=CLINYC
- So the station is still Central Park (KNYC, SPEC reference). The *publisher* of record is now The Weather Company. Whether TWC's value always equals the NWS CLI value is **UNVERIFIED**. Kalshi's rules warn that preliminary TWC data can show rounding or conversion differences.
- Kalshi's help pages (dated 2026-07-22) still say daily markets settle on the NWS Daily Climate Report. Those pages are older than the change. Market rules take priority, as the help page itself says.
- Historical: Kalshi's 2023 CFTC filing for the older NYC contract "NHIGH" named the NWS Daily Climate Report for Central Park, $1.00 settlement, last trading 11:59 pm ET. VERIFIED: https://www.cftc.gov/filings/orgrules/rules042623979.pdf
- **Implication for the backtest (2015–2025):** the whole period predates the TWC switch. Using GHCN-D TMAX at USW00094728 is a reasonable proxy for what the contract measured then (NWS CLI for Central Park). GHCN-D vs. CLI equality on every day is **UNVERIFIED**; Qasim could spot-check a few days.

### 2. Trenton: series KXHIGHTTTN exists

| Fact | Status | Source |
|---|---|---|
| Series **KXHIGHTTTN**, title "Trenton, NJ Daily Max Temp", daily, Climate and Weather, fee type quadratic, multiplier 1. | VERIFIED | `/series/KXHIGHTTTN` |
| Settlement source The Weather Company. Rules name the station as "Trenton (CLITTN)". | VERIFIED | `/series/KXHIGHTTTN`; `/markets?series_ticker=KXHIGHTTTN&limit=6` |
| CLITTN is the Trenton NJ climate summary issued by NWS Mount Holly (KPHI). The IEM page links it to station KTTN (Trenton-Mercer Airport, our SPEC reference). | VERIFIED | https://mesonet.agron.iastate.edu/wx/afos/p.php?pil=CLITTN |
| Earliest event we found: KXHIGHTTTN-26AUG26 (2026-08-26). Markets opened 2026-08-25T17:05Z. That day's 82–83° bracket settled YES at 82°F. | VERIFIED | `/events?series_ticker=KXHIGHTTTN&limit=200`; `/historical/markets?event_ticker=KXHIGHTTTN-26AUG26` |
| Same 6-market ladder structure as NYC. | VERIFIED | `/markets?series_ticker=KXHIGHTTTN&limit=6` |
| Liquidity is thin. 2026-08-26 event: 45 contracts total volume, all in one bracket. 2026-10-30 event at fetch time: 20 to 231 contracts per market. | VERIFIED (snapshot) | same URLs |
| A Trenton daily low series KXLOWTTTN and a monthly snowfall series KXTTNSNOWM also exist. | VERIFIED (search results and `/series/KXTTNSNOWM`) | https://kalshi.com/markets/kxlowtttn/trenton-daily-low-temp-/kxlowtttn-26oct07 |

Implication: a Trenton station contract is real, but only since late August 2026. It has never traded in a May–Sep heat season. For 2015–2025 the Trenton station leg is a **synthetic** contract on KTTN TMAX, not an observed market.

### 3. Kalshi fees

| Fact | Status | Source |
|---|---|---|
| Taker fee = round_up(M × 0.07 × C × P × (1 − P)). P = price in dollars, C = contracts, M = multiplier (default 1). | VERIFIED | https://kalshi.com/docs/kalshi-fee-schedule.pdf (effective 2026-07-07) |
| Maker fee = round_up(M × 0.0175 × C × P × (1 − P)); maker M defaults to 0 unless a series sets it. | VERIFIED | same |
| Rounding text says the fee is rounded up "to a centicent", but the schedule's table shows whole cents (1 contract at $0.50 shows $0.02; 100 at $0.50 shows $1.75). Unit is ambiguous. | VERIFIED (ambiguity) | same |
| Whether rounding is per order or per fill. | UNVERIFIED | — |
| Whether KXHIGHNY/KXHIGHTTTN charge maker fees (series multiplier 1 is reported, but not split by maker/taker). | UNVERIFIED | `/series/KXHIGHNY` |

Worked examples (our arithmetic, taker, $0.01 rounding): 800 contracts at $0.10 cost $80 plus a $5.04 fee (6.3%). 800 at $0.50 cost $400 plus $14.00 (3.5%). The fee is largest in dollars at P = 0.5 but largest as a share of premium for cheap contracts.

### 4. CME weather futures (institutional benchmark)

| Fact | Status | Source |
|---|---|---|
| CME Rule Chapter 403: Degree Days Index futures (HDD and CDD), 13 US stations. | VERIFIED | https://www.cmegroup.com/content/dam/cmegroup/rulebook/CME/IV/400/403/403.pdf |
| **New York La Guardia Airport (WBAN 14732)** is listed. Philadelphia International (WBAN 13739) is the nearest listed station to Trenton. Central Park and Trenton are not listed. | VERIFIED | same |
| Contract size $20 × index; index values reported by Speedwell Settlement Services from NWS observations. | VERIFIED | same |
| HDD/CDD use a 65°F base. US contracts: HDD for winter months, CDD for summer months; seasonal strips of 2, 3 or 5 months (e.g. CDD May–Sep). European cities and Tokyo also use CAT. | VERIFIED | https://www.cmegroup.com/education/lessons/overview-of-weather-markets.html ; https://www.cmegroup.com/articles/2023/cme-group-weather-suite-expanded.html (2023-06-27) |
| Exact listed months per city today. | UNVERIFIED (rulebook says "determined by the Exchange") | 403.pdf |

Why it matters: CME products are monthly or seasonal degree-day sums at airports, not daily heat-day binaries. They do allow seasonal tenor, which Kalshi does not. Their mismatch with a shop in Manhattan or Trenton is bigger (wrong station and wrong index). We use them only as context.

### 5. Cost and markup assumptions (for `station_premium`)

Observed snapshots (fetched about 2026-10-30T03:00Z, one moment each, not representative of summer):
- KXHIGHNY-26OCT30 ladder: sum of YES asks $1.06, sum of YES bids $0.99. Buying the whole ladder at the ask costs about 6% over $1. Bid-ask on the most active bracket was 1 cent.
- KXHIGHTTTN-26OCT30 ladder: sum of asks $1.08, sum of bids $0.93 (our sum of the listed quotes). Spreads up to 6 cents on one bracket.

Literature: Bürgi, Deng & Whelan (2025) find Kalshi contracts priced under 10 cents lose over 60% of stake on average, and the bias holds in the Climate & Weather category. A heat-day leg often sits in that price range. See docs/literature.md.

**Assumed markup scenarios (ASSUMED, label in all outputs):**

| Scenario | Markup over fair value | Basis |
|---|---|---|
| Low | 5% | ≈ observed NYC ladder overround in one snapshot |
| Base | 15% | ladder overround plus wider spreads in thin markets (Trenton snapshot ~8% on asks) plus some longshot bias |
| High | 50% | longshot bias for cheap contracts (Bürgi et al. 2025); thin Trenton book |

Fees are added on top with `kalshi_fee`. "Fair value" here means the modelled probability from training data. It is not a market price.

### 6. Contract we will model

**Station heat-day binary.** For reference station s (KNYC or KTTN), day t, threshold k:

```
payout_t = N × 1{TMAX_s,t >= k}      N = $800 = 800 contracts × $1
```

- Equality triggers (TMAX = k pays). This matches a Kalshi "k or above" leg because temperatures settle as whole °F, so "greater than k − 1" equals ">= k".
- Daily, local-standard-time day, as in the NWS climate report and GHCN-D.
- Implemented in `src/station_hedge.py::station_payout`. Missing TMAX gives a missing payout.

**How a Kalshi ladder approximates it.** On a given day:
1. If the top tail is "k or above" (strike T(k−1)), buy that one market.
2. If k is a bracket's lower bound, buy YES on that bracket, every bracket above it, and the top tail. Payout is exactly $1 if TMAX ≥ k.
3. If k is the upper bound of the bottom tail plus one (bottom tail = "k − 1 or below"), buy NO on the bottom tail.
4. If k falls inside a 2°F bracket (bracket parity is wrong that day), the hedge cannot be exact. Either include the bracket (pays at TMAX = k − 1 too, overhedge) or exclude it (misses TMAX = k, shortfall). This is a small **strike basis**, separate from geographic basis.
5. Cost = sum of asks of the markets bought + taker fees on each fill. Buying several legs pays several spreads, so ladder cost is above the single-contract model.

Labels in our results: 2015–2025 station payouts are **synthetic** (rule applied to GHCN-D TMAX). Prices are **modelled** (probability × (1 + markup)), never observed for those years. The only observed prices we have are the dated snapshots above.
