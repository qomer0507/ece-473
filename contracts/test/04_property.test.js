// Property tests over random trade sequences, extreme inputs, and the cross-check file for pytest.
const fs = require("fs");
const path = require("path");
const { expect } = require("chai");
const { ethers, deployMarket, ensureBalance, costF, rng, setTime, vectors, STATION, VEC } = require("./helpers");

const MAX = ethers.MaxUint256;
const E18 = 10n ** 18n;
const bal = async (c) => ethers.provider.getBalance(await c.getAddress());

describe("04 property: sponsor loss never exceeds b ln(n)", function () {
  it("120 random trade sequences (uniform prior): loss <= funding requirement, payouts conserve, collateral holds", async function () {
    const r = rng(473);
    const grid = [1, 5, 50, 200, 1000, 5000];
    let worstShare = 0, checks = 0;
    for (let s = 0; s < 120; s++) {
      const b = grid[s % grid.length];
      const unit = [1n, 10n ** 9n, 10n ** 12n][s % 3];
      const m = await deployMarket({ b, unit });
      const need = await m.market.requiredFunding();
      // b ln(n) in wei, as computed in double precision
      expect(Number(need)).to.be.closeTo(b * Math.log(12) * Number(unit), Math.max(2, 1e-9 * Number(need)));
      const traders = m.signers.slice(1, 6);
      const nTrades = 1 + Math.floor(r() * 25);
      for (let k = 0; k < nTrades; k++) {
        const t = traders[Math.floor(r() * traders.length)];
        // sizes from 1 share to about 20 b, to push prices to the extremes
        const shares = 1 + Math.floor(Math.pow(r(), 3) * 20 * b);
        if (r() < 0.25) await m.market.connect(t).buyBasket(shares, MAX, { value: 1000n * E18 });
        else await m.market.connect(t).buy(Math.floor(r() * 12), shares, MAX, { value: 1000n * E18 });
        const sold = await m.market.getSold();
        const top = sold.reduce((a, x) => (x > a ? x : a), 0n);
        expect(await bal(m.market)).to.be.gte(top * unit);
        checks++;
      }
      const pool = await bal(m.market);
      const totalPaid = await m.market.totalPaid();
      expect(pool).to.equal(m.value + totalPaid);

      // settle at a random temperature between 60 and 110
      const temp = 60 + Math.floor(r() * 51);
      await setTime(m.observationEnd + 1);
      await m.oracle.setReport(STATION, m.day, temp);
      await m.market.settle();
      const w = await m.market.winningBracket();
      const owed = await m.market.reserved();
      expect(owed).to.equal((await m.market.getSold())[Number(w)] * unit);

      // sponsor P&L = what comes back minus what went in
      const back = pool - owed;
      const loss = m.value - back; // positive = loss
      expect(loss, `sequence ${s}`).to.be.lte(need);
      const share = Number(loss) / Number(need);
      if (share > worstShare) worstShare = share;

      // conservation: winners + sponsor take exactly the pool
      let out = 0n;
      for (const t of traders) {
        const sh = await m.market.sharesOf(t.address, w);
        if (sh > 0n) {
          await m.market.connect(t).redeem();
          out += sh * unit;
        }
      }
      expect(out).to.equal(owed);
      if (back > 0n) await m.market.sponsorWithdraw();
      expect(await bal(m.market)).to.equal(0n);
    }
    console.log(`      ${checks} collateral checks; largest realised sponsor loss = ${(100 * worstShare).toFixed(1)}% of b ln(n)`);
  });

  it("40 random sequences with a random non-uniform seed: loss <= C(q0)", async function () {
    const r = rng(474);
    for (let s = 0; s < 40; s++) {
      const b = [5, 50, 200, 1000][s % 4];
      const initialQ = Array.from({ length: 12 }, () => Math.floor(r() * 5 * b));
      initialQ[Math.floor(r() * 12)] = 0;
      const m = await deployMarket({ b, initialQ });
      const need = await m.market.requiredFunding();
      expect(Number(need)).to.be.closeTo(costF(initialQ, b) * 1e12, Math.max(2, 1e-9 * Number(need)));
      for (let k = 0; k < 12; k++) {
        const shares = 1 + Math.floor(Math.pow(r(), 2) * 15 * b);
        const t = m.signers[1 + (k % 4)];
        if (r() < 0.25) await m.market.connect(t).buyBasket(shares, MAX, { value: 1000n * E18 });
        else await m.market.connect(t).buy(Math.floor(r() * 12), shares, MAX, { value: 1000n * E18 });
      }
      const pool = await bal(m.market);
      // worst case over all 12 outcomes, without settling
      const sold = await m.market.getSold();
      const top = sold.reduce((a, x) => (x > a ? x : a), 0n);
      const worstLoss = m.value - (pool - top * m.unit);
      expect(worstLoss, `sequence ${s}`).to.be.lte(need);
    }
  });

  it("the worst case is approached: one huge buy of a single bracket costs the sponsor almost b ln(n)", async function () {
    const m = await deployMarket({ b: 200 });
    const need = await m.market.requiredFunding();
    await m.market.connect(m.signers[1]).buy(11, 20000, MAX, { value: E18 });
    const loss = 20000n * m.unit - (await m.market.totalPaid());
    expect(loss).to.be.lte(need);
    expect(Number(loss) / Number(need)).to.be.gt(0.999999);
  });
});

describe("04 extreme inputs: no overflow, no underflow", function () {
  it("b = 1 share, unit = 1 wei: quantities up to 1e15 work, prices stay in [0, 1]", async function () {
    const m = await deployMarket({ b: 1, unit: 1 });
    const t = m.signers[1];
    await ensureBalance(t, 10n ** 20n);
    expect(await m.market.requiredFunding()).to.equal(2n); // floor(ln 12) wei
    await m.market.connect(t).buy(0, 1, MAX, { value: 10 });
    await m.market.connect(t).buy(5, 44, MAX, { value: 100 });      // just inside the exp cutoff
    await m.market.connect(t).buy(5, 2, MAX, { value: 100 });       // beyond the cutoff
    await m.market.connect(t).buy(7, 10n ** 15n, MAX, { value: 10n ** 15n + 100n }); // MAX_Q
    const p = await m.market.prices();
    expect(p[7]).to.equal(E18);
    expect(p[0]).to.equal(0n);
    expect(await bal(m.market)).to.be.gte(10n ** 15n);
    await expect(m.market.connect(t).buy(7, 1, MAX, { value: 100 })).to.be.revertedWith("Quantity too large");
    await expect(m.market.connect(t).buyBasket(1, MAX, { value: 100 })).to.be.revertedWith("Quantity too large");
    // a bracket whose price underflowed to 0 can still be bought, at a cost that is >= 0 and <= shares
    const c = await m.market.quoteBuy(0, 1000);
    expect(c).to.be.lte(1000n);
  });

  it("b = 1e12 shares, unit = 1 ether (largest allowed): costs match the float reference, collateral holds", async function () {
    const b = 10n ** 12n, unit = E18;
    const m = await deployMarket({ b, unit });
    const t = m.signers[1];
    await ensureBalance(t, 10n ** 36n);
    const q = new Array(12).fill(0);
    for (const [j, s] of [[6, 1n], [6, 10n ** 9n], [0, 10n ** 12n], [11, 10n ** 14n], [3, 10n ** 15n - 1n]]) {
      const quote = await m.market.quoteBuy(j, s);
      const q2 = q.slice();
      q2[j] += Number(s);
      const ref = costF(q2, 1e12) - costF(q, 1e12);
      expect(Number(quote) / 1e18).to.be.closeTo(ref, Math.max(1e-3, 1e-9 * ref));
      await m.market.connect(t).buy(j, s, quote, { value: quote });
      q[j] = q2[j];
      const sold = await m.market.getSold();
      const top = sold.reduce((a, x) => (x > a ? x : a), 0n);
      expect(await bal(m.market)).to.be.gte(top * unit);
    }
    await m.market.connect(t).buyBasket(10n ** 12n, MAX, { value: 10n ** 31n });
    const p = await m.market.prices();
    expect([...p].reduce((a, x) => a + x, 0n)).to.be.closeTo(E18, 13n);
  });

  it("a 1-share buy with a huge b never costs less than 0 and never more than 1 unit", async function () {
    const m = await deployMarket({ b: 10n ** 12n, unit: 10n ** 6n });
    for (let j = 0; j < 12; j += 5) {
      const c = await m.market.quoteBuy(j, 1);
      expect(c).to.be.lte(10n ** 6n);
      expect(Number(c)).to.be.closeTo(1e6 / 12, 2);
      await m.market.connect(m.signers[1]).buy(j, 1, MAX, { value: E18 });
    }
  });

  it("small b with spreads far beyond the exp cutoff: no revert, weights underflow to 0", async function () {
    const m = await deployMarket({ b: 3, unit: 10n ** 9n });
    const t = m.signers[1];
    await ensureBalance(t, 10n ** 30n);
    await m.market.connect(t).buy(2, 10n ** 9n, MAX, { value: 10n ** 19n });
    await m.market.connect(t).buy(9, 10n ** 12n, MAX, { value: 10n ** 22n });
    const p = await m.market.prices();
    expect(p[9]).to.equal(E18);
    expect(p[2]).to.equal(0n);
    // cost of the dominant bracket is then exactly shares * unit
    expect(await m.market.quoteBuy(9, 1000)).to.equal(1000n * 10n ** 9n);
    const q = await m.market.getQuantities();
    expect(await m.market.costOf([...q])).to.equal(10n ** 12n * 10n ** 9n);
  });
});

describe("04 cross-check file for the Python reference", function () {
  it("writes contract quotes for b in {50, 200, 1000, 5000} and sizes {10, 100, 1000} (uniform and climatology seed)", async function () {
    const V = vectors();
    const out = {
      note: "Quotes returned by BracketLMSR.sol in the Hardhat EVM (not a live chain). Written by test/04_property.test.js.",
      unit: "1000000000000", bounds: V.bounds, strike: V.strike, cases: [],
    };
    for (const b of [50, 200, 1000, 5000]) {
      for (const prior of ["uniform", "climatology"]) {
        const initialQ = prior === "uniform" ? [] : V.climatology_seeds[String(b)].map(BigInt);
        const m = await deployMarket({ b, initialQ });
        const q0 = (await m.market.getQuantities()).map((x) => x.toString());
        const base = {
          b, prior, q0,
          requiredFunding: (await m.market.requiredFunding()).toString(),
          priceAtOrAbove: (await m.market.priceAtOrAboveStrike()).toString(),
          prices: (await m.market.prices()).map((x) => x.toString()),
        };
        for (const size of [10, 100, 1000]) {
          out.cases.push({
            ...base, size,
            quoteBasket: (await m.market.quoteBasket(size)).toString(),
            quoteBuy6: (await m.market.quoteBuy(6, size)).toString(),
            quoteBuy0: (await m.market.quoteBuy(0, size)).toString(),
          });
        }
        // and one state after trading, to check a non-trivial q
        await m.market.connect(m.signers[1]).buyBasket(137, MAX, { value: E18 });
        await m.market.connect(m.signers[1]).buy(2, 59, MAX, { value: E18 });
        out.cases.push({
          b, prior: prior + "+trades", size: 100,
          q0: (await m.market.getQuantities()).map((x) => x.toString()),
          requiredFunding: null,
          priceAtOrAbove: (await m.market.priceAtOrAboveStrike()).toString(),
          prices: (await m.market.prices()).map((x) => x.toString()),
          quoteBasket: (await m.market.quoteBasket(100)).toString(),
          quoteBuy6: (await m.market.quoteBuy(6, 100)).toString(),
          quoteBuy0: (await m.market.quoteBuy(0, 100)).toString(),
        });
      }
    }
    expect(out.cases.length).to.equal(32);
    fs.writeFileSync(path.join(VEC, "contract_quotes.json"), JSON.stringify(out, null, 1));
  });
});
