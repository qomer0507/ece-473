# Archive note: which files belong to the earlier temperature study (2026-11-12 UTC)

Nothing has been moved. This note lists what could go to `archive/` (keeping the same relative paths under it)
so a grader opening the repo sees the rain project first, and what must stay because live code still reads it.
The temperature study is cited in the report as the pivot and the comparison section, so its results stay in
the repo either way; the question is only where.

## A. Earlier study only: safe to move to `archive/` (no live code reads them)

Docs
- `docs/SPEC.md`, `docs/SPEC_v2.md` (superseded by SPEC_v3; SPEC_v3 line 3 says SPEC_v2 is "kept as a comparison section", so keep a pointer)
- `docs/CONTEXT.md` (October handoff), `docs/milestone1.md`, `docs/data_dictionary.md` (TMAX columns only)
- `docs/notes/ehfaz_milestone1.md`, `qasim_milestone1.md`, `viktor_milestone1.md`, `part2_preregistration.md`,
  `region_pull_2026-11-11.md`, `risk_check_2026-11-11.md`, `docs/notes/research/*`
- `docs/status/ehfaz.md`, `docs/status/qasim.md` (temperature-era logs; the rain logs are `phase*_*.md`)
- `docs/literature.md`: temperature-era but still the project's reference list; keep in `docs/` or move and link.

Code
- `src/backtest.py`, `src/basis_risk.py`, `src/load_weather.py`, `src/local_residual.py`, `src/metrics.py`,
  `src/station_hedge.py`, `src/weights/__init__.py`
- `src/kalshi/data.py`, `src/kalshi/study_b.py` (temperature Study B; `client.py`, `rain_quotes.py`, `rain_price_model.py` stay)
- `scripts/run_experiment.py`, `scripts/part2_rank.py`, `scripts/panel_build_panel.py`, `panel_build_stations.py`,
  `panel_fetch_outlines.py`, `panel_iem_checks.py`, `panel_study_a.py`, `scripts/pull_ceraunic_cache.py`,
  `pull_ghcnd.py`, `pull_region_tmax.py`, `pull_station_meta.py`, `scripts/kalshi_pull.py`, `kalshi_settlement.py`,
  `kalshi_study_b.py`
- `sim/experiment_temperature.py`
- `tests/test_alignment.py`, `test_contracts.py`, `test_residual.py`, `test_panel_bootstrap.py`,
  `test_panel_hedge.py`, `test_panel_data.py` (the last reads `data/raw/region/tmax`; it is the one test that fails
  on a clone without `data/raw`), `tests/test_kalshi_study_b.py`
  (if the tests move, run them with `python -m pytest archive/tests -q` or drop them from the default run)

Data and results
- `data/processed/aligned_daily.csv` (Milestone I), `data/processed/kalshi/*` (temperature settlement aggregates)
- `data/manifests/*` (provenance of the TMAX pulls)
- `results/part1/`, `results/part2/` (empty), `results/part3/`, `results/studyB/`, `results/tables/`,
  `results/figures/`, `results/synthetic/`

## B. Earlier study, but live code reads it: keep in place (or move and fix the paths listed)

- `src/panel/hedge.py` and `src/panel/__init__.py`: Phase 3 temperature reach (`src/reach_temp/pairs.py`) uses
  `to_wide` and the panel helpers; `scripts/p0_rain_parks.py` imports `haversine_km` from it.
- `data/processed/panel/stations.csv`, `tmax_panel.parquet`, `outlines.csv`, `cli_mapping.csv`, `iem_cache/`:
  read by Phase 3 (`src/reach_temp`, `scripts/reach_rain_stations.py`) and by `scripts/p0_rain_parks.py` (has_cli).
- `contracts/BracketLMSR.sol`, `TemperatureOracle.sol`, `MockOracle.sol`, `mocks/TestHelpers.sol`,
  `contracts/test/0*_*.test.js`, `99_gas.test.js`, `helpers.js`, `test/vectors/reference.json`,
  `contract_quotes.json`, `remix/BracketLMSR_flat.sol`, `TemperatureOracle_flat.sol`, `artifacts/BracketLMSR.json`
  etc.: `contracts/scripts/compile.js` compiles and flattens all of them and `rain_helpers.js` requires
  `helpers.js`; `npm test` runs the whole suite (63 temperature checks + 99 rain). Moving them means editing
  `compile.js` and `rain_helpers.js`. Recommendation: leave them; the rain market was adapted from BracketLMSR and
  the report says so.
- `sim/lmsr.py`, `sim/make_vectors.py`, `tests/test_lmsr_reference.py`, `test_lmsr_experiment.py`,
  `test_lmsr_contract_crosscheck.py`: shared maths for both markets; live.
- `src/kalshi/client.py`: shared; live.

## C. Live (do not move)

Everything listed as LIVE in docs/REPO_GUIDE.md: `docs/SPEC_v3.md`, `PHASE2_PREREG.md`, `PHASE3_PREREG.md`,
`PHASE0.md`, `deploy_sepolia.md`, `demo_script.md`, `contract_spec.md`, `milestone2_facts.md`, `docs/status/phase*`;
`src/rain`, `src/hedge_eval`, `src/reach_temp`, `src/kalshi/{client,rain_quotes,rain_price_model}.py`;
`scripts/{rain_,hedge_,kalshi_rain_,p0_,reach_rain_}*`, `scripts/run_all.sh`, `check_env.py`; `sim/{lmsr,experiment,make_vectors}.py`;
the rain contracts and tests; `data/processed/{rain,rain_probe,hedge,kalshi_rain,kalshi_rain_probe,reach}`;
`results/{phase2,phase3,rain,kalshi_rain,market}`; `replication/`.

## D. Generated files that could be git-ignored instead of archived

- `contracts/artifacts/*.json` (bytecode; rewritten by every `npm test`); `contracts/remix/*_flat.sol` are also
  regenerated but are the files a student pastes into Remix, so keep those tracked.
- `__pycache__/`, `.pytest_cache/` are already ignored but the top-level `.pytest_cache/` directory exists in the
  working tree (not tracked).

## E. If files move

1. Keep the relative layout under `archive/` so the temperature-era docs' internal links still make sense.
2. Add one line at the top of `archive/README.md`: "Temperature study, October-November 2026, superseded by
   docs/SPEC_v3.md; kept as the comparison section of the report."
3. Re-run `bash scripts/run_all.sh` and `python scripts/check_env.py`; both must still pass (`check_env.py` lists
   `data/processed/panel/*` as needed by Phase 3, so those stay).
