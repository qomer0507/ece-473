# Ehfaz — Milestone I notes: literature, exchange contracts, pricing

Written 2026-10-30 (UTC). Status: docs, code and tests written; not yet reviewed by the team.

## What was done
- `docs/literature.md`: 8 verified references (basis risk, index insurance, weather-derivative pricing, prediction-market pricing).
- `docs/contract_spec.md`: Kalshi NYC and Trenton daily-high contracts, fees, trading hours, CME weather futures, markup scenarios, and the contract we model. Every row is marked VERIFIED (with URL) or UNVERIFIED.
- `src/station_hedge.py`: `station_payout`, `kalshi_fee`, `station_premium`, `contracts_for_notional`. Viktor's `src/local_residual.py` already imports `station_payout` from here, so his runner should now use this module instead of the fallback.
- `tests/test_contracts.py`: 19 tests (equality trigger, NaN handling, Series index, fee table values, round-up, float-noise guard, maker rate, premium cap). `python -m pytest tests/test_contracts.py -q` → 19 passed. Full suite → 44 passed (2026-10-30 ~03:10Z).

## Key findings
1. **NYC settlement source changed on 2026-08-14, not 2026-08-17.** KXHIGHNY rules named the NWS Climatological Report (Daily), Central Park, through the 2026-08-13 event. From the 2026-08-14 event on they name The Weather Company and "New York City (CLINYC)". CLINYC is the NWS Central Park climate report ID, so the station is still Central Park. Only the publisher of record changed. Kalshi help pages (dated 2026-07-22) still say NWS. Sources in contract_spec.md §1a.
2. **A Trenton contract exists.** KXHIGHTTTN ("Trenton, NJ Daily Max Temp"), settling on The Weather Company for "Trenton (CLITTN)" (NWS Mount Holly's Trenton climate report, KTTN). First event 2026-08-26. Very thin: 45 contracts traded on that first day. It has never run through a summer heat season.
3. **Fee formula verified.** Taker fee = round_up(0.07 × C × P × (1 − P)); maker rate 0.0175. Multiplier 1 for both series. The rounding unit is ambiguous (text says centicent, table shows cents); code defaults to cents and exposes a parameter.
4. **Realistic markup.** One NYC ladder snapshot summed to $1.06 at the asks (6% overround); Trenton $1.08. Bürgi, Deng & Whelan (2025) find Kalshi contracts under 10¢ lose over 60% on average, including in Climate & Weather. Proposed scenarios: 5% / 15% (base) / 50% markup over modelled fair value, plus fees. All labelled ASSUMED.
5. **Tenor mismatch.** Kalshi lists each day about 1.5 days ahead. A business cannot lock in a May–Sep season of heat-day cover at a known price. CME has seasonal CDD strips but only at airports (LaGuardia, Philadelphia), not Central Park or Trenton.

## Implications for the shared spec
- Backtest years 2015–2025 all predate both the TWC switch and the Trenton series. Station payouts for those years must be called **synthetic** (rule on GHCN-D TMAX), not exchange settlements.
- Threshold 90°F is not always a bracket edge on Kalshi (bracket parity shifts daily). Replicating ">= 90" can need a ladder and sometimes has a 1°F strike mismatch. We ignore this in the base model and note it as a limitation.
- No SPEC change proposed.

## Open questions
- Does TWC's published max always equal the NWS CLI max for Central Park and Trenton? (UNVERIFIED.) Rules mention possible rounding/conversion differences.
- Does GHCN-D TMAX for USW00094728 / USW00014792 match the CLI value day by day? Suggest Qasim spot-checks 5–10 days.
- Fee rounding: cents or centicents, per order or per fill? Does the series charge maker fees?
- Summer pricing: our only price snapshots are from late October. Heat-day contracts in July may price differently.
- Why did Kalshi switch to TWC? We found no announcement.

## Proposed Milestone II tasks (Ehfaz)
1. Pull settled KXHIGHNY and KXHIGHTTTN market histories (public API, read-only) for Aug–Oct 2026; record expiration values and compare with GHCN-D/CLI for the same days.
2. Measure observed ladder overround and spreads for the 2026 summer (May–Sep) where history is available; replace the 5/15/50% guesses with an observed range.
3. Add a ladder-replication function (choose markets for threshold k given a day's brackets; compute cost and strike mismatch).
4. Write the literature/pricing section of the report and a limitations paragraph.
5. Optional: price the station leg with a seasonal temperature model (Campbell & Diebold style) instead of flat frequency.

## Sources
- Kalshi API (public): https://api.elections.kalshi.com/trade-api/v2/series/KXHIGHNY ; .../series/KXHIGHTTTN ; .../markets?event_ticker=KXHIGHNY-26AUG13 ; .../historical/markets?event_ticker=KXHIGHNY-26AUG14 ; .../markets?event_ticker=KXHIGHNY-26AUG17 ; .../events?series_ticker=KXHIGHTTTN&limit=200 ; .../markets?event_ticker=KXHIGHNY-26OCT30
- Kalshi contract terms: https://assets.kalshi.com/contract_terms/GLOBALTEMPERATURE.pdf
- Kalshi fee schedule: https://kalshi.com/docs/kalshi-fee-schedule.pdf
- Kalshi help, weather markets: https://help.kalshi.com/markets/popular-markets/weather-markets
- Kalshi help, trading hours: https://help.kalshi.com/trading/what-are-trading-hours
- Kalshi 2023 CFTC filing (NHIGH): https://www.cftc.gov/filings/orgrules/rules042623979.pdf
- NWS CLI products via IEM: https://mesonet.agron.iastate.edu/wx/afos/p.php?pil=CLINYC ; https://mesonet.agron.iastate.edu/wx/afos/p.php?pil=CLITTN
- CME Rule 403: https://www.cmegroup.com/content/dam/cmegroup/rulebook/CME/IV/400/403/403.pdf
- CME weather overview: https://www.cmegroup.com/education/lessons/overview-of-weather-markets.html ; https://www.cmegroup.com/articles/2023/cme-group-weather-suite-expanded.html
- Bürgi, Deng & Whelan (2025): https://www.ucd.ie/economics/t4media/WP2025_19.pdf
- Other literature: see docs/literature.md
