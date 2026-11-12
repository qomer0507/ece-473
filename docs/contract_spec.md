# Contract specification (Ehfaz, Milestone I)

Compiled 2026-10-30 UTC. Each fact is marked **VERIFIED** (with the URL we read) or **UNVERIFIED**.
Kalshi API pages were read with a web-fetch tool between about 2026-10-30T02:30Z and 03:05Z. API responses are live and can change. Market snapshots below are single observations, not a price history.

Base URL for Kalshi API reads below: `https://api.elections.kalshi.com/trade-api/v2` (public, read-only, no account).

---

## 1. Kalshi NYC daily high: series KXHIGHNY

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

### 1a. Settlement source and station: what changed and when

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

## 2. Trenton: series KXHIGHTTTN exists

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

## 3. Kalshi fees

| Fact | Status | Source |
|---|---|---|
| Taker fee = round_up(M × 0.07 × C × P × (1 − P)). P = price in dollars, C = contracts, M = multiplier (default 1). | VERIFIED | https://kalshi.com/docs/kalshi-fee-schedule.pdf (effective 2026-07-07) |
| Maker fee = round_up(M × 0.0175 × C × P × (1 − P)); maker M defaults to 0 unless a series sets it. | VERIFIED | same |
| Rounding text says the fee is rounded up "to a centicent", but the schedule's table shows whole cents (1 contract at $0.50 shows $0.02; 100 at $0.50 shows $1.75). Unit is ambiguous. | VERIFIED (ambiguity) | same |
| Whether rounding is per order or per fill. | UNVERIFIED | — |
| Whether KXHIGHNY/KXHIGHTTTN charge maker fees (series multiplier 1 is reported, but not split by maker/taker). | UNVERIFIED | `/series/KXHIGHNY` |

Worked examples (our arithmetic, taker, $0.01 rounding): 800 contracts at $0.10 cost $80 plus a $5.04 fee (6.3%). 800 at $0.50 cost $400 plus $14.00 (3.5%). The fee is largest in dollars at P = 0.5 but largest as a share of premium for cheap contracts.

## 4. CME weather futures (institutional benchmark)

| Fact | Status | Source |
|---|---|---|
| CME Rule Chapter 403: Degree Days Index futures (HDD and CDD), 13 US stations. | VERIFIED | https://www.cmegroup.com/content/dam/cmegroup/rulebook/CME/IV/400/403/403.pdf |
| **New York La Guardia Airport (WBAN 14732)** is listed. Philadelphia International (WBAN 13739) is the nearest listed station to Trenton. Central Park and Trenton are not listed. | VERIFIED | same |
| Contract size $20 × index; index values reported by Speedwell Settlement Services from NWS observations. | VERIFIED | same |
| HDD/CDD use a 65°F base. US contracts: HDD for winter months, CDD for summer months; seasonal strips of 2, 3 or 5 months (e.g. CDD May–Sep). European cities and Tokyo also use CAT. | VERIFIED | https://www.cmegroup.com/education/lessons/overview-of-weather-markets.html ; https://www.cmegroup.com/articles/2023/cme-group-weather-suite-expanded.html (2023-06-27) |
| Exact listed months per city today. | UNVERIFIED (rulebook says "determined by the Exchange") | 403.pdf |

Why it matters: CME products are monthly or seasonal degree-day sums at airports, not daily heat-day binaries. They do allow seasonal tenor, which Kalshi does not. Their mismatch with a shop in Manhattan or Trenton is bigger (wrong station and wrong index). We use them only as context.

## 5. Cost and markup assumptions (for `station_premium`)

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

## 6. Contract we will model

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
