# A. Course fit: does the "market completeness" reframing suit ECE 473?

Researched 2026-11-11. Web sources plus a read-only clone of the public course repo.
Labels: **[C]** confirmed from a source I read. **[U]** unverified or not found.

## 1. What ECE 473 is

### Confirmed
- **[C]** Title: "Elements of Tokenized Finance", COS/ECE 473, Fall 2026. Earlier name: "Elements of Decentralized Finance" (Spring 2023 repo).
  Source: https://web3.princeton.edu/elements-of-defi/ and https://github.com/Blockchains-Princeton/COS-ECE-473-Fall-2026
- **[C]** Instructor: Prof. Pramod Viswanath.
- **[C]** TAs: Kaya Alpturer and **Niusha Moshrefi**. So "Niusha" is a teaching assistant. I found no other public profile for her. Nothing more is known.
- **[C]** Lecture topics, in order: blockchain primer; EVM and smart contracts; Exchanges I-IV (DEXes, bonding curves and CFMMs, improving CFMMs, aggregation and propAMMs); **Prediction Markets I: Incentives and Design**; **Prediction Markets II: Parlays, Conditional and Decision Markets**; options, derivatives, perpetuals (two lectures); midterm; lending pools; stablecoins; **Bridges and Oracles**; DePINs; New Banks; Old Banks vs New Banks; conclusion.
- **[C]** Grading: programming assignments 14%, in-class labs 24%, homeworks 15%, midterm 17%, **final project 30%**.
- **[C]** Final project wording on the course page (quoted):
  - "In-depth study of one of the elements of DeFi covered in the course."
  - "Potential project topics shall be provided by class staff, with a focus on prediction markets."
  - "Substantial coding and system building is expected."
  - "The final project report will serve as the final exam of the course."
  - AI use is encouraged, but the introduction, findings and conclusion must be written without AI.
- **[C]** Schedule: "Project FAQ" on 11/12. Project presentations on 11/17, 11/19, 12/01, 12/03.
- **[C]** Labs that matter for this project (from the course repo, `Labs/`):
  - Lab 7, "Using and Building a Prediction Market". Covers proper scoring rules, Hanson's LMSR, AMM versus order book. Includes a Solidity binary LMSR contract. States the market maker's worst-case loss is `b ln 2`. Resolution is by the contract owner; the lab says a real market needs an oracle.
  - Lab 8, "Trading Correlation in Prediction Markets". Three LMSR markets on A, B, and "A and B". Shows that correlation is tradeable information.
  - Lab 13, Chainlink oracle walk-through plus a class-run oracle that resists adversarial values.
  - Lab 14, "GPU Compute as a Commodity". A cash-settled forward used as a **proxy hedge**. The lab's own words: a hedge "can break when the financial asset and the business exposure are not identical", and the intermediary "is exposed to **basis risk**".

### Not found
- **[U]** No public rubric, milestone definitions, team-size rule, or report length. The page shows no Milestone I or II. Those dates come only from the team's own files.
- **[U]** No public list of this year's staff-provided project topics. The page says lecture 2 discussed potential projects; the slides are a Dropbox link I could not read.
- **[U]** No readable list of past projects. A Notion page titled "Princeton University Elements of DeFi Student Work" exists but needs JavaScript and returned nothing: https://recondite-monday-e86.notion.site/Princeton-University-Elements-of-DeFi-Student-Work-20abc022929b49a987e39ab256bd73e5
- **[U]** Princeton registrar listing. The page needs JavaScript and did not load: https://registrar.princeton.edu/course-offerings
- **[U]** Past-semester repos other than Spring 2023 are not public under the names I tried. The Spring 2023 repo holds labs and assignments only, with no project guidance.

## 2. Does the reframed project fit?

### Short answer
Yes on topic. Thin on "system building" unless a small mechanism piece is added.

### Why it fits
- The staff say projects focus on prediction markets. This project studies a live prediction market (Kalshi).
- Lab 14 teaches the exact idea: a proxy hedge and its basis risk. The hedgeability map is that lab done at scale, with real stations and real contracts.
- Lab 8 teaches that correlation between events has value. Multi-contract hedging of a local station is a direct use of that.
- "Which city to list next" is a market-design question. It matches "Prediction Markets I: Incentives and Design".
- Settlement source and station choice are an oracle question. That matches "Bridges and Oracles" and Lab 13.
- It answers Niusha's feedback directly. Metric: share of local heat-day risk removed, net of cost. Baseline: buy the nearest city contract. Test: the 2026-08-26 Newark and Trenton listings.

### Where it is weak
- Kalshi is a centralized, CFTC-regulated exchange. Nothing in the reframed plan is on-chain.
- The course page says "Substantial coding and system building is expected". A pure data study may read as an analysis project. This is a judgment call that only the staff can settle.
- **Action:** ask at the 11/12 Project FAQ whether a data-and-mechanism study on Kalshi meets the system-building bar. Do not assume.

### Concrete, modest suggestion
Do two small things. Do not rebuild the old auction, pool and mock-USDC prototype.

**(a) Cost the "next listing" with LMSR. About 1 to 2 days.**
- Take the top-ranked unlisted station from part 3.
- Model a new daily-high market for it, run by an LMSR market maker. Reuse the course's Lab 7/8 Solidity contract, or a Python port of its cost function.
- Report three numbers: the sponsor's worst-case subsidy per day (`b ln 2` for a binary market, `b ln n` for n temperature buckets; the binary bound is stated in Lab 7); the price impact a small business pays to buy its hedge size at a given `b`; and that cost versus the real Kalshi bid/ask spread seen on thin Trenton days.
- What it adds: a mechanism result. It turns "list this city next" into "list it, and bootstrapping liquidity costs at most $X per day". It uses course material by name. It gives one deployable contract and tests, which helps with "system building".
- What it costs: time; a choice of `b` that must be argued; no real order flow, so results are bounds and scenarios, not forecasts. Deploying to a testnet is optional and adds little.

**(b) Settlement-source section. About half a day to a day.**
- The team already found Kalshi's NYC source change (NWS report to The Weather Company, first event 2026-08-14, per the team's notes).
- Add one table: same city, different venue, different station and source. Kalshi NYC uses Central Park. Polymarket NYC uses LaGuardia via Weather Underground (see section 3). The team's own data says LaGuardia runs hotter than Central Park.
- What it adds: an oracle analysis tied to Lab 13. It shows "basis risk" has two parts: location, and data source.
- What it costs: little. Needs a spot check of source disagreement days.

If time allows only one, do (b). It is cheap and mostly done. Do (a) if the staff say system building is required.

## 3. Survey: weather risk on-chain and in prediction markets

- **Kalshi (centralized, CFTC-regulated).** Daily high and low temperature markets settle on the final NWS Daily Climate Report "at the listed station". Hourly markets settle on The Weather Company. Each market names its own source. The Chicago contract terms name NWS and Chicago Midway, and let Kalshi replace the source agency. Geographic basis risk is not addressed; the buyer picks a city. https://help.kalshi.com/markets/popular-markets/weather-markets and https://kalshi-public-docs.s3.amazonaws.com/contract_terms/CHIHIGH.pdf
- **Kalshi Trenton.** Series KXHIGHTTTN exists on kalshi.com. The Oct 13 2026 event shows about $2,294 volume and refers to weather.com/kalshi for status. This is consistent with the team's note about The Weather Company, but the page I read did not state the station or source. **[U]** I did not verify the Newark series or the exact 2026-08-26 start date. https://kalshi.com/markets/kxhightttn/trenton-nj-daily-max-temp/kxhightttn-26oct13
- **Polymarket (on-chain settlement).** Daily highest and lowest temperature markets for about 50 cities worldwide. NYC resolves on the **LaGuardia Airport station (KLGA)** using Weather Underground daily history, in whole degrees F. It finalizes when the next day's first data point posts. The Aug 6 2026 NYC event showed $146,238 volume. One airport station stands for the whole city, so basis risk is ignored. https://polymarket.com/event/highest-temperature-in-nyc-on-august-6-2026 and https://polymarket.com/weather
- **Arbol.** Parametric weather cover for farms and businesses. Uses Chainlink to bring NOAA rainfall data to smart contracts (post dated 2021-01-12). Its IPFS case study describes gridded and station data, immutable content hashes, and a "snap to grid" step that maps a client's latitude and longitude to the nearest grid cell. So it cuts location basis risk with per-site gridded data and bespoke structures. I found no public number for residual basis risk. https://arbol.io/post/businesses-and-farmers-can-now-hedge-weather-risk-through-the-arbol-platform-and-chainlink-data and https://docs.ipfs.tech/case-studies/arbol/
- **dClimate.** Decentralized marketplace for climate data and forecasts, spun out of Arbol (post dated 2021-02-01). Data gets "skill scores"; scoring runs as Chainlink external adapters. It is a data layer, not a hedge. The post does not discuss basis risk. https://www.arbol.io/post/an-introduction-to-dclimate-a-decentralized-network-for-climate-data-2
- **Etherisc with ACRE Africa (Kenya).** Blockchain crop insurance. Over 17,000 farmers by July 2021; payouts by M-Pesa. A Mercy Corps Ventures report says rainfall from the Africa Rainfall Climatology satellite product triggered payouts, read at each farmer's GPS location. That is per-location indexing; the grid resolution is not stated. https://cointelegraph.com/news/etherisc-onboards-17k-kenyan-farmers-covered-by-blockchain-based-crop-insurance and https://medium.com/mercy-corps-social-venture-fund/pilot-insights-driving-climate-resilience-for-smallholder-farmers-in-kenya-through-smart-1084d9e24cb5
- **Chainlink weather oracles.** Two routes. A Google Cloud node serving NOAA data from BigQuery (2021). An AccuWeather node serving "current weather by geolocation", including max and min temperature and precipitation (2021-12-15). These solve data delivery only. Which location and which source to use is left to the contract designer. https://www.nasdaq.com/articles/chainlink-integrates-weather-data-from-the-google-cloud-2021-08-06 and https://corporate.accuweather.com/newsroom/blog/the-accuweather-chainlink-node-is-now-live-making-weather-based-blockchain-applications-possible/

### Pattern
- Prediction markets (Kalshi, Polymarket): one station per city, liquid, cheap, large location basis risk.
- Parametric insurers (Arbol, Etherisc): per-site index, low location basis risk, bespoke and illiquid.
- The reframed project measures the gap between the two. I found no public source that maps it station by station. **[U]** That novelty claim rests on a limited search.

## Caveats
- I read the course page through a summarizing fetch tool. Quotes are short and should be rechecked against the live page before use in a report.
- The Notion student-work page, registrar page, Dropbox slides and web archive could not be read.
- The Polymarket and Kalshi figures are single-day snapshots.
