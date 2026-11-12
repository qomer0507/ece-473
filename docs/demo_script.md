# Live demo script for the Results section (90 seconds) and pre-flight checklist

Companion to docs/deploy_sepolia.md (the full step list with every expected number). Everything below uses the
guide's fixed numbers: station `TTN`, season `2025`, edges `[2,4,5,6,8]`, b = 100, unit = 0.0001 ETH, funding
0.018 ETH, hedge `[0,2,6,9,15,27]` (d = 3, size 3), quote 1025582224601672 wei, maxCost and VALUE
1050000000000000 wei, reported count 5, winning bucket 2, payout 6 shares = 0.0006 ETH.

Note on d: the guide still says "d is not chosen yet". Phase 2 has since chosen it: d = 3 for the Trenton
same-station case A (results/phase2/train_params.csv, h_j = [0, 0.667, 2, 3, 5, 9], so size 3 = [0,2,6,9,15,27],
exactly the guide's row) and d = 8 for the headline stand-in case B1. Say "d = 3, the training-season choice for
Trenton itself" and keep the guide's vector.

## What is pre-deployed and what is live

| Prepared in the morning (not live) | Live on stage |
|---|---|
| Oracle A + market A: the whole guide run to the end (opened, bought, reported 5, settled, redeemed, withdrawn). Etherscan page of market A open in a tab. | Nothing on A; it is shown as the finished replay. |
| Oracle B + market B: opened and funded 20-40 minutes before the talk with long times (see checklist), trading still open, nothing bought yet. Remix tab with both contracts in "Deployed Contracts". | `quoteBasket` (read), `buyBasket` (the one live transaction), `prices` before and after, the refused early `reportCount`. |
| Screen recording of the morning run (fallback 1). Terminal with `npx hardhat test --no-compile test/16_rain_guide.test.js` already run (fallback 2). | |

Sepolia blocks come every 12 s; a confirmed transaction normally shows in Remix within 15-45 s. One live
transaction is the most the slot can carry.

## The 90 seconds (what is on screen; what to say in one line)

| t | On screen | Say |
|---|---|---|
| 0-15 s | Slide: results/phase2/fig_hedge_effectiveness.png (the talk copy, results/talk/fig3_hedge_effectiveness.png). | "Kalshi's daily contract is below zero everywhere; the seasonal count contract works where the park's rain matches the station's and fails 28 km away. Here is that contract running." |
| 15-30 s | Tab 1: Etherscan page of market A (settled). Scroll the transaction list: deploy, buyBasket, reportCount, settle, redeem, sponsorWithdraw. | "This market replayed the real 2025 Trenton season on the testnet this morning: sponsor funded 0.018 ETH, buyer bought the stepped hedge, the reporter entered the real count of five loss days, settlement paid six shares." |
| 30-45 s | Tab 2: Remix, market B (fresh). Click `prices`: six values of 166666666666666666. Click `getEdges`: 2,4,5,6,8. | "A fresh market: six buckets on the season's count, each opens at one sixth; the bucket edges are the training-season quantiles." |
| 45-70 s | Buyer account. `quoteBasket([0,2,6,9,15,27])` = 1025582224601672. VALUE 1050000000000000 Wei. `buyBasket([0,2,6,9,15,27], 1050000000000000)`, confirm in MetaMask. While it confirms, keep talking. Then `prices` again: 15.0%, 15.3%, 16.0%, 16.5%, 17.5%, 19.7%. | "One transaction buys the whole stepped holding, more shares of the wet buckets; the quote is about 1.23 times the expected payout, and the wet buckets' prices moved up." |
| 70-80 s | Reporter account, oracle B: `reportCount(TTN, 2025, 5)`. MetaMask warns the transaction will fail; reject it. | "A report before the season ends is refused by the contract; that was one of the three fixes from the review." |
| 80-90 s | Back to tab 1 or slide: `winningBucket` = 2, `Redeemed` 600000000000000, sponsor withdrew 0.018425582 ETH. | "In 2025 the buyer got 0.0006 ETH back on a 0.001 ETH premium; a 12-loss-day season would pay 0.0027, and the sponsor can never lose more than 0.0179 ETH. Limits: one reporter, testnet only." |

If the slot is shorter, drop rows 30-45 s and 70-80 s; the live buy and the settled page carry the point.

## Fallbacks (decide within 10 seconds, do not wait)

1. `buyBasket` is still pending after 45 s, or MetaMask does not open: say "Sepolia is slow this minute; this is
   the same run recorded this morning", play the screen recording from the `quoteBasket` step (about 40 s), then
   return to the settled Etherscan page (which does not depend on anything live).
2. Remix or MetaMask will not connect at all: switch Remix's Environment to **Remix VM** (no MetaMask, instant;
   the deployed-contracts list is empty there, so this needs the two deploys to be done in the VM beforehand,
   in a second Remix browser window kept open since the morning), or go straight to fallback 3.
3. No browser at all: terminal, `cd contracts && npx hardhat test --no-compile test/16_rain_guide.test.js`
   (1 second): the rehearsal of steps 1-28 with the guide's numbers passes in the local EVM. Say what each line
   checked. Then the Etherscan page on the phone, or the slide with the transaction hashes from the morning.
4. Etherscan "Read Contract" works only if the source was verified (guide section 4, optional). If verification
   was not done, read values in Remix (`At Address` with the market A address), not on Etherscan.

## Pre-flight checklist, morning of the talk

Day before
- [ ] Sepolia test ETH in all three MetaMask accounts (Sponsor >= 0.05, Reporter >= 0.02, Buyer >= 0.02 ETH; two
      markets and a retry need more than the guide's minimum). Faucets are rate-limited: do not leave this to the morning.
- [ ] Accounts renamed Reporter / Sponsor / Buyer in MetaMask. Public addresses written in the guide's section 4 table.
- [ ] `python scripts/check_env.py` and `cd contracts && npm test` pass on the laptop (162 passing).
- [ ] Remix workspace saved with `contracts/remix/SeasonCountOracle_flat.sol` and `RainCountLMSR_flat.sol`,
      compiler 0.8.26, optimizer on, 200 runs, both compiled without errors.

Morning (allow 60 minutes; the settled market needs a 25-minute wait inside it)
- [ ] Run the guide's sections 1-3 completely on Sepolia (oracle A, market A, buy, wait, report 5, settle, redeem,
      withdraw). Screen-record it. Fill the section 4 table: addresses, every tx hash, gas used, anything that differed.
- [ ] Open the Etherscan page of market A and the `redeem` transaction (internal transfer of 0.0006 ETH) in tabs.
- [ ] Optional: verify market A's source on Etherscan (single file, 0.8.26, 200 runs) so "Read Contract" works.
- [ ] 20-40 minutes before the talk: deploy oracle B and market B with long times so trading is still open on stage:
      read `currentTime` = T, then seasonStart = tradingClose = T + 5400 (90 min), seasonEnd = T + 6000,
      reportDeadline = T + 7800; everything else as in the guide's step 7. Check `requiredFunding`, `prices`, `getEdges`.
- [ ] On market B as Buyer: `quoteBasket([0,2,6,9,15,27])` returns 1025582224601672 (last digits may differ by 1-2).
      Do not buy.
- [ ] VALUE in Remix set back to 0; unit shows Wei; gas limit "Estimated" or 5000000.
- [ ] Terminal open in `contracts/` with test 16 already run once (fallback 3). Recording file open in a player (fallback 1).
- [ ] Browser: exactly four tabs in order (slide deck, Etherscan A, Remix, MetaMask popup allowed), zoom 150%,
      notifications off, laptop on power, phone hotspot as backup network, Etherscan A page also open on the phone.
- [ ] MetaMask unlocked, Sepolia selected, Buyer account active (the first live click is the Buyer's).
- [ ] Say-out-loud check: the three numbers you will quote (quote 0.001026 ETH, payout 0.0006 ETH, sponsor bound 0.0179 ETH)
      and the three trust limits (one reporter; sponsor and reporter must be different people; no selling).

After the talk
- [ ] Record the live buyBasket hash and gas in the section 4 table; note what differed from the guide in
      docs/status/phase2_market.md (dated UTC line). Market B can be left to expire: after T + 7800 anyone can call
      `cancelAfterDeadline`, the Buyer `claimRefund`, the Sponsor `sponsorWithdraw`.
