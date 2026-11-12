# Part 3 experiment summary (SIMULATED)

Everything below is a simulation from the LMSR cost rule. No real orders, no real money, no live chain.
Written by `python -m sim.experiment`. Do not edit by hand.

- Ladder: <80, 80-81, 82-83, 84-85, 86-87, 88-89, 90-91, 92-93, 94-95, 96-97, 98-99, >=100 (n = 12). Basket = all brackets >= 90F.
- One payout unit pays 1 if TMAX >= 90F. Prices are per 1 unit of payout (read as $ per $1).
- Climatology prior: USW00014734, May-Sep, FIT years 2015-2019, 765 days, add-one smoothing.
  FIT share of days >= 90F: 0.2078. Smoothed prior P(>=90F): 0.2124.

## Bracket prior

| bracket | FIT days | climatology prior | uniform prior |
|---|---|---|---|
| <80 | 266 | 0.3436 | 0.0833 |
| 80-81 | 65 | 0.0849 | 0.0833 |
| 82-83 | 55 | 0.0721 | 0.0833 |
| 84-85 | 76 | 0.0991 | 0.0833 |
| 86-87 | 81 | 0.1055 | 0.0833 |
| 88-89 | 63 | 0.0824 | 0.0833 |
| 90-91 | 58 | 0.0759 | 0.0833 |
| 92-93 | 44 | 0.0579 | 0.0833 |
| 94-95 | 28 | 0.0373 | 0.0833 |
| 96-97 | 18 | 0.0245 | 0.0833 |
| 98-99 | 11 | 0.0154 | 0.0833 |
| >=100 | 0 | 0.0013 | 0.0833 |

## Basket pricing (SIMULATED)

Impact = average price paid minus pre-trade price.

| prior | b | basket | pre-trade price | avg price paid | impact | impact % | post-trade price |
|---|---|---|---|---|---|---|---|
| uniform | 50 | 10 | 0.5000 | 0.5250 | 0.0250 | 4.99% | 0.5498 |
| uniform | 50 | 100 | 0.5000 | 0.7169 | 0.2169 | 43.38% | 0.8808 |
| uniform | 50 | 1,000 | 0.5000 | 0.9653 | 0.4653 | 93.07% | 1.0000 |
| uniform | 200 | 10 | 0.5000 | 0.5062 | 0.0062 | 1.25% | 0.5125 |
| uniform | 200 | 100 | 0.5000 | 0.5619 | 0.0619 | 12.37% | 0.6225 |
| uniform | 200 | 1,000 | 0.5000 | 0.8627 | 0.3627 | 72.54% | 0.9933 |
| uniform | 1,000 | 10 | 0.5000 | 0.5012 | 0.0012 | 0.25% | 0.5025 |
| uniform | 1,000 | 100 | 0.5000 | 0.5125 | 0.0125 | 2.50% | 0.5250 |
| uniform | 1,000 | 1,000 | 0.5000 | 0.6201 | 0.1201 | 24.02% | 0.7311 |
| uniform | 5,000 | 10 | 0.5000 | 0.5002 | 0.0002 | 0.05% | 0.5005 |
| uniform | 5,000 | 100 | 0.5000 | 0.5025 | 0.0025 | 0.50% | 0.5050 |
| uniform | 5,000 | 1,000 | 0.5000 | 0.5250 | 0.0250 | 4.99% | 0.5498 |
| climatology | 50 | 10 | 0.2128 | 0.2302 | 0.0174 | 8.17% | 0.2483 |
| climatology | 50 | 100 | 0.2128 | 0.4293 | 0.2165 | 101.70% | 0.6664 |
| climatology | 50 | 1,000 | 0.2128 | 0.9226 | 0.7098 | 333.50% | 1.0000 |
| climatology | 200 | 10 | 0.2125 | 0.2168 | 0.0042 | 1.99% | 0.2210 |
| climatology | 200 | 100 | 0.2125 | 0.2583 | 0.0458 | 21.55% | 0.3079 |
| climatology | 200 | 1,000 | 0.2125 | 0.6952 | 0.4827 | 227.11% | 0.9756 |
| climatology | 1,000 | 10 | 0.2124 | 0.2132 | 0.0008 | 0.39% | 0.2141 |
| climatology | 1,000 | 100 | 0.2124 | 0.2209 | 0.0085 | 4.01% | 0.2296 |
| climatology | 1,000 | 1,000 | 0.2124 | 0.3111 | 0.0987 | 46.48% | 0.4230 |
| climatology | 5,000 | 10 | 0.2124 | 0.2125 | 0.0002 | 0.08% | 0.2127 |
| climatology | 5,000 | 100 | 0.2124 | 0.2140 | 0.0017 | 0.79% | 0.2157 |
| climatology | 5,000 | 1,000 | 0.2124 | 0.2297 | 0.0174 | 8.18% | 0.2477 |

## Sponsor funding (worst-case loss, in payout units)

Uniform start: b ln(n). Seeded start: C(q0) - min(q0), about b ln(1/p_min). Integer seed shares.

| b | uniform b ln(12) | climatology start | extra subsidy for the non-uniform prior |
|---|---|---|---|
| 50 | 124.2 | 332.5 | 208.3 |
| 200 | 497.0 | 1,330.9 | 834.0 |
| 1,000 | 2,484.9 | 6,655.5 | 4,170.5 |
| 5,000 | 12,424.5 | 33,277.1 | 20,852.6 |

## Realised sponsor P&L under SIMULATED trade sequences

One market per day. Outcomes: observed TMAX at the station, May-Sep 2020-2025 (918 days, 0.2397 of them >= 90F). Trades are made up:
- `hedger_only`: one >= 90F basket of 100 units.
- `noise_then_hedger`: 20 uninformed buys (random bracket, 1-50 units), then the basket.
- `informed_then_hedger`: one trader with a forecast (error sd 3F) moves prices to that belief, then the basket.
P&L in payout units per market day. Negative = sponsor loss.

| scenario | prior | b | mean P&L | 5th pct | min | share of days with a loss | worst-case bound |
|---|---|---|---|---|---|---|---|
| hedger_only | uniform | 50 | 47.7 | -28.3 | -28.3 | 24.0% | -124.2 |
| noise_then_hedger | uniform | 50 | 62.8 | -46.6 | -106.6 | 17.8% | -124.2 |
| informed_then_hedger | uniform | 50 | -45.3 | -114.5 | -122.9 | 81.0% | -124.2 |
| hedger_only | uniform | 200 | 32.2 | -43.8 | -43.8 | 24.0% | -497.0 |
| noise_then_hedger | uniform | 200 | 36.9 | -68.6 | -157.9 | 26.5% | -497.0 |
| informed_then_hedger | uniform | 200 | -227.7 | -484.4 | -489.1 | 90.7% | -497.0 |
| hedger_only | uniform | 1,000 | 27.3 | -48.8 | -48.8 | 24.0% | -2,484.9 |
| noise_then_hedger | uniform | 1,000 | 29.3 | -76.4 | -170.0 | 28.9% | -2,484.9 |
| informed_then_hedger | uniform | 1,000 | -1,162.8 | -2,435.4 | -2,437.8 | 90.7% | -2,484.9 |
| hedger_only | uniform | 5,000 | 26.3 | -49.8 | -49.8 | 24.0% | -12,424.5 |
| noise_then_hedger | uniform | 5,000 | 27.8 | -77.9 | -172.2 | 29.3% | -12,424.5 |
| informed_then_hedger | uniform | 5,000 | -5,830.2 | -12,187.4 | -12,187.4 | 90.7% | -12,424.5 |
| hedger_only | climatology | 50 | 19.0 | -57.1 | -57.1 | 24.0% | -332.5 |
| noise_then_hedger | climatology | 50 | 33.5 | -73.5 | -147.0 | 27.0% | -332.5 |
| informed_then_hedger | climatology | 50 | -33.8 | -99.2 | -331.5 | 80.1% | -332.5 |
| hedger_only | climatology | 200 | 1.9 | -74.2 | -74.2 | 24.0% | -1,330.9 |
| noise_then_hedger | climatology | 200 | 5.9 | -98.8 | -195.7 | 35.7% | -1,330.9 |
| informed_then_hedger | climatology | 200 | -172.1 | -387.6 | -1,323.3 | 90.0% | -1,330.9 |
| hedger_only | climatology | 1,000 | -1.9 | -77.9 | -77.9 | 24.0% | -6,655.5 |
| noise_then_hedger | climatology | 1,000 | -0.3 | -105.7 | -206.9 | 39.4% | -6,655.5 |
| informed_then_hedger | climatology | 1,000 | -878.1 | -1,909.4 | -6,605.4 | 90.1% | -6,655.5 |
| hedger_only | climatology | 5,000 | -2.6 | -78.6 | -78.6 | 24.0% | -33,277.1 |
| noise_then_hedger | climatology | 5,000 | -1.5 | -107.6 | -208.7 | 40.0% | -33,277.1 |
| informed_then_hedger | climatology | 5,000 | -4,400.9 | -9,511.7 | -33,011.8 | 90.1% | -33,277.1 |

## Gas (local Hardhat EVM, not Sepolia)

From results/part3/gas_report.json, written by `npm test` in contracts/. Median gas per call.

| function | median gas | calls measured |
|---|---|---|
| buy (repeat buyer) | 148,627 | 2 |
| buy (single bracket) | 148,687 | 26 |
| buyBasket (6 brackets >= 90) | 429,980 | 2 |
| buyBasket (repeat buyer) | 190,998 | 2 |
| cancelAfterDeadline | 81,495 | 1 |
| claimRefund | 39,768 | 1 |
| deploy BracketLMSR (n=12) | 3,492,795 | 1 |
| deploy BracketLMSR (n=12, seeded prior) | 3,942,385 | 1 |
| deploy TemperatureOracle | 514,812 | 6 |
| emergencyCancel | 72,742 | 1 |
| oracle.reportTemperature | 50,661 | 2 |
| oracle.setReporter | 47,785 | 1 |
| redeem | 42,398 | 1 |
| settle | 139,446 | 1 |
| sponsorWithdraw | 36,444 | 1 |

Gas depends mainly on the number of brackets (12 exp calls per quote) and on whether storage slots are written for the first time. It barely changes with the basket size or b (see the repeat-buyer rows, measured at sizes 100 and 1,000).

## Limits

- No real traders. The LMSR sets a price rule. It does not find a fair probability without informed orders.
- The uniform prior prices >= 90F at 0.50, far above the FIT frequency. A hedger would overpay until someone trades it down, and the contract has no sell function.
- The climatology prior is one station and five summers. The top bracket had 0 FIT days, so its price is set by the smoothing constant.
- Scenario P&L depends on the made-up trade sizes and forecast error. It shows direction, not magnitude.
