# Rain-count market experiment (SIMULATED)

Everything below is a simulation from the LMSR cost rule. No real orders, no real money, no live chain.
Written by `python -m sim.experiment`. Do not edit by hand.

- Buckets (loss days in the season): 0-2, 3-4, 5-6, 7-8, 9-10, 11+. Edges [2, 4, 6, 8, 10] are EXAMPLE edges, not the final ones.
- Stepped hedge of size s: 1s shares of bucket 7-8, 2s shares of bucket 9-10, 3s shares of bucket 11+. One payout unit = 1 (read as $1).
- Count distribution ("climatology"): observed loss-day counts, 16 usable training seasons 1999-2014 from data/processed/rain/season_counts_TTN.csv, bucket frequencies with add-0.5 smoothing.
- Uniform start: the hedger is the first trader; every bucket costs 1/6.
- Informed start: a made-up informed trader first buys until the prices equal the climatology distribution.
- The contract has no sell function, so prices move only when somebody buys.

## Count distribution

Training seasons used: 1999-2014 (16 usable). Loss-day counts: 2, 6, 6, 4, 8, 5, 5, 8, 2, 4, 12, 2, 1, 6, 12, 3.

| bucket | seasons in bucket | climatology probability | uniform start price |
|---|---|---|---|
| 0-2 | 4 | 0.2368 | 0.1667 |
| 3-4 | 3 | 0.1842 | 0.1667 |
| 5-6 | 5 | 0.2895 | 0.1667 |
| 7-8 | 2 | 0.1316 | 0.1667 |
| 9-10 | 0 | 0.0263 | 0.1667 |
| 11+ | 2 | 0.1316 | 0.1667 |

Expected payout of a size-1 hedge under this distribution: 0.5789 units. Its cost at the uniform prices, before any impact: 1.0000 units.

## Hedge pricing (SIMULATED)

Price per 1 = cost divided by expected payout (1.00 is fair under the distribution above). Impact = cost divided by the hedge's value at the pre-trade prices, minus 1.

| start | b | size s | max payout | expected payout | cost | price per 1 of expected payout | impact | top-bucket price before -> after | sponsor worst-case loss b ln 6 |
|---|---|---|---|---|---|---|---|---|---|
| uniform | 50 | 10 | 30 | 5.79 | 11.39 | 1.968 | 13.9% | 0.167 -> 0.242 | 89.6 |
| uniform | 50 | 100 | 300 | 57.89 | 217.88 | 3.763 | 117.9% | 0.167 -> 0.861 | 89.6 |
| uniform | 50 | 1,000 | 3,000 | 578.95 | 2,910.41 | 5.027 | 191.0% | 0.167 -> 1.000 | 89.6 |
| uniform | 200 | 10 | 30 | 5.79 | 10.34 | 1.786 | 3.4% | 0.167 -> 0.184 | 358.4 |
| uniform | 200 | 100 | 300 | 57.89 | 136.09 | 2.351 | 36.1% | 0.167 -> 0.378 | 358.4 |
| uniform | 200 | 1,000 | 3,000 | 578.95 | 2,643.00 | 4.565 | 164.3% | 0.167 -> 0.993 | 358.4 |
| uniform | 1,000 | 10 | 30 | 5.79 | 10.07 | 1.739 | 0.7% | 0.167 -> 0.170 | 1,791.8 |
| uniform | 1,000 | 100 | 300 | 57.89 | 106.82 | 1.845 | 6.8% | 0.167 -> 0.202 | 1,791.8 |
| uniform | 1,000 | 1,000 | 3,000 | 578.95 | 1,710.58 | 2.955 | 71.1% | 0.167 -> 0.605 | 1,791.8 |
| uniform | 5,000 | 10 | 30 | 5.79 | 10.01 | 1.730 | 0.1% | 0.167 -> 0.167 | 8,958.8 |
| uniform | 5,000 | 100 | 300 | 57.89 | 101.34 | 1.750 | 1.3% | 0.167 -> 0.173 | 8,958.8 |
| uniform | 5,000 | 1,000 | 3,000 | 578.95 | 1,139.23 | 1.968 | 13.9% | 0.167 -> 0.242 | 8,958.8 |
| informed | 50 | 10 | 30 | 5.79 | 7.00 | 1.209 | 20.9% | 0.132 -> 0.208 | 89.6 |
| informed | 50 | 100 | 300 | 57.89 | 201.45 | 3.480 | 248.0% | 0.132 -> 0.944 | 89.6 |
| informed | 50 | 1,000 | 3,000 | 578.95 | 2,898.59 | 5.007 | 400.7% | 0.132 -> 1.000 | 89.6 |
| informed | 200 | 10 | 30 | 5.79 | 6.07 | 1.048 | 4.8% | 0.132 -> 0.148 | 358.4 |
| informed | 200 | 100 | 300 | 57.89 | 92.58 | 1.599 | 59.9% | 0.132 -> 0.371 | 358.4 |
| informed | 200 | 1,000 | 3,000 | 578.95 | 2,594.65 | 4.482 | 348.2% | 0.132 -> 0.999 | 358.4 |
| informed | 1,000 | 10 | 30 | 5.79 | 5.84 | 1.009 | 0.9% | 0.132 -> 0.135 | 1,791.8 |
| informed | 1,000 | 100 | 300 | 57.89 | 63.63 | 1.099 | 9.9% | 0.132 -> 0.167 | 1,791.8 |
| informed | 1,000 | 1,000 | 3,000 | 578.95 | 1,362.38 | 2.353 | 135.3% | 0.132 -> 0.677 | 1,791.8 |
| informed | 5,000 | 10 | 30 | 5.79 | 5.80 | 1.002 | 0.2% | 0.132 -> 0.132 | 8,958.8 |
| informed | 5,000 | 100 | 300 | 57.89 | 58.99 | 1.019 | 1.9% | 0.132 -> 0.138 | 8,958.8 |
| informed | 5,000 | 1,000 | 3,000 | 578.95 | 699.89 | 1.209 | 20.9% | 0.132 -> 0.208 | 8,958.8 |

## Sponsor (SIMULATED)

Worst-case loss is b ln 6 whatever happens (tested on the contract). Expected P&L assumes the count follows the distribution above. In the informed start it includes what the informed trader paid and is expected to win.

| start | b | size s | informed trader paid | sponsor expected P&L | sponsor worst P&L after these trades | bound -b ln 6 |
|---|---|---|---|---|---|---|
| uniform | 50 | 10 | 0.0 | 5.6 | -18.6 | -89.6 |
| uniform | 50 | 100 | 0.0 | 160.0 | -82.1 | -89.6 |
| uniform | 50 | 1,000 | 0.0 | 2,331.5 | -89.6 | -89.6 |
| uniform | 200 | 10 | 0.0 | 4.5 | -19.7 | -358.4 |
| uniform | 200 | 100 | 0.0 | 78.2 | -163.9 | -358.4 |
| uniform | 200 | 1,000 | 0.0 | 2,064.1 | -357.0 | -358.4 |
| uniform | 1,000 | 10 | 0.0 | 4.3 | -19.9 | -1,791.8 |
| uniform | 1,000 | 100 | 0.0 | 48.9 | -193.2 | -1,791.8 |
| uniform | 1,000 | 1,000 | 0.0 | 1,131.6 | -1,289.4 | -1,791.8 |
| uniform | 5,000 | 10 | 0.0 | 4.2 | -20.0 | -8,958.8 |
| uniform | 5,000 | 100 | 0.0 | 43.4 | -198.7 | -8,958.8 |
| uniform | 5,000 | 1,000 | 0.0 | 560.3 | -1,860.8 | -8,958.8 |
| informed | 50 | 10 | 92.3 | -6.3 | -20.6 | -89.6 |
| informed | 50 | 100 | 92.3 | 136.0 | -86.7 | -89.6 |
| informed | 50 | 1,000 | 92.3 | 2,312.1 | -89.6 | -89.6 |
| informed | 200 | 10 | 369.2 | -29.9 | -104.3 | -358.4 |
| informed | 200 | 100 | 369.2 | 4.5 | -160.1 | -358.4 |
| informed | 200 | 1,000 | 369.2 | 1,985.6 | -358.1 | -358.4 |
| informed | 1,000 | 10 | 1,845.8 | -150.6 | -546.2 | -1,791.8 |
| informed | 1,000 | 100 | 1,845.8 | -145.0 | -488.4 | -1,791.8 |
| informed | 1,000 | 1,000 | 1,845.8 | 632.7 | -1,401.2 | -1,791.8 |
| informed | 5,000 | 10 | 9,229.1 | -753.4 | -2,754.5 | -8,958.8 |
| informed | 5,000 | 100 | 9,229.1 | -752.4 | -2,701.4 | -8,958.8 |
| informed | 5,000 | 1,000 | 9,229.1 | -632.5 | -2,060.5 | -8,958.8 |

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
| deploy RainCountLMSR | 1 | 3,776,889 | 3,776,889 | 3,776,889 |
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
- At the uniform start the top three buckets cost 1/6 each, whatever the climate. A hedger who trades first pays that price plus impact. Nobody can sell the price down (buy only).
- The distribution rests on 16 seasons at one station. A bucket with 0 seasons gets its probability from the smoothing constant alone.
- The bucket edges are example edges. The rain workstream chooses the final edges on the training seasons.
- The counts file belongs to the rain workstream and may still change. Re-run this script after it does.
- The informed trader is assumed to know the climatology exactly and to move prices all the way.
- Gas was measured locally. Sepolia gas prices and total fees were not measured.
