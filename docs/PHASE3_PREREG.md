# Phase 3 pre-registration (written 2026-11-12 UTC, before any Phase 3 analysis was run)

Status: EXPLORATORY. These questions were chosen after seeing Phase 2 results. Every Phase 3 figure and table says so. Rules below are fixed before running; deviations go under "Deviations" with a date and reason.

## Why
Phase 2 found that a seasonal rain-count contract hedges a park when the park's rain matches the settlement station's (Philadelphia, 35 held-out seasons, HE 0.65) and fails for a stand-in gauge 28 km from Trenton. It also found that Kalshi's day-ahead contract prices in the forecast (asks of about 0.75 on rain days, 0.23 on dry days). Two questions follow.

## Question 1: how far does a weather hedge reach?
For every pair (settlement station S, exposure gauge G) in the region, how does hedge effectiveness fall with distance, and is the decay different for rain and for temperature?

- Rain pairs: all ASOS stations in NJ, NY, PA, CT, DE, MD with hourly precipitation and at least 20 usable seasons (SPEC_v3 usable rule), S restricted to stations with an NWS daily climate report. Exposure definition at G: >= 0.25 inch in 10:00-18:00 local, season = Friday before Memorial Day through Labor Day, count per season. Contract at S: the exact seasonal count contract (Phase 2 strategy 4: payout max(C_S - d, 0), d chosen on TRAIN from {0..8}, premium 1.2 x TRAIN mean payout). Windows: TRAIN = first 60% of the pair's joint usable seasons, REPORT = the rest (fixed before running; the Phase 2 Trenton windows are not reused because pairs have different histories).
- Temperature pairs: the 84-station TMAX panel (data/processed/panel). Exposure at G: count of days with TMAX >= 90 in May-Sep. Contract at S: the same exact count contract on S's count, same d and premium rule. Same 60/40 split.
- Metric per pair: hedge effectiveness HE on REPORT seasons, exactly as Phase 2 defines it (downside semi-variance, reference level fixed at the TRAIN mean of unhedged cost). Also the daily trigger agreement rate and the Pearson correlation of seasonal counts, on all usable seasons.
- Analysis: HE against distance, one curve for rain and one for temperature, with a binned mean and a 95% bootstrap band (resample pairs, 2,000 draws, seed 473). The "reach" of each hazard = the largest distance bin whose lower band edge is above 0. Report also whether elevation difference and a coast indicator add anything in a simple regression, as Phase 1 did for temperature.
- Hypothesis written in advance: rain reach is shorter than temperature reach. If the curves do not separate, say so.
- The Trenton-PNE pair from Phase 2 is plotted as one point on the rain curve, labelled.

## Question 2: when must a contract be listed to work as a hedge?
Kalshi lists daily rain about 1.5 days ahead. How does the cost of $1 of protection, and the hedge effectiveness of buying it, change with how far ahead a buyer can trade?

- Observed part: the Phase 1 quote table (data/raw/kalshi/rain/quote_table.csv, aggregates only) gives asks at 36, 24, 12 and 2 hours before close. For each decision time: premium per $1 of payout, share of rain days with no offer, and the Brier score of the mid price. Pooled across the four cities, and NYC alone.
- Modelled part: for lead times of 1 to 7 days, price the same contract at the probability of precipitation a buyer would face at that lead, from the IEM MOS archive (GFS MOS/MEX at the settlement stations, https://mesonet.agron.iastate.edu/mos/), plus the Phase 1 fitted markup a and fee. Beyond the MOS horizon use the monthly climatology (lead = infinity). Label every modelled number.
- Metric: for the Trenton same-station park case and the Philadelphia same-station case, HE of buying the daily contract every season day at each lead time, Phase 2 rules (strategy 2 sizing on TRAIN). Plot HE and premium per $1 payout against lead time.
- Hypothesis written in advance: HE rises with lead time and the daily contract becomes a usable hedge only when listed well beyond its current 1.5 days. If HE stays below zero at every lead, that means the daily contract's shape, not its timing, is the binding problem, and we say so.

## What counts as a result
- Question 1 produces a reach in km for each hazard with a band, or a statement that reach cannot be resolved with the pairs available.
- Question 2 produces the lead time at which the daily contract's HE first exceeds zero, or the statement that it never does.
- No pair, station, lead time or window is dropped after seeing results. Pairs that fail the usable rule are listed.

## Deviations
(none yet)
