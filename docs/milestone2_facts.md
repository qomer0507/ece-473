# Milestone II fact sheet (for the team to write from; due 2026-11-12)

Course rule: "You write it. AI may only edit it." Write the update in your own words: goal, what you learned, where you stand, progress against the plan. Use numbers only where they support a point. This sheet is the verified material; it is not the submission.

## Goal (one sentence to write in your words)
Can an amusement park hedge its rainy-season losses on a prediction market? Hypothesis: a seasonal rain-day-count contract reduces a park's bad-season losses where Kalshi's existing daily rain contract does not.

## The pivot (keep to two or three sentences)
- Initial goal (one-pager): localized temperature hedging, NYC and Trenton, station-only vs a two-part hedge with a local layer.
- What it found: a Central Park contract missed 34-49% of 90F days at nearby stations; but the "local layer" was a product nobody sells, priced by assumption, and it beat the baseline by construction. Milestone I feedback said the goal and product were unclear.
- Why the change: pick a real buyer (parks), a real risk (rain), and a real baseline (Kalshi's daily rain contract, listed for Trenton, Philadelphia, Newark, NYC).

## What was learned so far (observed weather; prices modelled where stated)
- Kalshi's daily rain contract pays on about 34 days a season at Trenton; a park loses on about 5 (0.25 inch during 10-18h). 84% of pay days are not loss days. Same at Philadelphia over 85 seasons and Allentown over 70.
- Kalshi's prices are accurate (average price 42 cents, rain on 42% of days) but the market opens 1.5 days ahead, so the forecast is already in the price: about 75 cents on rain days, 23 cents on dry days. Buyers paid $1.06-1.31 per $1 received in every city and year with real prices (observed, 517 markets).
- Pre-registered test, held-out seasons, two independent implementations agreeing on 120 numbers:
  - Kalshi daily contract: hedge effectiveness below zero in every case (it makes bad seasons worse after premiums).
  - Seasonal count contract: removes about two-thirds of bad-season cost when the park's rain matches the station's (Philadelphia, 35 held-out seasons, HE 0.65, interval 0.29-0.78). Also works 29 km from Philadelphia (0.65, 30 seasons).
  - Failed 28 km from Trenton on 12 seasons (HE -0.37). So the reach of the hedge is the open question.
- Built: the seasonal contract as an on-chain LMSR market (six count buckets, basket purchase, oracle, refunds), 162 contract tests, run end to end on the real 2025 Trenton season locally. Not yet deployed to Sepolia.

## Where we stand against the plan (Oct 29 plan vs now)
- Planned by Nov 12: data, pricing, contract spec. Done, and beyond: the full comparison is done.
- Not done: Sepolia deployment (guide written; deploy pending), slides.
- Running now: how far a hedge reaches (every station pair in the region, rain and temperature) and when a contract must be listed to work (forecast skill by lead time, 2003-2026).

## Next steps (to Nov 16 slides, Nov 17+ presentation, Dec 15 report)
- Finish the reach and lead-time analyses; deploy to Sepolia and record the demo; slides by Nov 16; report draft by early December.

## Per-person (write honestly; each person must be able to explain their part)
- Qasim: weather data and the hedge comparison. Ehfaz: Kalshi markets, prices and the baseline price model. Viktor: the on-chain market and tests.
- The build used AI assistance heavily (allowed). Say so in one line if the form asks about challenges or process.

## Challenges to mention
- Real Kalshi prices exist for under one summer at Trenton, so the 28-season comparison uses a modelled price calibrated on real ones.
- The stand-in gauge is not the park; the park's own basis risk is unmeasured.
