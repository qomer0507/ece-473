# Phase 4 repo-readiness workstream: log (UTC)

Scope (written only): README.md, docs/REPO_GUIDE.md, docs/ARCHIVE_NOTE.md, docs/demo_script.md, scripts/run_all.sh,
scripts/check_env.py, this file. Nothing moved, renamed or deleted. No git commands run; the lead commits.
Machine clock, UTC.

## State (2026-11-12 22:15 UTC): complete

- `cd contracts && npm test`: **162 passing, 0 failing**, 1 min 35 s (compile with solc-js + Hardhat EVM).
- `python -m pytest tests -q`: **400 passed**, 8 s. Of these 61 are `test_lmsr_*`, 264 are `test_rain_*`,
  `test_hedge_*`, `test_kalshi_*`; the rest are temperature-era (`test_alignment`, `test_contracts`, `test_residual`,
  `test_panel_*`).
- `bash scripts/run_all.sh --no-contracts`: exit 0 in 140 s (pytest 7 s, sim.experiment 1 s, stand-ins 6 s,
  hedge_run 58 s, hedge_report 2 s, replicate 65 s). Full run with contracts: exit 0 in 214 s (22:20 UTC),
  results again identical to the committed files.
- Re-running steps 3-7 reproduced every committed CSV and summary byte for byte (sha256 of 21 files checked);
  only `results/market/manifest.json` changed (its `written_utc` field).
- `python scripts/check_env.py`: all required items present on the build machine; notes that `data/raw` is a
  symlink to `/home/claude/ece473-ceraunic/data/raw` (git-ignored; absent on a fresh clone).

## Findings for the lead

1. **One test needs `data/raw`.** `tests/test_panel_data.py::test_panel_matches_raw_file_for_one_station` reads
   `data/raw/region/tmax/USW00014734.csv` with no skip guard; on a clone without the raw cache it fails
   (FileNotFoundError), so a grader would see 399 passed, 1 failed. Options: add `pytest.mark.skipif` on the raw
   file (temperature-era file, outside this workstream's list), or say so in the README (done).
2. **Deploy guide, read as a student.** Every value that must be computed or copied appears with its number or
   formula: the three addresses (section 4 table), the oracle address (step 1 to step 7), T and the four times
   (formula table with a worked example), VALUE for the deploy and the buy, `quoteBasket`, `maxCost`, every
   expected read after each step, the cancel rehearsal's T2 times, the refund amount. Every contract function the
   guide names exists in the compiled ABI (checked by script). Gaps: (a) "d is not chosen yet" is stale: Phase 2 chose d = 3 for case A
   (the row the guide uses) and d = 8 for B1 (`results/phase2/train_params.csv`); (b) no faucet URL and no note
   that faucets are rate-limited (test ETH must be obtained the day before); (c) Sepolia block time (12 s) and the
   expected confirmation wait are not stated; (d) reading values on Etherscan needs source verification, which the
   guide marks optional and untried, so the stage demo should read values in Remix; (e) the error table omits
   constructor messages a student can hit when typing: "Deadline before season end", "Season already reported",
   "Need five edges", "Edges not increasing", "Claim period out of range", "Dispute delay too long", and the
   oracle's "Start must be before end", "Season end in the past", "Count above season days". All handled in
   docs/demo_script.md; the guide itself is the market workstream's file and was not edited.
3. **Sensitive or raw content in tracked files: none found.** Tracked paths (404, read from `.git/index`
   without git) were searched for `.env`, API keys, private keys, seed phrases, mnemonics, PEM blocks, bearer
   tokens and 64-hex-digit strings. The only 64-hex hits are ABDK fixed-point constants in
   `contracts/remix/*_flat.sol` and contract bytecode in `contracts/artifacts/*.json`. `hardhat.config.js` uses
   only Hardhat's built-in test accounts. Every tracked Kalshi-derived file (`data/processed/kalshi/`,
   `kalshi_rain/`, `kalshi_rain_probe/`, `results/studyB/`) holds aggregates (counts, means, bins, rule wordings,
   series metadata); no per-market quote or candle rows. `.gitignore` covers `data/raw`, `.env`, `*.env`,
   `node_modules`. `data/processed/panel/iem_cache/` holds NOAA/IEM public data (not Kalshi).
4. **Phase 3 is still running** (docs/status/phase3_temp.md written 21:40 UTC; `results/phase3/` empty;
   `scripts/reach_temp_*.py` named in that log do not exist yet). README step 8 points to the status files rather
   than listing commands that may change.
5. `results/talk/fig3_hedge_effectiveness.png` does not exist yet; README links the Phase 2 figure and names the
   talk path.
6. Archive recommendation (docs/ARCHIVE_NOTE.md): temperature-era docs, notes, `src/{backtest,basis_risk,
   load_weather,local_residual,metrics,station_hedge,weights}`, `src/kalshi/{data,study_b}.py`, the `panel_*`,
   `pull_*`, `part2_rank`, `run_experiment`, `kalshi_{pull,settlement,study_b}` scripts, `sim/experiment_temperature.py`,
   the temperature tests, `data/processed/{aligned_daily.csv,kalshi/}`, `data/manifests/`, `results/{part1,part2,
   part3,studyB,tables,figures,synthetic}` can move. Keep in place: `src/panel/` and `data/processed/panel/`
   (Phase 3 and `p0_rain_parks.py` read them) and the temperature contracts and their tests (`compile.js` and
   `rain_helpers.js` depend on them; `npm test` runs both suites).

## Log

- 2026-11-12 21:55 Read SPEC_v3, PHASE2_PREREG, milestone2_facts, deploy_sepolia, phase2_market, phase2_eval,
  phase2_replication, phase3_temp, PHASE3_PREREG, old README, CONTEXT, SPEC, SPEC_v2, results/phase2/summary.md;
  listed the tree (461 files outside node_modules) and the docstrings of every script and module.
- 2026-11-12 22:00 `npm test` started in the background; `pytest tests -q` 400 passed in 8 s.
- 2026-11-12 22:02 Tracked-file search for secrets and raw rows (finding 3). Parsed `.git/index` read-only.
- 2026-11-12 22:04 `npm test` 162 passing (1 min 35 s). scripts/check_env.py written and run: all present.
- 2026-11-12 22:06 scripts/run_all.sh written; run with `--no-contracts`: exit 0, 140 s; sha256 check of results
  before and after: identical except manifest timestamp.
- 2026-11-12 22:08 Deploy guide read step by step against the ABI (finding 2); `npx hardhat test --no-compile
  test/16_rain_guide.test.js` runs alone in 1 s (used as demo fallback 3).
- 2026-11-12 22:10 README.md rewritten (98 lines). docs/REPO_GUIDE.md, docs/ARCHIVE_NOTE.md, docs/demo_script.md written.
- 2026-11-12 22:15 This log. Status: COMPLETE.
