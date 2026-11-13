# Deploying the rain-count market on Sepolia with Remix and MetaMask

Testnet only. No real money. Never paste a private key or a seed phrase anywhere: MetaMask signs for you.

Status of this guide: every contract call and every number below was run in the local Hardhat EVM by `npm test`
(contracts/test/16_rain_guide.test.js and 17_rain_registered.test.js), and the whole guide (steps 1-28) was
rehearsed in the Remix VM on 2026-11-12 (Remix 2.6.14, compiler 0.8.26, optimizer 200 runs). Every predicted
number matched to the wei and every safety check fired. Three Remix interface quirks were found; they are built
into the steps below and listed under "Remix quirks". **MetaMask and Sepolia themselves are still untried.**

Contracts (flattened, no imports, ready to paste):

- `contracts/remix/SeasonCountOracle_flat.sol` (the oracle)
- `contracts/remix/RainCountLMSR_flat.sol` (the market)

## What the demo shows, in four sentences

A park loses money on rainy opening days. The market sells six "buckets" on the number of loss days in one
season at Trenton. A buyer holds more shares of the buckets with many loss days, so a wet season pays more.
The demo **replays the 2025 Trenton season**: the reporter enters the real 2025 count, **5 loss days**
(row `TTN,2025,all_days` of `data/processed/rain/season_counts_TTN.csv`, column `loss_days`).

The season dates on chain are short demo times, not the 2025 calendar. A season that is already over can not
be opened with its true dates: the oracle accepts a report only after a season end that was still in the
future when the season was opened.

## 0. What you need

1. Three MetaMask accounts on the Sepolia network. Rename them in MetaMask (account menu, "Account details",
   pencil icon) so you can not mix them up:
   - **Reporter**: deploys the oracle, opens the season, reports the count.
   - **Sponsor**: deploys the market and funds it. Withdraws at the end.
   - **Buyer**: buys the hedge and redeems it.
2. Sepolia test ETH in all three (any Sepolia faucet). The example needs about 0.03 ETH for the Sponsor,
   0.01 for the Reporter and 0.01 for the Buyer. That includes gas.
3. The Sponsor and the Reporter must be different accounts. See "Trust" at the end. Say this in the presentation.

Write the three public addresses in the table of section 4 now. You need the Buyer's address in step 15.

### How to switch accounts (you do this six times)

- **Sepolia:** click the MetaMask icon, click the account name at the top, choose the account. If MetaMask
  asks to connect the account to Remix, accept. Then look at the **ACCOUNT** field in Remix's "Deploy & run"
  tab. It must show the address of the account you chose. If it shows another address, reload the Remix page.
- **Remix VM (rehearsal):** there is no MetaMask. Use the **ACCOUNT** drop-down in Remix. Take the first
  account as Reporter, the second as Sponsor, the third as Buyer. Each has 100 test ETH.
- The deployed contracts stay in the "Deployed Contracts" list when you switch accounts. If the list is empty
  (page reload): select the contract name in the CONTRACT drop-down, paste the contract's address into the
  **At Address** field and click the button. The contract appears again.

### How to type arguments in Remix

- Click the small arrow next to a function to open the form with one field per argument.
- Text arguments (the station) are typed without quotes in that form: `TTN`.
- Lists are typed with square brackets, commas, no spaces: `[2,4,5,6,8]`.
- **Two VALUE fields.** The VALUE box at the top of the "Deploy & run" tab is used only for DEPLOYMENTS
  (steps 6 to 8 and 25). For a call on a deployed contract, such as the buy in steps 12 and 13 and 26, use the
  contract's OWN **Value** and **Gas limit** fields at the bottom of its box under "Deployed Contracts" (below
  "Low level interaction"). A buy with the money in the top box reverts with "Insufficient payment".
- **Set VALUE back to 0 yourself** after every payable call, in whichever field you used. Remix does not reliably
  reset it, and a stale value is sent with the next call.
- Units: set the unit next to each Value field to **Wei**.

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
7. For `cancelAfterDeadline` (step 27), and for `settle` if it ever says "Send more gas", set that contract's own
   **Gas limit** field to `300000` first. The contract keeps a gas reserve for its oracle call, and Remix's
   automatic estimate falls just short.

Rehearse once with Environment = **Remix VM** first. It is free and instant. The waiting times are the same,
because the Remix VM is expected to use the real clock for new blocks (not tried from here: check with
`currentTime()` before and after a wait).

## 2. The numbers

### Fixed numbers (the same for everybody)

| name | value | meaning |
|---|---|---|
| station | `TTN` | Trenton-Mercer |
| season | `2025` | the season that is replayed |
| seasonDays | `102` | days in the 2025 season |
| edges | `[2,4,5,6,8]` | the registered bucket edges (below) |
| b | `100` | LMSR liquidity, in shares |
| unit | `100000000000000` | wei paid per winning share = 0.0001 ETH |
| funding to send | `18000000000000000` | wei = 0.018 ETH |
| disputeDelay | `0` | seconds `settle()` waits after the report |
| claimPeriod | `604800` | 7 days, the minimum |
| hedge | `[0,2,6,9,15,27]` | shares per bucket (below) |
| maxCost and VALUE for the buy | `1050000000000000` | wei = 0.00105 ETH |
| count to report | `5` | Trenton 2025, observed |

### Times (yours; fill in after step 2)

All times are unix seconds. `T` is the number that `currentTime()` returns in step 2.
Example: if `T = 1790000000`, then T + 900 = `1790000900`, T + 1500 = `1790001500`, T + 3300 = `1790003300`.

| name | meaning | formula | your number |
|---|---|---|---|
| T | time now (step 2) | | |
| seasonStart | first season day | T + 900 (15 min) | |
| seasonEnd | count is final; report allowed from here | T + 1500 (25 min) | |
| tradingClose | last moment to buy; must be <= seasonStart | T + 900 | |
| reportDeadline | last moment for a valid report; must be > seasonEnd | T + 3300 (55 min) | |

You have 15 minutes from step 2 to finish the buy in step 13. If that is too tight, add 600 to all four numbers.
In a real season: seasonStart = Friday before Memorial Day, seasonEnd = a few days after Labor Day (when the
climate report is final), reportDeadline = seasonEnd + 14 days, disputeDelay = 2 days, claimPeriod = 30 days.

### Buckets: the registered edges

`edges` are the last counts of the first five buckets. The project's registered edges are `[2,4,5,6,8]`.
They are the 1/6, 2/6, 3/6, 4/6, 5/6 quantiles of the Trenton loss-day counts in the 16 training seasons
1999-2014 (results/market/registered_buckets.csv). The five quantiles are all different, so nothing had to be merged.

| bucket | 0 | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| loss days | 0-2 | 3-4 | 5 | 6 | 7-8 | 9 or more |
| training seasons in the bucket | 4 | 3 | 2 | 3 | 2 | 2 |
| mean count in the bucket, m | 1.75 | 3.667 | 5 | 6 | 8 | 12 |

### The hedge: a stepped holding

Rule (docs/PHASE2_PREREG.md): per unit of hedge size, hold max(m - d, 0) shares of each bucket.
d is the deductible: the loss days the park carries itself.
**d is not chosen yet** (the evaluation chooses it on the training seasons). This guide uses **d = 3** and hedge size 3.
Size 3 makes every number of shares whole: 3 x (0, 0.667, 2, 3, 5, 9) = `[0,2,6,9,15,27]`.

| d | hedge (size 3) | `quoteBasket` in a fresh market, wei | pays in the 2025 replay (5 loss days, bucket 2) |
|---|---|---|---|
| 2 | `[0,5,9,12,18,30]` | 1281027009166992 | 9 shares = 0.0009 ETH |
| **3 (used below)** | `[0,2,6,9,15,27]` | 1025582224601672 | 6 shares = 0.0006 ETH |
| 4 | `[0,0,3,6,12,24]` | 786628457016825 | 3 shares = 0.0003 ETH |

When d is known, use its row: same steps, other vector. For d = 2 use maxCost `1310000000000000`,
for d = 4 use `805000000000000`.

### Funding

The sponsor must send at least `floor(b x ln(6) x unit)` wei. This is also the most the sponsor can lose.
For b = 100 and unit = 100000000000000 that is **17,917,594,692,280,550 wei** (0.017918 ETH).
Send `18000000000000000` wei (0.018 ETH). The extra comes back with `sponsorWithdraw()` at the end.

You can not ask the contract for this number before it is deployed. If you change b, take the number from this
table (unit = 100000000000000 wei), or run `python -m sim.lmsr funding --b 100 --unit-wei 100000000000000` in
the repo root. After deployment `requiredFundingFor(b, unit)` gives it on chain.

| b | required funding, wei | send, wei |
|---|---|---|
| 50 | 8958797346140275 | 9000000000000000 |
| 100 | 17917594692280550 | 18000000000000000 |
| 200 | 35835189384561100 | 36000000000000000 |
| 500 | 89587973461402750 | 90000000000000000 |
| 1000 | 179175946922805500 | 180000000000000000 |

## 3. Deploy and run (numbered; record every transaction hash)

Each step says which account, what to type, and what you should see.

### Reporter account

1. Switch to **Reporter** (check the ACCOUNT field). CONTRACT drop-down: `SeasonCountOracle`. VALUE = 0.
   Click **Deploy**. Confirm in MetaMask. Record the oracle address (copy icon next to the deployed contract).
2. On the oracle click `currentTime`. The number is `T`. Fill in the times table in section 2 now.
3. Open `openSeason` and fill in:
   - station: `TTN`
   - season: `2025`
   - seasonStart: your T + 900
   - seasonEnd: your T + 1500
   - seasonDays: `102`

   Click **transact**. Confirm.
4. Check: `getSeason` with `TTN` and `2025` returns `opened = true`, your two times, `seasonDays = 102`,
   `reported = false`, `count = 0`.

### Sponsor account

5. Switch to **Sponsor** (check the ACCOUNT field). CONTRACT drop-down: `RainCountLMSR`.
6. VALUE: `18000000000000000`, unit **Wei**.
7. Open the Deploy form (arrow next to Deploy) and fill in:

   | argument | type this |
   |---|---|
   | _oracle | the oracle address from step 1 |
   | _station | `TTN` |
   | _season | `2025` |
   | _edges | `[2,4,5,6,8]` |
   | _b | `100` |
   | _unit | `100000000000000` |
   | _tradingClose | your T + 900 |
   | _reportDeadline | your T + 3300 |
   | _disputeDelay | `0` |
   | _claimPeriod | `604800` |

8. Click **transact**. Confirm in MetaMask. Record the market address. Check that VALUE is back to 0.
9. Check on the market:
   - `requiredFunding` = 17917594692280550
   - `funding` = 18000000000000000
   - `state` = 0 (0 = Open, 1 = Settled, 2 = Cancelled)
   - `getEdges` = 2,4,5,6,8
   - `prices` = six times 166666666666666666 (the last digit may differ). 1000000000000000000 means 100%,
     so each bucket starts at 16.67%.
   - `bucketOf` with `5` = 2 (five loss days fall in bucket 2)
   - Balance shown next to the contract: 0.018 ETH

### Buyer account: buy the stepped hedge

10. Switch to **Buyer** (check the ACCOUNT field). The market is still in the Deployed Contracts list.
11. `quoteBasket` with `[0,2,6,9,15,27]` returns **1025582224601672** wei (0.001025582 ETH; the last digit may
    differ by 1 or 2). This is a read: no transaction, no MetaMask window.
12. VALUE: `1050000000000000` Wei. This is the quote plus about 2.4%, as a round number.
13. Open `buyBasket`: quantities `[0,2,6,9,15,27]`, maxCost `1050000000000000`. Click **transact**. Confirm.
    The contract keeps exactly the quote and sends the rest back in the same transaction.
    If it fails with "Trading closed", more than 15 minutes have passed since step 2: see section 5.
14. Check that VALUE is back to 0.
15. Check on the market (paste the Buyer's address where an address is asked):
    - `sharesOfAll(buyer address)` = 0,2,6,9,15,27
    - `paid(buyer address)` = 1025582224601672 (the quote)
    - `totalPaid` = the same number
    - `prices` = about 150420933493721421, 153459637918370109, 159722444549102369, 164586717159761721,
      174764191356159266, 197046075522885112. Read them as 15.0%, 15.3%, 16.0%, 16.5%, 17.5%, 19.7%:
      the buckets the buyer bought most went up.
    - Balance of the contract: 0.019025582 ETH
16. Optional: `quoteBuy(5, 10)` shows the price of 10 more shares of the top bucket; `buy(5, 10, maxCost)` buys them.
    If you do this, the later balances in this guide are higher by what you paid.

### Wait for the season to end

17. Wait until `currentTime()` on the oracle is larger than your seasonEnd (T + 1500): 25 minutes after step 2.
    While you wait, show the fix for a premature report: switch to **Reporter**, open `reportCount` on the
    oracle with `TTN`, `2025`, `5` and click transact. MetaMask warns that the transaction is likely to fail;
    reject it. In the Remix VM there is no warning: the transaction fails and the Remix terminal shows
    "Season not over". Nothing is stored either way.
    After seasonEnd you have 30 minutes (until T + 3300, the reportDeadline) for step 18. A report after the
    deadline does not count: the market can then only be cancelled and refunded (steps 27 and 28).

### Reporter account: report the 2025 count

18. Switch to **Reporter** (check the ACCOUNT field). On the oracle: `reportCount` with station `TTN`,
    season `2025`, count `5`. Transact, confirm, record the hash. This works once. A second report is
    refused ("Already reported").
19. Check: on the oracle `getSeason(TTN, 2025)` shows `reported = true`, `count = 5`.
    On the market `hasValidReport` = true.

### Buyer account: settle and redeem

20. Switch to **Buyer**. (Any account may call `settle`; the Buyer is used so that you switch once.)
    On the market click `settle`. Confirm.
21. Check: `state` = 1 (Settled), `settledCount` = 5, `winningBucket` = 2, `reserved` = 600000000000000.
22. Click `redeem`. Confirm. The Buyer receives 6 shares x 0.0001 ETH = **0.0006 ETH**
    (the transaction's page on Etherscan shows it as an internal transfer; the Remix terminal shows the
    `Redeemed` event with amount 600000000000000).
    Check: `reserved` = 0; balance of the contract 0.018425582 ETH. A second `redeem` fails with "Nothing to redeem".

### Sponsor account: withdraw

23. Switch to **Sponsor** (check the ACCOUNT field). Click `sponsorWithdraw`. Confirm.
    The sponsor receives everything that is not owed to buyers:
    funding + what the buyer paid - payout = 0.018 + 0.001025582 - 0.0006 = **0.018425582 ETH**
    (18425582224601672 wei in the `SponsorWithdrawal` event). The contract's balance is now 0.

How to read the result:

- 2025 was an ordinary season (5 loss days; the training mean is 5.4). The buyer paid 0.001026 ETH and got
  0.0006 ETH back. The sponsor gained 0.000426 ETH.
- In a wet season it is the other way round. With 12 loss days (as in 2009 and 2013) the same hedge pays
  27 shares = 0.0027 ETH and the sponsor loses 0.001674 ETH. The sponsor can never lose more than the
  0.017918 ETH bound.
- Price check, to explain the market: under the training frequencies this hedge has an expected payout of
  8.34 shares (0.000834 ETH). The buyer paid 10.26 shares' worth (0.001026 ETH), 1.23 times the expected
  payout. The project's modelled premium is 1.20 times. The extra comes from the uniform start (every bucket
  opens at 1/6) and from the buyer's own price impact with b = 100. See results/market/summary.md (simulation).

### Cancel rehearsal (second market, about 12 minutes)

24. **Reporter**: call `currentTime` again; call the result T2. `openSeason` with `TTN`, `2028`, T2 + 300,
    T2 + 420, `102`.
25. **Sponsor**: VALUE `18000000000000000` Wei. Deploy a second `RainCountLMSR` with the same arguments as in
    step 7 except `_season = 2028`, `_tradingClose = T2 + 300`, `_reportDeadline = T2 + 600`.
26. **Buyer**: VALUE `1050000000000000` Wei. On the new market `buyBasket` with `[0,2,6,9,15,27]` and maxCost
    `1050000000000000`. You have 5 minutes from step 24.
27. Nobody reports. Wait until `currentTime()` is larger than T2 + 600 (10 minutes after step 24). Then any
    account calls `cancelAfterDeadline` on the new market. `state` = 2 (Cancelled). Before the deadline the
    call fails with "Deadline not passed".
28. **Buyer**: `claimRefund` returns exactly what the buyer paid (1025582224601672 wei).
    **Sponsor**: `sponsorWithdraw` returns the funding (0.018 ETH).
29. Alternative: while trading is open the Sponsor calls `emergencyCancel`. Same refunds.

## 4. What to record

| item | value |
|---|---|
| date and time (UTC) | |
| Remix compiler version and optimizer setting | |
| Reporter address (public address only) | |
| Sponsor address | |
| Buyer address | |
| oracle address, deploy tx hash, gas used | |
| T, and the four times used | |
| openSeason tx hash | |
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
| deploy RainCountLMSR | 3,776,901 |
| buyBasket `[0,2,6,9,15,27]`, first trade in a fresh market (step 13) | 354,120 |
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
| Season already opened | you opened (TTN, 2025) before on this oracle | deploy a new oracle (step 1) and start again; a season can not be changed |
| Trading must close by season start | `_tradingClose` is after seasonStart | use the same number as seasonStart |
| Trading close in the past | you were too slow; the time has passed | deploy a new oracle, read a new T, start again from step 1 |
| Trading closed | the buy came after tradingClose | same: new oracle, new T, and add 600 to every time |
| Funding below worst-case loss | VALUE is too small or was left at 0 | set VALUE to the "send" number of the funding table |
| unit out of range | unit below 1 gwei or above 1 ether | choose a unit in that range |
| Need six quantities | the vector does not have six numbers | write all six, zeros included |
| Cost above slippage limit | the price moved, or maxCost is below the quote | call `quoteBasket` again; use a maxCost above it |
| Insufficient payment | VALUE is below the cost (often VALUE was left at 0) | put the maxCost in VALUE |
| Cost rounds to zero | the bucket's price is below 1 wei (far behind the leader) | buy more shares of it, or another bucket |
| Quantity too large | more than 1e15 shares in a bucket | use a smaller number |
| Not an authorised reporter | `reportCount` was sent from the Sponsor or Buyer account | switch to Reporter |
| Season not over | report sent before seasonEnd | wait |
| No valid report | no report yet, or it was late, voided or out of range | report, or wait for the deadline and cancel |
| Dispute window still open | settle called before report time + disputeDelay | wait |
| Not sponsor | `sponsorWithdraw` was sent from another account | switch to Sponsor |
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

Prepare before the talk: run sections 1 to 3 completely once and keep that finished market's Etherscan page
open. For the live part deploy a fresh oracle and market shortly before the talk (steps 1 to 9).

1. (30 s) The problem: a park loses money on rainy opening days. The hedge is on the season's count of loss days.
2. (30 s) Show the market on Etherscan: funded by the sponsor with b ln 6 (0.018 ETH). Show `prices()`: six times 1/6.
   Show `getEdges()`: 2,4,5,6,8, chosen from 16 training seasons.
3. (60 s) Buyer: `quoteBasket([0,2,6,9,15,27])`, then `buyBasket`. One transaction, five buckets.
   Show `prices()` again: the high buckets went up. Show `sharesOfAll`.
4. (30 s) Try `reportCount` early: refused, "Season not over". This is the fix for a premature report.
5. (30 s) Switch to the finished market: the Reporter reported 5 loss days, the real Trenton count of 2025.
6. (30 s) Anyone settles. `winningBucket()` = 2.
7. (30 s) Buyer redeemed 6 shares (0.0006 ETH). Sponsor withdrew the rest and gained 0.000426 ETH.
   State what a wet season would have done: 12 loss days pay 27 shares; the sponsor's loss is capped at 0.017918 ETH.
8. (30 s) What can go wrong: no report, then `cancelAfterDeadline` and full refunds (show the rehearsal market).
9. (30 s) Limits: one reporter, sponsor and oracle must be separate, no selling, testnet only, d not final.

## Remix quirks found in the 2026-11-12 rehearsal

| # | What happens | What to do |
|---|---|---|
| 1 | The top VALUE box is only used for deployments. A `buyBasket` with the money there reverts with "Insufficient payment". | Put the buy's Value in the deployed contract's own Value field. |
| 2 | VALUE does not reliably reset to 0 after a transaction. | Set it back to 0 yourself after every payable call. |
| 3 | `cancelAfterDeadline` with automatic gas reverts with "Send more gas". | Set that contract's Gas limit to 300000 before the call. |

Rehearsal gas: `buyBasket` 353,808; `cancelAfterDeadline` 106,570. The Remix VM uses the real clock, so the
guide's waiting times apply unchanged. The VM's state is lost on page reload, so a VM backup demo must be set up
fresh on the day, ideally with shorter season times.
