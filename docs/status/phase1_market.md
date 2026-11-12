# Phase 1 market workstream (Viktor): progress log

Scope: contracts/**, sim/**, tests/test_lmsr_*.py, results/market/**, docs/deploy_sepolia.md, this file.
Binding inputs: docs/SPEC_v3.md ("Market (LMSR)") and docs/status/phase0_contract.md (review, M1-M3, m1-m12).
Times are UTC, taken from the machine clock and file timestamps. Newest entries at the bottom.
If you take over: read "State", "Design decisions" and "Open items", then the last log lines.

## State (2026-11-12 04:12 UTC): DONE for Phase 1, nothing deployed

- `npm test` in contracts/: **156 passing, 0 failing, 0 pending** (65 earlier temperature tests + 91 rain tests), about 1 minute.
- `python -m pytest tests/test_lmsr_*.py -q`: **56 passed** (29 earlier + 27 new).
- `npx hardhat test --no-compile test/15_rain_gas.test.js` alone: 2 passing.
- Not tested anywhere: Remix, MetaMask, Sepolia. No RPC from this machine. The deploy guide is a script, not a record.

## How to run

```
cd contracts && npm ci && npm test          # compiles with solc-js, runs all tests, writes remix/, vectors, gas report
cd .. && python -m sim.make_vectors         # only if sim/lmsr.py changed: rewrites the reference vectors
python -m sim.experiment                    # results/market/
python -m pytest tests/test_lmsr_*.py -q
```

Order matters after a contract change: `npm test` first (it rewrites contracts/test/vectors/rain_contract_quotes.json),
then pytest. The rain cross-check fails, not skips, if that file is missing or stale (sha256 of RainCountLMSR.sol).

## Files written

| file | what |
|---|---|
| contracts/RainCountLMSR.sol | new market: six count buckets, uniform start, vector buy |
| contracts/SeasonCountOracle.sol | new oracle: one report per (station, season), refused before the season end |
| contracts/MockCountOracle.sol | test oracle with seven modes (normal, revert, empty, short, long, garbage, gas burner) |
| contracts/mocks/RainTestHelpers.sol | EmptyFallbackOracle, OneWordOracle (review M1 cases) |
| contracts/scripts/compile.js | builds old and new contracts; maps `@openzeppelin/contracts@4.9.6/` to node_modules; flattens four files |
| contracts/remix/RainCountLMSR_flat.sol, SeasonCountOracle_flat.sol | generated, no imports; same bytecode size as the source build |
| contracts/test/rain_helpers.js, 11_rain_math, 12_rain_market, 13_rain_oracle, 14_rain_property, 15_rain_gas, 16_rain_guide | rain tests (6 + 25 + 47 + 9 + 2 + 2 = 91) |
| contracts/test/99_gas.test.js | changed: the temperature gas report skips when run alone |
| contracts/test/vectors/reference_rain.json, rain_contract_quotes.json | generated |
| sim/lmsr.py | extended: count buckets, vector quotes, funding helper, CountMarket, `python -m sim.lmsr funding` |
| sim/make_vectors.py | also writes reference_rain.json |
| sim/experiment.py | NOW the rain-count experiment |
| sim/experiment_temperature.py | the earlier temperature experiment, moved unchanged (results/part3) |
| tests/test_lmsr_rain_reference.py, test_lmsr_rain_crosscheck.py, test_lmsr_rain_experiment.py | new (13 + 8 + 6 = 27) |
| tests/test_lmsr_experiment.py | import changed to sim.experiment_temperature |
| results/market/ | hedge_pricing.csv, distribution.csv, stepped_hedge_price.png, summary.md, manifest.json, gas_report.json |
| docs/deploy_sepolia.md | student guide and demo outline |

Untouched: contracts/BracketLMSR.sol, TemperatureOracle.sol, MockOracle.sol, mocks/TestHelpers.sol, tests 01-04.

## Design decisions

- **Adapt, keep the old version.** The temperature contract and its 65 tests stay and still pass. The M1 reproduction test runs against it.
- **Buckets.** Exactly six. Five inclusive upper edges in the constructor (`[2,4,6,8,10]` gives 0-2, 3-4, 5-6, 7-8, 9-10, 11+). Nothing hard-coded. The last edge must be below the season days.
- **Uniform start only.** No seed. C(0) = b ln 6 is the required funding and the sponsor's worst-case loss. `requiredFundingFor(b, unit)` is public and pure.
- **One trade path.** `buy` builds a one-bucket vector and calls the same internal function as `buyBasket`. The charge is C(q_new) - costNow, so a basket equals its legs to the wei.
- **The season lives in the oracle.** The oracle owner opens a season (start, end, days) once. The market reads it in the constructor and copies start, end and days. So the report window of the oracle and the market can not disagree (fixes M3 for good, and m8).
- **M1.** Constructor: `_oracle.code.length > 0`, then one trial read that must be well formed and show an opened, unreported season. Every read is a low-level `staticcall` with a 100,000 gas cap; the answer must be exactly 7 words and every word in range, else it counts as "no valid report". `require(gasleft() >= 130,000)` before the read, so a caller can not starve a good oracle of gas to force a cancel (tested for every gas limit from 30,000 to 300,000).
- **M2 (disclosed).** Contract header, oracle header and the guide say: one reporter decides; sponsor and oracle must be different accounts; the contract can not enforce it. Added `disputeDelay` (0 to 30 days) between report and settle, and `voidReport` (oracle owner only, final). A voided report makes the market refund after the deadline. Without a void the wrong report settles; a test shows that on purpose.
- **m1.** `tradingClose <= seasonStart` is enforced. emergencyCancel only before tradingClose.
- **m2.** `unit >= 1 gwei`. A buy whose cost rounds to 0 wei is refused ("Cost rounds to zero"), so nobody gets free shares. Side effect: a bucket more than 45 b behind the leader can only be bought in an amount large enough to have a real cost.
- **m5.** `claimPeriod` (7 to 3650 days). After settle or cancel + claimPeriod the sponsor may `sweepUnclaimed()`. Claims work until the sweep happens.
- **m6.** `requiredFundingFor` view, formula in the guide, `python -m sim.lmsr funding`. Excess funding returns with sponsorWithdraw.
- **m7.** Count is unsigned and must be <= season days, in the oracle and again in the market.
- **m10.** No reference to missing files. OpenZeppelin import pinned: `@openzeppelin/contracts@4.9.6/security/ReentrancyGuard.sol` (as Lab 13). Comments say what is not guaranteed.
- **m11.** Each quantity is checked against 1e15 before adding: "Quantity too large", no panic.

## Minor items NOT fixed, and why

- **m3 (buy only).** No sell function. Same as Lab 7; selling needs a second rounding direction and more tests. Disclosed in the header and the guide.
- **m4.** Not applicable any more: the seed was removed.
- **m9 (any reporter can report any key; no ownership transfer).** Left. Fine for a one-student oracle; the owner can remove a reporter. Disclosed here.
- **m12 (licence header of the flattened file).** Left. Cosmetic; the BSD notice of ABDK is kept in the file.
- **Sponsor = reporter is not blocked on chain.** A check on addresses would be trivial to get around with a second account, so it would overstate the guarantee. Disclosed instead.
- **The oracle owner is also the first reporter.** Kept so that the demo needs three accounts. The dispute window is real only if the owner gives reporting to another account.
- **The pytest cross-check still reads a snapshot.** It does not start the EVM. It now fails if the snapshot is stale.

## Results (all from the local Hardhat EVM or from simulation)

Gas, local EVM, not Sepolia (results/market/gas_report.json):
deploy market 3,776,889; deploy oracle 840,559; openSeason 49,167; buy one bucket 179,507 first / 111,451 repeat;
stepped basket 268,264 as the first trade of a fresh market, 199,332-233,832 for later first-time buyers, 117,196-131,436 repeat;
the same position by three single buys 471,341; reportCount 56,241; settle 159,975; redeem 44,585; sponsorWithdraw 36,444;
cancelAfterDeadline 106,570; emergencyCancel 95,391; claimRefund 39,539; sweepUnclaimed 39,805; voidReport 31,012.
Deployed size: market 15,884 bytes, oracle 3,532 bytes (limit 24,576).

Experiment, SIMULATED (results/market/summary.md). Distribution: OBSERVED Trenton counts, 16 usable training seasons
1999-2014 (2, 6, 6, 4, 8, 5, 5, 8, 2, 4, 12, 2, 1, 6, 12, 3), add-0.5 smoothing, EXAMPLE edges [2,4,6,8,10].
Stepped hedge of size s = s, 2s, 3s shares of buckets 7-8, 9-10, 11+. Expected payout 0.579 per unit of size.

| start | b | sponsor bound b ln 6 | price per 1 of expected payout at s = 10 / 100 / 1,000 | impact at s = 10 / 100 / 1,000 |
|---|---|---|---|---|
| uniform | 50 | 89.6 | 1.97 / 3.76 / 5.03 | 14% / 118% / 191% |
| uniform | 200 | 358.4 | 1.79 / 2.35 / 4.57 | 3.4% / 36% / 164% |
| uniform | 1,000 | 1,791.8 | 1.74 / 1.85 / 2.96 | 0.7% / 6.8% / 71% |
| uniform | 5,000 | 8,958.8 | 1.73 / 1.75 / 1.97 | 0.1% / 1.3% / 14% |
| informed | 50 | 89.6 | 1.21 / 3.48 / 5.01 | 21% / 248% / 401% |
| informed | 200 | 358.4 | 1.05 / 1.60 / 4.48 | 4.8% / 60% / 348% |
| informed | 1,000 | 1,791.8 | 1.01 / 1.10 / 2.35 | 0.9% / 9.9% / 135% |
| informed | 5,000 | 8,958.8 | 1.00 / 1.02 / 1.21 | 0.2% / 1.9% / 21% |

Reading: at the uniform start the hedge costs at least 1.73 times its expected payout even in a deep market, because the three
top buckets open at 1/6 each. After informed trading a hedge of 100 needs b of about 1,000 (sponsor bound about 1,800 units) to
stay within 10% of fair value.

## Open items for whoever continues

1. **Final bucket edges.** The experiment and the guide use example edges. When the rain workstream fixes the edges, run
   `python -m sim.experiment --edges a b c d e` and update the example in docs/deploy_sepolia.md.
2. **Counts file may change.** data/processed/rain/season_counts_TTN.csv belongs to the rain workstream. Re-run the experiment after it changes
   (the summary lists the counts it used). `--placeholder` gives the labelled placeholder run instead.
3. **Remix and Sepolia rehearsal** by a student, following docs/deploy_sepolia.md. Things most likely to differ: the Remix gas-limit
   field, MetaMask's warning text for a refused report, timing of the 15-minute demo window.
4. docs/contract_spec.md describes the temperature contract. It is outside this workstream's file list and was not updated.

## Log

- 2026-11-12 03:45 Started. Read SPEC_v3, phase0_contract.md, the existing contract, tests, sim and pytest files. `npm ci` in contracts/ (node_modules was missing).
- 2026-11-12 03:50 contracts/SeasonCountOracle.sol, MockCountOracle.sol, RainCountLMSR.sol, mocks/RainTestHelpers.sol written; compile.js extended. Compiles with solc-js 0.8.26, optimizer 200, no warnings.
- 2026-11-12 03:52 sim/lmsr.py extended; sim/make_vectors.py writes reference_rain.json. Funding for b = 100, unit = 1e14 is 17,917,594,692,280,550 wei, the review's number. Old 29 pytest tests still pass.
- 2026-11-12 03:57 Tests 11, 12, 13 written. Two test mistakes of mine fixed (same-second block, season times). One real finding: with the "cost rounds to zero" rule, small buys of a bucket more than 45 b behind are refused; tests now assert that.
- 2026-11-12 04:00 Tests 14 (property, cancel solvency, extremes, cross-check file) and 15 (gas) written. Finding: at b = 1e12 and unit = 1 gwei a one-share quote is off by 14 wei (fixed-point step is 54 wei there); the test now uses the documented tolerance. The gas comparison "one basket vs three single buys" runs in fresh markets.
- 2026-11-12 04:02 `npm test`: 154 passing. 99_gas (temperature) made to skip when run alone.
- 2026-11-12 04:04 Found data/processed/rain/season_counts_TTN.csv. sim/experiment.py rewritten for the rain-count market and run on the observed training counts; temperature experiment moved to sim/experiment_temperature.py. Figure opened and checked; the "fair value" label overlapped a marker, moved below the line, checked again.
- 2026-11-12 04:05 Three new pytest files. 56 passed.
- 2026-11-12 04:08 docs/deploy_sepolia.md written. test/16_rain_guide.test.js rehearses the guide's steps and numbers in the local EVM (quote 1,068,243,163,504,235 wei, payout 0.002 ETH, sponsor gets back about 0.017068 ETH).
- 2026-11-12 04:10 Final runs: `npm test` 156 passing; 15_rain_gas alone 2 passing; experiment re-run; pytest 56 passed.
