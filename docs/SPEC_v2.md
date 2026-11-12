# Shared spec v2 (frozen 2026-11-11 UTC)

Supersedes docs/SPEC.md. Change only by editing this file and adding a dated line under "Changes".
Plan: "ECE 473 project plan: which weather market to list next". Review notes: docs/notes/.

## Definitions
- Season: May 1 to Sep 30. Years 2015-2025. Temperatures: daily TMAX, whole deg F.
- Heat event at location i, day t: H(i,t) = 1 if TMAX_i,t >= 90, else 0. Sensitivity (stretch only): 88, 92.
- Contract on station s with strike k: P = 1 if TMAX_s,t >= k. k is an integer, 80..100. Unit payout $1.
- Payout mismatch R = mean over days with both values present of 1{H != P}. Always also report:
  FN = share of days with H=1, P=0; FP = share with H=0, P=1; miss rate = FN days / hot days;
  false-payout rate = FP days / payout days.
- Windows: FIT 2015-2019, SELECT 2020-2022, REPORT 2023-2025. Nothing fitted on SELECT or REPORT.
- Baseline hedge for location i under listed set L: nearest station in L (haversine), k = 90.
- Adjusted hedge: the single (station in L, strike k) with the lowest FIT mismatch; ties go to k closest to 90, then nearest station.
- Uncertainty: bootstrap whole summers (years) jointly across all stations, 1,000 draws, seed 473.

## Stations
- Listed sets (GHCN ids): NYC Central Park USW00094728, Philadelphia Intl USW00013739 (station INFERRED, flag it),
  Newark USW00014734, Trenton-Mercer USW00014792.
  L_pre = {NYC, Philadelphia} (before 2026-08-26). L_now = all four.
- Exposure locations: airport-grade stations (id starts USW) with >= 90% season coverage overall and >= 80% in each window.
  Cooperative (USC) stations are excluded from main results (observation-time problem). Sensitivity only.
- Candidate new markets: exposure locations that have an NWS daily climate report (CLI) and are not in the listed set.
- Raw data: data/raw/region/ (334 stations, pulled 2026-11-11 from NCEI). Coverage: data/manifests/region_coverage.csv.

## Part 2 objective
s* = argmax over candidates s of SUM_i w_i [ R_L(i) - R_{L+s}(i) ], hedges = adjusted hedge as defined above.
Rank on SELECT. Report the winner on REPORT. Run for L_pre (does it pick Newark or Trenton?) and L_now (what next?).
Weights w_i: Census 2023 ZIP Business Patterns establishments, NAICS 722 + 713, each ZIP assigned to its nearest
exposure location. Until the Census key arrives: unweighted (w_i = 1), clearly labeled.

## Study B (real markets only)
- Only days where the market, the needed brackets and a quote existed. NYC summers 2023-2025; Philadelphia from 2024-11-20.
- Decision time: 24 h before market close. Price = yes_ask at that time (most recent hourly candle, at most 6 h stale).
- Fees: taker fee = ceil-to-cent(0.07 * C * P * (1 - P)). Costs are top-of-book estimates for small orders.
- Never publish raw Kalshi rows. Aggregates and figures only.

## Part 3 (LMSR bracket market)
- Exhaustive, non-overlapping temperature brackets with a boundary at 90. Atomic "buy all brackets >= 90" basket.
- LMSR cost C(q) = b * ln(sum_j exp(q_j / b)). Sponsor worst-case loss b * ln(n).
- Oracle: authorised reporter, one-time settlement, late/missing/stale report handling, emergency cancel with refunds,
  withdrawal after settlement. All paths tested with a mock oracle before any testnet deploy.
- Experiment: baskets of 10, 100, 1,000 payout units; several b. Report price paid, price impact, gas, sponsor P&L.

## Integrity rules
- Never invent data. Every number comes from a file produced by code in this repo or a cited source.
- Label simulated vs observed everywhere. No real-money trades. Testnet only. No private keys in the repo or in chat.
- Each workstream keeps a progress log in docs/status/<name>.md: dated lines, what was done, what is blocked, numbers found.

## File ownership
- Qasim workstream: src/panel/**, scripts/panel_*.py, tests/test_panel_*.py, data/processed/panel/**, results/part1/**, docs/status/qasim.md
- Ehfaz workstream: src/kalshi/**, src/weights/**, scripts/kalshi_*.py, scripts/census_*.py, tests/test_kalshi_*.py, tests/test_weights_*.py,
  data/raw/kalshi/** (git-ignored, never published), data/processed/kalshi/**, results/studyB/**, docs/status/ehfaz.md
- Viktor workstream: contracts/**, sim/**, tests/test_lmsr_*.py, results/part3/**, docs/status/viktor.md, docs/deploy_sepolia.md
- Do not edit another workstream's files or the old src/*.py modules. Import from them if useful.

## Changes
- 2026-11-11: created.
