# Can an amusement park hedge rainy-season losses on a prediction market?

ECE 473 (Princeton), fall 2026. Team: Qasim Omer, Ehfaz Zoha, Viktor Hrushka.

**Question.** A park loses money on days with heavy rain during opening hours. Kalshi lists a daily
"will it rain" contract settled at the park's nearest NWS station. Does that contract hedge the park, and
would a seasonal contract on the *count* of loss days do better, when the park is not at the station?

**Hypothesis (pre-registered, [docs/PHASE2_PREREG.md](docs/PHASE2_PREREG.md)).** A seasonal rain-day-count
contract reduces a park's bad-season losses where Kalshi's daily rain contract does not.

**Main result.** Kalshi's daily contract is never a hedge: it pays on about 34 days a season at Trenton while
a park loses on about 5, and its hedge effectiveness is below zero in every case after premiums. The seasonal
count contract removes about two thirds of bad-season cost when the park's rain matches the station's
(Philadelphia, 35 held-out seasons, HE 0.65 [0.29, 0.78]) but fails for a stand-in gauge 28 km from Trenton
(HE -0.37 [-0.62, -0.28]), so the registered claim "the seasonal contract beats Kalshi's" is **not** made and
location basis is the finding. Figure: [results/talk/fig3_hedge_effectiveness.png](results/phase2/fig_hedge_effectiveness.png)
(the talk version will be `results/talk/fig3_hedge_effectiveness.png`); numbers: [results/phase2/summary.md](results/phase2/summary.md).

**The pivot.** The project began as a temperature study (a Central Park contract missed 34-49% of 90F days at
nearby stations, but the proposed "local layer" was a product nobody sells, priced by assumption). After
Milestone I it was re-scoped to a real buyer (parks), a real risk (rain) and a real baseline (Kalshi's daily
rain contract). The temperature files are kept for comparison; [docs/ARCHIVE_NOTE.md](docs/ARCHIVE_NOTE.md) lists them.

We also built the seasonal contract as an on-chain LMSR market (six count buckets, basket purchase, oracle,
refunds; 162 contract tests) and ran it end to end on the real 2025 Trenton season locally. Sepolia deployment:
[docs/deploy_sepolia.md](docs/deploy_sepolia.md); demo plan: [docs/demo_script.md](docs/demo_script.md).

## Reproduce

Python 3.10+ (`pip install numpy pandas pyarrow matplotlib pytest requests`), Node 18+ (`cd contracts && npm ci`).
`python scripts/check_env.py` lists anything missing and which script produces it.
`bash scripts/run_all.sh` runs steps 3-7 below in order (about 5 minutes, no network). Flags: `--no-contracts`,
`--rebuild` (step 2, needs `data/raw`), `--pull` (step 1, network).

| Step | Command | Needs | Writes | Time |
|---|---|---|---|---|
| 1. Data pulls (network; cached, resumable) | `python scripts/p0_rain_fetch_iem.py`, `p0_rain_fetch_ncei_hourly.py`, `p0_rain_fetch_ncei_daily.py`, `rain_fetch_cli.py`; `python scripts/kalshi_rain_pull.py` | NOAA NCEI, IEM, Kalshi public API | `data/raw/**` (git-ignored) | 15-40 min |
| 2. Phase 1 build | `python scripts/p0_rain_analyze.py; python scripts/rain_build_daily.py; python scripts/rain_validate.py; python scripts/rain_summary.py`; `python scripts/kalshi_rain_quotes.py; python scripts/kalshi_rain_aggregates.py` | `data/raw` | `data/processed/rain/`, `data/processed/kalshi_rain/` (committed), `results/rain/`, `results/kalshi_rain/` | 2-3 min |
| 3. Tests | `cd contracts && npm test` (162); `python -m pytest tests -q` (400) | committed data | `contracts/remix/`, `contracts/test/vectors/`, `results/market/gas_report.json` | 1.5 min + 10 s |
| 4. Market experiment (simulated LMSR prices) | `python -m sim.experiment` | step 3 gas report | `results/market/` | 2 s |
| 5. Phase 2 evaluation (pre-registered) | `python scripts/hedge_build_standins.py; python scripts/hedge_run.py; python scripts/hedge_report.py` | committed processed data | `results/phase2/`, `data/processed/hedge/` | 75 s |
| 6. Independent replication | `python replication/replicate.py` | committed processed data; imports nothing from `src/` | `replication/*.csv` | 70 s |
| 7. Market tests only | `python -m pytest tests/test_lmsr_*.py -q` (61) | step 3 vectors | | 5 s |
| 8. Phase 3 (exploratory, running) | see `docs/status/phase3_*.md`; `python scripts/reach_rain_stations.py; python scripts/reach_rain_fetch.py iem` | network for the rain pull | `data/processed/reach/`, `results/phase3/` | hours |

Everything is deterministic (bootstrap seed 473): a re-run of steps 3-6 reproduces the committed CSVs byte for
byte. One test, `tests/test_panel_data.py::test_panel_matches_raw_file_for_one_station`, reads `data/raw` and
fails without it; everything else runs from committed files.

## Where each result lives

| What | Where |
|---|---|
| Headline table, verdict, sceptic's notes | `results/phase2/summary.md`, `headline_table.csv`, `metrics_tidy.csv` (every case x strategy x metric with 95% interval), `train_params.csv`, `season_net_cost.csv` |
| Figures | `results/talk/fig3_hedge_effectiveness.png`, `fig_b1_net_cost_by_season.png`; `results/rain/loss_vs_kalshi_days.png`; `results/kalshi_rain/calibration.png`; `results/market/stepped_hedge_price.png` |
| Replication (second implementation from the written rules) | `replication/results.csv`, `params.csv`, `ambiguity_sensitivity.csv`; log `docs/status/phase2_replication.md` |
| Rain counts per station and season (observed) | `data/processed/rain/season_counts_*.csv`, `daily_*.parquet`; summary `results/rain/summary_main.md` |
| Kalshi prices, calibration, fitted price model (aggregates only) | `data/processed/kalshi_rain/*.csv`, `price_model.json`; log `docs/status/phase1_kalshi.md` |
| On-chain market: contracts, tests, gas, simulation | `contracts/RainCountLMSR.sol`, `SeasonCountOracle.sol`, `contracts/test/1*_rain_*.test.js`, `results/market/summary.md`, `docs/contract_spec.md` |
| Phase 3 reach and lead-time analyses (exploratory) | `results/phase3/`, `docs/status/phase3_*.md`, pre-registration `docs/PHASE3_PREREG.md` |
| Work logs with UTC timestamps | `docs/status/phase0_*.md` to `phase4_*.md` |

## Labelling convention

Every table and figure says which numbers are which. **Observed**: station weather (NOAA GHCN-Daily, NCEI ISD,
IEM ASOS/METAR, NWS climate reports) and real Kalshi quotes (517 markets, 2021-2026). **Modelled**: every
Kalshi price outside the days with real quotes (fitted on the real ones, `src/kalshi/rain_price_model.py`) and
every premium of the seasonal contract (expected payout plus loading). **Simulated**: LMSR market prices in
`sim/` and `results/market/` (no orders were placed anywhere). Loss per loss day is a scenario parameter L; nothing
is presented as a park's actual loss. The stand-in gauges (PNE, DYL) are not the park.

## Pre-registration and replication

`docs/PHASE2_PREREG.md` fixed the question, strategies, windows (TRAIN 1999-2014, REPORT 2015-2026), metric and
what counts as a result before any hedge number was computed; reading choices made before the first run are in
`docs/status/phase2_eval.md`; deviations: none forced. A second implementation written from the documents alone
(`replication/replicate.py`, no imports from `src/`) reproduces the TRAIN parameters and REPORT hedge
effectiveness of cases A, B1 and D and lists the readings on which the B1 sign depends. Phase 3 questions were
chosen after seeing Phase 2 and are labelled exploratory (`docs/PHASE3_PREREG.md`).

## AI use

The code, data pipelines, tests and these working documents were built with heavy AI assistance (allowed by the
course). The team wrote the milestone updates, the report and the slides themselves. Every number in them traces
to a file in `results/` or `data/processed/` produced by code in this repository.

## Data sources and terms

- NOAA NCEI (GHCN-Daily, ISD) and NWS climate reports via the Iowa Environmental Mesonet: US public-domain data;
  cached raw under `data/raw` (git-ignored), reduced files committed under `data/processed`.
- Kalshi public API (read-only, no account): only aggregates are committed (`data/processed/kalshi_rain/`,
  `data/processed/kalshi_rain_probe/`, `results/studyB/`). Raw candle and quote rows stay in `data/raw/kalshi`
  and are never committed.
- Park coordinates from Wikipedia (CC BY-SA); operating calendars read from queue-times.com (evidence only, not
  an input to any count). Testnet only; no real-money trades; no private keys anywhere in the repository.

Repo map by folder: [docs/REPO_GUIDE.md](docs/REPO_GUIDE.md). Frozen spec: [docs/SPEC_v3.md](docs/SPEC_v3.md).
