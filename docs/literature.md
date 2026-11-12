# Literature (Ehfaz, Milestone I)

Compiled 2026-10-30 UTC. Each entry was checked against a bibliographic or publisher page via web search. Summaries are in our own words. Entries we could not verify were dropped.

## A. Geographic basis risk in weather hedging

1. **Woodard, J. D., & Garcia, P. (2008).** "Basis risk and weather hedging effectiveness." *Agricultural Finance Review*, 68(1), 99–117. DOI 10.1108/00214660880001221.
   URL: https://ideas.repec.org/a/eme/afrpps/v68y2008i1p99-117.html (seminar version: https://ageconsearch.umn.edu/record/9254/files/sp07wo01.pdf)
   *Why it matters:* The closest analogue to our question. Using Illinois corn, they show temperature hedges work much better for a large aggregated exposure than for single districts, and that precipitation gains nothing from aggregation. Implies a single small business (our "local point") sits at the worst end of basis risk. They also warn that risk premia on thin local contracts can erase hedge value, which is our cost question.

2. **Vedenov, D. V., & Barnett, B. J. (2004).** "Efficiency of weather derivatives as primary crop insurance instruments." *Journal of Agricultural and Resource Economics*, 29(3).
   URL: https://ideas.repec.org/a/ags/jlaare/30916.html
   *Why it matters:* Designs weather contracts per district and tests them in and out of sample. A model for our chronological train/test split, and an early result that weather-index hedges vary a lot by location.

## B. Index (parametric) insurance and basis risk

3. **Jensen, N. D., Barrett, C. B., & Mude, A. G. (2016).** "Index insurance quality and basis risk: Evidence from northern Kenya." *American Journal of Agricultural Economics*, 98(5), 1450–1469.
   URL: https://ideas.repec.org/a/oup/ajagec/v98y2016i5p1450-1469..html
   *Why it matters:* Decomposes the risk an index policy leaves behind. The index removes much of the covariate (area-wide) risk, but policyholders keep most idiosyncratic risk. Same split as our station leg (covariate) vs. local residual (idiosyncratic).

4. **Clarke, D. J. (2016).** "A theory of rational demand for index insurance." *American Economic Journal: Microeconomics*, 8(1), 283–306.
   URL: https://ideas.repec.org/a/aea/aejmic/v8y2016i1p283-306.html
   *Why it matters:* Shows that with basis risk, demand for index cover can fall as risk aversion rises, and can vanish for very risk-averse buyers. Supports evaluating Strategy A with risk-averse objectives, not only expected cost. It also motivates the residual layer: removing basis risk changes who would buy.

## C. Weather derivative pricing and temperature modelling

5. **Jewson, S., & Brix, A. (with Ziehmann, C.) (2005).** *Weather Derivative Valuation: The Meteorological, Statistical, Financial and Mathematical Foundations.* Cambridge University Press. DOI 10.1017/CBO9780511493348.
   URL: https://www.cambridge.org/core/books/weather-derivative-valuation/AE08A07961FD7548ED796D33D9E250DE
   *Why it matters:* Standard reference for pricing temperature contracts (burn analysis, index modelling, use of forecasts). Our "expected payout × (1 + loading)" premium is the simplest form of the actuarial pricing it describes.

6. **Campbell, S. D., & Diebold, F. X. (2005).** "Weather forecasting for weather derivatives." *Journal of the American Statistical Association*, 100, 6–16.
   URL: https://ideas.repec.org/a/bes/jnlasa/v100y2005p6-16.html (NBER WP: https://www.nber.org/papers/w10141)
   *Why it matters:* Time-series model of daily US city temperatures with seasonal mean and seasonal volatility. A possible upgrade from a flat climatological probability for pricing the station leg.

## D. Prediction-market pricing (cost of the Kalshi leg)

7. **Snowberg, E., & Wolfers, J. (2010).** "Explaining the favorite-long shot bias: Is it risk-love or misperceptions?" *Journal of Political Economy*, 118(4), 723–746.
   URL: https://www.nber.org/papers/w15923
   *Why it matters:* Documents that low-probability outcomes are overpriced in betting markets and argues misperception of small probabilities explains it. A heat-day contract is often a low-probability leg, so its market price likely exceeds fair value.

8. **Bürgi, C., Deng, W., & Whelan, K. (2025).** "Makers and Takers: The Economics of the Kalshi Prediction Market." UCD Centre for Economic Research Working Paper WP25/19 (also CESifo WP 12122).
   URL: https://www.ucd.ie/economics/t4media/WP2025_19.pdf
   *Why it matters:* Direct evidence on Kalshi. Finds a favourite-longshot bias across categories, including Climate & Weather. Buyers of contracts under 10 cents lost over 60% on average; takers did worse than makers; fees hit cheap contracts hardest. This is our main basis for markup scenarios (see docs/contract_spec.md section 5). Working paper, not yet peer reviewed.

## Gaps
- No peer-reviewed study found yet on basis risk for *daily* station-settled retail contracts (Kalshi-style) vs. a nearby business. That is the gap our project fills.
- No verified source yet on what a local residual (OTC/parametric) layer would cost for a small business. Loading stays an assumption swept 0–100% (SPEC).
