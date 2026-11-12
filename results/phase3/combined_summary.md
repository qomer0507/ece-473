# Combined reach: rain and temperature (Phase 3, Question 1) - EXPLORATORY

Note: exploratory; observed weather, modelled prices. Reach = the largest 10 km bin whose lower 95% band edge is above 0 (registered definition), recomputed here from each curve file with one rule.

## Reach side by side
| hazard | pairs | pairs with HE | reach, pairs resampled | reach, gauges resampled | same-station bin mean HE [pair band] |
|---|---|---|---|---|---|
| rain | not available yet | | | | |
| temperature | 992 | 951 | none | none | -0.92 [-2.62, 0.34] |

## Do the curves separate?
- Not testable yet: the rain curve file is missing. Rerun `python scripts/reach_combined.py` once data/processed/reach/rain_pairs.csv and results/phase3/rain_reach_curve.csv exist.

## Pre-registered hypothesis: rain reach is shorter than temperature reach - **UNRESOLVED**
- The rain curve is not available yet, so the hypothesis cannot be tested.
- Temperature: no bin, including the same-station bin, has a lower band edge above 0 under either bootstrap (results/phase3/temp_reach_summary.md explains why: the registered d grid {0..8} is far below the 20-40 hot days a season at the warm stations).

## Caveats
- Rain and temperature pairs have different histories (rain pairs use up to several decades of seasons, temperature pairs 11 seasons, 5 of them REPORT), so a band width is not comparable across hazards.
- HE is unbounded below; bin means are pulled by pairs whose REPORT seasons barely exceed the TRAIN reference. Medians are shown as a labelled extra.
- The bands resample pairs or gauges, not seasons; all pairs of a hazard share seasons.
