# Phase 1: Kalshi rain workstream log

All times UTC. Raw Kalshi rows stay in data/raw/kalshi/ (git-ignored). Only aggregates appear here and in data/processed/kalshi_rain/.
"Observed" = real Kalshi quotes or results. "Modelled" = output of src/kalshi/rain_price_model.py.

## How to continue if interrupted
1. `python scripts/kalshi_rain_pull.py` is resumable: it skips every market whose candle file exists in data/raw/kalshi/candles/<series>/. Its log is data/raw/kalshi/rain/pull_log.csv; `--status` prints what is and is not cached without touching the network.
2. `python scripts/kalshi_rain_quotes.py` builds the per-market quote table (data/raw/kalshi/rain/quote_table.csv) from the cache (no network).
3. `python scripts/kalshi_rain_aggregates.py` writes the aggregates, the fitted price model and the figure (no network).
4. `python -m pytest tests/test_kalshi_rain_*.py -q`

## Progress log
- 2026-11-11 22:50: Read SPEC_v3, phase0_kalshi.md, phase0_verdict.md, client.py, fee section of docs/contract_spec.md. Cache at start: 16 KXRAIN and 10 KXRAINNYC candle files from the Phase 0 sample. API reachable (HTTP 200 on /historical/cutoff).
