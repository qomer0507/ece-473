"""Rain workstream library (SPEC_v3).

Modules
  calendar   season calendar (Friday before Memorial Day through Labor Day; weekend-plus-holiday variant)
  hourly     load the hourly station series, map UTC hour labels to local clock time and to the NWS climate day
  daily      opening-hours totals, loss-day flags, Kalshi-rule flag, usable-day and usable-season rules, counts
  reference  loaders for the comparison data (GHCN-Daily PRCP, NWS climate report via IEM)

All functions take their inputs as arguments. There is no module-level state apart from named constants.
"""
