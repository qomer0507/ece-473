# Phase 3: lead-time workstream log (Question 2 of docs/PHASE3_PREREG.md)

All times UTC. EXPLORATORY (pre-registration status). Raw Kalshi rows stay in data/raw/kalshi/ (git-ignored);
only aggregates are written here and under data/processed/leadtime/. MOS archive pulls are cached under
data/raw/mos/. "Observed" = real Kalshi quotes or station weather. "Modelled" = a price built from MOS or
climatology plus the Phase 1 markup and fee.

## How to continue if interrupted
1. `python scripts/leadtime_observed.py` (quote table -> data/processed/leadtime/observed_by_decision_time.csv; no network)
2. `python scripts/leadtime_mos_pull.py` (IEM MOS archive -> data/raw/mos/; resumable, skips cached files)
3. `python scripts/leadtime_mos_skill.py` (PoP by lead, Brier, calibration)
4. `python scripts/leadtime_he.py` (modelled price by lead, HE by lead, bootstrap)
5. `python scripts/leadtime_report.py` (figure and summary)
6. `python -m pytest tests/test_leadtime_*.py -q`

## Progress log
- 2026-11-12 22:55: Read PHASE3_PREREG (Question 2), phase1_kalshi.md, phase2_eval.md, SPEC_v3, rain_price_model.py, price_model.json, src/hedge_eval. Created directories. Nothing from the earlier cancelled attempt existed.
- 2026-11-12 22:58: Read https://mesonet.agron.iastate.edu/mos/ (archive status: AVN 2000-06 to 2003-12, GFS MAV 2003-12 to now, MEX 2020-07-12 to now, NBS 2018-11 to now, NBE 2020-07-23 to now) and the bulk form /mos/fe.phtml -> /cgi-bin/request/mos.py (one CSV per station, model and date range). Probed KTTN: GFS rows carry p06 and p12 (percent) at 6-hourly valid times out to 72 h; MEX carries p12 and p24 (24 h ending at 00Z valid times) out to 192 h; NBS carries p06, p12 out to 72 h (6-hourly rows only in the archive). A fast second request got HTTP 429, so the pull uses a 6 s gap and retries. Wrote src/leadtime/mos_archive.py and scripts/leadtime_mos_pull.py; pull started in the background (plan: GFS 2004-2026, MEX 2020-2026, AVN 2000-2003, NBS 2019-2026, NBE 2020-2026, both stations, runs Apr 23 - Sep 30).

## Reading choices, fixed BEFORE any skill or hedge result was computed
1. Lead time of a run = (Kalshi close time of the climate day - MOS run time), in days. The Kalshi close is
   04:00Z the next calendar day in summer (midnight local at the end of the rain day; phase1_kalshi.md). So the
   observed decision times 36, 24, 12, 2 h before close are leads 1.5, 1.0, 0.5, 0.08 days on the same axis.
   The lead is measured from the model run time; MOS text is issued 2-4 h later, so a buyer's real lead is a
   little shorter. For a whole-day lead L the run used is the one whose lead is closest to L days (GFS runs at
   00, 06, 12, 18Z, so the 06Z run of day D+1-L; MEX runs at 00 and 12Z, so the 00Z run of day D+1-L).
2. Probability of measurable precipitation for climate day D (local calendar day):
   main field = the model's 24-h PoP (p24) ending 00Z D+1 where the model has one (MEX only);
   otherwise the two 12-h PoPs (p12) ending 12Z D and 00Z D+1 combined as 1 - (1 - p1)(1 - p2).
   Both cover 00Z D to 00Z D+1 = 20:00 local D-1 to 20:00 local D (EDT), four hours earlier than the climate
   day; the archive has no field aligned with local midnight. The combination assumes independence of the
   two half-days and therefore overstates the 24-h probability when rain persists; the calibration table
   shows the size of that bias. For MEX the combined-p12 value is also kept, for comparison with the p24 line.
3. Model lines: GFS MAV (AVN before 2003-12-16, labelled) for leads 1-3 days; MEX for leads 4-7 days (MEX
   also gives 1-3 days and is kept as a second line); NBS (1-3 days) and NBE (4-7 days) as a second family.
   The main skill-by-lead and price-by-lead tables use GFS/MEX. Lead 1.5 days (the observed-end check) uses
   the GFS 18Z run of day D-1 (lead 1.42 days).
4. Outcome = Kalshi rule: official daily total (ghcn_prcp_in in data/processed/rain/daily_<station>.parquet)
   >= 0.01 inch; missing total = No. Days: May 1 - Sep 30 for the skill tables. A target day with no run at
   the chosen lead (archive gap) is left out of the skill table and counted.
5. Modelled ask(lead) = clamp(PoP(lead) + a) + taker fee, a = 0.0851 (price_model.json "skill") and a = 0.068
   as the sensitivity; clamp = whole cents in [0.01, 0.99]; u (no-offer share on rain days) = 0.0833 as in
   Phase 2 strategy 2. Lead = infinity: PoP = monthly climatology from TRAIN seasons (Phase 2 strategy 5 p),
   same markup and fee (this differs from strategy 5, which used (1 + loading) p and no fee; it is the same
   contract priced with the same markup rule as every other lead).
6. HE by lead: Phase 2 cases A (TTN same-station) and D-same (PHL same-station), joint usable days, strategy 2
   rules: n chosen on TRAIN from {0.05..1.0} to maximise TRAIN HE, ties to the smallest n; reference = TRAIN
   mean of D_park; HE on REPORT seasons; bootstrap over REPORT seasons, 2,000 draws, seed 473, percentile
   interval. Windows for a MOS-priced lead: a season is "available" for a model line if a MOS value exists for
   at least 90% of its joint usable season days at that lead (mirrors the Phase 1 90% rule; drops partial first
   seasons such as MEX 2020). Then:
   - Trenton, GFS leads 1-3: Phase 2 windows restricted to available seasons (TRAIN 2004-2014, REPORT 2015-2026).
   - Philadelphia, GFS leads 1-3: the Phase 2 TRAIN window (1941-1990) has no MOS season, so the available seasons
     are split 60/40 as Question 1 of the pre-registration does (first 60% TRAIN, rest REPORT), labelled.
   - MEX leads 4-7 (and MEX 1-3): there are too few MEX seasons to split (2021-2026). n and the reference level
     are taken from the same station's GFS lead-3 TRAIN choice (the nearest lead with a TRAIN window); all
     available MEX seasons are REPORT seasons. Stated as a limitation wherever shown.
   - Lead = infinity (climatology price): run on all Phase 2 seasons with the Phase 2 windows, and also on the
     same restricted windows as the GFS and MEX lines so the curve is comparable within one set of seasons.
   A season day in an available season without a MOS value at the chosen lead is priced at the climatology
   price for that day ("carry-forward to climatology"); the count of such days is reported.
7. Observed part (task 1): from the quote table, per decision time, pooled over the four cities (all series and
   years) and NYC alone. Usable ask = fresh quote with ask < 1.00 (buyable flag). Premium per $1 of payout =
   sum of asks on bought days / sum of results on bought days (one contract per market day; fee shown separately
   as in Phase 1). Share of rain days with no offer = rain days with has_quote and ask_is_1 / rain days with a
   quote. Brier of the mid on two-sided days. Mean ask on rain and dry days over buyable days.
- 2026-11-12 23:00: Task 1 done. src/leadtime/observed.py, scripts/leadtime_observed.py -> data/processed/leadtime/observed_by_decision_time.csv (aggregates only; four groups x four decision times). Check: the 24-h four-city KXRAIN 2026 premium per $1 payout (1.148) equals the Phase 1 set-C figure.
- 2026-11-12 23:00: Note: daily_<station>.parquet holds season days only (Friday before Memorial Day to Labor Day), so the skill tables are over those days, not all of May-Sep. Skill tables use days with a non-missing official total; the hedge keeps the Phase 2 rule (missing = No).
- 2026-11-12 23:01: Amendment to reading choice 2, made from the file layout before any skill or price
  number was computed. In the GFS MAV files the first p12 of a run is the period ending 18-24 h after the run
  (00Z and 06Z runs: first p12 at 00Z next day; 12Z and 18Z runs: at 12Z next day), and the first p06 is 12 h
  after the run. So no run with a lead under 1.42 days (the 18Z run of D-1) has both p12 values for the window
  00Z D - 00Z D+1. Consequences: (a) the main line's shortest lead is 1.42 days (target 1.5; this is also the
  observed-end check against Kalshi's 36-hour asks); the target "1 day" on the main line has no value and is
  reported as not available; (b) an extra, labelled line "p06x4" combines the four p06 values ending 12Z D,
  18Z D, 00Z D+1, 06Z D+1 (window 06Z-06Z = 02:00-02:00 local, closer to the climate day) as 1 - prod(1 - p);
  it exists from the 00Z run of D (lead 1.17 days, the "1 day" point) and at leads 1.42, 2, 3. Four combined
  periods assume more independence than two, so this line is expected to overstate the probability more; the
  calibration tables show it. MEX leads 4-7 use p24 (00Z runs; MEX has no p06). The p12x2 value is kept for
  every line as the one field formed the same way at every lead.
- 2026-11-12 23:06: Wrote src/leadtime/mos_pop.py (PoP by run and lead, Brier, calibration), src/leadtime/hedge_by_lead.py (modelled price by lead, strategy-2 sizing, bootstrap via src/hedge_eval), scripts/leadtime_mos_skill.py, scripts/leadtime_he.py, tests/test_leadtime_pop.py and tests/test_leadtime_hedge.py (16 pass: PoP combination, lead matching, carry-forward, clamp, fee, hand-checked HE). Pull still running (GFS done for both stations, MEX in progress).
- 2026-11-12 23:11: Debug runs of the skill and HE scripts on the GFS/MEX cache worked (code checks only; 161 MEX KTTN 2020 p12 rows at the 192-h step hold values above 100 and are treated as missing). Added KEWR and KNYC 2025-2026 (GFS, MEX, NBS) to the pull plan for the observed-end price check; the check now forms PoPs for every quote-table market day, not only park-season days. Wrote scripts/leadtime_report.py. Waiting for the NBS/NBE pull to finish before the final runs.
- 2026-11-12 23:14: MOS pull complete: 110 of 110 files cached (GFS 2004-2026, AVN 2000-2003, MEX 2020-2026, NBS 2019-2026, NBE 2020-2026 for KTTN and KPHL; GFS/MEX/NBS 2025-2026 for KEWR and KNYC), 0 errors, about 150 MB. Final skill run started.
