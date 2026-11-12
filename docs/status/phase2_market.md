# Phase 2 market workstream (Viktor): progress log

Scope: contracts/**, sim/**, tests/test_lmsr_*.py, results/market/**, docs/deploy_sepolia.md, docs/contract_spec.md,
results/rain/loss_vs_kalshi_days.png and scripts/rain_summary.py (chart fix only), this file.
Binding inputs: docs/PHASE2_PREREG.md (strategy 3), docs/SPEC_v3.md, docs/status/phase1_market.md.
Not read, not written: src/hedge_eval, results/phase2, replication/ (the hedge is evaluated by two other people).
Times are UTC from the machine clock. Newest entries at the bottom.

## State (2026-11-12 04:47 UTC): Phase 2 tasks 1-5 done, nothing deployed

- `npm test` in contracts/: **162 passing, 0 failing** (156 before + 6 in test/17_rain_registered.test.js).
- `python -m pytest tests/test_lmsr_*.py -q`: **61 passed** (56 before; the experiment file went from 6 to 11 tests).
- Registered edges **[2, 4, 5, 6, 8]** (buckets 0-2, 3-4, 5, 6, 7-8, 9+). No ties. m_j = 1.75, 3.667, 5, 6, 8, 12. q_j = 0.2368, 0.1842, 0.1316, 0.1842, 0.1316, 0.1316.
- **The deductible d is not known.** Everything is run for d = 2, 3, 4 and labelled. When d is fixed: `python -m sim.experiment --d <d>`, and use that row of the hedge table in docs/deploy_sepolia.md.
- Not tested anywhere: Remix, MetaMask, Sepolia. The guide's Remix details (VALUE resets to 0, At Address, the Remix VM using the real clock) are from memory, marked as untried.

## How to run

```
cd contracts && npm test                    # compiles, runs all tests, rewrites remix/, vectors, gas report
cd .. && python -m sim.experiment           # results/market/ (after npm test, so the gas table is current)
python -m pytest tests/test_lmsr_*.py -q
python scripts/rain_summary.py --figure-only   # results/rain/loss_vs_kalshi_days.png only
```

## Results (SIMULATED unless marked; details in results/market/summary.md)

- Expected payout per unit of hedge size: 3.544 (d = 2), 2.781 (d = 3), 2.079 (d = 4). Registered MODELLED premium = 1.20 times that.
- Uniform start, no impact: the hedge costs 1.16 / 1.18 / 1.20 times its expected payout (d = 2 / 3 / 4), because every bucket opens at 1/6.
- d = 3, hedge of 100 x L, price per 1 of expected payout: uniform start 2.91 (b = 50), 2.10 (200), 1.36 (1,000), 1.21 (5,000), 1.19 (20,000); informed start 2.87, 1.95, 1.17, 1.03, 1.01. Impact at b = 1,000: 15% (uniform), 17% (informed). Sponsor bound b ln 6: 90, 358, 1,792, 8,959, 35,835.
- The LMSR price equals the registered 1.20 at b = 7.8 / 8.5 / 9.5 times the hedge size (informed start, d = 2 / 3 / 4); deeper markets are cheaper than 1.20.
- Sponsor's expected loss to the informed trader: 0.0268 x b (KL of q from uniform). Break-even fee on all trades: never above 11.3% of trade cost; 0% while b is below about 12 to 14 times the hedge size (the hedger's impact pays), where the hedger pays 1.11 to 1.15 with no fee. At b = 5,000 and a hedge of 100: 8.0% to 9.1% on all trades, or 34% to 59% on the hedger alone (all-in 1.38 to 1.64, above 1.20).
- One hedger per market, a made-up informed trader, a fee that changes nobody's behaviour: all assumptions, all stated in the summary.
- Gas, LOCAL EVM: the registered basket [0,2,6,9,15,27] as first trade 354,120; deploy market 3,776,901.
- Chart results/rain/loss_vs_kalshi_days.png, OBSERVED: 34.5 Kalshi-pay days against 5.4 loss days per season (28 seasons), 84% of pay days are not loss days, 100% of loss days are pay days. Phase 1 chart (hourly sum): 36.4.

## Open items

1. d: wait for the evaluation workstream, then re-run as above and drop the two unused rows from the guide.
2. Remix and Sepolia rehearsal by a student.
3. docs/status/phase1_market.md still describes the example edges and the old guide numbers. It is outside this phase's file list and was left as the Phase 1 record.
4. results/rain/summary_main.md and summary_by_case.csv still present the hourly-sum flag as the main one. They belong to the rain workstream; only the chart was redrawn.
5. A quantile rule that interpolates differently (numpy "weibull") gives 8.67 for the last edge. Rounded up that would be 9, not 8. No training season has 9 loss days, so m_j and q_j would not change, but a report season with exactly 9 would move bucket. Recorded in summary.md; the registered edges use the plain empirical quantile.

## Log

- 2026-11-12 04:30 Started. Read PHASE2_PREREG, SPEC_v3, phase1_market.md, sim/experiment.py, the deploy guide, test 16, phase0_kalshi.md. contracts/node_modules is present.
- 2026-11-12 04:34 Task 1. Registered edges computed from data/processed/rain/season_counts_TTN.csv (all_days, usable, 1999-2014, loss_days): sorted counts 1,2,2,2,3,4,4,5,5,6,6,6,8,8,12,12; quantiles 1/6..5/6 = 2,4,5,6,8 by the inverted empirical CDF and also by linear interpolation. Edges [2,4,5,6,8], buckets 0-2, 3-4, 5, 6, 7-8, 9+. No ties: six distinct buckets, nothing merged. n_j = 4,3,2,3,2,2; m_j = 1.75, 3.667, 5, 6, 8, 12; q_j = 0.2368, 0.1842, 0.1316, 0.1842, 0.1316, 0.1316. New helpers in sim/lmsr.py (registered_edges, bucket_means, registered_holdings). Written to results/market/registered_buckets.csv.
- 2026-11-12 04:37 Task 2. sim/experiment.py rewritten for the registered product: d = 2, 3, 4 (d not chosen yet, labelled), b = 50..20,000, sizes 10/100/1,000 x L, uniform and informed starts, comparison with the registered premium 1.20, hypothetical break-even fee. Figure opened twice: reference-line labels collided with markers, moved into the legend; legend was clipped, labels shortened; third render is clean. tests/test_lmsr_rain_experiment.py rewritten (11 tests).
- 2026-11-12 04:40 Task 3. contracts/RainCountLMSR.sol: comment only (the registered edges added to the header), so the flattened Remix files and the bytecode metadata changed; logic unchanged. New contracts/test/17_rain_registered.test.js (6 tests): data file gives the registered edges; bucketOf for every count 0..102; for d = 2, 3, 4 deploy, fund exactly b ln 6 (one wei less refused), buy the stepped basket 3 x max(m_j - d, 0), report the real 2025 Trenton count (5), settle, redeem, sponsor withdraw; a hedge of 10 x L with unit L/12 settled on every real REPORT season 2015-2026. Test 16 (guide rehearsal) moved to the registered edges and the 2025 count. `npm test`: 162 passing. Remix files regenerated by the same run.
- 2026-11-12 04:42 Task 4a. scripts/rain_summary.py: figure() now uses ref_ghcn_pay_days (official daily total); new flag --figure-only so the tables (rain workstream) are not rewritten. Chart redrawn and opened: mean 34.5 Kalshi-pay days against 5.4 loss days (about 6 times), 84% of pay days are not loss days, Kalshi pays on 100% of loss days. The Phase 1 chart (hourly sum) showed a mean of 36.4. Value labels got a white backing so the mean line does not cross them. tests/test_rain_*.py still 138 passed.
- 2026-11-12 04:45 Task 3 and 5. docs/deploy_sepolia.md rewritten: registered edges, d = 3 hedge [0,2,6,9,15,27] (rows for d = 2 and 4), replay of the real 2025 Trenton count (5), expected value after every step. Read as a student; fixed: T was needed before the oracle existed (now: deploy, read currentTime, fill a times table with a worked example); how to switch accounts and check the ACCOUNT field, also in the Remix VM; At Address after a reload; how to type lists and text; VALUE left over or left at 0; maxCost given as a number instead of "quote + 2%"; funding table for other b (requiredFundingFor can not be called before deployment); which account settles; where to see the redeemed amount; the 30-minute report window; four more error messages. Test 16 extended to assert the new numbers. Gas test 15 measures the guide's basket (22 rows).
- 2026-11-12 04:46 Task 4b. docs/contract_spec.md rewritten: A rain-count contract, B Kalshi daily rain contract (rules from phase0_kalshi.md), C side by side; the temperature text kept unchanged under "Earlier temperature study" with headings one level down.
- 2026-11-12 04:47 Final runs: `npm test` 162 passing; `python -m sim.experiment`; pytest tests/test_lmsr_*.py 61 passed; tests/test_rain_*.py 138 passed.
