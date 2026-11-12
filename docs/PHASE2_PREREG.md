# Phase 2 pre-registration (written 2026-11-12 UTC, before any hedge evaluation was run)

Binding for Phase 2. Extends docs/SPEC_v3.md. Nothing here may be changed after results are seen; additions go under "Deviations" with a date and a reason.

## Question
Does a seasonal rain-count contract cut a park's bad-season cost more than Kalshi's daily rain contract, when the park is NOT at the settlement station and its true rain sensitivity is NOT exactly the contract's trigger?

## Notation (per season y, all in units of L = loss per loss day; L = 1)
- D_park(y): loss days at the park location (definition varies by case, below).
- C_S(y): count of days at settlement station S with >= 0.25 inch in 10:00-18:00 (the contract's index).
- K_S(y): Kalshi-pay days at S (official daily total >= 0.01 inch; GHCN daily, the `ref_ghcn` version).
- Net cost(y) = D_park(y) - payout(y) + premium(y). Unhedged net cost = D_park(y).
- Only usable season days count, and D_park, C_S, K_S use the same set of days (days usable at both locations).

## Windows
- Trenton cases: TRAIN 1999-2014, REPORT 2015-2026.
- Philadelphia cases: TRAIN 1941-1990, REPORT 1991-2026 (seasons failing the usable rule are dropped; 1941-47 flagged as doubtful and also reported excluded).
- Everything below marked "chosen on TRAIN" uses TRAIN seasons only.

## Strategies
0. No hedge.
1. Kalshi daily, naive: buy 1 contract (pays 1 = L) on every season day at S.
2. Kalshi daily, sized: buy n contracts every day, n chosen on TRAIN from {0.05, 0.1, ..., 1.0} to maximise TRAIN hedge effectiveness.
   Price for 1 and 2: MODELLED, src/kalshi/rain_price_model.py, recommended "skill" model with fitted parameters, fees included, unfilled-order rule as fitted. p (monthly rain frequency) from TRAIN seasons. Sensitivity: markup a = 0.068.
3. Seasonal count contract, bucketed (the product we build): six buckets with integer upper edges e1..e5 chosen on TRAIN as the 1/6, 2/6, ..., 5/6 quantiles of C_S (ties merged upward; if fewer than six distinct buckets result, use the nearest valid edges and record it). Holding h_j = max(m_j - d, 0) units of bucket j, where m_j is the TRAIN mean of C_S within bucket j (bucket midpoint if empty; top bucket uses TRAIN mean or e5 + 2 if empty) and the deductible d is chosen on TRAIN from {0, 1, ..., 8} to maximise TRAIN hedge effectiveness. Payout(y) = h_j for the bucket containing C_S(y).
   Premium = (1 + loading) * expected payout, expected payout = sum_j h_j * q_j, q_j = (n_j + 0.5) / (N + 3) from TRAIN bucket counts (add-half smoothing). Loading 0.20 main; 0.10 and 0.30 sensitivity. MODELLED.
4. Seasonal count contract, exact (benchmark, not built): payout = max(C_S(y) - d, 0), same d rule, premium = (1 + loading) * TRAIN mean payout. Shows what bucketing costs.
5. Fair-comparison variant of 1 and 2: Kalshi daily contract priced at (1 + loading) * expected payout with the same loading as strategy 3 (no forecast information, no spread). This isolates contract SHAPE from market TIMING and markup.

## Metrics (REPORT seasons; also shown on TRAIN, labelled in-sample)
- Primary: hedge effectiveness HE = 1 - SV(hedged net cost) / SV(unhedged), SV = mean of max(x - TRAIN mean of unhedged net cost, 0)^2. (The reference level is fixed from TRAIN so that paying a premium every year is not rewarded or punished by a moving mean.)
- Secondary: mean net cost; mean of the worst 3 REPORT seasons (Trenton) or worst 10% (Philadelphia) by unhedged cost, comparing hedged vs unhedged cost in those same seasons; standard deviation of net cost; premium per $1 of useful payout, where useful payout = min(payout, D_park) summed over seasons; total premium; share of seasons where the hedge reduced net cost.
- Uncertainty: bootstrap whole REPORT seasons, 2,000 draws, seed 473, 95% percentile interval for each metric and for the DIFFERENCE HE(strategy 3) - HE(strategy 2).

## Cases
A. Same-station (upper bound, circular by construction; reported only as a ceiling): D_park = C_S at Trenton.
B. Location basis (HEADLINE for Trenton): settlement S = Trenton (TTN); park loss measured at a stand-in gauge. B1: Philadelphia NE (PNE). B2: Doylestown (DYL), if it has enough usable seasons. Report the distance from each stand-in to Sesame Place and to Trenton. State plainly that the stand-in is not the park.
C. Sensitivity misspecification, at Trenton and combined with B1: the park's true loss day is (c1) >= 0.10 inch, (c2) >= 0.50 inch, (c3) 10:00-20:00 window, (c4) 10:00-16:00 window, (c5) weekends and holidays only; the contract stays at 0.25 inch, 10:00-18:00, all days.
D. Long history: S = Philadelphia (PHL), same-station (85 seasons) and with PNE as stand-in (seasons available at both).
E. Allentown (ABE) same-station, as the "should be listed" case: strategies 0, 3, 4 only (no Kalshi market exists there).

## What counts as a result
- "The seasonal contract beats Kalshi's" is claimed only if the bootstrap interval for HE(3) - HE(2) excludes zero in case B1 on REPORT seasons, and the sign agrees in case D with a stand-in.
- If HE(3) is not above zero in case B, say so: the product does not hedge a park 11-30 km away, and location basis is the finding.
- Strategy 5 decides how much of any gap is contract shape and how much is timing and markup.
- Every figure and table says which numbers are observed (weather) and which are modelled (prices).

## Deviations
(none yet)
