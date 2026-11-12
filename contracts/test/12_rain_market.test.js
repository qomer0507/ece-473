// RainCountLMSR: construction, buckets, single buys, vector buys (baskets), slippage, limits.
const { expect } = require("chai");
const { ethers, deployRain, deploy, costF, pricesF, rng, setTime, ensureBalance, balanceOf, bucketOf,
  EDGES, STATION, SEASON, SEASON_DAYS, DAYS } = require("./rain_helpers");

const MAX = ethers.MaxUint256;
const E18 = 10n ** 18n;
const sum = (a) => a.reduce((x, y) => x + y, 0n);

describe("12 rain market: construction and views", function () {
  it("stores the definition and copies the season from the oracle", async function () {
    const m = await deployRain();
    expect(await m.market.NUM_BUCKETS()).to.equal(6n);
    expect((await m.market.getEdges()).map(Number)).to.deep.equal(EDGES);
    expect(await m.market.station()).to.equal(STATION);
    expect(await m.market.season()).to.equal(BigInt(SEASON));
    expect(await m.market.seasonStart()).to.equal(BigInt(m.seasonStart));
    expect(await m.market.seasonEnd()).to.equal(BigInt(m.seasonEnd));
    expect(await m.market.seasonDays()).to.equal(BigInt(SEASON_DAYS));
    expect(await m.market.sponsor()).to.equal(m.sponsor.address);
    expect(await m.market.oracle()).to.equal(await m.oracle.getAddress());
    expect(await m.market.state()).to.equal(0n);
    expect((await m.market.getQuantities()).map(Number)).to.deep.equal([0, 0, 0, 0, 0, 0]);
  });

  it("emits MarketCreated with the arguments", async function () {
    const m = await deployRain();
    const receipt = await m.market.deploymentTransaction().wait();
    const ev = receipt.logs.map((l) => m.market.interface.parseLog(l)).find((e) => e && e.name === "MarketCreated");
    expect(ev.args.sponsor).to.equal(m.sponsor.address);
    expect(ev.args.oracle).to.equal(await m.oracle.getAddress());
    expect(ev.args.station).to.equal(STATION);
    expect(ev.args.season).to.equal(BigInt(SEASON));
    expect(ev.args.edges.map(Number)).to.deep.equal(EDGES);
    expect(ev.args.b).to.equal(200n);
    expect(ev.args.funding).to.equal(m.value);
    expect(ev.args.requiredFunding).to.equal(await m.market.requiredFunding());
  });

  it("maps every count from 0 to 102 to exactly one bucket; edges are inclusive upper ends", async function () {
    const { market } = await deployRain();
    const want = { 0: 0, 2: 0, 3: 1, 4: 1, 5: 2, 6: 2, 7: 3, 8: 3, 9: 4, 10: 4, 11: 5, 12: 5, 102: 5 };
    for (const [c, j] of Object.entries(want)) expect(await market.bucketOf(Number(c)), `count ${c}`).to.equal(BigInt(j));
    const seen = new Set();
    let prev = 0n;
    for (let c = 0; c <= SEASON_DAYS; c++) {
      const j = await market.bucketOf(c);
      expect(j).to.equal(BigInt(bucketOf(c)));
      expect(j >= prev).to.equal(true);
      prev = j;
      seen.add(Number(j));
    }
    expect([...seen]).to.deep.equal([0, 1, 2, 3, 4, 5]);
  });

  it("other edges work: [0,1,3,7,20] gives 0 | 1 | 2-3 | 4-7 | 8-20 | 21+", async function () {
    const { market } = await deployRain({ edges: [0, 1, 3, 7, 20] });
    const want = { 0: 0, 1: 1, 2: 2, 3: 2, 4: 3, 7: 3, 8: 4, 20: 4, 21: 5, 102: 5 };
    for (const [c, j] of Object.entries(want)) expect(await market.bucketOf(Number(c))).to.equal(BigInt(j));
  });

  it("starts at uniform prices 1/6", async function () {
    const { market } = await deployRain();
    const p = await market.prices();
    expect(p.length).to.equal(6);
    for (const x of p) expect(x).to.be.closeTo(E18 / 6n, 2n);
    expect(await market.price(5)).to.equal(p[5]);
    await expect(market.price(6)).to.be.revertedWith("Bad bucket");
  });

  it("funding: exactly b*ln(6)*unit is accepted, one wei less is refused, excess is stored", async function () {
    const b = 200n, unit = 10n ** 12n;
    const m = await deployRain({ b, unit });
    const need = await m.market.requiredFunding();
    expect(Number(need)).to.be.closeTo(200 * Math.log(6) * 1e12, 1e3);
    expect(await m.market.funding()).to.equal(m.value);
    const exact = await deployRain({ b, unit, value: need });
    expect(await exact.market.funding()).to.equal(need);
    await expect(deployRain({ b, unit, value: need - 1n })).to.be.revertedWith("Funding below worst-case loss");
    await expect(deployRain({ b, unit, value: 0n })).to.be.revertedWith("Funding below worst-case loss");
  });

  it("rejects bad constructor arguments (b, unit, edges, times, delays)", async function () {
    const bad = async (o, msg) => expect(deployRain(o), msg).to.be.revertedWith(msg);
    await bad({ b: 0 }, "b out of range");
    await bad({ b: 10n ** 12n + 1n, value: 1n }, "b out of range");
    // review item m2: a dust unit is refused
    await bad({ unit: 1, value: 1n }, "unit out of range");
    await bad({ unit: 10n ** 9n - 1n, value: 1n }, "unit out of range");
    await bad({ unit: E18 + 1n, value: 1n }, "unit out of range");
    await bad({ edges: [2, 4, 6, 8] }, "Need five edges");
    await bad({ edges: [2, 4, 6, 8, 10, 12] }, "Need five edges");
    await bad({ edges: [] }, "Need five edges");
    await bad({ edges: [2, 2, 6, 8, 10] }, "Edges not increasing");
    await bad({ edges: [2, 4, 6, 10, 8] }, "Edges not increasing");
    await bad({ edges: [2, 4, 6, 8, 102] }, "Last edge must be below season days");
    await bad({ disputeDelay: 30 * DAYS + 1 }, "Dispute delay too long");
    await bad({ claimPeriod: 7 * DAYS - 1 }, "Claim period out of range");
    await bad({ claimPeriod: 3650 * DAYS + 1 }, "Claim period out of range");
    const t = (await ethers.provider.getBlock("latest")).timestamp;
    await bad({ tradingClose: t - 10 }, "Trading close in the past");
    await bad({ reportDeadline: t + 2000 }, "Deadline before season end");
    await bad({ reportDeadline: t + 1500 }, "Deadline before season end");
  });

  it("review m1: trading must close at or before the season start", async function () {
    const t = (await ethers.provider.getBlock("latest")).timestamp;
    await expect(deployRain({ tradingClose: t + 1001, seasonStart: t + 1000 })).to.be.revertedWith("Trading must close by season start");
    await expect(deployRain({ tradingClose: t + 1999, seasonStart: t + 1000 })).to.be.revertedWith("Trading must close by season start");
    const early = await deployRain({ tradingClose: t + 500, seasonStart: t + 1000 });
    expect(await early.market.tradingClose()).to.equal(BigInt(t + 500));
  });

  it("accepts the largest edge that leaves the top bucket reachable, and a dispute delay of 30 days", async function () {
    const m = await deployRain({ edges: [0, 1, 2, 3, 101], disputeDelay: 30 * DAYS });
    expect(await m.market.bucketOf(102)).to.equal(5n);
    expect(await m.market.disputeDelay()).to.equal(BigInt(30 * DAYS));
  });
});

describe("12 rain market: single-bucket buys", function () {
  it("charges the quote, credits shares, emits Trade, matches the float reference", async function () {
    const m = await deployRain({ b: 200 });
    const quote = await m.market.quoteBuy(4, 100);
    expect(Number(quote) / 1e12).to.be.closeTo(costF([0, 0, 0, 0, 100, 0], 200) - costF([0, 0, 0, 0, 0, 0], 200), 1e-9);
    const call = m.market.connect(m.alice).buy(4, 100, quote, { value: quote });
    await expect(call).to.emit(m.market, "Trade").withArgs(m.alice.address, 4n, 100n, quote);
    await expect(call).to.changeEtherBalances([m.alice, m.market], [-quote, quote]);
    expect(await m.market.sharesOf(m.alice.address, 4)).to.equal(100n);
    expect((await m.market.sharesOfAll(m.alice.address)).map(Number)).to.deep.equal([0, 0, 0, 0, 100, 0]);
    expect(await m.market.paid(m.alice.address)).to.equal(quote);
    expect(await m.market.totalPaid()).to.equal(quote);
    expect(await m.market.costNow()).to.equal((await m.market.requiredFunding()) + quote);
    const p = (await m.market.prices()).map((x) => Number(x) / 1e18);
    const ref = pricesF([0, 0, 0, 0, 100, 0], 200);
    for (let j = 0; j < 6; j++) expect(p[j]).to.be.closeTo(ref[j], 1e-12);
  });

  it("monotonicity: a buy raises that bucket's price and lowers every other price", async function () {
    const m = await deployRain({ b: 50 });
    const r = rng(12);
    for (let k = 0; k < 20; k++) {
      const j = Math.floor(r() * 6);
      const before = await m.market.prices();
      await m.market.connect(m.alice).buy(j, 1 + Math.floor(r() * 40), MAX, { value: E18 });
      const after = await m.market.prices();
      for (let i = 0; i < 6; i++) {
        if (i === j) expect(after[i]).to.be.gt(before[i]);
        else expect(after[i]).to.be.lt(before[i]);
      }
      expect(sum([...after])).to.be.closeTo(E18, 7n);
    }
  });

  it("the cost of a buy lies between shares*price_before and shares*price_after", async function () {
    const m = await deployRain({ b: 200 });
    for (const [j, s] of [[0, 10n], [3, 250n], [5, 1000n], [3, 40n]]) {
      const before = (await m.market.prices())[j];
      const cost = await m.market.quoteBuy(j, s);
      await m.market.connect(m.alice).buy(j, s, MAX, { value: E18 });
      const after = (await m.market.prices())[j];
      expect(cost * E18).to.be.gte(s * m.unit * before - E18);
      expect(cost * E18).to.be.lte(s * m.unit * after + E18 * m.unit);
    }
  });

  it("rejects zero shares, a bad bucket, low payment, and buys at or after the trading close", async function () {
    const m = await deployRain();
    await expect(m.market.connect(m.alice).buy(0, 0, MAX, { value: 1 })).to.be.revertedWith("Zero quantity");
    await expect(m.market.connect(m.alice).buy(6, 1, MAX, { value: E18 })).to.be.revertedWith("Bad bucket");
    await expect(m.market.quoteBuy(6, 1)).to.be.revertedWith("Bad bucket");
    await expect(m.market.quoteBuy(0, 0)).to.be.revertedWith("Zero quantity");
    const quote = await m.market.quoteBuy(2, 10);
    await expect(m.market.connect(m.alice).buy(2, 10, MAX, { value: quote - 1n })).to.be.revertedWith("Insufficient payment");
    await setTime(m.tradingClose - 2);
    await m.market.connect(m.alice).buy(2, 10, MAX, { value: E18 }); // mined at tradingClose - 1
    await expect(m.market.connect(m.alice).buy(2, 10, MAX, { value: E18 })).to.be.revertedWith("Trading closed"); // at tradingClose
    await expect(m.market.connect(m.alice).buyBasket([0, 0, 0, 1, 2, 3], MAX, { value: E18 })).to.be.revertedWith("Trading closed");
  });

  it("returns any excess payment", async function () {
    const m = await deployRain();
    const quote = await m.market.quoteBuy(1, 77);
    await expect(m.market.connect(m.alice).buy(1, 77, MAX, { value: quote + 12345n }))
      .to.changeEtherBalances([m.alice, m.market], [-quote, quote]);
    const q2 = await m.market.quoteBasket([5, 0, 0, 1, 2, 3]);
    await expect(m.market.connect(m.alice).buyBasket([5, 0, 0, 1, 2, 3], MAX, { value: q2 + E18 }))
      .to.changeEtherBalances([m.alice, m.market], [-q2, q2]);
  });

  it("slippage: reverts above maxCost, passes at maxCost, and protects against a trade that lands first", async function () {
    const m = await deployRain();
    const quote = await m.market.quoteBuy(5, 100);
    await expect(m.market.connect(m.alice).buy(5, 100, quote - 1n, { value: quote })).to.be.revertedWith("Cost above slippage limit");
    // bob's order lands first and moves the price
    await m.market.connect(m.bob).buy(5, 500, MAX, { value: E18 });
    await expect(m.market.connect(m.alice).buy(5, 100, quote, { value: E18 })).to.be.revertedWith("Cost above slippage limit");
    const quote2 = await m.market.quoteBuy(5, 100);
    expect(quote2).to.be.gt(quote);
    await m.market.connect(m.alice).buy(5, 100, quote2, { value: quote2 });
  });
});

describe("12 rain market: vector buys (buyBasket)", function () {
  const STEPPED = [0n, 0n, 0n, 1n, 2n, 3n];

  it("buys a stepped hedge in one transaction and emits BasketTrade with the vector and the cost", async function () {
    const m = await deployRain();
    const v = STEPPED.map((x) => x * 100n);
    const quote = await m.market.quoteBasket(v);
    const call = m.market.connect(m.alice).buyBasket(v, quote, { value: quote });
    await expect(call).to.emit(m.market, "BasketTrade").withArgs(m.alice.address, v, quote);
    await expect(call).to.changeEtherBalances([m.alice, m.market], [-quote, quote]);
    expect([...(await m.market.sharesOfAll(m.alice.address))]).to.deep.equal(v);
    expect([...(await m.market.getQuantities())]).to.deep.equal(v);
    expect(await m.market.paid(m.alice.address)).to.equal(quote);
  });

  it("the charge is exactly C(q_new) - C(q_old) from costOf()", async function () {
    const m = await deployRain({ b: 137 });
    const r = rng(21);
    for (let k = 0; k < 12; k++) {
      const v = Array.from({ length: 6 }, () => BigInt(Math.floor(r() * 300)));
      v[Math.floor(r() * 6)] += 1n;
      const qOld = [...(await m.market.getQuantities())];
      const qNew = qOld.map((x, j) => x + v[j]);
      const want = (await m.market.costOf(qNew)) - (await m.market.costOf(qOld));
      expect(await m.market.quoteBasket(v)).to.equal(want);
      await expect(m.market.connect(m.alice).buyBasket(v, MAX, { value: E18 }))
        .to.changeEtherBalances([m.alice, m.market], [-want, want]);
    }
    const q = [...(await m.market.getQuantities())];
    expect(await m.market.totalPaid()).to.equal((await m.market.costOf(q)) - (await m.market.requiredFunding()));
  });

  it("a basket costs exactly the sum of sequential single buys, to the wei (stepped hedge, 3 sizes, 4 values of b)", async function () {
    for (const b of [50, 200, 1000, 5000]) {
      for (const size of [10n, 100n, 1000n]) {
        const v = STEPPED.map((x) => x * size);
        const one = await deployRain({ b });
        const legs = await deployRain({ b });
        const quote = await one.market.quoteBasket(v);
        await one.market.connect(one.alice).buyBasket(v, MAX, { value: quote });
        let total = 0n;
        for (let j = 0; j < 6; j++) {
          if (v[j] === 0n) continue;
          const c = await legs.market.quoteBuy(j, v[j]);
          await legs.market.connect(legs.alice).buy(j, v[j], MAX, { value: c });
          total += c;
        }
        expect(total, `b=${b} size=${size}`).to.equal(quote);
        expect(await legs.market.totalPaid()).to.equal(await one.market.totalPaid());
        expect(await legs.market.costNow()).to.equal(await one.market.costNow());
        expect([...(await legs.market.prices())]).to.deep.equal([...(await one.market.prices())]);
      }
    }
  });

  it("arbitrary vectors: 40 random baskets equal their legs bought one by one in a random order, to the wei", async function () {
    const r = rng(22);
    for (let s = 0; s < 40; s++) {
      const b = [7, 50, 200, 1000][s % 4];
      const unit = [10n ** 9n, 10n ** 12n, 10n ** 15n][s % 3];
      const one = await deployRain({ b, unit });
      const legs = await deployRain({ b, unit });
      // same random starting state in both markets
      const start = Array.from({ length: 6 }, () => BigInt(Math.floor(r() * 3 * b)));
      start[0] += 1n;
      for (const mk of [one, legs]) await mk.market.connect(mk.bob).buyBasket(start, MAX, { value: 10n ** 22n });
      // arbitrary vector: zeros, ones and large entries mixed
      const v = Array.from({ length: 6 }, () => (r() < 0.3 ? 0n : BigInt(1 + Math.floor(Math.pow(r(), 2) * 5 * b))));
      if (v.every((x) => x === 0n)) v[3] = 1n;
      const quote = await one.market.quoteBasket(v);
      await one.market.connect(one.alice).buyBasket(v, quote, { value: quote });
      const order = [0, 1, 2, 3, 4, 5].sort(() => r() - 0.5);
      let total = 0n;
      for (const j of order) {
        if (v[j] === 0n) continue;
        const c = await legs.market.quoteBuy(j, v[j]);
        await legs.market.connect(legs.alice).buy(j, v[j], c, { value: c });
        total += c;
      }
      expect(total, `sequence ${s}`).to.equal(quote);
      expect(await legs.market.paid(legs.alice.address)).to.equal(await one.market.paid(one.alice.address));
      expect([...(await legs.market.getQuantities())]).to.deep.equal([...(await one.market.getQuantities())]);
    }
  });

  it("one basket of 1,000 costs exactly the same as 10 baskets of 100", async function () {
    const a = await deployRain();
    const c = await deployRain();
    await a.market.connect(a.alice).buyBasket(STEPPED.map((x) => x * 1000n), MAX, { value: E18 });
    for (let k = 0; k < 10; k++) await c.market.connect(c.alice).buyBasket(STEPPED.map((x) => x * 100n), MAX, { value: E18 });
    expect(await c.market.totalPaid()).to.equal(await a.market.totalPaid());
  });

  it("rejects a zero vector and a vector of the wrong length", async function () {
    const m = await deployRain();
    await expect(m.market.connect(m.alice).buyBasket([0, 0, 0, 0, 0, 0], MAX, { value: 1 })).to.be.revertedWith("Zero quantity");
    await expect(m.market.connect(m.alice).buyBasket([1, 2, 3, 4, 5], MAX, { value: E18 })).to.be.revertedWith("Need six quantities");
    await expect(m.market.connect(m.alice).buyBasket([1, 2, 3, 4, 5, 6, 7], MAX, { value: E18 })).to.be.revertedWith("Need six quantities");
    await expect(m.market.connect(m.alice).buyBasket([], MAX, { value: E18 })).to.be.revertedWith("Need six quantities");
    await expect(m.market.quoteBasket([1, 2, 3])).to.be.revertedWith("Need six quantities");
    await expect(m.market.costOf([1, 2, 3])).to.be.revertedWith("Need six quantities");
  });

  it("is atomic: a basket that fails the slippage limit or the payment fills no leg", async function () {
    const m = await deployRain();
    const v = [0n, 0n, 0n, 100n, 200n, 300n];
    const quote = await m.market.quoteBasket(v);
    await expect(m.market.connect(m.alice).buyBasket(v, quote - 1n, { value: quote })).to.be.revertedWith("Cost above slippage limit");
    await expect(m.market.connect(m.alice).buyBasket(v, MAX, { value: quote - 1n })).to.be.revertedWith("Insufficient payment");
    expect((await m.market.getQuantities()).map(Number)).to.deep.equal([0, 0, 0, 0, 0, 0]);
    expect(await m.market.totalPaid()).to.equal(0n);
    expect((await m.market.sharesOfAll(m.alice.address)).map(Number)).to.deep.equal([0, 0, 0, 0, 0, 0]);
    await m.market.connect(m.alice).buyBasket(v, quote, { value: quote }); // passes at exactly maxCost
  });

  it("review m11: an absurd quantity gives 'Quantity too large', not an overflow panic", async function () {
    const m = await deployRain();
    const huge = [10n ** 15n + 1n, 10n ** 30n, MAX, MAX - 1n];
    for (const x of huge) {
      await expect(m.market.quoteBuy(3, x)).to.be.revertedWith("Quantity too large");
      await expect(m.market.connect(m.alice).buy(3, x, MAX, { value: 1 })).to.be.revertedWith("Quantity too large");
      await expect(m.market.quoteBasket([1, 1, x, 1, 1, 1])).to.be.revertedWith("Quantity too large");
      await expect(m.market.connect(m.alice).buyBasket([x, x, x, x, x, x], MAX, { value: 1 })).to.be.revertedWith("Quantity too large");
    }
    // the per-bucket cap also holds across trades
    await ensureBalance(m.alice, 10n ** 28n);
    await m.market.connect(m.alice).buy(3, 10n ** 15n, MAX, { value: 10n ** 27n + E18 });
    await expect(m.market.connect(m.alice).buy(3, 1, MAX, { value: E18 })).to.be.revertedWith("Quantity too large");
  });

  it("review m2: shares are never free. A buy whose cost rounds to 0 wei is refused", async function () {
    const m = await deployRain({ b: 10, unit: 10n ** 9n });
    await m.market.connect(m.alice).buy(5, 1000, MAX, { value: E18 }); // bucket 5 is now 100 b ahead
    expect((await m.market.prices())[0]).to.equal(0n);
    expect(await m.market.quoteBuy(0, 500)).to.equal(0n); // the review's free 500 shares
    await expect(m.market.connect(m.bob).buy(0, 500, MAX, { value: 0 })).to.be.revertedWith("Cost rounds to zero");
    await expect(m.market.connect(m.bob).buyBasket([500, 500, 0, 0, 0, 0], MAX, { value: 0 })).to.be.revertedWith("Cost rounds to zero");
    expect(await m.market.sharesOf(m.bob.address, 0)).to.equal(0n);
    // a buy large enough to have a real cost still works
    const quote = await m.market.quoteBuy(0, 990);
    expect(quote).to.be.gt(0n);
    await m.market.connect(m.bob).buy(0, 990, quote, { value: quote });
  });
});

describe("12 rain market: collateral", function () {
  it("the balance covers the largest possible payout after every trade (5 values of b, baskets and single buys)", async function () {
    const r = rng(23);
    let refused = 0;
    for (const b of [1, 5, 50, 200, 5000]) {
      const m = await deployRain({ b });
      await ensureBalance(m.alice, 10n ** 24n);
      for (let k = 0; k < 25; k++) {
        if (r() < 0.5) {
          const v = Array.from({ length: 6 }, () => BigInt(Math.floor(Math.pow(r(), 3) * 30 * b)));
          v[Math.floor(r() * 6)] += 1n;
          await m.market.connect(m.alice).buyBasket(v, MAX, { value: 10n ** 20n });
        } else {
          const j = Math.floor(r() * 6), shares = 1 + Math.floor(Math.pow(r(), 3) * 30 * b);
          if ((await m.market.quoteBuy(j, shares)) === 0n) {
            // a bucket priced below 2^-64: the buy is refused (review m2), nothing changes
            await expect(m.market.connect(m.alice).buy(j, shares, MAX, { value: 1 })).to.be.revertedWith("Cost rounds to zero");
            refused++;
          } else await m.market.connect(m.alice).buy(j, shares, MAX, { value: 10n ** 20n });
        }
        const q = await m.market.getQuantities();
        const top = q.reduce((a, x) => (x > a ? x : a), 0n);
        expect(await balanceOf(m.market)).to.be.gte(top * m.unit);
        expect(await balanceOf(m.market)).to.equal(m.value + (await m.market.totalPaid()));
        expect(await m.market.costNow()).to.be.gte(top * m.unit);
      }
    }
    console.log(`      ${refused} zero-cost buys refused`);
  });
});
