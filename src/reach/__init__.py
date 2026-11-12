"""Phase 3 reach workstream, rain part (docs/PHASE3_PREREG.md, Question 1).

Modules
  rain_hourly   reduce raw IEM METAR / NCEI ISD pulls to one row per hour (same rules as Phase 0)
  rain_geo      haversine distance, coast indicator (Atlantic or Long Island Sound within 15 km)
  rain_pairs    station loss matrices, pair construction, joint seasons, the exact count contract and its HE
  rain_curve    distance bins, bootstrap bands (by pair and by exposure gauge), reach, regression

Observed weather only. Every premium is modelled. Nothing is imputed.
"""
