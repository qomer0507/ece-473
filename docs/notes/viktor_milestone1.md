# Viktor — Milestone I notes: local residual simulator

Written 2026-10-30 (UTC). Status: code and tests exist; one first run on real aligned data, not yet reviewed by the team.

## What exists now
- `src/local_residual.py`: target, station (A), residual, two-part (B) payouts.
- `src/metrics.py`: mismatch, shortfall, overhedge, error, premium, objectives, break-even loading.
- `src/backtest.py`: runs A and B on identical rows per pair and threshold.
- `scripts/run_experiment.py`: CLI runner, tables, loading-sweep figure.
- `tests/test_residual.py`: 14 deterministic tests, all passing.
- Synthetic pipeline check: outputs in `results/synthetic/` with a `SYNTHETIC_` prefix. Not findings.
- First real run: 2026-10-30T03:02Z on `data/processed/aligned_daily.csv`
  (Qasim; md5 719ef1d10359f6ec02014fd5dde3e62a). 7 local/reference pairs,
  11,781 rows in, 131 dropped for missing local TMAX. Outputs in `results/tables/`
  and `results/figures/loading_sweep.png`. These are preliminary and unreviewed.
  The input is a GHCN-Daily cache inherited from the prior Ceraunic repo
  (see `data/manifests/raw_provenance.csv`); Qasim's spot checks cover provenance.
- If the data file is missing, the script exits with code 2 and writes nothing.
- `src/station_hedge.py` (Ehfaz) was not present at run time. A private fallback
  with the same SPEC rule was used. The run manifest records which one was used.
  Rerun once Ehfaz's module lands.

## Formulas
Per day t, threshold k, notional N = $800, station fraction q (default 1):

```
target_t   = N * 1{local_tmax_t >= k}
station_t  = q * N * 1{ref_tmax_t >= k}             Strategy A
R_t        = max(target_t - station_t, 0)           residual layer
B_t        = station_t + R_t = max(target_t, station_t)   Strategy B
shortfall  = max(target - payout, 0)
overhedge  = max(payout - target, 0)
abs error  = |target - payout|
premium    = E_train[payout] * (1 + loading)        loading ASSUMED
net cost C = premium + target - payout              (per day)
```

Conventions: `>=` triggers at equality. NaN inputs give NaN payouts. Missing rows
are dropped and counted, never imputed. Premiums never enter payout functions.

## Architecture

```
data/processed/aligned_daily.csv   (Qasim)
            |
            v
src/backtest.py  prepare(): season filter, train/test split, drop+count NaN
            |
            +--> src/local_residual.py  target, residual, two-part
            |          |
            |          +--> src/station_hedge.py  station_payout (Ehfaz; fallback if absent)
            |
            +--> src/metrics.py  mismatch, payout metrics, premium, objectives, break-even
            |
            v
scripts/run_experiment.py --> results/tables/comparison_{metrics,break_even,loading_sweep,row_accounting}.csv
                          --> results/tables/run_manifest.json
                          --> results/figures/loading_sweep.png
```

Pricing uses train-window expectations only (2015–2021). Test metrics (2022–2025) use those train prices.

## "B wins by construction"
B pays `max(target, station)`. So B has zero shortfall on every day. Saying B
"reduces shortfall" is not a finding. Also, B's overhedge equals A's, because the
residual never offsets overpayment.

The real question is cost. The residual costs `(1+L) * E[R]` per day.
- Risk-neutral buyer: B minus A in expected cost = `L * E[R]` in-sample. Break-even
  loading is 0. Any positive loading makes B worse. This is trivially true and says nothing about the data.
- Risk-averse buyer: we add two objectives so break-even is informative.
  - Mean-variance: `E[C] + (a/N) Var(C)`, a = 1 by default (ASSUMED).
  - Mean-CVaR: `E[C] + g * CVaR_0.95(C)`, g = 0.25 by default (ASSUMED).
- Both objectives shift one-for-one with a constant premium. So the station
  premium cancels in B − A, and B − A is linear in L. The break-even `L*` is solved exactly.
- The sweep runs L from 0% to 100% and plots B − A for each objective. Below zero means B preferred.

Assumptions: daily costs treated as i.i.d. draws; no discounting; no counterparty
risk; no transaction cost beyond the loading; target is a stylized loss, not revenue.
The risk-aversion parameters are arbitrary. Break-even values should be reported
together with the parameters, and ideally across a small range of them.

Out-of-sample (test) break-even under risk-neutral is not exactly 0. That is
because test E[R] differs from the train E[R] used for pricing. It measures pricing drift, not value.

## Station premium for A
`E_train[station payout] * (1 + markup)`, markup = 0.20 by default. This is ASSUMED.
It is a CLI flag (`--station-markup`). Replace with observed prices only if Ehfaz
confirms a contract matching station, source, window and threshold.

## Pooling
Recommendation: out of scope for Milestone II.
- The question is about one business's mismatch. Pooling changes it to a seller's risk question.
- With two cities and a few local stations we have too few independent exposures for a meaningful pooling estimate.
- Residual payouts across nearby stations are strongly correlated on hot days, so diversification would be small and hard to measure.
- It would need a seller capital model we do not have.
Possible final-report extension: report the correlation of residual payouts across pairs as a one-line diagnostic.

## Open questions
1. Station notional fraction q: fixed at 1, or fit on train? Fitting q is allowed on train only.
2. Station premium: any observed price we can legitimately use, or stay with the assumed markup?
3. Risk-aversion parameters: which values do we report as the headline, and which as sensitivity?
4. Should the residual be priced per pair (as now) or with one pooled E[R]? Current code: per pair.
5. Do we need bootstrap confidence intervals on break-even loading? Recommended for Milestone II.
6. Data quality flags: which `data_quality` values should be excluded, beyond missing TMAX?
7. Settlement source mismatch (Kalshi vs NWS/GHCN) means results are reference-station simulations. Agree on wording.

## Proposed Milestone II tasks (Viktor)
- Integrate `src/station_hedge.py` once present; delete nothing, keep fallback for tests.
- Run on real `aligned_daily.csv`; write `results/tables/comparison_*.csv` and the loading-sweep figure.
- Add bootstrap (by season-year blocks) intervals for mismatch rates and break-even loading.
- Add a mismatch-frequency bar chart and a payout comparison figure (2–4 figures total).
- Sensitivity over thresholds 85/90/95 and risk-aversion parameters.
- Add an optional q fit on train, with test evaluation only.
- Write the results and limitations section with the team.
