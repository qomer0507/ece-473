"""Phase 2 hedge evaluation library. Implements docs/PHASE2_PREREG.md.

Modules
  data        load the daily rain tables; joint usable-day alignment of a settlement station and a park gauge
  strategies  TRAIN-only parameter choice (n, bucket edges, m_j, d, h_j, q_j, premium, monthly p) and the
              per-season payout / premium / net cost of strategies 0-5
  metrics     hedge effectiveness with a fixed TRAIN reference level and the secondary metrics
  bootstrap   whole-season bootstrap (2,000 draws, seed 473), paired across strategies
  cases       the registered cases A, B1, B2, C, D, E and the runner

Weather inputs (D_park, C_S, K_S) are OBSERVED station data. Every premium and price is MODELLED.
All functions take their inputs as arguments. There is no module-level state apart from named constants.
"""
