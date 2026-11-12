# ECE 473 — Ceraunic Project Context, Handoff, and Build Plan

**Prepared:** October 29, 2026  
**Purpose:** Self-contained handoff for another AI assistant or team member. Read this before proposing work, writing code, or drafting course submissions.  
**Course project title:** *Localized Weather Hedging Using Event Contracts* (an earlier course submission used *Localized Weather Insurance Using Event Contracts*).  
**Team:** Qasim Omer, Ehfaz Zoha, Viktor Hrushka.  
**Upcoming milestones:** Milestone I update due October 29, 2026; Milestone II due November 12, 2026.

> **Status and provenance convention:** This file separates (A) facts established in the supplied Ceraunic historical project summary and instructor's Milestone I email, (B) scope or division of work previously **proposed/accepted** in planning discussions, and (C) the **recommended forward-looking implementation plan**. Do not misrepresent proposed work as completed, simulated results as customer outcomes, or past Ceraunic work as new ECE 473 team work. The actual ECE 473 one-pager, rubric, current code, and current contributions by each team member have not been provided in this conversation.

---

## 1. The idea in plain language

**Ceraunic** is the name of a broader research effort and proposed platform that helps small businesses protect themselves against losses caused by adverse weather. Examples include an ice cream shop losing sales on unusually cold days, a café losing foot traffic on rainy days, or an outdoor venue losing customers during extreme heat.

A business can buy a **weather contract** that pays according to an objective measurement, such as whether a specified weather station records a temperature below a threshold. Existing contracts may be available on a venue such as Kalshi or, for some exposures and timescales, institutional weather derivatives markets. But the business's actual location can have different weather from the station used to settle the contract.

That mismatch is **geographic basis risk**: a standard contract may work exactly as designed yet fail to pay when the business has an adverse local weather event.

A **local residual hedge** is a second, customized financial arrangement intended to cover the payout *gap* the standardized weather contract leaves behind. In the broader Ceraunic concept, market makers, insurers, or other eligible risk-takers quote a premium for assuming that remaining local risk. Ceraunic would try to pair existing market liquidity with competitive quotes for the smaller residual exposure.

**Illustrative example (NOT research data):** An ice cream shop needs an $800 payout if local temperature is below 70°F. A standardized weather-station contract also promises $800 if the station is below 70°F. On a particular day, the station reads 75°F but the shop's local temperature is 65°F. The standard contract pays $0, while the shop's target payout is $800. A correctly structured local residual contract could pay the missing $800. The customer would have to pay premiums for both components; the combined strategy is worthwhile only if the protection benefit justifies those costs.

### Terms to keep straight

- **Hedge:** A position or agreement used to reduce exposure to an unfavorable event; not necessarily profitable on its own.
- **Weather index / station contract:** A derivative or payout agreement based on a specified weather measurement and its rule.
- **Parametric protection:** Pays when a predefined measurable trigger is met, rather than necessarily reimbursing individually documented actual losses.
- **Geographic basis risk:** Difference between a reference station's relevant weather/payout and a business's local weather/payout.
- **Residual risk:** The target exposure not offset by the standard contract.
- **Local residual hedge:** A customized payout or financial contract designed to reduce that residual risk.
- **RFQ (request for quote):** Customer requests a price; qualified counterparties respond with quotes.
- **Premium / price:** Money paid for protection; expected payouts alone do not determine a fair price. Capital, tail risk, fees, and counterparty costs matter.
- **Hedge effectiveness:** A specified statistical measure of how well a hedge reduces target exposure. Always define the metric; never use it interchangeably with savings, profit, or customer benefit.

---

## 2. Separate the long-term Ceraunic vision from the ECE 473 deliverable

### A. Long-term startup/platform vision — NOT the required class MVP

A potential business-facing application might eventually:

1. Take location, revenue/sales history, covered period, weather sensitivities, desired payout, and retained risk.
2. Determine suitable standardized exchange-traded weather contracts, if any.
3. Quantify the local residual exposure.
4. Request quotes from competing risk providers, arranged by geography, hazard, and tenor.
5. Show total premium and relevant payout terms to the business.
6. Support legally appropriate purchasing, collateral/counterparty arrangements, and weather-triggered settlement.

The broader Ceraunic project history documents a **simulation prototype** including a portal, Python-based engine, Solidity contracts, and accounting flow (sales upload → quote → purchase → auction → settlement → pool accounting). The summary reports 41 passing Foundry tests and agreement between its simulated Python and contract accounting. Those are historical prototype facts, **not** proof of live insurance customers, production marketplace, or profitability. Later architectural ideas included seasonal hedging, local RFQs, and possible margin/netting mechanisms; these are not established commercial features.

### B. ECE 473 semester project — our recommended core deliverable

**Build a reproducible Python weather-hedging research system** that takes historical daily weather data and compares:

- **Strategy A — station-only hedge:** standardized contract(s) settling on a specified reference station or published weather index.
- **Strategy B — two-part hedge:** the same station-based hedge plus *simulated* local residual protection.

Run it for the narrowed geography of **New York City and Trenton** and **temperature only**. Evaluate whether the second part materially reduces mismatch with the target local payout and, crucially, whether it is economically justifiable given premiums, trading costs, and assumptions about residual-market pricing.

**Do not build as core course scope:** a complete SaaS website, authentication, payment rails, live Kalshi trading, real underwritten insurance, a blockchain deployment, junior/senior pools, tokens, or a production quote marketplace. An optional simple dashboard can visualize output, but notebooks/scripts + figures + a report are sufficient as a proposed course deliverable.

**Scope provenance:** The historical project summary records that on October 8 the ECE 473 team accepted a narrower course plan: NYC and Trenton; temperature only; station-only versus two-part local hedge; portal removed from course deliverables; pooling optional. This must be compared to the group's actual submitted one-pager before claiming any new scope change in the Milestone I form.

---

## 3. Research question, hypothesis, and output

### Central question

**Can standardized weather-station contracts, supplemented with custom local residual payouts, more effectively and economically hedge business-relevant local temperature exposure than standardized contracts alone?**

### Subquestions

1. How often do local temperatures and reference-station temperatures differ enough to change whether a contract would pay?
2. How much of a target local payout can a station-based strategy reproduce on held-out historical days?
3. What residual payout is needed to close the gap, and how often would it trigger?
4. How does the two-part strategy compare using payout error, uncovered shortfall, variance or loss reduction, and total cost?
5. How sensitive are conclusions to location, temperature threshold, contract size, premiums, measurement source, and lookback period?

### Deliverable

A tested, reproducible **Python simulator/backtester** with cleaned or reproducibly acquired datasets, clear contract definitions, daily scenario outputs, summary tables, plots, a brief methods explanation, and a final course presentation/report.

**Intended result, not a presupposed result:** A two-part hedge may match local payout targets better mechanically, but could fail economically because the residual hedge is expensive, difficult to collateralize, or unlikely to be quoted. Negative findings are legitimate and important.

---

## 4. Proposed quantitative method

This section is a **recommended technical specification**, not a statement that the team already implemented it.

### Step 1 — Define a target payout at the business location

Start with a simple **stylized local temperature payoff**, not actual revenue compensation, unless the team has real validated sales data.

Example cold-day payout for location `x` on day `t`:

```
T_local(t) = P * 1{local_temperature(t) < threshold}
```

where `P` is a hypothetical fixed dollar payout (e.g., $800) and `threshold` might be 70°F. Choose a temperature definition (daily maximum or minimum), threshold, observation time, and day boundary and use them consistently. It is acceptable to run both heat and cold scenarios in sensitivity analysis, but avoid broadening the main scope excessively.

### Step 2 — Model a standardized station payout

```
S_station(t) = q * contract_payout(station_temperature(t), threshold, terms)
```

For the first mechanical demonstration, an equivalent binary payoff can isolate geographic mismatch. For more realistic analysis, use actual or well-documented indicative Kalshi contract terms and prices, **only if those contracts match the specified city, station, settlement source, time window, and threshold**. Do not label hypothetical contracts as actually tradeable.

### Step 3 — Define the local residual payoff rigorously

A simple **shortfall-only** local layer is:

```
R_local(t) = max(T_local(t) - S_station(t), 0)
Two_part_payout(t) = S_station(t) + R_local(t)
```

This removes **underpayment** relative to the local target in an idealized fully funded residual product. It does **not** automatically eliminate **overpayment** where the station contract pays but the local target does not. If exact target replication is claimed, the team needs a mechanism to offset overpayment too (e.g., a signed residual arrangement) and must explain its feasibility. For the initial project, measure both under- and over-hedging and describe this distinction clearly.

It may be useful to optimize contract size `q` in a training window, but do not optimize against the test window. If no station hedge is an attractive match, record that failure rather than forcing a positive result.

### Step 4 — Compare economic value, not only payout matching

Calculate and report, with explicit definitions:

- Count/share of **trigger mismatches** between local target and station contract.
- Average absolute payout error: `mean(abs(target - actual_payout))`.
- Uncovered loss / shortfall: `mean(max(target - actual_payout, 0))`.
- Overhedge: `mean(max(actual_payout - target, 0))`.
- Dispersion or variance of the **net residual**, if appropriate.
- Total **premium / estimated transaction cost** for each strategy.
- **Net economic comparison**, under clearly labeled pricing assumptions.

For a simple threshold decision, the most the business should pay for the added residual hedge **under an expected-cash-shortfall-only objective** can be related to the expected shortfall it eliminates. Under risk aversion, willingness to pay can differ. Do **not** claim a universally optimal premium or infer commercial demand solely from this toy model.

### Step 5 — Backtest correctly

- Select an exact historical range with usable consistent data; document chosen dates.
- Check missingness, units, time zones, station changes, grid alignment, and measurement conventions.
- If fitting a payout model, hedge ratio, or price model, separate training and held-out testing chronologically.
- Evaluate **both strategies on the same days and target exposures**.
- Test multiple thresholds and locations; report confidence/uncertainty when feasible.
- Write down hypotheses and evaluation measures **before** running a new empirical comparison to limit cherry-picking.
- Keep **observed contract pricing** separate from **illustrative or modeled residual pricing**.

### Important data complication

The Ceraunic history notes an unresolved **Kalshi settlement-source discrepancy**: at least one NYC heat series reportedly named **The Weather Company** as the settlement source starting around August 17, 2026, whereas some past station-leg analysis used an **NWS climate report**. A contract's actual settlement data must be matched to the correct source before claiming realistic payout results. If unresolved, label results as synthetic/reference-station simulations rather than observed exchange settlement accuracy.

---

## 5. Data to use and how to source it

**Potential sources from Ceraunic history (not confirmation that the team has downloaded them):**

| Data | Purpose | Cautions |
|---|---|---|
| NOAA / NWS / GHCN-D / IEM station observations | Reference-station temperatures and validation | Verify station ID, temperature variable, observation day, gaps, revisions, and settlement rule |
| PRISM gridded climate data | Approximate local temperature at a selected point | Grid cell ≠ thermometer at shop; spatial resolution/representativeness and download restrictions matter |
| Kalshi historical or available contract terms and market data | Standardized contract trigger, quote/cost assumptions | Available contracts, expiration, settlement source, fees, liquidity, and bid/ask must match analysis |
| Optional other weather grids (nClimGrid) | Robustness comparison | Added complexity; use only after baseline works |

**Geography:** NYC and Trenton. Choose precise representative local points and reference stations with defensible proximity and coverage. An evaluation comparing two *cities* is not by itself a test of shop-level basis risk; compare a local point to a defined reference measurement, with clear spatial logic.

**Data restrictions documented in the historical Ceraunic handoff:** PRISM has a daily repeat-download limit for the same file; avoid unnecessary re-pulls. Some CME/Databento data is paid; get permission before paid downloads. Raw datasets are not guaranteed present even if previous Ceraunic repository scripts refer to them.

---

## 6. Three-person responsibility plan

The following **originated as a proposed team allocation** in October planning, not a verified record of completed work. Treat it as the working structure unless the team confirms changes.

### Ehfaz Zoha — literature, standard exchange contracts, and pricing

**Milestone I target (planned):**
- Identify a small set of credible references on weather derivatives, parametric products, and geographic basis risk.
- Identify suitable standardized temperature contract families, terms, station definitions, and accessible pricing data.
- Document realistic challenges: fees, spread, expiration/tenor, liquidity, and settlement-data source.

**By Milestone II (recommended):**
- Deliver documented `station_contracts` specification and daily payout simulator.
- Produce contract data dictionary and a basic station-only cost model with observed prices where defensible, plus explicit assumption scenarios when not.
- Supply a short literature/pricing summary and limitations.

**Hand-offs:** shares contract rules and station identities with Qasim; a callable payout/cost module with Viktor.

### Qasim Omer — local and station weather data, geographic basis risk, backtests

**Milestone I target (planned):**
- Identify NOAA/PRISM data sources for NYC and Trenton.
- Define local-versus-station temperature observations and spatial-pair selection.
- Propose basis-risk metrics and backtesting structure.

**By Milestone II (recommended):**
- Deliver aligned day-by-day data (`date`, `city`, `local_temp`, `station_temp`, metadata).
- Quantify temperature/payout-trigger mismatches and visualize local vs. station series.
- Produce station-only hedge performance, with coherent time split, units, and missing-data handling.

**Hand-offs:** sends cleaned data and validation notes to both teammates.

### Viktor Hrushka — local residual simulator, integration, plots

**Milestone I target (planned):**
- Specify how local residual payouts are calculated from local target and station payout.
- Outline the simulator architecture and performance measures.
- Consider whether optional pooling deserves analysis; default is **not required**.

**By Milestone II (recommended):**
- Implement residual hedge simulator, integration runner, and output plots.
- Ensure the comparison includes shortfalls, overhedges, and premium/cost assumptions.
- Add tests for matching conditions, station mismatch, missing data, and payout edge cases.

**Hand-offs:** merges everyone’s modules into one reproducible run and summary.

### All three

- Agree on a single target payout definition, city/station/local-point mappings, weather observation window, and metric definitions **before** running experiments.
- Review results and failure cases, prepare final report, and clearly attribute contributions.
- Document what was inherited from historical Ceraunic work versus produced during ECE 473.

---

## 7. Milestone I — October 29: exact instructor instructions

The instructor's email (Niusha) says to submit **one update per group** via:

https://docs.google.com/forms/d/e/1FAIpQLScWKJ0jcfL46b3ZzdM44O0xKisLFlP9-N6rp0PyHTg3qPvcsw/viewform?usp=publish-editor

**Limit: one page.** Must cover exactly these three areas:

1. **Planned vs. actual progress, per person.** For each of Qasim, Ehfaz, and Viktor, describe what the original one-pager said they would accomplish by Milestone I and what they actually completed.
2. **Remaining work for Milestone II (11/12).** Detail what still needs doing and assign each task to a person.
3. **Refinements to plan.** Describe changes to scope, approach, timeline, or assignments and why; otherwise explicitly say no changes.

**Critically:** The conversation does not establish what each member has *actually completed* by October 29, nor provide the original submitted one-pager. A future model must collect these factual updates from the group or inspect authorized repositories/commits before drafting a truthful final submission. Do not invent progress, downloaded data, completed notebooks, or slides. If NYC/Trenton, temperature-only, and no portal were already agreed before the one-pager, call that **current scope**, not a novel Milestone I refinement.

**Proposed Milestone I expectations** (not instructor-required deliverables): agreed research question, feasible sources, definitions for strategies and metrics, responsibility split, preliminary literature/data/model progress. The instructor's email does **not** require a working prototype or specific graphs by Milestone I; it requires an accurate progress report.

### Ready-to-fill one-page structure

**ECE 473 Milestone I — Localized Weather Hedging Using Event Contracts**  
**Team:** Qasim Omer, Ehfaz Zoha, Viktor Hrushka

**Planned vs. actual progress**  
- **Ehfaz — contracts/literature:** Planned: [paste original one-pager expectation]. Actual: [completed references, contracts, quotes, issues; do not infer].
- **Qasim — NOAA/PRISM and basis risk:** Planned: [paste original one-pager expectation]. Actual: [data pulled, cleaned, compared, or still pending].
- **Viktor — local hedge simulator:** Planned: [paste original one-pager expectation]. Actual: [design, prototype code, tests, or still pending].

**Through Milestone II (November 12)**  
- Ehfaz: confirm station contract terms and pricing model.
- Qasim: assemble/validate aligned historical weather and run station-only basis-risk backtest.
- Viktor: implement local residual payout simulator and integrated comparison plots.
- All: assess mismatches, hedge effectiveness, and cost assumptions; document failures/uncertainty.

**Refinements:** [No change if original scope already NYC/Trenton, temperature-only, Python research rather than portal; otherwise describe agreed scope changes accurately and why.]

Submit one update on behalf of the whole group. This template should be trimmed to one page after filling.

---

## 8. Milestone II — November 12: proposed working deliverables

The supplied email only gives the **date** for Milestone II; it does not state an exact Milestone II rubric. The following is a sensible **internal acceptance target**, not an official instruction.

By November 12 the group should aim to demonstrate:

1. **A clean reproducible dataset** for NYC and Trenton: metadata for local grid point, reference station, dates, daily temperatures, completeness.
2. **A fully specified reference-station contract simulator** producing daily payouts and clearly labeled pricing assumptions.
3. **A local residual hedge simulator** that computes coverage gaps, including explicit treatment of overhedging.
4. **A single comparison runner** evaluating Strategies A and B on the same sample, including payout error, average shortfall, mismatch frequency, and cost assumptions.
5. **2–4 clear figures/tables** (temperature scatter/series, trigger-mismatch frequency, comparison of residual payouts, cost/performance sensitivity).
6. **Preliminary findings and limitations**, not a claim of guaranteed superiority. Code runs on a documented command and tests basic edge cases.

### Suggested build schedule (modifiable)

| Dates | Lead | Work | Exit criterion |
|---|---|---|---|
| Oct 29–Nov 2 | All, each on assigned inputs | Freeze contract/target definitions; identify/reference datasets; draft module APIs | Written contract spec and data schema agreed |
| Nov 3–6 | Qasim + Ehfaz | Load/clean aligned temperatures; implement station contract payoffs/costs | One valid historical daily sample and Strategy A output |
| Nov 3–7 | Viktor | Implement target/local residual payouts and tests | Strategy B daily output works with synthetic tests |
| Nov 7–9 | All | Integrate, run comparison and basic scenarios | Reproducible tables/plots on chosen history |
| Nov 10–12 | All | Validate methodology, sensitivity, limitations, and milestone write-up | Demo/script, plots, draft technical summary |

If obtaining actual Kalshi quotes proves difficult, **do not block the entire project**. First complete the mechanical basis-risk experiment with transparently hypothetical premiums. Separately report what actual market data is and is not available, and clearly limit any profitability conclusions.

---

## 9. Suggested code architecture (forward-looking, not present repository layout)

```text
ece473-ceraunic/
  README.md                       # project setup, scope, run commands
  requirements.txt OR pyproject.toml
  docs/
    research_question.md
    contract_spec.md             # temperature variable, location, payout rules, date convention
    data_dictionary.md
    milestone1.md                # completed progress; NOT hypothetical progress
  data/
    raw/                         # optional, avoid committing huge or restricted sources
    processed/
    manifests/                   # provenance / fetch dates / station IDs / source links
  src/
    load_weather.py              # Qasim: NOAA/PRISM loading and alignment
    basis_risk.py                # Qasim: mismatch and target metrics
    station_hedge.py             # Ehfaz: contract payout + cost assumptions
    local_residual.py            # Viktor: residual payout model
    backtest.py                  # integrate and compare A/B
    metrics.py                   # objective functions and summary metrics
  tests/
    test_contracts.py
    test_residual.py
    test_alignment.py
  scripts/
    run_experiment.py
  notebooks/
    exploration.ipynb            # exploratory only; no hidden pipeline dependencies
  results/
    figures/
    tables/
```

### Minimum data interface

```python
# one record per city/day/local-point/reference-station pairing
{
    "date": "YYYY-MM-DD",
    "city": "NYC or Trenton",
    "local_point_id": "...",
    "station_id": "...",
    "local_temperature_f": 65.0,
    "station_temperature_f": 75.0,
    "temperature_variable": "TMAX or TMIN",
    "data_quality": "...",
}
```

### Minimum simulation interface

```python
# conceptual function signatures, not previously implemented code
local_target_payout(local_temp, threshold, notional)
station_payout(station_temp, threshold, notional, contract_terms)
residual_shortfall_payout(target_payout, station_payout)
evaluate_backtest(daily_records, station_premiums, residual_premium_model)
```

Add deterministic unit tests before relying on the model:

- Both station/local trigger → standard contract pays, no additional shortfall.
- Local triggers, station does not → residual covers the modeled gap.
- Station triggers, local does not → record overhedging; do not silently call it zero residual risk.
- Neither triggers → neither pays.
- Missing value / inconsistent time alignment → reject or flag rather than impute silently.
- Zero/partial station notional → residual scales correctly.
- Premiums recorded separately from gross payouts.

---

## 10. Existing Ceraunic results: useful context, NOT automatically class results

The supplied 16-page historical Ceraunic summary describes:

- A separate **weekly local rainfall** study on 26 station pairs, with 25/26 positive pair-level improvements and pooled median paired hedge-effectiveness improvement `+0.229` (95% interval `+0.119` to `+0.318`). Median effectiveness levels were approximately `0.491` and `0.808`; those are a **different statistic** from `+0.229`.
- A **heat-contract payout-matching** result of approximately `0.95` on an earlier city-day sample, but this was **not** buyer net hedging effectiveness after prices and fees.
- Significant negative results: expensive hedge markups, inadequate liquidity, weak temperature-residual gains relative to earlier thresholds, learned revenue-proxy failures, and difficult pool capital requirements.
- An earlier simulation prototype with engine/API, Solidity contracts, and web portal, tested only in a simulated/local environment according to the older audit.
- A public repository snapshot identified in a later handoff as `https://github.com/ehfuzzz/ceraunic` (2026-10-28); the summary says historical code, cached derived data, paper, and site content can be found there, but we have **not verified its current state** in this handoff. Never assume that repo contains the ECE 473 group's new, three-person course work.

These facts can justify the motivation and show why pricing is important, but should **not** be copied into the ECE 473 results section without checking experimental compatibility, source provenance, and what is original course work.

### Research integrity guardrails

- Do not claim 26/26 improved; corrected historical claim is 25/26.
- Do not interpret 0.95 gross payout matching as 95% money saved.
- Do not claim an existing live marketplace or insurance sales.
- Do not conflate weekly rainfall research and NYC/Trenton daily temperature backtests.
- Do not claim an exact local hedge is available for purchase just because it can be simulated.
- Do not assume the original prototype's simulated trading/bookkeeping system must be rebuilt for class.
- Report failed tests and economic limitations; avoid cherry-picking periods or thresholds.
- No unauthorized real trading, paid data pulls, account creation, or mainnet deployment.

---

## 11. What the next AI model should do

**Assume you are helping a three-person ECE 473 team execute the project from its current, partly unverified state.**

1. Treat this document as project context, not proof of completed work.
2. Keep the academic scope focused on **NYC + Trenton / temperature / station-only vs. two-part residual hedge / Python analysis** until the team explicitly requests a change.
3. Before writing a final Milestone I submission, ask for or verify the team's **original one-pager commitments** and **actual progress from each member**, then fit the response to the instructor's one-page, three-category structure. Do not invent achievements.
4. If asked to start building immediately, begin with a clear contract/data specification and synthetic tests, then reproducible data access. Prioritize a working numerical comparison over an app/UI.
5. Clearly label observed exchange data vs. modeled and illustrative prices; separate payout fit from net economics.
6. Make all code reviewable, runnable, modular, and independently testable. Provide exact inputs/outputs and small tests. Avoid overengineering.
7. If external research, GitHub repository inspection, or course rubric verification is requested, verify current facts with tools; do not assume a previous summary establishes a live/current state.
8. When choosing new metrics or conducting new experiments, specify them up front and record changes.
9. If a team member proposes to build a website, explain that a small demo UI is optional, not the research deliverable; ensure the underlying simulator is correct first.
10. The end goal is a credible course-quality **experimental system and paper/presentation** that answers *when* local residual protection helps and whether its extra cost can be justified, rather than a claim that the startup model is already proven.

---

## 12. Open questions / confirmation checklist

These need answers from the team, the original one-pager, or authorized project materials; do not fill them with guesses:

- What EXACT tasks did the original one-pager assign each person by October 29?
- What has Ehfaz actually completed, with files/links or concrete outputs?
- What has Qasim actually completed, with files/links or concrete outputs?
- What has Viktor actually completed, with files/links or concrete outputs?
- Is the course project code in a new repo or part of the existing Ceraunic repo?
- Which exact NYC and Trenton local points and reference stations are intended?
- Is TMAX, TMIN, or another temperature metric the agreed contract variable?
- Which date range is realistically accessible for weather data and relevant contract quotes?
- Is an observed exchange-pricing analysis feasible by November 12, or should it be clearly separated as a sensitivity study?
- Does the full course syllabus require hardware, a specific system architecture, presentation format, or other deliverables? Nothing in the provided email establishes such requirements.

---

## 13. Sources supplied for this handoff

1. **User-uploaded 16-page `ece473 project .pdf`**, describing Ceraunic history, October course scope/team allocation (notably pp. 9–10), prior research and prototype (pp. 4–8), and an October 28 project/repository handoff (pp. 13–16).
2. **Niusha's Milestone I email quoted by the user**, stating the one-page, one-per-group submission content, the submission form, and the November 12 Milestone II date.
3. **Current conversation clarifications**, in which the user requested a straightforward distinction between building the long-term Ceraunic app/platform and constructing a focused three-person ECE 473 research simulator.

**Bottom line:** We are building and validating the **core quantitative weather-hedging comparison** behind Ceraunic, not shipping an insurance app. Milestone I is a truthful written progress update; Milestone II should show the system working on data with preliminary comparisons; the final course deliverable should provide robust results and limitations.
