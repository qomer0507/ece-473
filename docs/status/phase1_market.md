# Phase 1 market workstream (Viktor): progress log

Scope: contracts/**, sim/**, tests/test_lmsr_*.py, results/market/**, docs/deploy_sepolia.md, this file.
Binding inputs: docs/SPEC_v3.md ("Market (LMSR)") and docs/status/phase0_contract.md (review, M1-M3, m1-m12).
Times are UTC. Newest entries at the bottom. If you take over: read "Design decisions", then the last log lines.

## Design decisions (so far)

- New files; the temperature version (BracketLMSR.sol, TemperatureOracle.sol, MockOracle.sol, tests 01-04, 99) stays as it is.
- contracts/RainCountLMSR.sol: six buckets on the season's loss-day count, five inclusive upper edges, uniform start only.
- contracts/SeasonCountOracle.sol: the owner opens a season (start, end, number of days) once; a reporter reports the count once, only at or after the season end.
- The market copies season start, season end and season days from the oracle at deployment (one trial read). So the two can not disagree.
- Every oracle read is a low-level staticcall with a gas cap; failure or a malformed answer means "no valid report".

## Log

- 2026-11-12 03:45 Started. Read SPEC_v3, phase0_contract.md, the existing contract, tests, sim and pytest files. `npm ci` in contracts/ done (node_modules was missing).
- 2026-11-12 04:25 Written and compiling (solc-js 0.8.26, optimizer 200): contracts/RainCountLMSR.sol (15,884 bytes deployed), SeasonCountOracle.sol (3,532), MockCountOracle.sol, mocks/RainTestHelpers.sol. scripts/compile.js now builds old and new contracts, maps the pinned import `@openzeppelin/contracts@4.9.6/` to node_modules, and flattens four files into remix/.
- 2026-11-12 04:30 sim/lmsr.py extended (count buckets, vector quotes, funding helper, CountMarket, `python -m sim.lmsr funding`). sim/make_vectors.py also writes contracts/test/vectors/reference_rain.json. Old 29 pytest tests still pass.
- 2026-11-12 04:50 JS tests written and passing when run file by file: test/rain_helpers.js, 11_rain_math (6), 12_rain_market (25), 13_rain_oracle (47). Still to do: 14 property + cross-check file, 15 gas, experiment, pytest, Remix files check, deploy guide.
- 2026-11-12 05:20 `npm test` in contracts/: 154 passing (65 earlier temperature tests + 89 rain tests), about 1 minute. test/15_rain_gas.test.js passes alone (2 passing). test/99_gas.test.js (temperature) now skips its report when run alone instead of failing.
- 2026-11-12 05:25 Rain counts exist: data/processed/rain/season_counts_TTN.csv (rain workstream, may still change). Experiment uses it: calendar all_days, season_usable True, training seasons only (16 usable, 1999-2014). Bucket edges are still the EXAMPLE edges [2,4,6,8,10]; final edges come from the rain workstream. Placeholder distribution kept behind `--placeholder`.
- 2026-11-12 05:35 sim/experiment.py is now the rain-count experiment (results/market/). The temperature experiment moved unchanged to sim/experiment_temperature.py (results/part3/). Figure results/market/stepped_hedge_price.png opened and checked: title says SIMULATED, axes and legend readable, fair-value line labelled.
- 2026-11-12 05:40 pytest tests/test_lmsr_*.py: 56 passed (29 earlier + 27 new in test_lmsr_rain_reference.py, test_lmsr_rain_crosscheck.py, test_lmsr_rain_experiment.py). The rain cross-check FAILS (does not skip) if rain_contract_quotes.json is missing or was written from a different RainCountLMSR.sol (sha256 check).
