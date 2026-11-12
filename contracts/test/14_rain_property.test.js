// RainCountLMSR property tests over random trade sequences, extreme inputs,
// and the cross-check file for pytest (tests/test_lmsr_rain_crosscheck.py).
const fs = require("fs");
const path = require("path");
const { expect } = require("chai");
const { ethers, deployRain, ensureBalance, costF, rng, setTime, snapshot, revertTo, balanceOf, rainVectors, sourceHash,
  EDGES, STATION, SEASON, SEASON_DAYS, VEC } = require("./rain_helpers");

const MAX = ethers.MaxUint256;
const E18 = 10n ** 18n;
// one count inside each bucket for edges [2,4,6,8,10]
const COUNT_IN_BUCKET = [1, 3, 5, 7, 9, 40];

describe("14 rain property: the sponsor's loss never exceeds b ln(6)", function () {
  it("120 random trade sequences (single buys and baskets, sizes up to 60 b): after EVERY trade the loss in each of the six outcomes is <= b ln(6) unit; then settle in the worst bucket and pay everybody", async function () {
    const r = rng(473);
    const grid = [1, 5, 50, 200, 1000, 5000];
    let worstShare = 0, checks = 0, refused = 0;
    for (let s = 0; s < 120; s++) {
      const b = grid[s % grid.length];
      const unit = [10n ** 9n, 10n ** 12n, 10n ** 15n][s % 3];
      const m = await deployRain({ b, unit });
      const need = await m.market.requiredFunding();
      expect(Number(need)).to.be.closeTo(b * Math.log(6) * Number(unit), Math.max(2, 1e-9 * Number(need)));
      const traders = m.signers.slice(2, 8);
      for (const t of traders) await ensureBalance(t, 10n ** 24n);
      const nTrades = 1 + Math.floor(r() * 20);
      for (let k = 0; k < nTrades; k++) {
        const t = traders[Math.floor(r() * traders.length)];
        // sizes from 1 share to about 60 b: well past the 45 b exp cutoff
        const size = () => BigInt(1 + Math.floor(Math.pow(r(), 3) * 60 * b));
        const v = [0n, 0n, 0n, 0n, 0n, 0n];
        if (r() < 0.4) for (let j = 0; j < 6; j++) v[j] = r() < 0.5 ? 0n : size();
        if (v.every((x) => x === 0n)) v[Math.floor(r() * 6)] = size();
        const quote = await m.market.quoteBasket(v);
        if (quote === 0n) {
          await expect(m.market.connect(t).buyBasket(v, MAX, { value: 1 })).to.be.revertedWith("Cost rounds to zero");
          refused++;
          continue;
        }
        await m.market.connect(t).buyBasket(v, quote, { value: quote });
        // worst case over all six outcomes, without settling
        const q = await m.market.getQuantities();
        const paid = await m.market.totalPaid();
        const pool = await balanceOf(m.market);
        expect(pool).to.equal(m.value + paid);
        for (let j = 0; j < 6; j++) {
          const payout = q[j] * unit;
          expect(pool, `sequence ${s} trade ${k} bucket ${j}: collateral`).to.be.gte(payout);
          // sponsor loss if bucket j wins = payout - paid by buyers
          if (payout > paid) {
            const loss = payout - paid;
            expect(loss, `sequence ${s} trade ${k} bucket ${j}: loss`).to.be.lte(need);
            worstShare = Math.max(worstShare, Number(loss) / Number(need));
          }
          checks++;
        }
      }
      // settle in the bucket with the most shares (the sponsor's worst outcome) and pay everybody
      const q = [...(await m.market.getQuantities())];
      let w = 0;
      for (let j = 1; j < 6; j++) if (q[j] > q[w]) w = j;
      const pool = await balanceOf(m.market);
      await setTime(m.seasonEnd + 1);
      await m.oracle.setReport(STATION, SEASON, COUNT_IN_BUCKET[w]);
      await m.market.settle();
      expect(await m.market.winningBucket()).to.equal(BigInt(w));
      const owed = await m.market.reserved();
      expect(owed).to.equal(q[w] * unit);
      let out = 0n;
      for (const t of traders) {
        const sh = await m.market.sharesOf(t.address, w);
        if (sh > 0n) {
          await m.market.connect(t).redeem();
          out += sh * unit;
        }
      }
      expect(out).to.equal(owed); // winners take exactly what is owed
      const back = pool - owed;
      expect(m.value - back, `sequence ${s}`).to.be.lte(need); // realised sponsor loss
      if (back > 0n) await m.market.connect(m.sponsor).sponsorWithdraw();
      expect(await balanceOf(m.market)).to.equal(0n);
    }
    console.log(`      ${checks} outcome checks; ${refused} zero-cost buys refused; largest possible sponsor loss seen = ${(100 * worstShare).toFixed(4)}% of b ln(6)`);
    expect(worstShare).to.be.gt(0.9).and.lte(1); // the bound is approached, never passed
  });

  it("the worst case is approached: one huge buy of a single bucket costs the sponsor almost exactly b ln(6)", async function () {
    const m = await deployRain({ b: 200 });
    const need = await m.market.requiredFunding();
    await m.market.connect(m.alice).buy(5, 20000, MAX, { value: E18 });
    const loss = 20000n * m.unit - (await m.market.totalPaid());
    expect(loss).to.be.lte(need);
    expect(Number(loss) / Number(need)).to.be.gt(0.999999);
  });

  it("a bucket whose price has underflowed to zero can still win and is paid in full", async function () {
    const m = await deployRain({ b: 10, unit: 10n ** 9n });
    await m.market.connect(m.alice).buy(0, 7, MAX, { value: E18 });
    await m.market.connect(m.bob).buy(5, 1000, MAX, { value: E18 }); // 100 b ahead of bucket 0
    expect((await m.market.prices())[0]).to.equal(0n);
    await setTime(m.seasonEnd + 1);
    await m.oracle.setReport(STATION, SEASON, 0);
    await m.market.settle();
    await expect(m.market.connect(m.alice).redeem()).to.changeEtherBalance(m.alice, 7n * m.unit);
    await expect(m.market.connect(m.bob).redeem()).to.be.revertedWith("Nothing to redeem");
    await m.market.connect(m.sponsor).sponsorWithdraw();
    expect(await balanceOf(m.market)).to.equal(0n);
  });
});

describe("14 rain property: cancel and refund solvency with many buyers", function () {
  it("60 random markets, 9 buyers, both cancel paths: every buyer gets the exact cost basis, the sponsor the funding, the balance ends at 0", async function () {
    const r = rng(475);
    let refunds = 0;
    for (let s = 0; s < 60; s++) {
      const b = [3, 50, 200, 1000][s % 4];
      const unit = [10n ** 9n, 10n ** 12n, 10n ** 16n][s % 3];
      const m = await deployRain({ b, unit });
      const buyers = m.signers.slice(2, 11);
      const spent = new Map(buyers.map((t) => [t.address, 0n]));
      for (const t of buyers) await ensureBalance(t, 10n ** 24n);
      const nTrades = 5 + Math.floor(r() * 25);
      for (let k = 0; k < nTrades; k++) {
        const t = buyers[Math.floor(r() * buyers.length)];
        const v = Array.from({ length: 6 }, () => (r() < 0.6 ? 0n : BigInt(1 + Math.floor(Math.pow(r(), 2) * 20 * b))));
        if (v.every((x) => x === 0n)) v[Math.floor(r() * 6)] = 1n;
        const quote = await m.market.quoteBasket(v);
        if (quote === 0n) continue;
        // pay too much on purpose: the excess must come straight back and not count as "paid"
        await m.market.connect(t).buyBasket(v, quote, { value: quote + BigInt(Math.floor(r() * 1e6)) });
        spent.set(t.address, spent.get(t.address) + quote);
      }
      const total = [...spent.values()].reduce((a, x) => a + x, 0n);
      expect(await m.market.totalPaid()).to.equal(total);
      expect(await balanceOf(m.market)).to.equal(m.value + total);
      if (s % 2 === 0) {
        await m.market.connect(m.sponsor).emergencyCancel();
      } else {
        await setTime(m.reportDeadline + 1);
        await m.market.connect(buyers[0]).cancelAfterDeadline();
      }
      expect(await m.market.reserved()).to.equal(total);
      // random claim order; the sponsor withdraws somewhere in the middle
      const order = buyers.slice().sort(() => r() - 0.5);
      const sponsorAt = Math.floor(r() * order.length);
      for (let i = 0; i < order.length; i++) {
        if (i === sponsorAt) await expect(m.market.connect(m.sponsor).sponsorWithdraw()).to.changeEtherBalance(m.sponsor, m.value);
        const t = order[i];
        const due = spent.get(t.address);
        if (due === 0n) {
          await expect(m.market.connect(t).claimRefund()).to.be.revertedWith("Nothing to refund");
        } else {
          await expect(m.market.connect(t).claimRefund()).to.changeEtherBalance(t, due);
          await expect(m.market.connect(t).claimRefund()).to.be.revertedWith("Nothing to refund");
          refunds++;
        }
      }
      expect(await m.market.reserved()).to.equal(0n);
      expect(await balanceOf(m.market)).to.equal(0n);
    }
    console.log(`      ${refunds} refunds checked`);
  });
});

describe("14 rain extreme inputs: no overflow, no underflow", function () {
  it("b = 1 share, unit = 1 gwei: quantities up to 1e15 work, prices stay in [0, 1]", async function () {
    const m = await deployRain({ b: 1, unit: 10n ** 9n });
    const t = m.alice;
    await ensureBalance(t, 10n ** 26n);
    expect(await m.market.requiredFunding()).to.equal(1791759469n); // floor(ln 6 * 1e9) wei
    await m.market.connect(t).buy(0, 1, MAX, { value: E18 });
    await m.market.connect(t).buy(3, 44, MAX, { value: E18 });
    await m.market.connect(t).buy(4, 10n ** 15n, MAX, { value: 10n ** 24n + E18 }); // MAX_Q
    const p = await m.market.prices();
    expect(p[4]).to.equal(E18);
    expect(p[0]).to.equal(0n);
    expect(await balanceOf(m.market)).to.be.gte(10n ** 24n);
    await expect(m.market.connect(t).buy(4, 1, MAX, { value: E18 })).to.be.revertedWith("Quantity too large");
  });

  it("b = 1e12 shares, unit = 1 ether (largest allowed): quotes match the float reference, collateral holds", async function () {
    const b = 10n ** 12n, unit = E18;
    const m = await deployRain({ b, unit });
    const t = m.alice;
    await ensureBalance(t, 10n ** 36n);
    const q = new Array(6).fill(0);
    for (const v of [[0, 0, 1, 0, 0, 0], [10 ** 9, 0, 0, 0, 0, 0], [0, 10 ** 12, 0, 10 ** 12, 0, 0], [0, 0, 0, 0, 0, 10 ** 14], [1, 2, 3, 4, 5, 10 ** 15 - 10 ** 14 - 1]]) {
      const quote = await m.market.quoteBasket(v.map(BigInt));
      const q2 = q.map((x, j) => x + v[j]);
      const ref = costF(q2, 1e12) - costF(q, 1e12);
      expect(Number(quote) / 1e18).to.be.closeTo(ref, Math.max(1e-3, 1e-9 * ref));
      await m.market.connect(t).buyBasket(v.map(BigInt), quote, { value: quote });
      for (let j = 0; j < 6; j++) q[j] = q2[j];
      const sold = await m.market.getQuantities();
      const top = sold.reduce((a, x) => (x > a ? x : a), 0n);
      expect(await balanceOf(m.market)).to.be.gte(top * unit);
    }
    const p = await m.market.prices();
    expect([...p].reduce((a, x) => a + x, 0n)).to.be.closeTo(E18, 7n);
  });

  it("a 1-share buy with a huge b costs unit / 6 within the fixed-point tolerance 2 (b unit 2^-60 + 1) wei", async function () {
    // b * unit = 1e21 wei: one 64.64 rounding step is about 54 wei here, so the quote is not exact to the wei.
    const m = await deployRain({ b: 10n ** 12n, unit: 10n ** 9n });
    const tol = 2 * (1e21 / 2 ** 60 + 1);
    for (let j = 0; j < 6; j++) {
      const c = await m.market.quoteBuy(j, 1);
      expect(Number(c)).to.be.closeTo(1e9 / 6, tol);
      expect(c).to.be.lte(10n ** 9n);
    }
    // with a sensible b the same quote is exact to 2 wei
    const s = await deployRain({ b: 1000, unit: 10n ** 9n });
    expect(Number(await s.market.quoteBuy(2, 1))).to.be.closeTo((Math.log((5 + Math.exp(1 / 1000)) / 6) * 1000) * 1e9, 2);
  });

  it("small b with spreads far beyond the exp cutoff: no revert; the leading bucket costs exactly 1 unit per share", async function () {
    const m = await deployRain({ b: 3, unit: 10n ** 9n });
    const t = m.alice;
    await ensureBalance(t, 10n ** 30n);
    await m.market.connect(t).buy(2, 10n ** 9n, MAX, { value: 10n ** 19n });
    await m.market.connect(t).buy(5, 10n ** 12n, MAX, { value: 10n ** 22n });
    const p = await m.market.prices();
    expect(p[5]).to.equal(E18);
    expect(p[2]).to.equal(0n);
    expect(await m.market.quoteBuy(5, 1000)).to.equal(1000n * 10n ** 9n);
    const q = await m.market.getQuantities();
    expect(await m.market.costOf([...q])).to.equal(10n ** 12n * 10n ** 9n);
  });
});

describe("14 cross-check file for the Python reference", function () {
  it("writes contract quotes for the stepped hedge: b in {50, 200, 1000, 5000}, sizes {10, 100, 1000}, from the uniform start and from a traded state", async function () {
    const V = rainVectors();
    const out = {
      note: "Quotes returned by RainCountLMSR.sol in the Hardhat EVM (not a live chain). Written by test/14_rain_property.test.js. " +
        "The 'informed' states use a PLACEHOLDER count distribution; they only move q away from zero.",
      unit: "1000000000000", edges: EDGES, stepped: [0, 0, 0, 1, 2, 3],
      source_sha256: { "RainCountLMSR.sol": sourceHash("RainCountLMSR.sol") },
      cases: [],
    };
    for (const b of [50, 200, 1000, 5000]) {
      for (const state of ["uniform", "informed"]) {
        const m = await deployRain({ b });
        if (state === "informed") {
          await m.market.connect(m.bob).buyBasket(V.informed_q[String(b)].map(BigInt), MAX, { value: 10n ** 20n });
        }
        const q = (await m.market.getQuantities()).map((x) => x.toString());
        const base = {
          b, state, q,
          requiredFunding: (await m.market.requiredFunding()).toString(),
          costNow: (await m.market.costNow()).toString(),
          prices: (await m.market.prices()).map((x) => x.toString()),
        };
        for (const size of [10, 100, 1000]) {
          const vector = out.stepped.map((x) => x * size);
          out.cases.push({
            ...base, size, vector,
            quoteBasket: (await m.market.quoteBasket(vector)).toString(),
            quoteBuy5: (await m.market.quoteBuy(5, size)).toString(),
            quoteBuy0: (await m.market.quoteBuy(0, size)).toString(),
          });
        }
      }
    }
    expect(out.cases.length).to.equal(24);
    fs.writeFileSync(path.join(VEC, "rain_contract_quotes.json"), JSON.stringify(out, null, 1));
  });
});
