# Rain-count market experiment (SIMULATED)

Everything below is a simulation from the LMSR cost rule. No real orders, no real money, no live chain, no real traders.
Only the Trenton season counts are observed data. Written by `python -m sim.experiment`. Do not edit by hand.

## The registered product (docs/PHASE2_PREREG.md, strategy 3)

TRAIN seasons: 1999-2014 (16 usable, calendar all_days, column loss_days). Counts by season: 2, 6, 6, 4, 8, 5, 5, 8, 2, 4, 12, 2, 1, 6, 12, 3.
Sorted: 1, 2, 2, 2, 3, 4, 4, 5, 5, 6, 6, 6, 8, 8, 12, 12.

Quantiles 1/6, 2/6, 3/6, 4/6, 5/6 of the counts: 2, 4, 5, 6, 8 (smallest count with at least that share of seasons at or below it); 2, 4, 5, 6, 8 (linear interpolation, the numpy default).
**Registered edges: [2, 4, 5, 6, 8].** The five quantiles are all different, so there are six distinct buckets. No ties had to be merged and no edge was moved.
Two buckets are one count wide (5 and 6). That is what the quantile rule gives; it was not changed.

| bucket | loss days | TRAIN seasons n_j | TRAIN counts in bucket | bucket mean m_j | smoothed probability q_j | holding h_j, d = 2 | holding h_j, d = 3 | holding h_j, d = 4 |
|---|---|---|---|---|---|---|---|---|
| 0 | 0-2 | 4 | 1 2 2 2 | 1.7500 | 0.2368 | 0.0000 | 0.0000 | 0.0000 |
| 1 | 3-4 | 3 | 3 4 4 | 3.6667 | 0.1842 | 1.6667 | 0.6667 | 0.0000 |
| 2 | 5 | 2 | 5 5 | 5.0000 | 0.1316 | 3.0000 | 2.0000 | 1.0000 |
| 3 | 6 | 3 | 6 6 6 | 6.0000 | 0.1842 | 4.0000 | 3.0000 | 2.0000 |
| 4 | 7-8 | 2 | 8 8 | 8.0000 | 0.1316 | 6.0000 | 5.0000 | 4.0000 |
| 5 | 9+ | 2 | 12 12 | 12.0000 | 0.1316 | 10.0000 | 9.0000 | 8.0000 |

- m_j is the TRAIN mean count in the bucket. q_j = (n_j + 0.5) / (N + 3).
- A hedge of size s holds s x h_j shares of bucket j, h_j = max(m_j - d, 0). It pays s x h_j units of L if the season's count lands in bucket j.
- **The deductible d is not known yet.** The evaluation workstream chooses it on TRAIN. Every table below shows d = 2, 3, 4.
- On the contract shares are whole numbers. All h_j are multiples of 1/12 here, so a payout unit of L/12 makes every holding whole (multiply the shares and b by 12). The simulation uses the exact fractions.

| d | expected payout per unit of size, sum h_j q_j | registered MODELLED premium (x 1.20) | value at uniform prices, sum h_j / 6 | uniform value / expected payout |
|---|---|---|---|---|
| 2 | 3.5439 | 4.2526 | 4.1111 | 1.160 |
| 3 | 2.7807 | 3.3368 | 3.2778 | 1.179 |
| 4 | 2.0789 | 2.4947 | 2.5000 | 1.203 |

## Set-up of the simulation

- (a) Uniform start: the hedger is the first trader; every bucket costs 1/6.
- (b) Informed start: a made-up informed trader first buys until the prices equal q. Then the hedger buys.
- The contract has no sell function, so prices move only when somebody buys.
- One hedger per market. "Expected" always means: if the count really follows q.
- One unit = L, the park's loss per loss day (read as $1).

## Headline table (SIMULATED): price paid per 1 of expected payout

1.00 is fair under q. The registered MODELLED premium is 1.20. Each cell shows d = 2 / 3 / 4.

| start | b | sponsor worst-case loss b ln 6 | size 10 | size 100 | size 1,000 |
|---|---|---|---|---|---|
| uniform | 50 | 89.6 | 1.48 / 1.55 / 1.65 | 2.57 / 2.91 / 3.42 | 2.80 / 3.20 / 3.81 |
| uniform | 200 | 358.4 | 1.24 / 1.26 / 1.30 | 1.93 / 2.10 / 2.34 | 2.72 / 3.11 / 3.68 |
| uniform | 1,000 | 1,791.8 | 1.17 / 1.20 / 1.22 | 1.32 / 1.36 / 1.41 | 2.32 / 2.60 / 3.00 |
| uniform | 5,000 | 8,958.8 | 1.16 / 1.18 / 1.21 | 1.19 / 1.21 / 1.24 | 1.48 / 1.55 / 1.65 |
| uniform | 20,000 | 35,835.2 | 1.16 / 1.18 / 1.20 | 1.17 / 1.19 / 1.21 | 1.24 / 1.26 / 1.30 |
| informed | 50 | 89.6 | 1.32 / 1.36 / 1.42 | 2.54 / 2.87 / 3.36 | 2.79 / 3.20 / 3.80 |
| informed | 200 | 358.4 | 1.07 / 1.08 / 1.09 | 1.81 / 1.95 / 2.14 | 2.71 / 3.09 / 3.65 |
| informed | 1,000 | 1,791.8 | 1.01 / 1.02 / 1.02 | 1.15 / 1.17 / 1.19 | 2.26 / 2.52 / 2.88 |
| informed | 5,000 | 8,958.8 | 1.00 / 1.00 / 1.00 | 1.03 / 1.03 / 1.03 | 1.32 / 1.36 / 1.42 |
| informed | 20,000 | 35,835.2 | 1.00 / 1.00 / 1.00 | 1.01 / 1.01 / 1.01 | 1.07 / 1.08 / 1.09 |

## Price impact (SIMULATED)

Impact = cost divided by the hedge's value at the pre-trade prices, minus 1. Each cell shows d = 2 / 3 / 4.

| start | b | size 10 | size 100 | size 1,000 |
|---|---|---|---|---|
| uniform | 50 | 27.7% / 31.7% / 36.8% | 121.5% / 147.2% / 184.2% | 141.1% / 171.8% / 216.4% |
| uniform | 200 | 6.5% / 7.3% / 8.3% | 66.4% / 78.5% / 94.6% | 134.5% / 163.6% / 205.7% |
| uniform | 1,000 | 1.3% / 1.4% / 1.6% | 13.4% / 15.1% / 17.3% | 100.2% / 120.6% / 149.2% |
| uniform | 5,000 | 0.3% / 0.3% / 0.3% | 2.6% / 2.8% / 3.2% | 27.7% / 31.7% / 36.8% |
| uniform | 20,000 | 0.1% / 0.1% / 0.1% | 0.6% / 0.7% / 0.8% | 6.5% / 7.3% / 8.3% |
| informed | 50 | 32.2% / 36.2% / 41.5% | 153.6% / 187.2% / 236.0% | 179.3% / 220.0% / 279.9% |
| informed | 200 | 7.3% / 8.0% / 9.0% | 81.2% / 95.4% / 114.5% | 170.7% / 209.1% / 265.3% |
| informed | 1,000 | 1.4% / 1.5% / 1.7% | 15.2% / 16.8% / 19.0% | 125.6% / 151.5% / 188.4% |
| informed | 5,000 | 0.3% / 0.3% / 0.3% | 2.9% / 3.1% / 3.5% | 32.2% / 36.2% / 41.5% |
| informed | 20,000 | 0.1% / 0.1% / 0.1% | 0.7% / 0.8% / 0.9% | 7.3% / 8.0% / 9.0% |

## LMSR price against the registered premium (SIMULATED against MODELLED)

LMSR cost divided by the registered premium (1.20 x expected payout). Below 1.00 the market is cheaper than the modelled premium; above 1.00 it is dearer. Each cell shows d = 2 / 3 / 4.

| start | b | size 10 | size 100 | size 1,000 |
|---|---|---|---|---|
| uniform | 50 | 1.23 / 1.29 / 1.37 | 2.14 / 2.43 / 2.85 | 2.33 / 2.67 / 3.17 |
| uniform | 200 | 1.03 / 1.05 / 1.09 | 1.61 / 1.75 / 1.95 | 2.27 / 2.59 / 3.06 |
| uniform | 1,000 | 0.98 / 1.00 / 1.02 | 1.10 / 1.13 / 1.18 | 1.94 / 2.17 / 2.50 |
| uniform | 5,000 | 0.97 / 0.99 / 1.01 | 0.99 / 1.01 / 1.03 | 1.23 / 1.29 / 1.37 |
| uniform | 20,000 | 0.97 / 0.98 / 1.00 | 0.97 / 0.99 / 1.01 | 1.03 / 1.05 / 1.09 |
| informed | 50 | 1.10 / 1.14 / 1.18 | 2.11 / 2.39 / 2.80 | 2.33 / 2.67 / 3.17 |
| informed | 200 | 0.89 / 0.90 / 0.91 | 1.51 / 1.63 / 1.79 | 2.26 / 2.58 / 3.04 |
| informed | 1,000 | 0.85 / 0.85 / 0.85 | 0.96 / 0.97 / 0.99 | 1.88 / 2.10 / 2.40 |
| informed | 5,000 | 0.84 / 0.84 / 0.84 | 0.86 / 0.86 / 0.86 | 1.10 / 1.14 / 1.18 |
| informed | 20,000 | 0.83 / 0.83 / 0.83 | 0.84 / 0.84 / 0.84 | 0.89 / 0.90 / 0.91 |

Reading:
- Uniform start: even with no impact the hedge costs sum h_j / 6 instead of sum h_j q_j (ratio in the product table above). The hedge buys the high buckets, and the uniform start prices them at 1/6 each while q gives the top three 0.13 to 0.18.
- Informed start: the price is 1.00 plus impact. It is below the registered 1.20 only when b is large against the hedge.
  - d = 2: the LMSR price equals 1.20 at b = 7.76 x hedge size (sponsor worst-case loss 13.90 x hedge size).
  - d = 3: the LMSR price equals 1.20 at b = 8.52 x hedge size (sponsor worst-case loss 15.27 x hedge size).
  - d = 4: the LMSR price equals 1.20 at b = 9.53 x hedge size (sponsor worst-case loss 17.08 x hedge size).

## Who pays for the sponsor? Break-even fee, scenario (b) (SIMULATED, hypothetical fee)

The informed trader buys at uniform prices what is worth more under q. If q is right, the sponsor expects to lose b x KL(q || uniform) = **0.02679 x b** to that trader. With the uniform start this is the cost of finding the price.
The hedger pays more than the expected payout (impact). That excess goes to the sponsor.
Sponsor expected P&L = hedger's excess - informed trader's expected profit. Where it is negative, a fee could cover it.
The contract charges NO fee. The fee below is hypothetical, and it assumes the fee changes nobody's trades.

- Fee on all trades = shortfall / (informed trader's cost + hedger's cost).
- Fee on the hedger only = shortfall / hedger's cost. This is the honest one: an informed trader who pays a fee trades less.
- 0.0% means the hedger's impact already covers the sponsor.
- With no hedger at all, the fee on the informed trader's own cost would have to be 11.3%. That is the upper limit of the fee on all trades, whatever b is.

| b | size | d | informed trader's expected profit | hedger pays above expected payout | sponsor expected P&L | fee on all trades | fee on hedger only | hedger's price per 1 with that fee | registered premium |
|---|---|---|---|---|---|---|---|---|---|
| 50 | 10 | 2 | 1.34 | 11.42 | 10.08 | 0.00% | 0.00% | 1.322 | 1.20 |
| 50 | 10 | 3 | 1.34 | 10.07 | 8.73 | 0.00% | 0.00% | 1.362 | 1.20 |
| 50 | 10 | 4 | 1.34 | 8.63 | 7.29 | 0.00% | 0.00% | 1.415 | 1.20 |
| 50 | 100 | 2 | 1.34 | 544.22 | 542.88 | 0.00% | 0.00% | 2.536 | 1.20 |
| 50 | 100 | 3 | 1.34 | 520.54 | 519.20 | 0.00% | 0.00% | 2.872 | 1.20 |
| 50 | 100 | 4 | 1.34 | 490.72 | 489.38 | 0.00% | 0.00% | 3.360 | 1.20 |
| 50 | 1,000 | 2 | 1.34 | 6,354.73 | 6,353.39 | 0.00% | 0.00% | 2.793 | 1.20 |
| 50 | 1,000 | 3 | 1.34 | 6,117.89 | 6,116.55 | 0.00% | 0.00% | 3.200 | 1.20 |
| 50 | 1,000 | 4 | 1.34 | 5,819.65 | 5,818.31 | 0.00% | 0.00% | 3.799 | 1.20 |
| 200 | 10 | 2 | 5.36 | 2.60 | -2.76 | 3.23% | 7.25% | 1.151 | 1.20 |
| 200 | 10 | 3 | 5.36 | 2.23 | -3.13 | 4.05% | 10.42% | 1.193 | 1.20 |
| 200 | 10 | 4 | 5.36 | 1.87 | -3.49 | 4.99% | 15.39% | 1.258 | 1.20 |
| 200 | 100 | 2 | 5.36 | 287.64 | 282.28 | 0.00% | 0.00% | 1.812 | 1.20 |
| 200 | 100 | 3 | 5.36 | 265.19 | 259.84 | 0.00% | 0.00% | 1.954 | 1.20 |
| 200 | 100 | 4 | 5.36 | 238.00 | 232.64 | 0.00% | 0.00% | 2.145 | 1.20 |
| 200 | 1,000 | 2 | 5.36 | 6,050.51 | 6,045.15 | 0.00% | 0.00% | 2.707 | 1.20 |
| 200 | 1,000 | 3 | 5.36 | 5,813.67 | 5,808.31 | 0.00% | 0.00% | 3.091 | 1.20 |
| 200 | 1,000 | 4 | 5.36 | 5,515.42 | 5,510.07 | 0.00% | 0.00% | 3.653 | 1.20 |
| 1,000 | 10 | 2 | 26.79 | 0.50 | -26.28 | 9.65% | 73.13% | 1.756 | 1.20 |
| 1,000 | 10 | 3 | 26.79 | 0.43 | -26.36 | 9.96% | 93.35% | 1.963 | 1.20 |
| 1,000 | 10 | 4 | 26.79 | 0.36 | -26.43 | 10.26% | 124.98% | 2.289 | 1.20 |
| 1,000 | 100 | 2 | 26.79 | 53.95 | 27.16 | 0.00% | 0.00% | 1.152 | 1.20 |
| 1,000 | 100 | 3 | 26.79 | 46.68 | 19.90 | 0.00% | 0.00% | 1.168 | 1.20 |
| 1,000 | 100 | 4 | 26.79 | 39.43 | 12.64 | 0.00% | 0.00% | 1.190 | 1.20 |
| 1,000 | 1,000 | 2 | 26.79 | 4,450.84 | 4,424.06 | 0.00% | 0.00% | 2.256 | 1.20 |
| 1,000 | 1,000 | 3 | 26.79 | 4,214.14 | 4,187.35 | 0.00% | 0.00% | 2.515 | 1.20 |
| 1,000 | 1,000 | 4 | 26.79 | 3,916.40 | 3,889.61 | 0.00% | 0.00% | 2.884 | 1.20 |
| 5,000 | 10 | 2 | 133.94 | 0.10 | -133.84 | 10.99% | 376.60% | 4.779 | 1.20 |
| 5,000 | 10 | 3 | 133.94 | 0.08 | -133.85 | 11.06% | 479.89% | 5.817 | 1.20 |
| 5,000 | 10 | 4 | 133.94 | 0.07 | -133.87 | 11.13% | 641.72% | 7.443 | 1.20 |
| 5,000 | 100 | 2 | 133.94 | 10.15 | -123.79 | 8.00% | 33.96% | 1.378 | 1.20 |
| 5,000 | 100 | 3 | 133.94 | 8.66 | -125.28 | 8.53% | 43.69% | 1.482 | 1.20 |
| 5,000 | 100 | 4 | 133.94 | 7.24 | -126.70 | 9.07% | 58.90% | 1.644 | 1.20 |
| 5,000 | 1,000 | 2 | 133.94 | 1,142.00 | 1,008.06 | 0.00% | 0.00% | 1.322 | 1.20 |
| 5,000 | 1,000 | 3 | 133.94 | 1,006.82 | 872.89 | 0.00% | 0.00% | 1.362 | 1.20 |
| 5,000 | 1,000 | 4 | 133.94 | 863.10 | 729.17 | 0.00% | 0.00% | 1.415 | 1.20 |
| 20,000 | 10 | 2 | 535.75 | 0.02 | -535.72 | 11.25% | 1510.62% | 16.118 | 1.20 |
| 20,000 | 10 | 3 | 535.75 | 0.02 | -535.72 | 11.27% | 1925.11% | 20.267 | 1.20 |
| 20,000 | 10 | 4 | 535.75 | 0.02 | -535.73 | 11.28% | 2574.73% | 26.770 | 1.20 |
| 20,000 | 100 | 2 | 535.75 | 2.51 | -533.24 | 10.49% | 149.41% | 2.512 | 1.20 |
| 20,000 | 100 | 3 | 535.75 | 2.13 | -533.61 | 10.66% | 190.44% | 2.927 | 1.20 |
| 20,000 | 100 | 4 | 535.75 | 1.78 | -533.97 | 10.81% | 254.67% | 3.577 | 1.20 |
| 20,000 | 1,000 | 2 | 535.75 | 259.94 | -275.80 | 3.23% | 7.25% | 1.151 | 1.20 |
| 20,000 | 1,000 | 3 | 535.75 | 222.90 | -312.85 | 4.05% | 10.42% | 1.193 | 1.20 |
| 20,000 | 1,000 | 4 | 535.75 | 187.01 | -348.74 | 4.99% | 15.39% | 1.258 | 1.20 |

The same thing in one line per d. Only b / size matters, so these hold for every hedge size (one hedger per market):

| d | expected payout per unit of size | self-financing point: b / size | hedger's price per 1 there, no fee | b / size where the LMSR price is 1.20 | fee on the hedger needed there | hedger's price per 1 with that fee |
|---|---|---|---|---|---|---|
| 2 | 3.5439 | 14.045 | 1.106 | 7.757 | 0.00% | 1.200 |
| 3 | 2.7807 | 13.063 | 1.126 | 8.520 | 0.00% | 1.200 |
| 4 | 2.0789 | 12.027 | 1.155 | 9.530 | 0.00% | 1.200 |

Reading:
- Self-financing point: the b at which the hedger's impact exactly pays for the informed trader. Smaller b: the sponsor expects a profit and the hedger pays more. Larger b: the hedger pays less and the sponsor expects a loss.
- At the b where the LMSR price equals the registered 1.20, the sponsor expects a profit, so no fee is needed.
- A deeper market (large b against the hedge) gives the hedger a price near 1.00 and leaves the sponsor a loss of about 0.0268 x b. A fee on the hedger of (that loss / hedge cost) would cover it; the table shows when that fee pushes the hedger's all-in price above 1.20.
- With several hedgers in one market the informed trader is paid for once and the fee per hedger falls. That was not simulated.

## All rows (SIMULATED)

| start | b | size | d | max payout | expected payout | cost | price per 1 | cost / registered premium | impact | top-bucket price before -> after | sponsor worst P&L after these trades | bound -b ln 6 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| uniform | 50 | 10 | 2 | 100 | 35.44 | 52.52 | 1.482 | 1.235 | 27.7% | 0.167 -> 0.431 | -47.5 | -89.6 |
| uniform | 50 | 10 | 3 | 90 | 27.81 | 43.16 | 1.552 | 1.293 | 31.7% | 0.167 -> 0.425 | -46.8 | -89.6 |
| uniform | 50 | 10 | 4 | 80 | 20.79 | 34.20 | 1.645 | 1.371 | 36.8% | 0.167 -> 0.417 | -45.8 | -89.6 |
| uniform | 50 | 100 | 2 | 1,000 | 354.39 | 910.43 | 2.569 | 2.141 | 121.5% | 0.167 -> 1.000 | -89.6 | -89.6 |
| uniform | 50 | 100 | 3 | 900 | 278.07 | 810.43 | 2.914 | 2.429 | 147.2% | 0.167 -> 1.000 | -89.6 | -89.6 |
| uniform | 50 | 100 | 4 | 800 | 207.89 | 710.43 | 3.417 | 2.848 | 184.2% | 0.167 -> 1.000 | -89.6 | -89.6 |
| uniform | 50 | 1,000 | 2 | 10,000 | 3,543.86 | 9,910.41 | 2.797 | 2.330 | 141.1% | 0.167 -> 1.000 | -89.6 | -89.6 |
| uniform | 50 | 1,000 | 3 | 9,000 | 2,780.70 | 8,910.41 | 3.204 | 2.670 | 171.8% | 0.167 -> 1.000 | -89.6 | -89.6 |
| uniform | 50 | 1,000 | 4 | 8,000 | 2,078.95 | 7,910.41 | 3.805 | 3.171 | 216.4% | 0.167 -> 1.000 | -89.6 | -89.6 |
| uniform | 200 | 10 | 2 | 100 | 35.44 | 43.79 | 1.236 | 1.030 | 6.5% | 0.167 -> 0.221 | -56.2 | -358.4 |
| uniform | 200 | 10 | 3 | 90 | 27.81 | 35.16 | 1.264 | 1.054 | 7.3% | 0.167 -> 0.219 | -54.8 | -358.4 |
| uniform | 200 | 10 | 4 | 80 | 20.79 | 27.07 | 1.302 | 1.085 | 8.3% | 0.167 -> 0.217 | -52.9 | -358.4 |
| uniform | 200 | 100 | 2 | 1,000 | 354.39 | 684.28 | 1.931 | 1.609 | 66.4% | 0.167 -> 0.808 | -315.7 | -358.4 |
| uniform | 200 | 100 | 3 | 900 | 278.07 | 584.98 | 2.104 | 1.753 | 78.5% | 0.167 -> 0.805 | -315.0 | -358.4 |
| uniform | 200 | 100 | 4 | 800 | 207.89 | 486.59 | 2.341 | 1.950 | 94.6% | 0.167 -> 0.799 | -313.4 | -358.4 |
| uniform | 200 | 1,000 | 2 | 10,000 | 3,543.86 | 9,641.65 | 2.721 | 2.267 | 134.5% | 0.167 -> 1.000 | -358.4 | -358.4 |
| uniform | 200 | 1,000 | 3 | 9,000 | 2,780.70 | 8,641.65 | 3.108 | 2.590 | 163.6% | 0.167 -> 1.000 | -358.4 | -358.4 |
| uniform | 200 | 1,000 | 4 | 8,000 | 2,078.95 | 7,641.65 | 3.676 | 3.063 | 205.7% | 0.167 -> 1.000 | -358.4 | -358.4 |
| uniform | 1,000 | 10 | 2 | 100 | 35.44 | 41.63 | 1.175 | 0.979 | 1.3% | 0.167 -> 0.177 | -58.4 | -1,791.8 |
| uniform | 1,000 | 10 | 3 | 90 | 27.81 | 33.24 | 1.195 | 0.996 | 1.4% | 0.167 -> 0.176 | -56.8 | -1,791.8 |
| uniform | 1,000 | 10 | 4 | 80 | 20.79 | 25.40 | 1.222 | 1.018 | 1.6% | 0.167 -> 0.176 | -54.6 | -1,791.8 |
| uniform | 1,000 | 100 | 2 | 1,000 | 354.39 | 466.19 | 1.315 | 1.096 | 13.4% | 0.167 -> 0.284 | -533.8 | -1,791.8 |
| uniform | 1,000 | 100 | 3 | 900 | 278.07 | 377.13 | 1.356 | 1.130 | 15.1% | 0.167 -> 0.281 | -522.9 | -1,791.8 |
| uniform | 1,000 | 100 | 4 | 800 | 207.89 | 293.16 | 1.410 | 1.175 | 17.3% | 0.167 -> 0.277 | -506.8 | -1,791.8 |
| uniform | 1,000 | 1,000 | 2 | 10,000 | 3,543.86 | 8,229.99 | 2.322 | 1.935 | 100.2% | 0.167 -> 0.978 | -1,770.0 | -1,791.8 |
| uniform | 1,000 | 1,000 | 3 | 9,000 | 2,780.70 | 7,230.07 | 2.600 | 2.167 | 120.6% | 0.167 -> 0.978 | -1,769.9 | -1,791.8 |
| uniform | 1,000 | 1,000 | 4 | 8,000 | 2,078.95 | 6,230.37 | 2.997 | 2.497 | 149.2% | 0.167 -> 0.978 | -1,769.6 | -1,791.8 |
| uniform | 5,000 | 10 | 2 | 100 | 35.44 | 41.22 | 1.163 | 0.969 | 0.3% | 0.167 -> 0.169 | -58.8 | -8,958.8 |
| uniform | 5,000 | 10 | 3 | 90 | 27.81 | 32.87 | 1.182 | 0.985 | 0.3% | 0.167 -> 0.169 | -57.1 | -8,958.8 |
| uniform | 5,000 | 10 | 4 | 80 | 20.79 | 25.08 | 1.206 | 1.005 | 0.3% | 0.167 -> 0.169 | -54.9 | -8,958.8 |
| uniform | 5,000 | 100 | 2 | 1,000 | 354.39 | 421.64 | 1.190 | 0.991 | 2.6% | 0.167 -> 0.187 | -578.4 | -8,958.8 |
| uniform | 5,000 | 100 | 3 | 900 | 278.07 | 337.09 | 1.212 | 1.010 | 2.8% | 0.167 -> 0.187 | -562.9 | -8,958.8 |
| uniform | 5,000 | 100 | 4 | 800 | 207.89 | 258.07 | 1.241 | 1.034 | 3.2% | 0.167 -> 0.186 | -541.9 | -8,958.8 |
| uniform | 5,000 | 1,000 | 2 | 10,000 | 3,543.86 | 5,251.91 | 1.482 | 1.235 | 27.7% | 0.167 -> 0.431 | -4,748.1 | -8,958.8 |
| uniform | 5,000 | 1,000 | 3 | 9,000 | 2,780.70 | 4,316.03 | 1.552 | 1.293 | 31.7% | 0.167 -> 0.425 | -4,684.0 | -8,958.8 |
| uniform | 5,000 | 1,000 | 4 | 8,000 | 2,078.95 | 3,420.45 | 1.645 | 1.371 | 36.8% | 0.167 -> 0.417 | -4,579.6 | -8,958.8 |
| uniform | 20,000 | 10 | 2 | 100 | 35.44 | 41.14 | 1.161 | 0.967 | 0.1% | 0.167 -> 0.167 | -58.9 | -35,835.2 |
| uniform | 20,000 | 10 | 3 | 90 | 27.81 | 32.80 | 1.180 | 0.983 | 0.1% | 0.167 -> 0.167 | -57.2 | -35,835.2 |
| uniform | 20,000 | 10 | 4 | 80 | 20.79 | 25.02 | 1.203 | 1.003 | 0.1% | 0.167 -> 0.167 | -55.0 | -35,835.2 |
| uniform | 20,000 | 100 | 2 | 1,000 | 354.39 | 413.72 | 1.167 | 0.973 | 0.6% | 0.167 -> 0.172 | -586.3 | -35,835.2 |
| uniform | 20,000 | 100 | 3 | 900 | 278.07 | 330.08 | 1.187 | 0.989 | 0.7% | 0.167 -> 0.171 | -569.9 | -35,835.2 |
| uniform | 20,000 | 100 | 4 | 800 | 207.89 | 251.99 | 1.212 | 1.010 | 0.8% | 0.167 -> 0.171 | -548.0 | -35,835.2 |
| uniform | 20,000 | 1,000 | 2 | 10,000 | 3,543.86 | 4,379.29 | 1.236 | 1.030 | 6.5% | 0.167 -> 0.221 | -5,620.7 | -35,835.2 |
| uniform | 20,000 | 1,000 | 3 | 9,000 | 2,780.70 | 3,516.11 | 1.264 | 1.054 | 7.3% | 0.167 -> 0.219 | -5,483.9 | -35,835.2 |
| uniform | 20,000 | 1,000 | 4 | 8,000 | 2,078.95 | 2,707.13 | 1.302 | 1.085 | 8.3% | 0.167 -> 0.217 | -5,292.9 | -35,835.2 |
| informed | 50 | 10 | 2 | 100 | 35.44 | 46.86 | 1.322 | 1.102 | 32.2% | 0.132 -> 0.381 | -41.3 | -89.6 |
| informed | 50 | 10 | 3 | 90 | 27.81 | 37.88 | 1.362 | 1.135 | 36.2% | 0.132 -> 0.373 | -40.3 | -89.6 |
| informed | 50 | 10 | 4 | 80 | 20.79 | 29.42 | 1.415 | 1.179 | 41.5% | 0.132 -> 0.362 | -38.8 | -89.6 |
| informed | 50 | 100 | 2 | 1,000 | 354.39 | 898.61 | 2.536 | 2.113 | 153.6% | 0.132 -> 1.000 | -89.6 | -89.6 |
| informed | 50 | 100 | 3 | 900 | 278.07 | 798.61 | 2.872 | 2.393 | 187.2% | 0.132 -> 1.000 | -89.6 | -89.6 |
| informed | 50 | 100 | 4 | 800 | 207.89 | 698.61 | 3.360 | 2.800 | 236.0% | 0.132 -> 1.000 | -89.6 | -89.6 |
| informed | 50 | 1,000 | 2 | 10,000 | 3,543.86 | 9,898.59 | 2.793 | 2.328 | 179.3% | 0.132 -> 1.000 | -89.6 | -89.6 |
| informed | 50 | 1,000 | 3 | 9,000 | 2,780.70 | 8,898.59 | 3.200 | 2.667 | 220.0% | 0.132 -> 1.000 | -89.6 | -89.6 |
| informed | 50 | 1,000 | 4 | 8,000 | 2,078.95 | 7,898.59 | 3.799 | 3.166 | 279.9% | 0.132 -> 1.000 | -89.6 | -89.6 |
| informed | 200 | 10 | 2 | 100 | 35.44 | 38.04 | 1.073 | 0.894 | 7.3% | 0.132 -> 0.179 | -32.2 | -358.4 |
| informed | 200 | 10 | 3 | 90 | 27.81 | 30.04 | 1.080 | 0.900 | 8.0% | 0.132 -> 0.178 | -40.2 | -358.4 |
| informed | 200 | 10 | 4 | 80 | 20.79 | 22.66 | 1.090 | 0.908 | 9.0% | 0.132 -> 0.175 | -47.6 | -358.4 |
| informed | 200 | 100 | 2 | 1,000 | 354.39 | 642.03 | 1.812 | 1.510 | 81.2% | 0.132 -> 0.788 | -310.7 | -358.4 |
| informed | 200 | 100 | 3 | 900 | 278.07 | 543.26 | 1.954 | 1.628 | 95.4% | 0.132 -> 0.783 | -309.5 | -358.4 |
| informed | 200 | 100 | 4 | 800 | 207.89 | 445.89 | 2.145 | 1.787 | 114.5% | 0.132 -> 0.773 | -306.8 | -358.4 |
| informed | 200 | 1,000 | 2 | 10,000 | 3,543.86 | 9,594.37 | 2.707 | 2.256 | 170.7% | 0.132 -> 1.000 | -358.4 | -358.4 |
| informed | 200 | 1,000 | 3 | 9,000 | 2,780.70 | 8,594.37 | 3.091 | 2.576 | 209.1% | 0.132 -> 1.000 | -358.4 | -358.4 |
| informed | 200 | 1,000 | 4 | 8,000 | 2,078.95 | 7,594.37 | 3.653 | 3.044 | 265.3% | 0.132 -> 1.000 | -358.4 | -358.4 |
| informed | 1,000 | 10 | 2 | 100 | 35.44 | 35.94 | 1.014 | 0.845 | 1.4% | 0.132 -> 0.140 | -315.5 | -1,791.8 |
| informed | 1,000 | 10 | 3 | 90 | 27.81 | 28.24 | 1.015 | 0.846 | 1.5% | 0.132 -> 0.140 | -323.2 | -1,791.8 |
| informed | 1,000 | 10 | 4 | 80 | 20.79 | 21.15 | 1.017 | 0.848 | 1.7% | 0.132 -> 0.140 | -330.3 | -1,791.8 |
| informed | 1,000 | 100 | 2 | 1,000 | 354.39 | 408.33 | 1.152 | 0.960 | 15.2% | 0.132 -> 0.238 | -355.3 | -1,791.8 |
| informed | 1,000 | 100 | 3 | 900 | 278.07 | 324.75 | 1.168 | 0.973 | 16.8% | 0.132 -> 0.234 | -338.9 | -1,791.8 |
| informed | 1,000 | 100 | 4 | 800 | 207.89 | 247.32 | 1.190 | 0.991 | 19.0% | 0.132 -> 0.229 | -316.3 | -1,791.8 |
| informed | 1,000 | 1,000 | 2 | 10,000 | 3,543.86 | 7,994.70 | 2.256 | 1.880 | 125.6% | 0.132 -> 0.977 | -1,768.9 | -1,791.8 |
| informed | 1,000 | 1,000 | 3 | 9,000 | 2,780.70 | 6,994.84 | 2.515 | 2.096 | 151.5% | 0.132 -> 0.977 | -1,768.8 | -1,791.8 |
| informed | 1,000 | 1,000 | 4 | 8,000 | 2,078.95 | 5,995.34 | 2.884 | 2.403 | 188.4% | 0.132 -> 0.977 | -1,768.3 | -1,791.8 |
| informed | 5,000 | 10 | 2 | 100 | 35.44 | 35.54 | 1.003 | 0.836 | 0.3% | 0.132 -> 0.133 | -1,721.5 | -8,958.8 |
| informed | 5,000 | 10 | 3 | 90 | 27.81 | 27.89 | 1.003 | 0.836 | 0.3% | 0.132 -> 0.133 | -1,729.1 | -8,958.8 |
| informed | 5,000 | 10 | 4 | 80 | 20.79 | 20.86 | 1.003 | 0.836 | 0.3% | 0.132 -> 0.133 | -1,736.1 | -8,958.8 |
| informed | 5,000 | 100 | 2 | 1,000 | 354.39 | 364.53 | 1.029 | 0.857 | 2.9% | 0.132 -> 0.149 | -1,392.5 | -8,958.8 |
| informed | 5,000 | 100 | 3 | 900 | 278.07 | 286.73 | 1.031 | 0.859 | 3.1% | 0.132 -> 0.149 | -1,470.3 | -8,958.8 |
| informed | 5,000 | 100 | 4 | 800 | 207.89 | 215.13 | 1.035 | 0.862 | 3.5% | 0.132 -> 0.148 | -1,541.9 | -8,958.8 |
| informed | 5,000 | 1,000 | 2 | 10,000 | 3,543.86 | 4,685.86 | 1.322 | 1.102 | 32.2% | 0.132 -> 0.381 | -4,132.2 | -8,958.8 |
| informed | 5,000 | 1,000 | 3 | 9,000 | 2,780.70 | 3,787.52 | 1.362 | 1.135 | 36.2% | 0.132 -> 0.373 | -4,030.5 | -8,958.8 |
| informed | 5,000 | 1,000 | 4 | 8,000 | 2,078.95 | 2,942.05 | 1.415 | 1.179 | 41.5% | 0.132 -> 0.362 | -3,876.0 | -8,958.8 |
| informed | 20,000 | 10 | 2 | 100 | 35.44 | 35.46 | 1.001 | 0.834 | 0.1% | 0.132 -> 0.132 | -6,992.5 | -35,835.2 |
| informed | 20,000 | 10 | 3 | 90 | 27.81 | 27.83 | 1.001 | 0.834 | 0.1% | 0.132 -> 0.132 | -7,000.1 | -35,835.2 |
| informed | 20,000 | 10 | 4 | 80 | 20.79 | 20.81 | 1.001 | 0.834 | 0.1% | 0.132 -> 0.132 | -7,007.2 | -35,835.2 |
| informed | 20,000 | 100 | 2 | 1,000 | 354.39 | 356.89 | 1.007 | 0.839 | 0.7% | 0.132 -> 0.136 | -6,671.1 | -35,835.2 |
| informed | 20,000 | 100 | 3 | 900 | 278.07 | 280.20 | 1.008 | 0.840 | 0.8% | 0.132 -> 0.136 | -6,747.8 | -35,835.2 |
| informed | 20,000 | 100 | 4 | 800 | 207.89 | 209.67 | 1.009 | 0.840 | 0.9% | 0.132 -> 0.136 | -6,818.3 | -35,835.2 |
| informed | 20,000 | 1,000 | 2 | 10,000 | 3,543.86 | 3,803.80 | 1.073 | 0.894 | 7.3% | 0.132 -> 0.179 | -3,224.2 | -35,835.2 |
| informed | 20,000 | 1,000 | 3 | 9,000 | 2,780.70 | 3,003.60 | 1.080 | 0.900 | 8.0% | 0.132 -> 0.178 | -4,024.4 | -35,835.2 |
| informed | 20,000 | 1,000 | 4 | 8,000 | 2,078.95 | 2,265.96 | 1.090 | 0.908 | 9.0% | 0.132 -> 0.175 | -4,762.0 | -35,835.2 |

## Gas (local Hardhat EVM, NOT Sepolia)

From results/market/gas_report.json, written by `npm test` in contracts/ (test/15_rain_gas.test.js). Gas does not depend on b and barely on the hedge size; it depends on whether storage slots are written for the first time.

| function | calls measured | min | median | max |
|---|---|---|---|---|
| buy (one bucket, first buy of this buyer) | 1 | 179,507 | 179,507 | 179,507 |
| buy (one bucket, repeat) | 2 | 111,313 | 111,451 | 111,451 |
| buyBasket all six buckets (first buy of this buyer) | 1 | 314,308 | 314,308 | 314,308 |
| buyBasket all six buckets (repeat) | 1 | 143,266 | 143,266 | 143,266 |
| buyBasket stepped [0,0,0,1,2,3] x size (first buy of this buyer) | 3 | 199,332 | 199,924 | 233,832 |
| buyBasket stepped [0,0,0,1,2,3] x size (repeat) | 3 | 117,196 | 131,214 | 131,436 |
| cancelAfterDeadline | 1 | 106,570 | 106,570 | 106,570 |
| claimRefund | 2 | 39,539 | 39,539 | 39,539 |
| deploy RainCountLMSR | 1 | 3,776,901 | 3,776,901 | 3,776,901 |
| deploy SeasonCountOracle | 1 | 840,559 | 840,559 | 840,559 |
| emergencyCancel | 1 | 95,391 | 95,391 | 95,391 |
| oracle.openSeason | 1 | 49,167 | 49,167 | 49,167 |
| oracle.reportCount | 1 | 56,241 | 56,241 | 56,241 |
| oracle.setReporter | 1 | 45,727 | 45,727 | 45,727 |
| oracle.voidReport | 1 | 31,012 | 31,012 | 31,012 |
| redeem | 2 | 44,585 | 44,585 | 44,585 |
| settle | 1 | 159,975 | 159,975 | 159,975 |
| sponsorWithdraw | 2 | 36,444 | 36,444 | 36,444 |
| stepped x100 as ONE basket (fresh market) | 1 | 268,264 | 268,264 | 268,264 |
| stepped x100 by THREE single buys (fresh market, sum) | 1 | 471,341 | 471,341 | 471,341 |
| sweepUnclaimed | 1 | 39,805 | 39,805 | 39,805 |

## Limits

- No real traders. The LMSR is a pricing rule. It finds a fair price only if informed traders show up.
- Nobody can sell the price down (buy only). A hedger who trades first pays the uniform prices plus impact.
- q rests on 16 seasons at one station. "Fair" and "expected" mean fair under q, not under the true climate.
- The deductible d is not chosen yet; d = 2, 3, 4 are shown side by side.
- Some other quantile conventions interpolate to a non-whole number at 2/6 (about 3.7 to 3.8) and 5/6 (8.67 under one rule). Rounded to the observed counts they give the same edges, except that one rule could give 9 for the last edge. No TRAIN season has 9 loss days, so the TRAIN buckets, m_j and q_j would be the same.
- The informed trader is assumed to know q exactly and to move prices all the way. The fee is assumed not to change behaviour.
- The registered premium is MODELLED (expected payout x 1.20). Nobody has offered that price.
- Gas was measured locally. Sepolia gas prices and total fees were not measured.
