ECE 473 Milestone I: Localized Weather Hedging Using Event Contracts
Team: Qasim Omer, Ehfaz Zoha, Viktor Hrushka

1. PLANNED VS. ACTUAL PROGRESS

Ehfaz Zoha
Planned: literature review, Kalshi contract data, trading costs.
Actual:
- Wrote a literature summary of 8 verified references. They cover basis risk, index insurance, weather-derivative pricing and prediction-market pricing.
- Documented Kalshi's daily high-temperature contract rules.
- Finding: Kalshi's NYC market changed its named settlement source from the NWS Climatological Report to The Weather Company. The first event under the new source was 2026-08-14. The station did not change: it is still the Central Park report.
- Finding: a Trenton series, KXHIGHTTTN, exists but has only listed since 2026-08-26, and its volume is very thin. Kalshi lists each day only about 1.5 days ahead.
- Verified Kalshi's taker fee formula: 0.07 × contracts × P × (1 − P), rounded up.
- Wrote the station-contract payout and fee module, with 19 tests.

Qasim Omer
Planned: NOAA/PRISM data, basis-risk analysis, backtests.
Actual:
- Built a daily maximum-temperature dataset from NOAA GHCN-Daily, May–Sep 2015–2025. It covers two reference stations (Central Park and Trenton-Mercer) and seven nearby "local" stations 7–41 km away.
- Spot-checked 44 station-days against NOAA's own service. All 44 matched.
- Preliminary result at a 90°F heat-day trigger: daily correlations are 0.93–0.99, yet the triggers disagree on 6–11% of season days.
- Inland stations run hotter: a Central Park contract misses 34–49% of heat days at LaGuardia, Teterboro, Newark and Philadelphia NE.
- JFK runs cooler: on 57% of Central Park heat days, JFK is not hot. That is an overhedge.
- Distance does not predict mismatch. Siting matters more: coast versus urban heat.
- Wrote the loader and basis-risk module, with 11 tests.

Viktor Hrushka
Planned: residual-market simulation, pooling, charts.
Actual:
- Built the two-part hedge simulator: local target payout, residual = max(target − station payout, 0), and explicit overhedge tracking.
- Built a comparison runner with a 2015–21 train / 2022–25 test split and a premium "loading" sweep under risk-neutral, mean-variance and CVaR objectives. It has 14 tests.
- The first end-to-end run on the real data works.
- Design point: the two-part hedge removes shortfall by construction. So the real question is how much markup on the local layer is still worth paying.

2. REMAINING WORK FOR MILESTONE II (11/12)
- Ehfaz: get realistic heat-day pricing (current snapshots are from October). Check whether The Weather Company values match the NWS reports. Finalize the cost model and fee rounding.
- Qasim: spot-check GHCN values against the NWS daily climate reports. Pick one "business" point per city. Add a non-airport local point (Princeton-area COOP station or PRISM cell). Add bootstrap confidence intervals to the mismatch rates.
- Viktor: decide between fixed and fitted station contract size. Set the headline risk-aversion settings. Add bootstrap intervals for the break-even markup. Produce the final figures.
- All: pre-register the final A-vs-B comparison, run it, and draft the report and presentation.

3. REFINEMENTS
- Scope is unchanged: NYC and Trenton, temperature only (daily max, heat day ≥ 90°F, May–Sep), station-only versus two-part hedge, Python simulator, no portal. We are dropping pooling, which was optional, to focus on the core comparison.
- "Local" sites are nearby real weather stations, not PRISM grid cells. Gridded data partly reflects the reference station and would understate basis risk.
- We will label backtests as reference-station simulations, because 2015–2025 predates both the settlement-source switch and the Trenton listing.
- Challenges: Kalshi offers day-ahead contracts only, with no season-long cover. Pricing assumptions need summer data, which we don't have yet.
