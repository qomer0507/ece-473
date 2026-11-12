"""Phase 3, Question 1, temperature part (docs/PHASE3_PREREG.md). EXPLORATORY.

Modules
  pairs     pair construction (S with a climate report, G any exposure station, <= 200 km), joint usable seasons,
            seasonal counts, daily trigger agreement, count correlation
  contract  the exact seasonal count contract (Phase 2 strategy 4) fitted on TRAIN, HE on REPORT
  curve     distance bins, bootstrap by pair and by gauge, reach
  regress   OLS of HE on distance, elevation difference and a coast indicator

Weather (TMAX) is observed. Every premium is modelled. Nothing here reads files; the scripts do.
"""
