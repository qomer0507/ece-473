# Localized Weather Hedging Using Event Contracts (ECE 473, Princeton)

Team: Qasim Omer, Ehfaz Zoha, Viktor Hrushka.

Question: does adding a local residual layer to a station-settled temperature
contract reduce local payout mismatch enough to justify its extra cost?
The frozen definitions are in `docs/SPEC.md`.

## Setup
Python 3.10+.

```
pip install numpy pandas matplotlib pytest
```

## Run
Tests:
```
python -m pytest tests -q
```

Comparison of Strategy A (station-only) and Strategy B (station + local residual):
```
python scripts/run_experiment.py
```
This needs `data/processed/aligned_daily.csv` (built by the data workstream).
If the file is missing, the script stops with an error and writes nothing.

Useful flags (all prices are ASSUMED, not observed):
```
--station-markup 0.20      station premium = E[payout] * (1 + markup)
--thresholds 85 90 95
--mv-a 1.0                 mean-variance risk aversion
--cvar-gamma 0.25 --cvar-alpha 0.95
```

Pipeline test with made-up temperatures (not results):
```
python scripts/run_experiment.py --synthetic
```
Synthetic output goes only to `results/synthetic/`, with a `SYNTHETIC_` prefix.

## Outputs
- `results/tables/comparison_metrics.csv` — mismatch, shortfall, overhedge, error, premiums.
- `results/tables/comparison_break_even.csv` — break-even residual loading per objective.
- `results/tables/comparison_loading_sweep.csv` and `results/figures/loading_sweep.png`.
- `results/tables/comparison_row_accounting.csv` — rows used and dropped.
- `results/tables/run_manifest.json` — inputs and assumptions of the run.

## Layout
```
src/local_residual.py   target, residual, two-part payouts
src/metrics.py          metrics, premiums, objectives, break-even loading
src/backtest.py         train/test backtest of A vs B
src/station_hedge.py    station contract payout (Ehfaz)
src/load_weather.py     data loading and alignment (Qasim)
scripts/run_experiment.py
docs/notes/             per-person notes
```
