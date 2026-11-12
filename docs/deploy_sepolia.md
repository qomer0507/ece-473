# Deploying the rain-count market on Sepolia with Remix and MetaMask

Testnet only. No real money. Never paste a private key or a seed phrase anywhere: MetaMask signs for you.

Status of this guide: every contract call below was run in the local Hardhat EVM by `npm test` (contracts/).
**Nothing here was tried in Remix, in MetaMask or on Sepolia** (the build machine has no access to them).
Treat the first run as a rehearsal and write down anything that differs.

Contracts (flattened, no imports, ready to paste):

- `contracts/remix/SeasonCountOracle_flat.sol` (the oracle)
- `contracts/remix/RainCountLMSR_flat.sol` (the market)

## 0. What you need

1. Three MetaMask accounts on the Sepolia network. Give them names in MetaMask:
   - **Reporter**: deploys the oracle, opens the season, reports the count.
   - **Sponsor**: deploys the market and funds it. Withdraws at the end.
   - **Buyer**: buys the hedge and redeems it.
2. Sepolia test ETH in all three (any Sepolia faucet). The example below needs about 0.03 ETH for the
   Sponsor, 0.01 for the Reporter and 0.01 for the Buyer, plus gas.
3. The Sponsor and the Reporter must be different accounts. See "Trust" at the end. Say this in the presentation.

## 1. Remix set-up

1. Open https://remix.ethereum.org. Create a blank workspace.
2. Create two files and paste the two flattened files into them.
3. Solidity compiler tab:
   - Compiler: **0.8.26**
   - Advanced configurations: **Enable optimization, 200 runs**. EVM version: default.
4. Compile both files. There should be no errors.
5. Deploy & run tab: Environment = **Injected Provider - MetaMask**. Check that Remix shows "Sepolia (11155111)".
6. Gas limit: choose **Estimated Gas**. If your Remix only has a number field, type `5000000`
   (deploying the market needs about 3.8 million gas; the old default of 3,000,000 is too small).

Rehearse once with Environment = **Remix VM** first. It is free and instant. Use the short demo times below.

## 2. Choose the numbers (before deploying anything)

### Times

All times are unix seconds. Get the current time from https://www.unixtimestamp.com, or deploy the oracle
first and call `currentTime()`. Call it `T`.

| name | meaning | demo value (about 45 minutes in total) | real season |
|---|---|---|---|
| seasonStart | first season day | T + 900 (15 min) | Friday before Memorial Day, 00:00 local |
| seasonEnd | count is final; report allowed from here | T + 1500 (25 min) | the day after Labor Day, plus a few days for the climate report |
| tradingClose | last moment to buy; must be <= seasonStart | T + 900 | same as seasonStart |
| reportDeadline | last moment for a valid report; must be > seasonEnd | T + 3300 (55 min) | seasonEnd + 14 days |
| disputeDelay | seconds `settle()` waits after the report | 0 (or 120 to show the window) | 2 days |
| claimPeriod | seconds to claim before the sponsor may sweep | 604800 (7 days, the minimum) | 2592000 (30 days) |

Write the four time numbers down before you start. In the demo you have 15 minutes to deploy the market and buy.
If that is too tight, add 600 to every time.

### Market size and funding

Example: `b = 100`, `unit = 100000000000000` wei (0.0001 ETH per payout unit).

The sponsor must send at least `floor(b * ln(6) * unit)` wei. This is also the most the sponsor can lose.

- By hand: `b * unit * 1.791759469228055`, rounded up.
- By script (repo root): `python -m sim.lmsr funding --b 100 --unit-wei 100000000000000`
- On chain, after any market is deployed: `requiredFundingFor(b, unit)`.

For the example: **17,917,594,692,280,550 wei** (0.017918 ETH). Send `18000000000000000` wei (0.018 ETH).
The extra 82,405,307,719,450 wei comes back with `sponsorWithdraw()` at the end.

### Buckets

`edges` are the last counts of the first five buckets. Example `[2,4,6,8,10]`:

| bucket | 0 | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| loss days | 0-2 | 3-4 | 5-6 | 7-8 | 9-10 | 11 or more |

These are example edges. Use the final edges from the rain workstream when they exist.
The last edge must be below `seasonDays`.

## 3. Deploy and run (numbered; record every transaction hash)

### Reporter account

1. In MetaMask switch to **Reporter**. In Remix select contract `SeasonCountOracle`. Click **Deploy**. Confirm in MetaMask.
   Record the oracle address.
2. Call `currentTime()` to check the clock. Compute your four times from it if you have not yet.
3. Call `openSeason` with:
   - station: `TTN`
   - season: `2027`
   - seasonStart: your number (T + 900)
   - seasonEnd: your number (T + 1500)
   - seasonDays: `102`
4. Check: `getSeason("TTN", 2027)` returns `opened = true` and your times.

### Sponsor account

5. In MetaMask switch to **Sponsor**. In Remix select contract `RainCountLMSR`.
6. In the **VALUE** field type `18000000000000000` and choose **Wei**.
7. Open the Deploy arguments and fill in:

   | argument | example |
   |---|---|
   | _oracle | the oracle address from step 1 |
   | _station | `TTN` |
   | _season | `2027` |
   | _edges | `[2,4,6,8,10]` |
   | _b | `100` |
   | _unit | `100000000000000` |
   | _tradingClose | T + 900 |
   | _reportDeadline | T + 3300 |
   | _disputeDelay | `0` |
   | _claimPeriod | `604800` |

8. Click **transact**. Confirm in MetaMask. Record the market address.
9. Check: `requiredFunding()` = 17917594692280550, `funding()` = 18000000000000000, `state()` = 0 (Open),
   `prices()` shows six numbers near 166666666666666666 (1/6 each; 1e18 means 100%).

### Buyer account: buy a stepped hedge

A stepped hedge pays more when the season is worse. Example: `[0,0,0,10,20,30]` pays 10 units for 7-8 loss
days, 20 units for 9-10, 30 units for 11 or more.

10. In MetaMask switch to **Buyer**.
11. Call `quoteBasket([0,0,0,10,20,30])`. From a fresh market it returns about 1068243163504235 wei (0.001068 ETH).
12. Add 2% for slippage: `maxCost = 1089608026774319`.
13. Type the same number in **VALUE** (Wei). Call `buyBasket` with quantities `[0,0,0,10,20,30]` and that maxCost.
    Confirm in MetaMask. The contract keeps the exact cost and sends back the rest in the same transaction.
14. Check: `sharesOfAll(buyer address)` = `[0,0,0,10,20,30]`; `paid(buyer address)` = the cost;
    `prices()` have moved (the top bucket is now about 0.202).
15. Optional: buy one bucket with `buy(bucket, shares, maxCost)` and compare with `quoteBuy(bucket, shares)`.
16. Remember to set VALUE back to 0 after each payable call.

### Wait for the season to end

17. Wait until the time is past `seasonEnd`. Call `currentTime()` on the oracle to see the chain's clock.
    To show the M3 fix, try `reportCount` before the season end from the Reporter account. Remix and MetaMask
    warn that the transaction will fail with "Season not over". Do not send it.

### Reporter account: report the count

18. Switch to **Reporter**. On the oracle call `reportCount("TTN", 2027, 9)`. (9 loss days is in bucket 4.)
    This works once. A second report is refused. Record the hash.
19. On the market, `hasValidReport()` now returns true.

### Anyone: settle

20. From any account call `settle()` on the market. If `disputeDelay` is not 0, wait that many seconds after the
    report first; before that the call fails with "Dispute window still open".
21. Check: `state()` = 1 (Settled), `settledCount()` = 9, `winningBucket()` = 4, `reserved()` = 2000000000000000.

### Buyer account: redeem

22. Switch to **Buyer**. Call `redeem()`. The buyer receives 20 shares x 0.0001 ETH = 0.002 ETH.
    A second `redeem()` fails with "Nothing to redeem".

### Sponsor account: withdraw

23. Switch to **Sponsor**. Call `sponsorWithdraw()`. The sponsor receives everything that is not owed to buyers:
    funding + what buyers paid - payout = 0.018 + 0.001068 - 0.002 = about 0.017068 ETH.
    The sponsor lost about 0.000932 ETH on this market. The bound was 0.017918 ETH.

### Cancel rehearsal (second market, about 10 minutes)

24. Reporter: `openSeason("TTN", 2028, T2 + 300, T2 + 420, 102)` (T2 = the time now).
25. Sponsor: deploy a second market with `_season = 2028`, `_tradingClose = T2 + 300`, `_reportDeadline = T2 + 600`.
26. Buyer: buy something.
27. Nobody reports. After `reportDeadline`, any account calls `cancelAfterDeadline()`. `state()` = 2 (Cancelled).
28. Buyer: `claimRefund()` returns exactly what the buyer paid. Sponsor: `sponsorWithdraw()` returns the funding.
29. Alternative: while trading is open the Sponsor calls `emergencyCancel()`. Same refunds.

## 4. What to record

| item | value |
|---|---|
| date and time (UTC) | |
| Remix compiler version and optimizer setting | |
| Reporter, Sponsor, Buyer addresses (public addresses only) | |
| oracle address, deploy tx hash, gas used | |
| openSeason tx hash, the four times used | |
| market address, deploy tx hash, gas used, VALUE sent | |
| quoteBasket result, buyBasket tx hash, gas used, cost paid | |
| prices() before and after the buy | |
| reportCount tx hash, gas used, count | |
| settle tx hash, gas used | |
| redeem tx hash, gas used, amount received | |
| sponsorWithdraw tx hash, gas used, amount received | |
| cancel rehearsal: market address, cancel tx hash, claimRefund tx hash | |
| anything that differed from this guide | |

Gas used is on the transaction's Sepolia Etherscan page (https://sepolia.etherscan.io) and in the Remix terminal.
For comparison, gas measured locally (Hardhat EVM, not Sepolia; `results/market/gas_report.json`):

| call | gas (local) |
|---|---|
| deploy SeasonCountOracle | 840,559 |
| openSeason | 49,167 |
| deploy RainCountLMSR | 3,776,889 |
| buyBasket, stepped hedge, first trade in a fresh market | 268,264 |
| buyBasket, stepped hedge, later first-time buyer | 199,332 to 233,832 |
| buyBasket, stepped hedge, repeat buyer | 117,196 to 131,436 |
| buy, one bucket (first / repeat) | 179,507 / 111,451 |
| reportCount | 56,241 |
| settle | 159,975 |
| redeem | 44,585 |
| sponsorWithdraw | 36,444 |
| cancelAfterDeadline / emergencyCancel | 106,570 / 95,391 |
| claimRefund | 39,539 |

Optional: verify the source on Sepolia Etherscan (single file, compiler 0.8.26, optimization 200 runs, MIT
licence, paste the flattened file). Not tried from here.

## 5. If a call fails

| message | meaning | what to do |
|---|---|---|
| Oracle has no code | the oracle address is a wallet or a typo | paste the oracle contract address |
| Oracle read failed | the address is a contract but not this oracle | same |
| Season not opened in oracle | step 3 was skipped, or station/season differ | call `openSeason` first; use the same station and season |
| Trading must close by season start | `_tradingClose` is after seasonStart | use a smaller `_tradingClose` |
| Trading close in the past | you were too slow; the time has passed | open a new season with later times |
| Funding below worst-case loss | VALUE is too small | send at least `b * unit * 1.7918` wei |
| unit out of range | unit below 1 gwei or above 1 ether | choose a unit in that range |
| Need six quantities | the vector does not have six numbers | write all six, zeros included |
| Cost above slippage limit | the price moved, or maxCost is below the quote | quote again |
| Insufficient payment | VALUE is below the cost | put the maxCost in VALUE |
| Cost rounds to zero | the bucket's price is below 1 wei (far behind the leader) | buy more shares of it, or another bucket |
| Quantity too large | more than 1e15 shares in a bucket | use a smaller number |
| Season not over | report sent before seasonEnd | wait |
| No valid report | no report yet, or it was late, voided or out of range | report, or wait for the deadline and cancel |
| Dispute window still open | settle called before report time + disputeDelay | wait |
| Deadline not passed | cancel called at or before reportDeadline | wait |
| Valid report exists, call settle | a good report is there | call `settle()` |
| Send more gas | the gas limit is below about 150,000 | set the gas limit to 300000 |

## 6. Trust: say this in the presentation

- **One reporter decides the outcome.** The contract checks who reports and when. It can not check that the
  count is true. A wrong count that arrives on time settles the market, and `settle()` is final.
- **Sponsor and oracle must be different accounts, run by different people.** If the sponsor also controls the
  reporter, the sponsor chooses the winning bucket. The contract can not enforce this. In a class demo one
  student holds all three accounts, so the demo shows the mechanics, not the trust.
- **The dispute delay is the only correction.** During the delay the oracle owner can call `voidReport`. The market
  then finds no valid report and refunds everyone after the deadline. With `disputeDelay = 0` there is no window.
  In this oracle the owner is also the first reporter, so the window helps only if the owner hands reporting to
  another account with `setReporter`.
- **The sponsor can cancel while trading is open.** Buyers get their money back but lose the hedge. Trading closes
  by the first season day, so the sponsor can not cancel after seeing the season's weather.
- **No selling.** A buyer can not exit before settlement.
- **Unclaimed money.** After the claim period (at least 7 days) the sponsor may take what nobody claimed.

## 7. Demo script outline (about 5 minutes on stage)

Prepare before the talk: oracle deployed, season opened with a 15-minute start, market deployed. Keep the
Etherscan pages of both contracts open. Have a second, finished market ready in case the network is slow.

1. (30 s) The problem: a park loses money on rainy opening days. The hedge is on the season's count of loss days.
2. (30 s) Show the market on Etherscan: funded by the sponsor with b ln 6. Show `prices()`: six times 1/6.
3. (60 s) Buyer: `quoteBasket([0,0,0,10,20,30])`, then `buyBasket`. One transaction, three buckets.
   Show `prices()` again: the top buckets went up. Show `sharesOfAll`.
4. (30 s) Try `reportCount` early: refused, "Season not over". This is the fix for a premature report.
5. (30 s) After the season end (switch to the prepared market if needed): Reporter reports 9 loss days.
6. (30 s) Anyone settles. `winningBucket()` = 4.
7. (30 s) Buyer redeems 20 units. Sponsor withdraws the rest. State the sponsor's result and the bound.
8. (30 s) What can go wrong: no report, then `cancelAfterDeadline` and full refunds (show the rehearsal market).
9. (30 s) Limits: one reporter, sponsor and oracle must be separate, no selling, testnet only.
