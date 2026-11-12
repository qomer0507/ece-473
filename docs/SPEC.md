# Shared spec (frozen 2026-10-30 UTC for Milestone I)

All three workstreams use these defaults. Change them only by editing this file and logging the change in docs/notes/CHANGELOG.md.

## Question
Does adding a local residual layer to a station-settled temperature contract reduce local payout mismatch enough to justify its extra cost?

## Exposure (primary)
- Variable: daily maximum temperature (TMAX), °F, local standard time day as reported by NWS/GHCN-D.
- Event: heat day, TMAX >= 90°F. Sensitivity thresholds: 85, 95.
- Season: May 1 – Sep 30.
- Period: 2015-05-01 to 2025-09-30 (data permitting). Train = 2015–2021, test = 2022–2025.
- Notional: $800 per event day (illustrative, not a customer figure).

## Locations
- NYC reference station: Central Park (KNYC, GHCN USW00094728). Kalshi's NYC high-temp market is believed to reference this station; Ehfaz workstream verifies.
- Trenton reference station: Trenton-Mercer Airport (KTTN, GHCN USW00014792). Whether any exchange contract settles here is an open question for the Ehfaz workstream.
- "Local" business points: other real stations near each reference (Qasim workstream picks and justifies, with distance). Using real thermometers avoids the PRISM-smoothing problem; PRISM is an optional robustness check.

## Strategies
- A, station-only: pays N * 1{station TMAX >= k}.
- B, two-part: A plus residual R = max(target − A, 0), target = N * 1{local TMAX >= k}.
- Note: B has zero shortfall by construction. The result that matters is cost: residual premium = expected residual payout * (1 + loading), loading swept 0–100%. Report break-even loading and overhedge (A pays, local does not).

## Metrics
trigger mismatch rate (both directions), mean shortfall, mean overhedge, mean absolute payout error, premium paid, net cost per $ of target payout.

## Integrity rules
- Never invent data. Every number must come from a file in data/ or results/ produced by code in this repo, or from a cited web source.
- Label observed vs. assumed prices.
- Prior Ceraunic results are background only, not ECE 473 results.
- No trading, no accounts, no paid data.

## File ownership
- Ehfaz: docs/notes/ehfaz_*.md, docs/literature.md, docs/contract_spec.md, src/station_hedge.py, tests/test_contracts.py
- Qasim: docs/notes/qasim_*.md, docs/data_dictionary.md, src/load_weather.py, src/basis_risk.py, scripts/pull_*.py, data/**, tests/test_alignment.py
- Viktor: docs/notes/viktor_*.md, src/local_residual.py, src/metrics.py, src/backtest.py, scripts/run_experiment.py, tests/test_residual.py, results/**
