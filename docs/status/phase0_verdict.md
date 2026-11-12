# Phase 0 verdict (2026-11-12 UTC)

Sources: phase0_rain.md, phase0_kalshi.md, phase0_contract.md. Key tables: data/processed/rain_probe/prelim_counts_summary.csv, data/processed/kalshi_rain_probe/.

1. Hourly rain history. Trenton starts 1998: 29 usable seasons, not 40+. Philadelphia 85, Newark 75, Allentown 70. Hourly sums match daily totals within 0.02 inch on 97.7% (Trenton) and 98.9% (Philadelphia) of days.
2. Kalshi daily rain. Listed for NYC (2021-09, gap 2022-08 to 2025-01), Philadelphia (2026-07-15), Trenton and Newark (2026-08-27). Rule: any measurable rain (>= 0.01 inch) over the climate day; trace = No since 2026-07-15. Real summer prices: NYC 2025 and 2026 only; Philadelphia 73 days; Trenton 35 days. Results match the NWS report on every day checked. Accountability level $25,000 per strike per member.
3. Calendars. queue-times.com has dated calendars from 2018 (Great Adventure), 2019 (Dorney), 2022 (Sesame Place). All parks run daily from Memorial Day weekend to Labor Day.
4. Contract. Sound with fixes. 65 JS and 29 Python tests pass; maths and solvency independently confirmed. Three major fixes: oracle address validation, single-reporter trust (disclose, separate accounts), premature report. Adapt, about 20 hours.

First numbers (preliminary). Trenton 1998-2026, every day from the Friday before Memorial Day to Labor Day (about 102 days): any-rain days average 33.8 per season (20-48); days with >= 0.25 inch between 10:00 and 18:00 average 5.3 (1-12). 84% of any-rain days are not opening-hours loss days. Philadelphia over 85 seasons: 30.8, 4.9, 84%.

Design decisions proposed for Phase 1
- Lead: Sesame Place with Trenton (11.3 km; exact Kalshi baseline; 29 seasons). Long-history check: Philadelphia (85 seasons). "Should be listed" case: Dorney Park with Allentown (10.7 km, 70 seasons, climate report, no Kalshi rain market).
- Operating days: every day from the Friday before Memorial Day through Labor Day. Weekends plus holidays as a sensitivity case.
- Baseline cost: modelled, calibrated on NYC 2025-2026 and the four-city overlap of Jul-Sep 2026. Labelled as modelled.
- Baseline rule: trace = No (the rule a park faces today).
- Contract: adapt BracketLMSR to six count buckets with a uniform start; fix M1 and M3; disclose M2 and use separate sponsor and oracle accounts.
