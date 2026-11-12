# B. Prior-work check and originality rating

Date of search: 2026-11-11. Web search only. Every entry below was checked against a publisher, repository, RePEc, Crossref or arXiv page. Summaries are in my own words. Items I could not verify were dropped.

Access limits to know about:
- SSRN pages would not load. The Luo (2026) entry rests on the Crossref abstract record only. The Iturbide (2026) entry rests on the author's replication repository README only. The team must read both full papers.
- Several journal articles are paywalled. Those entries rest on abstracts or open working-paper versions.

## Headline

1. The idea is not untouched. One 2026 SSRN working paper (Luo) already studies Kalshi weather contracts as hedges, measures geographic basis risk across station pairs, tests multi-station portfolios out of sample, and says the basis-risk map is the main object. That is very close to Part 1.
2. Part 3 (which city should the exchange list next, tested against the Newark and Trenton listings) has no precedent that I could find after several search phrasings.
3. Two prior results are a direct threat to the "best combination of listed contracts" claim. Luo finds multi-station portfolios beat the best single station out of sample in only 43% of cases. Leppert et al. find interpolation beats nearest-station by only 2 to 3% for heat indices.

## a) Spatial basis risk, multi-station hedges, index design

**Woodard, J. D. and Garcia, P. (2008).** Basis risk and weather hedging effectiveness. Agricultural Finance Review 68(1), 99-117.
https://ideas.repec.org/a/eme/afrpps/v68y2008i1p99-117.html (open version: https://ideas.repec.org/p/ags/eaa101/9254.html)
- Studies weather hedges for U.S. corn at several levels of spatial aggregation. Finds geographic basis risk can be large but should not rule out hedging with a contract on another location. It matters less as the hedger's exposure is more aggregated.
- Overlap: the classic "hedge with a non-local city contract" paper. Supports the baseline of buying a nearby city contract. No binary contracts, no listing question.

**Norton, M. T., Turvey, C. and Osgood, D. (2013).** Quantifying spatial basis risk for weather index insurance. Journal of Risk Finance 14(1), 20-34. (AAEA 2010 working paper version exists; the journal year is 2013, not 2012.)
https://ideas.repec.org/a/eme/jrfpps/15265941311288086.html
- Compares payouts at pairs of nearby stations and relates the gap to distance, altitude, latitude and longitude. Distance matters for rain. Altitude matters for heat. Geography is a weak predictor overall. The best predictor is the payout at a nearby station. Suggests insuring a portfolio of stations.
- Overlap: same pairwise-mismatch design as the team's Central Park versus Newark numbers. Supports "distance does not predict mismatch" for heat.

**Ritter, M., Musshoff, O. and Odening, M. (2014).** Minimizing geographical basis risk of weather derivatives using a multi-site rainfall model. Computational Economics 44(1), 67-86.
https://link.springer.com/doi/10.1007/s10614-013-9410-y (open version: https://ageconsearch.umn.edu/record/122527/files/Ritter.pdf)
- Builds optimal weights on several station contracts for a rainfall put at two German sites. Fit on 1973-2000, tested on 2001-2010. Basis-risk error falls about 42% at one site (four stations) and 23% at the other (two stations). Gains stop after two to five stations. Only slightly better than inverse-distance weights. Ignores transaction costs.
- Overlap: this is Part 1's method (optimal portfolio of station contracts, out of sample). Differences: rainfall, two sites, hypothetical contracts, no prices.

**D'Aversa, M., Mainini, A., Moretto, E., Stefani, S. and Uberti, P. (2023, issue 2025).** Minimizing the impact of geographical basis risk on weather derivatives. Annals of Operations Research 347, 535-551.
https://link.springer.com/article/10.1007/s10479-023-05483-3
- Keeps one traded reference contract (Rome) and finds, for each of 197 Italian stations, the strike that makes the reference payoff match the local payoff. Altitude and latitude explain the optimal strike well. Distance does not. Tested out of sample over 20 years.
- Overlap: this is the "location-adjusted strike" idea in Part 1, done at similar scale. Differences: degree-day payoffs, one reference city, no portfolio of cities, no market prices, Italy.

**Musshoff, O., Odening, M. and Xu, W. (2011; online 2009).** Management of climate risks in agriculture: will weather derivatives permeate? Applied Economics 43(9), 1067-1077.
https://ideas.repec.org/a/taf/applec/v43y2009i9p1067-1077.html
- Simulates rainfall options for wheat in north-east Germany. Separates and sizes local basis risk and geographical basis risk. Shows hedge value depends on index, strike and tick size.
- Overlap: gives the standard split of basis risk that the team should adopt.

**Dalhaus, T. and Finger, R. (2016).** Can gridded precipitation data and phenological observations reduce basis risk of weather index-based insurance? Weather, Climate, and Society 8(4), 409-419.
https://doi.org/10.1175/wcas-d-16-0020.1
- German wheat. Gridded rainfall does about as well as station data. Better timing of the index window helps more than better spatial data.
- Overlap: indirect. Warns that spatial refinement is not always the biggest gain.

**Leppert, D., Dalhaus, T. and Lagerkvist, C.-J. (2021).** Accounting for geographic basis risk in heat index insurance: how spatial interpolation can reduce the cost of risk. Weather, Climate, and Society 13(2), 273-286.
https://journals.ametsoc.org/view/journals/wcas/13/2/WCAS-D-20-0070.1.xml
- Extreme-heat indices for corn in Illinois and Iowa. Compares nearest station with inverse-distance and kriging. Interpolated indices beat nearest station by only about 2 to 3% in risk reduction. The edge grows when stations are sparse.
- Overlap: closest heat-specific study. Same baseline (nearest station) and same question (does combining stations help).

**Guo, Y. and Li, J. S.-H. (2023).** Kriging methods for modelling spatial basis risk in weather index insurances: a technical note. arXiv:2311.14844 (DOI points to a World Scientific journal).
https://arxiv.org/abs/2311.14844
- Tests interpolation from nearest neighbour to kriging on NOAA rainfall. Finds interpolating raw daily data does not reliably beat interpolating the index itself.

**Gyamerah, S. A., Ngare, P. and Ikpe, D. (2019).** Mitigating geographical basis risk of weather derivatives using spatial-temporal regime-switching temperature model. AIMS Mathematics 4(4), 1274-1290.
https://www.aimspress.com/article/id/4149
- Multi-location temperature model. The hedger picks a weighted basket of stations to cut basis risk. Model paper, no market data.

**Yang, C. C., Brockett, P. L. and Wen, M.-M. (2009).** Basis risk and hedging efficiency of weather derivatives. Journal of Risk Finance 10(5), 517-536.
https://ideas.repec.org/a/eme/jrfpps/15265940911001411.html
- U.S. power producers hedging load with exchange city indexes versus regional indexes. Basis risk is low in the Northeast and Mid-Atlantic and high elsewhere. Neither index type wins everywhere. Discusses which standard contracts should survive.
- Overlap: the nearest older work to "are the listed cities the right ones", for the team's own region.

**Golden, L. L., Wang, M. and Yang, C. (2007).** Handling weather related risks through the financial markets: considerations of credit risk, basis risk, and hedging. Journal of Risk and Insurance 74(2), 319-346.
https://ideas.repec.org/a/bla/jrinsu/v74y2007i2p319-346.html
- Trade-off between exchange contracts (basis risk) and local over-the-counter contracts (credit risk), with a combined "basis hedge". Verified at title and venue level only.

**Gao, H., Yang, S. and Liu, X. (2024).** Managing basis risks in weather parametric insurance. arXiv:2409.16599.
https://arxiv.org/abs/2409.16599
- Monte Carlo study. Basis risk falls as contracts are pooled and depends on the geometry of insured site, station and event footprint.

Station network design: I found no paper that optimizes where to place index-insurance stations as a formal location problem. The nearest are Norton et al., Leppert et al. and Yang et al. above.

## b) Completeness, Arrow-Debreu view, prediction markets as hedges

**Ross, S. A. (1976).** Options and efficiency. Quarterly Journal of Economics 90(1), 75-89.
https://ideas.repec.org/a/oup/qjecon/v90y1976i1p75-89..html
**Breeden, D. T. and Litzenberger, R. H. (1978).** Prices of state-contingent claims implicit in option prices. Journal of Business 51(4), 621-651.
https://econpapers.repec.org/RePEc:ucp:jnlbus:v:51:y:1978:i:4:p:621-51
- The textbook basis for "a strike ladder spans payoffs on one underlying". They say nothing about spanning across locations. That gap is the team's question.

**Pennock, D. M. and Wellman, M. P. (arXiv 2013).** Compact securities markets for Pareto optimal reallocation of risk. arXiv:1301.3886.
https://arxiv.org/abs/1301.3886
- Shows when far fewer securities than states still give efficient risk sharing. Theory for "how many contracts are enough".

**Wolfers, J. and Zitzewitz, E. (2004).** Prediction markets. Journal of Economic Perspectives 18(2), 107-126. (NBER w10504.)
https://www.nber.org/system/files/working_papers/w10504/w10504.pdf
- Standard survey of contract types and what prices mean.

**Diercks, A. M., Katz, J. D. and Wright, J. H. (2026).** Kalshi and the rise of macro markets. Federal Reserve FEDS 2026-010.
https://www.federalreserve.gov/econres/feds/files/2026010pap.pdf
- Treats each Kalshi strike contract as an Arrow-Debreu security and builds full distributions for macro releases. No weather and no hedging test. Good citation for the Arrow-Debreu framing of bracket ladders.

**Luo, Z. (2026).** Prediction markets as weather hedges: geographic basis risk, settlement constraints, and contract replication. SSRN working paper, DOI 10.2139/ssrn.7138562 (Crossref record created 2026-08-03).
https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7138562 (abstract read via https://api.crossref.org/works/10.2139/ssrn.7138562)
- Kalshi daily weather contracts as risk transfer. About 288,000 price observations on about 16,000 resolved contracts. Simple recalibration does not improve raw prices. Measures residual basis risk between the settlement-station degree-day index and a local proxy over 30 station pairs, two trigger types, 24 years. Basis risk is large, rises with distance, and is lower for heating than cooling triggers. Multi-station portfolios beat the best single station out of sample in only 43% of cases. Ridge shrinkage does not help. Building a degree-day claim from the binary bins costs about 1% of exposure variance. Realized temperature falls outside the bin ladder on 17% of days. Concludes geography dominates and the basis-risk map is the key object.
- Overlap: very high with Part 1 and partly Part 2. This is the paper to beat.

**Iturbide, P. (2026).** Basis risk in prediction markets: can a rain contract hedge New York rooftop bars? SSRN working paper 7552699. Pre-registered 2026-09-16.
https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7552699 (code: https://github.com/pauliturbide21-blip/kalshi-rain-basis-risk)
- Kalshi's daily New York rain contract against evening-only losses at ten venues. About 69% of payouts land on evenings with no loss. Uses real Kalshi market data, checks calibration and liquidity, compares the listed contract with a hypothetical better-designed one.
- Overlap: same template as Parts 1 and 2 (real listed contract, real prices, hypothetical alternative contract). The mismatch is in time of day, not location.

**Kalshi Research (2026-08-31).** Weathering the storm: hedging climate risk.
https://kalshi.com/research/insights/hedging-climate-risk
- Exchange's own report. Calibration of about 70,000 daily weather markets per horizon. Two hedging stories (Los Angeles ice cream shop, New York subway ridership). No station-to-site basis risk, no multi-city hedge, no formal effectiveness measure. Published five days after the Newark and Trenton listing. Not independent.

**Eren, E. (2026).** Do prediction markets work as hedges? Four Pillars research note.
https://research.4pillars.io/en/data/content/do-prediction-markets-work-as-hedges
- 1,265 Kalshi markets, Aug 2025 to Aug 2026. Weather contracts are held to expiry far more than sports contracts. Reads this as some real hedging demand. No basis risk analysis.

**Zhao, G. (2026).** Market information from prediction market and its potential as a financial instrument. Princeton senior thesis (ORFE).
https://theses-dissertations.princeton.edu/entities/publication/499f2d4e-8782-4836-9b65-8e5bc9a0c671
- Polymarket rate contracts as state-contingent assets in a portfolio. No weather. Shows undergraduate work in this space exists.

Trade press that names basis risk as the open problem for prediction-market hedges, without analysis:
- Business Insurance, 2026-10-26: https://www.businessinsurance.com/prediction-markets-gain-role-in-risk-transfer/
- iGaming Business, 2026-08-28: https://igamingbusiness.com/prediction-markets/hedging-risk-via-prediction-market-contracts/
- University of Maryland Smith School, 2026-10-21: https://www.rhsmith.umd.edu/news/could-prediction-markets-be-new-hedge-against-business-risk
- Hobby repository, Chicago ice cream shop Monte Carlo, assumed sales curve, no basis risk: https://github.com/crownthebook-design/weather-hedge-monte-carlo

## c) Contract design and "which contract to list"

**Black, D. G. (1986).** Success and failure of futures contracts: theory and empirical evidence. Monograph 1986-1, Salomon Brothers Center, New York University.
https://libcat.library.tamu.edu/Record/in00000415766
- Catalogue record verified. Content not read. Known in later surveys for linking contract success to the size of the cash market, price volatility and how well existing contracts already cross-hedge the risk. Cite through Till (2014) unless the team reads the monograph.

**Duffie, D. and Jackson, M. O. (1989).** Optimal innovation of futures contracts. Review of Financial Studies 2(3), 275-296.
https://scilit.com/publications/9f8ccd416098509130828973e4fc70c1
- An exchange that wants maximum volume picks which contract to create, given hedgers with mean-variance preferences in an incomplete market. This is the theory version of Part 3.

**Cuny, C. J. (1993).** The role of liquidity in futures market innovations. Review of Financial Studies 6(1), 57-78.
https://ideas.repec.org/a/oup/rfinst/v6y1993i1p57-78.html
- Exchange design of a new market when liquidity matters, with competing exchanges. Says liquidity shapes design, not only hedging fit.

**Duffie, D. and Rahi, R. (1995).** Financial market innovation and security design: an introduction. Journal of Economic Theory 65(1), 1-42.
https://researchonline.lse.ac.uk/id/eprint/4089
- Survey of the security design literature. Bibliographic record verified. Abstract not available on the page.

**Tashjian, E. and Weissman, M. (1995).** Advantages to competing with yourself: why an exchange might design futures contracts with correlated payoffs. Journal of Financial Intermediation 4(2), 133-157.
https://ideas.repec.org/a/eee/jfinin/v4y1995i2p133-157.html
- Bibliographic record verified. Abstract not read. The title question is the Newark-next-to-Central-Park question. The team should read it.

**Athanasoulis, S. G. and Shiller, R. J. (2001).** World income components: measuring and exploiting risk-sharing opportunities. American Economic Review 91(4), 1031-1054.
https://ideas.repec.org/a/aea/aecrev/v91y2001i4p1031-1054.html
- Solves for the best new contracts to create from the covariance of incomes across countries. Closest empirical precedent for "optimize which new market to open". Macro, not weather.

**Corkish, J., Holland, A. and Vila, A. F. (1997).** The determinants of successful financial innovation: an empirical analysis of futures innovation on LIFFE. Bank of England Working Paper 70.
https://ideas.repec.org/p/boe/boeewp/70.html
- Contract success follows the size and volatility of the underlying market and first-mover advantage. Liquidity looks like a result of success more than a cause.

**Till, H. (2014).** Why some futures contracts succeed and others fail: a survey of relevant research. EDHEC working paper.
https://climateinstitute.edhec.edu/publications/why-some-futures-contracts-succeed-and-others-fail-survey-relevant-research
- Survey of the success-and-failure literature.

**Church, R. and ReVelle, C. (1974).** The maximal covering location problem. Papers in Regional Science 32(1), 101-118.
https://scilit.com/publications/3efa99f9e1b0e8cad782263374e68a16
- The operations research model that Part 3 is an instance of: choose sites to cover the most weighted demand.

Exchanges choosing weather cities:
- CME added Baltimore, Detroit, Salt Lake City and four European cities in June 2005, and Paris, Essen, Burbank, Houston, Philadelphia and Boston in June 2023. Neither notice gives selection criteria beyond rising demand.
  https://www.cmegroup.com/media-room/press-releases/2005/6/20/cme_to_list_sevennewweathercontractsincitiesintheunitedstatesand.html
  https://www.cmegroup.com/articles/2023/cme-group-weather-suite-expanded.html
- Kalshi added Seattle, Las Vegas, Washington DC, San Francisco and New Orleans in January 2026. No reason given. https://www.climatesight.app/blog/kalshi-adds-five-new-cities/
- Kalshi's temperature rulebook filings keep the city as a blank and the reasoning in confidential appendices. https://www.cftc.gov/filings/orgrules/rules08172617953.pdf
- Newark and Trenton check: Kalshi market pages exist for Newark (EWR) with an event date of 2026-08-27 and for Trenton from 2026-08-31. That is consistent with a 2026-08-26 listing. I found no public announcement or stated rationale.
  https://kalshi.com/markets/kxhightewr/newark-nj-ewr-daily-max-temp/kxhightewr-26aug27
  https://kalshi.com/markets/kxhightttn/trenton-nj-daily-max-temp/kxhightttn-26aug31
- I found no academic study of how any exchange picks weather cities.

## d) Empirical work on Kalshi weather markets

**Bürgi, C., Deng, W. and Whelan, K. (2025).** Makers and takers: the economics of the Kalshi prediction market. UCD Centre for Economic Research WP25/19.
https://www.ucd.ie/economics/t4media/WP2025_19.pdf
- All Kalshi categories, 2021 to April 2025. Strong favourite-longshot bias. Contracts under 10 cents lose over 60% on average. Takers lose more than makers. The bias is significant inside the Climate and Weather category too.

**Crosier, A. W. (2026).** Prediction markets beat the weather forecast on tomorrow's high temperature. arXiv:2609.23969.
https://arxiv.org/abs/2609.23969 (coverage: https://nextpredict.io/market-news/industry/study-kalshi-weather-markets-outperform-public-forecasts/)
- Seven cities including New York and Philadelphia, 7,590 city-days. The market-implied high beats the National Blend of Models in six of seven cities, by about 10% in error early in trading.

**OddsReference Research (2026).** Weather prediction market efficiency: 40,032-contract study. Web article with PDF, not peer reviewed.
https://oddsreference.pages.dev/predictions/research/weather-efficiency-paper
- Kalshi daily highs. Forecast edges do not survive fees. Round-trip taker cost about 3 to 3.5 cents. Longshot bias in weather is small (about 0.4 points under 10%). Calls the market roughly semi-strong efficient.

**Le, N. A. (2026).** Decomposing crowd wisdom: domain-specific calibration dynamics in prediction markets. arXiv:2602.19520.
https://arxiv.org/abs/2602.19520
- 353 million trades on Kalshi and Polymarket. Calibration varies by domain, horizon and trade size. Abstract does not single out weather.

**Muthum, K. (2025).** Evaluating the wisdom of the crowd: Kalshi weather market calibration. Blog and dashboard.
https://www.cs.utexas.edu/~kavish/blog/kalshi-weather-calibration.html
- Calibration tooling for seven cities from one-minute candles. The post states no numeric results.

Luo (2026), Iturbide (2026), Kalshi Research (2026) and Eren (2026) in section b also belong here.

## e) Direct precedent

(i) Mapping local hedgeability from actually listed prediction-market contracts with real strikes and prices.
- Partial precedent exists: Luo (2026). It uses real Kalshi contracts, station pairs, multi-station portfolios and out-of-sample tests. From the abstract it works with degree-day indices over 30 station pairs. It does not appear to cover hundreds of stations, binary heat-day events, strike shifting on the actual ladder, or bid/ask-costed hedges at off-station sites. I could not read the full text to confirm.
- Outside prediction markets, D'Aversa et al. (2023) did location-adjusted strikes for 197 stations and Ritter et al. (2014) did optimal station portfolios.
- I found no published map of this kind for NY/NJ/PA or for 90F heat days.

(ii) Optimizing which city a prediction market should list next for weather.
- None found. Phrasings tried: optimal city or station selection for weather contracts, exchange weather city listing criteria, contract listing coverage optimization, next city, new cities with basis risk, station network design for index insurance, hedgeability map.
- Nearest relatives are theory (Duffie and Jackson 1989; Cuny 1993; Tashjian and Weissman 1995), a macro application (Athanasoulis and Shiller 2001) and the generic location model (Church and ReVelle 1974).

## Originality rating

| Part | Rating | Reason |
|---|---|---|
| 1. Hedgeability map from listed contracts at adjusted strikes | Medium (low for method, medium for setting and scale) | Luo (2026) already tests multi-station Kalshi hedges out of sample; D'Aversa et al. already do adjusted strikes. New: binary heat-day miss rates, hundreds of stations, the actual ladder, both ideas combined. |
| 2. Pricing with real Kalshi bid/ask | Medium | Iturbide and Luo use real Kalshi prices, but no one found prices a geographic hedge at off-station sites with quoted spreads. Short history for Newark and Trenton limits it. |
| 3. Which city to list next, validated on Newark and Trenton | High | No empirical precedent found. Theory and the covering model are old; the application and the real-listing check are new. |

Overall: medium-high for a course project, provided Luo (2026) is cited up front and the contribution is stated as going beyond it.

## Must cite and differentiate

1. Luo (2026). Same venue, same question, and a negative result on multi-station portfolios. Differentiate by tail-event (heat day) hedging, scale, strike adjustment, bid/ask costing and the listing problem.
2. Ritter, Musshoff and Odening (2014) together with D'Aversa et al. (2023). These are the two halves of Part 1's method. Differentiate by using listed binary contracts with real prices and by combining portfolio weights with strike shifts.
3. Duffie and Jackson (1989), with Church and ReVelle (1974) for the formulation. Part 3 is an empirical, coverage-based answer to their theoretical question.
Also worth one line each: Iturbide (2026) as the sibling paper on temporal basis risk, and Leppert et al. (2021) for heat.

## Findings that threaten the idea

- Luo: portfolios beat the best single station out of sample only 43% of the time, and shrinkage did not fix it. The team's Part 1 may show the same. Plan to report it honestly if so.
- Luo: basis risk rises with distance. The team says distance does not predict mismatch. These use different measures (degree-day variance versus 90F miss rate) and different station sets. The team must explain the gap.
- Ritter et al.: gains stop after two to five stations and transaction costs were left out. With four listed cities and real spreads, net gains may be small.
- Leppert et al.: for heat, interpolation beats nearest station by only 2 to 3%.
- Dalhaus and Finger: better spatial data helped less than better index timing.
- Bürgi et al.: cheap contracts are overpriced for takers. A 90F hedge often means buying a cheap tail bracket, so the hedger pays the bias. OddsReference finds the weather bias is small, so this is unsettled.
- OddsReference: taker round trip costs about 3 to 3.5 cents, large against a low-probability bracket price.
- Luo: outcomes fall outside the bin ladder on 17% of days. Strike shifts are limited to what the ladder offers each day.
- Cuny and Corkish et al.: exchanges list for liquidity and volume, not hedging coverage. Kalshi may have picked Newark and Trenton for other reasons. Its filings keep the reasons confidential.
- The validation has two data points and the team already knows the answer. State the objective and weights before running it, and report the rank of every candidate.

## Findings that support the idea

- D'Aversa et al.: distance does not explain the right strike; altitude and latitude do. Matches the team's finding.
- Norton et al.: geography is a weak predictor of payout gaps; altitude matters for heat.
- Ritter et al.: a small optimal portfolio cut basis risk 20 to 40% out of sample for rain.
- Woodard and Garcia: hedging with another location's contract is workable.
- Yang, Brockett and Wen: city contracts hedge Northeast and Mid-Atlantic power load well, and contract choice affects which contracts survive.
- Luo: geography is the largest friction and the map is the object to study. This supports the project's framing.
- Crosier, Luo and OddsReference: Kalshi weather prices are accurate, so historical quotes are a fair basis for costing.
- Eren: holding patterns suggest some real hedging demand in weather contracts.
- Trade press in late 2026 names basis risk as the open problem. The topic is timely.
