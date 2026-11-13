# Combined reach: rain and temperature (Phase 3, Question 1) - EXPLORATORY

Note: exploratory; observed weather, modelled prices. Reach = the largest 10 km bin whose lower 95% band edge is above 0 (registered definition), recomputed here from each curve file with one rule.

## Reach side by side
| hazard | pairs | pairs with HE | reach, pairs resampled | reach, gauges resampled | same-station bin mean HE [pair band] |
|---|---|---|---|---|---|
| rain | 926 | 916 | 0 km | 0 km | 0.82 [0.65, 0.92] |
| temperature | 992 | 951 | none | none | -0.92 [-2.62, 0.34] |

## Do the curves separate?
- Bins where both hazards have a band: 21. Bins where the rain band lies wholly above the temperature band: 19 [0, 10, 20, 40, 50, 60, 70, 80, 90, 110, 120, 130, 140, 150, 160, 170, 180, 190, 200]. Bins where the temperature band lies wholly above the rain band: 0 [].
- The curves separate in the bins listed; elsewhere the bands overlap.

## Pre-registered hypothesis: rain reach is shorter than temperature reach - **NOT SUPPORTED**
- The two reaches are equal.
- Temperature: no bin, including the same-station bin, has a lower band edge above 0 under either bootstrap (results/phase3/temp_reach_summary.md explains why: the registered d grid {0..8} is far below the 20-40 hot days a season at the warm stations).

## Caveats
- Rain and temperature pairs have different histories (rain pairs use up to several decades of seasons, temperature pairs 11 seasons, 5 of them REPORT), so a band width is not comparable across hazards.
- HE is unbounded below; bin means are pulled by pairs whose REPORT seasons barely exceed the TRAIN reference. Medians are shown as a labelled extra.
- The bands resample pairs or gauges, not seasons; all pairs of a hazard share seasons.
