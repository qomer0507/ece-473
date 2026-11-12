# Part 2 pre-registration (written 2026-11-11 UTC, before the first ranking run)

Follows docs/SPEC_v2.md. Written before any candidate ranking was computed.

- Exposure locations: the 84 airport-grade stations flagged is_exposure in data/processed/panel/stations.csv.
- Candidates: exposure locations with an NWS daily climate report (has_cli), not in the listed set.
  For L_pre the candidates also include Newark and Trenton.
- Hedge available to a location under a listed set: the adjusted hedge (lowest FIT mismatch over station in set, strike 80..100).
- Score of candidate s: SUM_i w_i [R_L(i) - R_{L+s}(i)] on SELECT (2020-2022), over all 84 exposure locations, including s itself.
  Also reported: the same sum excluding s itself, so a station is not ranked high only for covering itself.
- Weights: w_i = 1 for this run (no Census key yet). Labeled "unweighted". The weighted run repeats this unchanged.
- Winner = top SELECT score. Its gain is then reported on REPORT (2023-2025). No re-ranking on REPORT.
- Uncertainty: year-block bootstrap, 1,000 draws, seed 473, on the SELECT scores and on the REPORT gain.
- Check: under L_pre, where do Newark and Trenton rank? Two data points; a check, not proof.
- Greedy extension: after adding the winner, repeat to get the next two picks.
