# Phase 4: figures and findings workstream (log, UTC)

Scope (written only): results/talk/**, docs/FINDINGS.md, this file. Nothing else touched. No git commands run.

## How to rerun
`python results/talk/make_figures.py` from the repository root. Writes results/talk/fig1..fig8.png (1920x1080, 16:9) and results/talk/figure_numbers.csv (every number printed on a figure, with its source file). Reads only data/processed and results; never data/raw. Figures 6 and 7 are drawn from results/phase3 when the files exist and are placeholders otherwise (see below).

## Log
- 2026-11-12 21:55 Read PHASE2_PREREG, results/phase2/summary.md, results/rain/summary_main.md, phase1_kalshi.md, results/market/summary.md, phase2_market.md, milestone2_facts.md, PHASE3_PREREG.md, phase3_temp.md, phase2_replication.md. results/phase3/ is empty; docs/status/phase3_temp.md records reading choices only (fixed 21:40 UTC), no results.
- 2026-11-12 22:00 Loaded the dataviz skill. Palette: its reference categorical slots 1-4 (blue, orange, aqua, yellow) on the light surface #fcfcfb; validated with scripts/validate_palette.js (all checks pass; aqua and yellow carry a contrast warning, met with direct value labels on every figure). Status red is used only for the failed registered case and the placeholders. Type: titles 30 pt bold stating the finding, subtitles 20 pt, ticks 19 pt, footnote 15 pt with the observed/modelled/simulated label and the source file.
- 2026-11-12 22:05 Checked "two implementations agree on 120 numbers" (milestone2_facts.md) against the files: replication/results.csv vs results/phase2/metrics_tidy.csv (variant main). 300 of 300 shared numbers (cases A, B1, D-same, D-same-ex4147, D-PNE; strategies 0-5; metrics HE, mean net cost, total premium, mean payout, SD; TRAIN and REPORT) agree to 2e-13. The 120 are the registered cases A, B1, D-same with strategies 2-5. Strategy 5n1 in the replication has no counterpart in metrics_tidy and was left out.
- 2026-11-12 22:10 Wrote results/talk/make_figures.py; eight renders. Each figure opened and checked at slide size; fixed in turn: subtitles and footnotes overflowing the right edge (wrapping added), a note row colliding with the footnote, fig3 legend over the subtitle, fig5 labels over the curve, fig8 box text overflowing. Final pass: all eight legible, no clipped text.
- 2026-11-12 22:12 Smoke-tested the fig6/fig7 code against synthetic CSVs in the scratchpad (flexible column lookup: distance/bin, he, lo, hi, case). Both render; synthetic files deleted.
- 2026-11-12 22:15 Wrote docs/FINDINGS.md.

## Figure status
| File | Status | Note |
|---|---|---|
| fig1_wrong_days.png | complete | Trenton 1999-2026, GHCN pay days vs loss days; 34.5 vs 5.4, ratio 6.4 |
| fig2_forecast_in_price.png | complete | drawn from binned aggregates only (calibration.csv, ask, 24 h); counts per bin split by yes_share; means by outcome from model_eval.csv held-out set C |
| fig3_hedge_effectiveness.png | complete | restyled version of results/phase2/fig_hedge_effectiveness.png; strategies 2-5, cases A, B1, D-same, D-PNE; B1 marked FAILED; A's lower tail to -1.16 drawn |
| fig4_net_cost_philadelphia.png | complete | D-same REPORT seasons, strategies 0, 2, 3 |
| fig5_market_price.png | complete | d = 3, x = b / hedge size (the simulation depends only on that ratio); uniform vs informed |
| fig6_reach.png | PLACEHOLDER | results/phase3/*reach_curve.csv absent; code in place |
| fig7_leadtime.png | PLACEHOLDER | results/phase3/leadtime_he_by_lead.csv absent; code in place |
| fig8_method.png | complete | diagram, no implementation detail |

## Doubts to pass on
- Fig 2 mixes two sources on purpose: the histogram is all 403 two-sided days (2021-2026, old and new trace rules), the 0.75 / 0.23 means are from the held-out 2026 set C (209 days); the bins themselves give 0.77 / 0.26. Both are printed on the slide.
- Fig 4's "two-thirds" is the HE (downside semi-variance removed), not the cut in mean or worst-season cost; FINDINGS.md says so.
- Fig 5 shows d = 3; the market experiment was run for d = 2, 3, 4 because the evaluation chose d per case (3 for A and D-same, 8 for B1).
- Fig 6/7 column names are guesses until Phase 3 writes its files; `_col()` in the script matches common names and prints a message if it cannot find distance or HE columns.
