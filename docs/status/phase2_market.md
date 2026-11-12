# Phase 2 market workstream (Viktor): progress log

Scope: contracts/**, sim/**, tests/test_lmsr_*.py, results/market/**, docs/deploy_sepolia.md, docs/contract_spec.md,
results/rain/loss_vs_kalshi_days.png and scripts/rain_summary.py (chart fix only), this file.
Binding inputs: docs/PHASE2_PREREG.md (strategy 3), docs/SPEC_v3.md, docs/status/phase1_market.md.
Not read, not written: src/hedge_eval, results/phase2, replication/ (the hedge is evaluated by two other people).
Times are UTC from the machine clock. Newest entries at the bottom.

## Log

- 2026-11-12 04:30 Started. Read PHASE2_PREREG, SPEC_v3, phase1_market.md, sim/experiment.py, the deploy guide, test 16, phase0_kalshi.md. contracts/node_modules is present.
- 2026-11-12 04:50 Task 1. Registered edges computed from data/processed/rain/season_counts_TTN.csv (all_days, usable, 1999-2014, loss_days): sorted counts 1,2,2,2,3,4,4,5,5,6,6,6,8,8,12,12; quantiles 1/6..5/6 = 2,4,5,6,8 by the inverted empirical CDF and also by linear interpolation. Edges [2,4,5,6,8], buckets 0-2, 3-4, 5, 6, 7-8, 9+. No ties: six distinct buckets, nothing merged. n_j = 4,3,2,3,2,2; m_j = 1.75, 3.667, 5, 6, 8, 12; q_j = 0.2368, 0.1842, 0.1316, 0.1842, 0.1316, 0.1316. New helpers in sim/lmsr.py (registered_edges, bucket_means, registered_holdings). Written to results/market/registered_buckets.csv.
- 2026-11-12 04:58 Task 2. sim/experiment.py rewritten for the registered product: d = 2, 3, 4 (d not chosen yet, labelled), b = 50..20,000, sizes 10/100/1,000 x L, uniform and informed starts, comparison with the registered premium 1.20, hypothetical break-even fee. Figure opened twice: reference-line labels collided with markers, moved into the legend; legend was clipped, labels shortened; third render is clean. tests/test_lmsr_rain_experiment.py rewritten (11 tests).
