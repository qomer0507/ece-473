# Phase 0: feasibility probe (2026-11-12 UTC)

Final plan: "ECE 473 final plan: rain hedging for parks on prediction markets".
Baseline = a park buys Kalshi's existing daily rain contract. Solution = a seasonal contract on the count of
operating days with >= 0.25 inch of rain during opening hours (10am-6pm local), built as an LMSR market on Sepolia.
Metric = cut in bad-season net cost, measured on 40+ seasons of rain history.

Phase 0 answers four questions before any full build. It commits nothing. Keep what you pull; do not start Phase 1.

1. How far back, and how complete, is hourly rain at Trenton and the other stations near the parks?
2. Does Kalshi list daily rain for Trenton, Newark, Philadelphia, NYC? Since when, under what exact rule, with what price history?
3. Are the parks' past operating calendars public? If not, what rule stands in for them?
4. Is the existing LMSR bracket contract sound, and what does adapting it to six rain-count buckets take?

Rules for every workstream
- Never invent data. Every number comes from a file you produced or a cited source. Say "not found" when that is the answer.
- Report bad news plainly. A "no" in Phase 0 is a useful result.
- Write only your own files. Keep a dated progress log (UTC) in your status file and update it as you go.
- Never publish raw Kalshi rows; aggregates only. No trading, no accounts, no private keys.
- If a host is refused by the network filter, record it and move on. Do not route around it.

Files
- Rain/parks probe: docs/status/phase0_rain.md, scripts/p0_rain_*.py, data/raw/rain/**, data/processed/rain_probe/**
- Kalshi rain probe: docs/status/phase0_kalshi.md, scripts/p0_kalshi_*.py, data/raw/kalshi/** (git-ignored), data/processed/kalshi_rain_probe/**
- Contract review: docs/status/phase0_contract.md only (read-only review; do not edit contracts/ or sim/)
