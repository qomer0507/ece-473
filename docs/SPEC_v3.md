# Shared spec v3: rain hedging for parks (frozen 2026-11-12 UTC)

Supersedes SPEC_v2 for the rain project. The heat study (SPEC_v2) is finished and kept as a comparison section.
Phase 0 evidence: docs/status/phase0_verdict.md and the three phase0_*.md files. Change this file only with a dated line under "Changes".

## Buyer and loss
- Lead: Sesame Place (Langhorne, PA), settlement station Trenton-Mercer (ASOS TTN, NWS climate report CLITTN), 11.3 km.
- Long-history check: Philadelphia Intl (PHL, CLIPHL), 85 usable seasons.
- "Should be listed" case: Dorney Park with Allentown (ABE), 10.7 km, 70 seasons, climate report, no Kalshi rain market.
- Season: every day from the Friday before Memorial Day through Labor Day (about 102 days). Sensitivity: weekends plus Memorial Day, July 4, Labor Day.
- Loss day: >= 0.25 inch of rain between 10:00 and 18:00 local clock time (America/New_York) at the station. Sensitivity: 0.10 and 0.50 inch; 10:00-16:00 and 10:00-20:00.
- Loss per loss day: a scenario parameter L (dollars). Results are reported per $1 of L and over a stated range. Never presented as a park's actual loss.
- Usable seasons: Trenton 1998-2026 (29). A season counts only if >= 90% of opening-hour hours are present. Unusable days are dropped and counted, never imputed.

## Baseline (what exists today)
- Kalshi daily rain contract at the same station: pays $1 if the climate-day total is >= 0.01 inch. Trace and missing = No (the rule since 2026-07-15).
- Strategy: buy N contracts on every season day, N chosen on the training seasons.
- Price: MODELLED for all seasons (real Trenton prices cover 35 summer days). Model = probability of rain that day as a market would see it + spread + Kalshi taker fee, calibrated on real prices: NYC 2025 and 2026, and the four-city overlap Jul-Sep 2026. Always labelled "modelled". Where real prices exist, also report results on real prices.
- Second baseline: no hedge.

## Solution
- Seasonal contract on the count of loss days at the station, six buckets, edges chosen on training seasons.
- A buyer holds a vector of bucket quantities. Stepped payout = more units of higher buckets.
- Price: expected payout on training seasons plus loading (10%, 20%, 30%), labelled modelled. The LMSR experiment reports what a sponsor-funded market charges.

## Evaluation
- Train: seasons 1998-2014. Report: 2015-2026. Nothing chosen on report seasons.
- Net cost per season = L * loss days - payout + premium.
- Primary metric: hedge effectiveness = 1 - (downside semi-variance of hedged net cost / that of unhedged), 95% interval from bootstrap over whole seasons (1,000 draws, seed 473).
- Also: mean of the worst 10% of seasons (labelled noisy), premium per $1 of useful payout, share of loss days paid, share of payouts on non-loss days.
- Philadelphia 1941-2026 repeats the same analysis as the long-history check.

## Market (LMSR)
- Adapt contracts/BracketLMSR.sol: six integer-count buckets, uniform start (sponsor bound b*ln 6), buy an arbitrary vector of quantities in one transaction.
- Fix M1 (validate oracle address and return data), M3 (no report before season end). Disclose M2 (single reporter); sponsor and oracle are separate accounts.
- Oracle reports the season's count once, after the season ends. Late, missing, stale, cancel-and-refund, withdrawal paths tested with a mock oracle.

## Integrity rules
- Never invent data. Label modelled vs observed everywhere. Aggregates only for Kalshi data; raw rows stay in data/raw (git-ignored).
- No real-money trades, no private keys anywhere, testnet only.
- Each workstream logs to docs/status/phase1_<name>.md with dated UTC lines.

## Files
- Rain workstream: src/rain/**, scripts/rain_*.py, tests/test_rain_*.py, data/processed/rain/**, results/rain/**, docs/status/phase1_rain.md
- Kalshi workstream: src/kalshi/** (existing client may be extended), scripts/kalshi_rain_*.py, tests/test_kalshi_rain_*.py, data/processed/kalshi_rain/**, results/kalshi_rain/**, docs/status/phase1_kalshi.md
- Market workstream: contracts/**, sim/**, tests/test_lmsr_*.py, results/market/**, docs/deploy_sepolia.md, docs/status/phase1_market.md
- Do not edit another workstream's files. Do not run git commands; the lead commits.

## Changes
- 2026-11-12: created from Phase 0 results.
- 2026-11-12: Trenton has 28 usable seasons (1999-2026); 1998 falls just under the 90% rule. Train = 1999-2014.
- 2026-11-12: The Kalshi-pay flag uses the official daily total (GHCN daily, which matches the NWS climate report Kalshi settles on), not the sum of hourly readings. The hourly sum overcounts at Trenton in 2002-2013 (0.01 inch dew readings). Both versions stay in the tables.
