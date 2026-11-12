# Phase 0, question 4: contract review (read-only)

Reviewer: independent probe for the Viktor workstream. Date: 2026-11-12 UTC. Status: DONE.

## Verdict: SOUND WITH FIXES

- The LMSR maths, the collateral accounting and the b ln(n) loss bound are correct. I found no way to make the contract insolvent and no critical bug.
- Three major problems must be fixed or disclosed before any testnet deploy: funds can be locked for ever by a wrong oracle address (reproduced), settlement trusts one reporter with no correction path (and the sponsor can be that reporter), and one premature report forces a cancel.
- The contract already runs a six-bucket rain-count market by constructor parameters alone (reproduced), but every name says "temperature" and the basket is the wrong shape. Recommendation: **adapt, do not rewrite**. About **20 hours** (range 16 to 24) for contract, tests, Python reference, Remix files and deploy guide.
- Nothing was deployed. Not tested: Remix itself, MetaMask, Sepolia (RPC blocked here).

## 1. Test runs

`npm test` writes into contracts/artifacts, contracts/remix, contracts/test/vectors and results/part3. To keep this review read-only I ran it in a scratch copy of contracts/ (same node_modules). File hashes of contracts/, sim/, tests/ and results/part3 are unchanged after the review.

| suite | command | result |
|---|---|---|
| JavaScript (Hardhat EVM, solc-js 0.8.26, optimizer 200) | `npm test` in contracts/ | 65 passing, 0 failing, 0 skipped. Run twice (31 s, 33 s), same result. |
| Python | `python -m pytest tests/test_lmsr_*.py -q` | 29 passed, 0 failed, 0 skipped (3.3 s) |

- Not flaky: random numbers are seeded and block times are set explicitly.
- Regenerated artifacts, both flattened Remix files and contract_quotes.json are byte-identical to the committed files. gas_report.json differs in one number (seeded deploy 3,942,397 vs 3,942,385 gas).
- `test/99_gas.test.js` fails when run alone (1 failing): it needs the gas log filled by the other files in the same process.
- The pytest cross-check file (7 tests) and two experiment tests are guarded by `skipif` (missing contract_quotes.json or station file). Both files exist, so nothing was skipped. If contract_quotes.json is deleted, the cross-check skips silently.

## 2. Findings

Line numbers refer to contracts/BracketLMSR.sol unless another file is named.

### Critical
None found.

### Major

**M1. A wrong oracle address locks all funds for ever.** Lines 136, 301, 451-457.
The constructor checks only `_oracle != address(0)`. `_hasValidReport()` wraps the oracle call in try/catch, but Solidity's catch does not cover a target without code, or return data that cannot be decoded. Reproduced (probe A): with the oracle set to an EOA, to a contract with an empty fallback, or to a contract that returns one word instead of three, `settle()` and `cancelAfterDeadline()` both revert without a reason, and `emergencyCancel()` is refused after tradingClose. The state stays Open; trader payments and sponsor funding cannot leave. Only a contract that reverts (no such function) is caught and can be cancelled. A student pasting an address into Remix can hit this.
Fix: require `_oracle.code.length > 0` and make one trial `getReport` call in the constructor; read the oracle with a low-level staticcall and treat failure or short return data as "no valid report". About 1.5 h with tests.

**M2. One reporter decides the outcome, with no correction and no dispute window.** Lines 298-312; TemperatureOracle.sol lines 10-11, 52-63.
`settle()` can be called by anyone the moment an on-time report exists, and it is final. The oracle comment "If it is wrong or late, the market cancels and refunds" is false for a wrong on-time report. If the sponsor also owns the oracle (the planned one-student deploy), the sponsor chooses the winning bucket, or withholds the report. Probe G: a hedger who would have received 0.04 ETH gets only the 0.02296 ETH cost back, and the sponsor avoids a loss of 0.01704 ETH out of a 0.01792 ETH bound. The guard in lines 323-326 ("the sponsor cannot cancel once a loss is in sight") does not hold in that setup.
This follows from the plan ("authorised oracle reports once"), so the fix is mostly disclosure: use different accounts for oracle and sponsor, say so in the presentation, correct the comment. Optional: a short dispute delay before `settle()`.

**M3. A premature report is permanent and forces a cancel.** TemperatureOracle.sol lines 54, 57; market lines 303, 319.
The oracle accepts a report from the first second of `day` and never lets it be replaced. A report made before `observationEnd` is "stale" for ever, so the market can only wait for the deadline and cancel. The existing test "stale report ... then cancel" documents this as intended. For a season-long market, one early click loses the whole season's hedge.
Fix in the adapted oracle: refuse reports before the season end (store a not-before time per market id). About 1 h inside the oracle rewrite.

### Minor

- **m1. Sponsor's free option until tradingClose** (lines 327-331). `emergencyCancel()` refunds everybody at cost. If trading is still open when forecasts turn against the sponsor, the sponsor can cancel. Rule for the rain market: tradingClose at or before the first operating day.
- **m2. Zero-cost shares** (lines 62-63, 405, 430). A bucket more than 45 b below the leader has weight 0. Probe D: after a 1,000-share buy at b = 10, 500 shares of another bucket cost 0 wei and were bought with no payment. The true LMSR cost is below 1 wei there, and solvency holds (probe F: 3,600 trades of up to 200 b; the balance always covered the largest payout; worst loss exactly 100% of requiredFunding). With a dust `unit` (1 to 3 wei) most small trades also cost 0. Use unit >= 1e9 wei.
- **m3. Buy only.** No sell. A buyer cannot exit; prices move back only if someone buys the other buckets. Same as Lab 7.
- **m4. Uniform start or a larger bound.** `initialQ` (lines 159-168) can encode a prior, but then the sponsor's worst case is b ln(1/p_min), not b ln(n) (results/part3: 1,330.9 vs 497.0 at b = 200). The plan's "b ln(6)" needs the uniform start, where every bucket opens at 1/6.
- **m5. Unclaimed money stays reserved for ever** (lines 338-358). No sweep, no claim deadline. A winner contract that cannot receive ETH keeps its payout stuck (tested; other users are not affected).
- **m6. Funding must be computed off-chain.** `requiredFunding` is readable only after deploy; one wei short reverts (line 173); any excess is locked until settle or cancel.
- **m7. Temperature limits in the oracle** (TemperatureOracle.sol lines 24-25, 55). Values -80..140. A count of -1 is accepted (maps to bucket 0); 141 is refused.
- **m8. `marketDay` and `observationEnd` are not linked** (lines 139-146). The staleness check is only as good as the timestamps the sponsor types.
- **m9. Any authorised reporter can report any (station, day) key**; no ownership transfer. Fine for a one-student oracle, not for a shared one.
- **m10. Comments point at things that do not exist or were not checked.** Line 57 cites docs/status/viktor.md (missing). Line 7 imports `@openzeppelin/contracts/security/ReentrancyGuard.sol` without a version; Lab 13 pins `@4.9.6`. The current npm release is 5.6.1 and has only `utils/ReentrancyGuard.sol`, so the unflattened source will probably not compile in Remix (Remix not reachable here; not tested). The flattened file avoids this.
- **m11.** An absurd `shares` value reverts with a Panic instead of "Quantity too large" (lines 425-426). Cosmetic.
- **m12.** The flattened file carries one MIT header but bundles ABDK (BSD-4-Clause). The notice is kept in a comment. Cosmetic.

### What I checked and found correct

- **Log-sum-exp** (lines 388-418). Every exponent is <= 0; the largest term is exactly 1.0; the sum is in [1, n]; ln is >= 0. No overflow within the stated bounds (b <= 1e12, q <= 1e15, unit <= 1 ether: the largest products are 1e33 and 3.5e30).
- **Precision.** Measured in the suite: exp, ln and weight within 1 unit of 2^-64; cost error at most 4.1e-19 x b x unit. My own recomputation (naive formula, 100-digit decimals, no import from sim/) of all 120 wei amounts in contract_quotes.json: worst error 0.983 wei at unit = 1e12.
- **Rounding.** C(q) is floored. Each buy is charged C(new) - costNow (lines 430, 446-448), so charges telescope and the total paid is exact, whatever the order. Per-trade rounding is +/- 1 wei and cannot be farmed (path independence holds to the wei in the tests and in my prototype check).
- **Solvency.** balance = funding + totalPaid >= C(q0) + (costNow - C(q0)) = costNow >= C(q) >= max(q) x unit >= any payout (lines 173, 310, 417). This does not depend on fixed-point error. Sponsor loss <= requiredFunding = floor(b ln(n) x unit).
- **Refund rule** (lines 350-358, 459-463). Each trader gets back exactly what they paid; the sponsor gets the funding back; reserved = totalPaid <= balance. Probe E: 60 random six-bucket markets, 10 traders, both cancel paths; the balance ends at 0 every time.
- **Reentrancy.** All eight state-changing functions are nonReentrant; effects come before the ETH send (lines 343-346, 354-357, 363-366); the oracle read is a view call.
- **Access control.** emergencyCancel and sponsorWithdraw are sponsor-only; settle and cancelAfterDeadline are open to anyone by design.
- **Deadlines** (lines 300-304, 318-319, 453). A report is valid only if observationEnd <= reportedAt <= reportDeadline. Late, missing and stale reports all end in cancelAfterDeadline. settle and cancel cannot both succeed. Boundary times are tested.

## 3. The test suite

It mostly tests what it claims, with tight tolerances. Weak points:

- **Cannot fail, or nearly so:** "a 1-share buy ... never costs less than 0" (unsigned integer); `quoteBuy(0, 1000) <= 1000` in the b = 1 test; the bytecode-size test; the gas test (checks only that labels exist).
- **Events:** `Settled` and `Reported` are checked for emission only, not for arguments.
- **Property tests** use trades up to 20 b, never past the 45 b cutoff, and only n = 12. They settle at a random temperature, not the worst bucket, but a separate check (balance >= largest sold x unit after every trade) does enforce the bound.
- **The pytest cross-check does not run the contract.** It reads a committed snapshot written by the JS suite. If the contract changes and `npm test` is not re-run, pytest still passes.
- **Missing cases:** oracle address without code or with a wrong ABI (M1); n = 6; many buyers then cancel as a property test; a zero-priced bucket that wins; a sponsor who is also the reporter; negative or out-of-range reports; refund of excess to a contract that rejects ETH; the sponsor buying in its own market. Already covered: redeem twice, refund twice, withdraw twice, settle at the 89/90 edge, zero shares, b = 1 and b = 1e12.

**Is the Python reference independent?** Partly. The numerics are independent (60-digit decimals against 64.64 fixed point, and the float layer is tested against the naive formula). The specification is not: same author, same formula split, and it copies the contract's exp cutoff on purpose. My separate naive recomputation agrees, so I found no shared mistake. It covers only the 12-bracket temperature ladder.

## 4. results/part3

Recomputed by hand formula (scratch script recompute.py):

| quantity | hand | file |
|---|---|---|
| uniform, b = 200, basket 100: cost = b ln((e^0.5 + 1)/2) | 56.186 | 56.186 |
| same trade, post-trade price e^0.5/(e^0.5 + 1) | 0.622459 | 0.622459 |
| uniform, b = 1,000, basket 1,000: cost | 620.115 | 620.115 |
| b ln(12), b = 50 | 124.245 | 124.245 |
| smoothed prior P(>= 90F) = 165/777 | 0.212355 | 0.2124 |
| climatology, b = 5,000, basket 100: cost (exact prior vs integer seed) | 21.4034 | 21.4036 |
| outcome days, and days >= 90F, from the station file | 918 and 220 (0.239651) | 918, 0.239651 |
| hedger_only, uniform, b = 200: mean and minimum sponsor P&L | 32.2208, -43.8140 | 32.2208, -43.814 |

All match. price_impact.png is legible; the title starts with "SIMULATED" and the footer says "No real orders"; axes, units and legend are labelled; the log-log axes are stated. I did not review the scenario code in sim/experiment.py line by line.
Everything in results/part3 is for the 12-bracket temperature market. None of it describes six rain-count buckets.

## 5. Adaptation plan

**By parameters alone: yes, it works** (probe C, unmodified contract). bounds = [3, 5, 7, 9, 11] gives 0-2, 3-4, 5-6, 7-8, 9-10, 11+. Counts 0, 2, 3, 4, ... 11, 12, 60 and 140 each settled in the right bucket. Funding at b = 100, unit = 1e14 wei: 17,917,594,692,280,550 wei = b ln(6) x unit. A ladder of 10, 20, 30, 40, 50 units of buckets 1 to 5 cost 26.4539 units by five `buy()` calls, the same to the wei in either order.
It is not presentable that way: the count travels in a field called `tempF` under a "station" name, `strike` is a dummy, the basket buys equal amounts only, the five buys are not atomic (744,865 gas), and M1 and M3 remain.

| # | change | hours |
|---|---|---|
| 1 | Rename to a count market: oracle interface, `count` (unsigned) for `tempF`, market id for station/day, bucket for bracket. Remove `strike`, `strikeIndex`, `priceAtOrAboveStrike`, `quoteBasket`, `buyBasket`, `BasketTrade`. | 2 |
| 2 | Vector buy: `quoteBuyMany(amounts)` and `buyMany(amounts, maxCost)` with one event. A throwaway prototype (about 40 lines) matched sequential buys to the wei in 160 random trades; one vector buy used 114,945 gas against 207,528 for the same position by single buys. | 1.5 |
| 3 | Remove `initialQ` and `seed` (uniform start only, so the bound is exactly b ln 6). | 1 |
| 4 | New count oracle: one report per market id, refused before the season end (M3), range check against operating days, corrected comment (M2). | 2 |
| 5 | M1 fix: code check and trial call in the constructor, robust oracle read. | 1.5 |
| 6 | Events and comments. | 0.5 |
| 7 | Tests: port the suite to n = 6, replace basket tests by vector tests, add the cases listed below. | 6 |
| 8 | Python reference: vector quote, new reference vectors for n = 6. | 2 |
| 9 | Regenerate Remix files, write the deploy guide, dry run on the Remix VM, one Sepolia rehearsal. | 3.5 |
| | **Total** | **20** |

Not included: a new simulation for the rain-count market to replace results/part3 (about 4 to 6 h, Phase 1 work).

**Tests to add:** vector buy equals sequential buys (exact wei); zero vector and wrong length rejected; vector buy is atomic under the slippage limit; settle at every bucket edge (2/3, 4/5, 6/7, 8/9, 10/11), at 0 and at the maximum count; funding equals b ln 6 and one wei less is rejected; oracle is an EOA, an empty-return contract, a short-return contract; report before season end refused; report above operating days refused; random multi-buyer sequences then each cancel path; a zero-priced bucket wins; worst case over all six outcomes after every trade, including sizes past 45 b.

**Adapt or rewrite?** Adapt. The risky parts (fixed-point cost, collateral invariant, state machine, deadline logic) are correct and tested, and the changes mostly delete code. A rewrite in Lab 7 style would be shorter but would need the same test effort again; I estimate about 30 h for the same assurance.

**Distance from the labs.** Lab 7 is a binary market of about 100 lines: buyYes/buyNo, owner resolves, 1 ETH per share, plain exp that overflows past about 400 shares at b = 10, no oracle, no cancel. Lab 8 adds the log-sum-exp form; this contract uses the same idiom (`divu(d, b).neg().exp()`) for n outcomes. Lab 13 supplies the ReentrancyGuard import and the report/read oracle pattern. So the contract is Lab 8 maths for n outcomes, plus the Lab 13 guard, plus a three-state machine: 473 lines.
A student can explain it in five blocks: the cost function and why the maximum is subtracted; why charges telescope and the balance always covers the payout; the three states; the oracle time window; refunds. Harder to explain: the exp cutoff, 64.64 rounding, the `costNow` guard. Changes 1 and 3 remove the two parts that are hardest to justify for this plan.

## 6. Missing for the student deploy

- **docs/deploy_sepolia.md does not exist.** docs/status/viktor.md does not exist either.
- **contracts/remix:** both flattened files are current, have no imports, and compile with solc 0.8.26 to the same bytecode size as the source build (13,901 and 1,918 bytes; limit 24,576). They are usable for the temperature market as it stands. They were never opened in Remix or deployed. They must be regenerated after the adaptation.
- **Compiler settings** to state in the guide: 0.8.26, optimizer on, 200 runs. Paste the flattened file, not the source (m10).
- **Constructor arguments** are not written down anywhere. For the rain market as it stands: oracle address, id string, day number, bounds `[3,5,7,9,11]` (example edges), a dummy strike that is one of the bounds, b, unit, `[]`, three unix times (tradingClose <= observationEnd < reportDeadline), and a VALUE of at least b ln(6) x unit in wei.
- **Deploy order** is not written down: (1) oracle from account A; (2) market from account B with the funding; (3) buys; (4) after observationEnd, report from A; (5) anyone settles; (6) winners redeem; (7) sponsor withdraws. Plus one cancel rehearsal.
- Also missing: a way to compute the funding and the timestamps before deploy, a compressed demo timeline (minutes, not a season), a place to record addresses and transaction hashes, Etherscan verification steps. Measured locally: deploy of a six-bucket market 3,436,513 gas, first buy 175,921, repeat buy 107,521. Sepolia cost was not measured.

## Scratch files (not part of the repo)

/tmp/claude-0/-home-claude/2e63bb70-b158-5596-9232-154fe1f82d44/scratchpad/p0_contract/ holds npm_test_run1.log, npm_test_run2.log, probe/ProbeHelpers.sol, probe/probe.test.js, probe/probe_run1.log, probe/probe_run2.log, proto/ProtoLMSR.sol, proto/proto_run.log and recompute.py.

## Progress log (UTC)

- 2026-11-12 01:22 Started. Read docs/PHASE0.md. Scope: read-only review of contracts/, sim/, tests/test_lmsr_*.py, results/part3. Only this file is written.
- 2026-11-12 01:24 Read BracketLMSR.sol, TemperatureOracle.sol, MockOracle.sol, mocks/TestHelpers.sol, scripts/compile.js, test/01-04 and 99. Ran `npm test` in a scratch copy: 65 passing. Regenerated artifacts, Remix files and contract_quotes.json are byte-identical to the committed ones; gas_report.json differs in one number.
- 2026-11-12 01:25 pytest tests/test_lmsr_*.py (with -p no:cacheprovider so nothing is written): 29 passed, 0 skipped.
- 2026-11-12 01:29 Read sim/lmsr.py, sim/make_vectors.py, the pytest files, results/part3, and Labs 7, 8, 13 (as data). Ran probes A, C, D, E, F, G. A confirmed the stuck-funds bug. Probe F first failed because of my own test funding; fixed and re-run, passes.
- 2026-11-12 01:30 Second full `npm test`: 65 passing again. Independent recomputation of the contract quotes and of results/part3 numbers: all match.
- 2026-11-12 01:32 Throwaway vector-buy prototype compiled and checked. Confirmed 99_gas.test.js fails when run alone. Confirmed the latest OpenZeppelin release (5.6.1) has no security/ReentrancyGuard.sol. Hashes of contracts/, sim/, tests/ and results/part3 unchanged.
- 2026-11-12 01:35 Report written. Earlier log lines in this file briefly carried wrong clock times (my estimates); corrected from file timestamps.
