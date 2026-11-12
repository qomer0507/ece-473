# Verdict on project direction (2026-11-11 UTC)

Inputs: A_course_fit.md, B_novelty.md, D_resources.md, ../risk_check_2026-11-11.md.

## Two facts that changed the recommendation
1. COS/ECE 473 is "Elements of Tokenized Finance" (Prof. Pramod Viswanath; TAs Kaya Alpturer and Niusha Moshrefi). Final projects focus on prediction markets. The course page expects substantial coding and system building. Labs 7 and 8 are LMSR prediction markets in Solidity; Lab 13 is oracles; Lab 14 is a proxy hedge with basis risk.
2. Luo (2026, SSRN 7138562) already studies Kalshi weather contracts as geographic hedges: 30 station pairs, 24 years, degree-day triggers. Multi-station portfolios beat the best single station out of sample only 43% of the time. Basis risk rises with distance. So a hedgeability map alone is not original.

## Recommended project
"Which local weather market should be listed next, and what would it cost to run?"
1. Measure the gap (baseline). Map how well listed Kalshi contracts (NYC, Philadelphia, Newark, Trenton) cover 90F heat days at about 300 station locations, using real bracket ladders and real quotes. Baseline = nearest contract at face-value strike. Cite and differentiate from Luo.
2. Choose the next market (new). Business-weighted coverage optimization over candidate stations. Pre-register objective and weights. Check against Kalshi's 2026-08-26 Newark and Trenton listings (two data points, weak test).
3. Build it (course fit). On-chain LMSR market for the chosen station, reusing the Lab 7 contract, settled by an oracle on the station's NWS report. Report sponsor subsidy (b ln n) and the price a business pays to hedge at realistic size. This replaces assumed premiums with a mechanism price.

## Alternatives considered
- Pricing-efficiency study of Kalshi weather markets: already done (Crosier 2026; Bürgi, Deng & Whelan 2025). Low originality.
- Settlement-source/oracle study: small; keep as a section.
- Rebuild the old auction/pool prototype: no. Large and unfocused.

## Resources
- NOAA GHCN-Daily, about 300 stations with TMAX 2015-2025: free, no account. Blocked from the cloud workspace and from the linked-Mac shell. Run a pull script in the Mac's own Terminal.
- Kalshi prices: NYC from 2021-08-06 (six brackets by July 2023), Philadelphia from 2024-11-20, Newark and Trenton from 2026-08-26. NYC 2023-2026 already cached. Licence unclear for research: do not publish raw data; ask Kalshi.
- Census CBP/ZBP 2023: free, needs a free API key.
- Course LMSR lab code: public course repo.
- Solidity tooling: Hardhat via npm works in the cloud workspace; Foundry download blocked there.

## Open items
- Ask staff at the 11/12 Project FAQ: does this count as system building, and does the reframe need approval?
- Read Luo (2026) and Iturbide (2026) in full; SSRN did not load for us.
- Reconcile "distance does not predict mismatch" (our 7 stations) with Luo's opposite result.
- Final deadline and rubric still unknown.
