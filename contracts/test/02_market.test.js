// Trading: prices, monotonicity, path independence, basket, slippage, collateral, events.
const { expect } = require("chai");
const { ethers, deployMarket, tx, costF, pricesF, rng, setTime, BOUNDS } = require("./helpers");

const MAX = ethers.MaxUint256;
const E18 = 10n ** 18n;
const sum = (a) => a.reduce((x, y) => x + y, 0n);

describe("02 market: construction and views", function () {
  it("stores the ladder: 12 exhaustive brackets with a boundary at 90", async function () {
    const { market } = await deployMarket({ gasLabel: "deploy BracketLMSR (n=12)" });
    expect(await market.numBrackets()).to.equal(12n);
    expect((await market.getBounds()).map(Number)).to.deep.equal(BOUNDS);
    expect(await market.strikeIndex()).to.equal(6n);
    expect(await market.strike()).to.equal(90n);
  });

  it("maps every whole temperature from -80 to 140 to exactly one bracket, in order", async function () {
    const { market } = await deployMarket();
    const expectAt = { "-80": 0, 79: 0, 80: 1, 81: 1, 82: 2, 89: 5, 90: 6, 91: 6, 92: 7, 99: 10, 100: 11, 140: 11 };
    for (const [t, j] of Object.entries(expectAt)) expect(await market.bracketOf(Number(t))).to.equal(BigInt(j));
    let prev = 0n;
    for (let t = -80; t <= 140; t++) {
      const j = await market.bracketOf(t);
      expect(j >= prev && j <= 11n).to.equal(true);
      prev = j;
    }
  });

  it("starts at uniform prices 1/12 and P(T>=90) = 6/12", async function () {
    const { market } = await deployMarket();
    const p = await market.prices();
    for (const x of p) expect(x).to.be.closeTo(E18 / 12n, 2n);
    expect(await market.priceAtOrAboveStrike()).to.be.closeTo(E18 / 2n, 12n);
    expect(await market.price(3)).to.equal(p[3]);
  });

  it("requires sponsor funding of at least b*ln(n)*unit, and stores it", async function () {
    const b = 200n, unit = 10n ** 12n;
    const { market } = await deployMarket({ b, unit });
    const need = await market.requiredFunding();
    const ref = 200 * Math.log(12) * 1e12;
    expect(Number(need)).to.be.closeTo(ref, 1e3);
    // exactly the requirement is accepted, one wei less is rejected
    await deployMarket({ b, unit, value: need });
    await expect(deployMarket({ b, unit, value: need - 1n })).to.be.revertedWith("Funding below worst-case loss");
    await expect(deployMarket({ b, unit, value: 0n })).to.be.revertedWith("Funding below worst-case loss");
  });

  it("rejects bad constructor arguments", async function () {
    const bad = async (o, msg) => expect(deployMarket(o)).to.be.revertedWith(msg);
    await bad({ b: 0 }, "b out of range");
    await bad({ b: 10n ** 12n + 1n, value: 1n }, "b out of range");
    await bad({ unit: 0, value: 1n }, "unit out of range");
    await bad({ unit: 10n ** 18n + 1n, value: 1n }, "unit out of range");
    await bad({ bounds: [80, 80, 90] }, "Bounds not increasing");
    await bad({ bounds: [80, 90, 85] }, "Bounds not increasing");
    await bad({ bounds: [80, 85, 95] }, "Strike is not a boundary");
    await bad({ bounds: [], value: 1n }, "Bad number of brackets");
    await bad({ bounds: Array.from({ length: 32 }, (_, i) => 70 + i), value: 1n }, "Bad number of brackets");
    await bad({ initialQ: [0, 1, 2] }, "initialQ length");
    await bad({ initialQ: new Array(12).fill(5) }, "initialQ minimum must be 0");
    await bad({ initialQ: [0, ...new Array(11).fill(10n ** 15n + 1n)], value: 1n }, "initialQ too large");
    await bad({ tradingClose: 1 }, "Trading close in the past");
    const t = (await ethers.provider.getBlock("latest")).timestamp;
    await bad({ tradingClose: t + 500, observationEnd: t + 400 }, "Observation ends before trading");
    await bad({ tradingClose: t + 500, observationEnd: t + 600, reportDeadline: t + 600 }, "Deadline before observation end");
    const f = await require("./helpers").factory("BracketLMSR");
    await expect(f.deploy(ethers.ZeroAddress, "X", 1, BOUNDS, 90, 1, 1, [], t + 500, t + 600, t + 700, { value: 10 }))
      .to.be.revertedWith("Zero oracle");
  });

  it("accepts 2 brackets (binary market, as in Lab 7) and 32 brackets", async function () {
    const two = await deployMarket({ bounds: [90] });
    expect(await two.market.numBrackets()).to.equal(2n);
    expect(await two.market.strikeIndex()).to.equal(1n);
    expect(Number(await two.market.requiredFunding())).to.be.closeTo(200 * Math.log(2) * 1e12, 1e3);
    const many = await deployMarket({ bounds: Array.from({ length: 31 }, (_, i) => 75 + i) });
    expect(await many.market.numBrackets()).to.equal(32n);
    const p = await many.market.prices();
    expect(sum([...p])).to.be.closeTo(E18, 33n);
  });
});

describe("02 market: buying one bracket", function () {
  it("charges the quote, credits shares, emits Trade, and matches the float reference", async function () {
    const { market, signers, unit } = await deployMarket({ b: 200 });
    const alice = signers[1];
    const quote = await market.quoteBuy(6, 100);
    const q0 = new Array(12).fill(0), q1 = q0.slice();
    q1[6] = 100;
    const ref = (costF(q1, 200) - costF(q0, 200)) * 1e12;
    expect(Number(quote)).to.be.closeTo(ref, 1e3);
    const before = await ethers.provider.getBalance(await market.getAddress());
    const call = market.connect(alice).buy(6, 100, quote, { value: quote });
    await expect(call).to.emit(market, "Trade").withArgs(alice.address, 6n, 100n, quote);
    await tx("buy (single bracket)", call);
    expect(await market.sharesOf(alice.address, 6)).to.equal(100n);
    expect(await market.paid(alice.address)).to.equal(quote);
    expect(await market.totalPaid()).to.equal(quote);
    expect(await ethers.provider.getBalance(await market.getAddress())).to.equal(before + quote);
    expect((await market.getSold())[6]).to.equal(100n);
    void unit;
  });

  it("monotonicity: a buy raises that bracket's price and lowers every other price", async function () {
    const { market, signers } = await deployMarket({ b: 200 });
    const r = rng(1);
    for (let k = 0; k < 25; k++) {
      const j = Math.floor(r() * 12);
      const shares = 1 + Math.floor(r() * 300);
      const before = await market.prices();
      await tx("buy (single bracket)", market.connect(signers[1]).buy(j, shares, MAX, { value: E18 }));
      const after = await market.prices();
      expect(after[j], `trade ${k}`).to.be.gt(before[j]);
      for (let i = 0; i < 12; i++) if (i !== j) expect(after[i]).to.be.lte(before[i]);
    }
  });

  it("the cost of a buy is between shares*price_before and shares*price_after", async function () {
    const { market, signers, unit } = await deployMarket({ b: 500 });
    for (const j of [0, 6, 11]) {
      const pb = (await market.prices())[j];
      const cost = await market.quoteBuy(j, 250);
      await market.connect(signers[1]).buy(j, 250, MAX, { value: cost });
      const pa = (await market.prices())[j];
      expect(cost).to.be.gte((250n * unit * pb) / E18);
      expect(cost).to.be.lte((250n * unit * pa) / E18 + 1n);
    }
  });

  it("prices sum to 1 within 13e-18 after every one of 40 random trades", async function () {
    const { market, signers } = await deployMarket({ b: 50 });
    const r = rng(2);
    for (let k = 0; k < 40; k++) {
      const j = Math.floor(r() * 12);
      await market.connect(signers[2]).buy(j, 1 + Math.floor(r() * 400), MAX, { value: E18 });
      const p = await market.prices();
      const s = sum([...p]);
      expect(s).to.be.lte(E18);
      expect(E18 - s).to.be.lte(13n);
    }
    // and they agree with the float reference
    const q = (await market.getQuantities()).map(Number);
    const ref = pricesF(q, 50);
    const p = await market.prices();
    for (let j = 0; j < 12; j++) expect(Number(p[j]) / 1e18).to.be.closeTo(ref[j], 1e-12);
  });

  it("rejects zero shares, a bad bracket, and trades after the trading close", async function () {
    const { market, signers, tradingClose } = await deployMarket();
    await expect(market.buy(0, 0, MAX, { value: 1 })).to.be.revertedWith("Zero shares");
    await expect(market.buy(12, 1, MAX, { value: E18 })).to.be.revertedWith("Bad bracket");
    await expect(market.quoteBuy(12, 1)).to.be.revertedWith("Bad bracket");
    await expect(market.price(12)).to.be.revertedWith("Bad bracket");
    await setTime(tradingClose);
    await expect(market.connect(signers[1]).buy(0, 1, MAX, { value: E18 })).to.be.revertedWith("Trading closed");
    await expect(market.connect(signers[1]).buyBasket(1, MAX, { value: E18 })).to.be.revertedWith("Trading closed");
  });
});

describe("02 market: cost path independence", function () {
  it("the same final position costs exactly the same in any order (3 orders, exact wei)", async function () {
    const trades = [[6, 120], [0, 40], [11, 300], [6, 80], [3, 15], [9, 500], [0, 1]];
    const orders = [trades, trades.slice().reverse(), [trades[2], trades[5], trades[0], trades[6], trades[1], trades[4], trades[3]]];
    const totals = [], costs = [];
    for (const order of orders) {
      const { market, signers } = await deployMarket({ b: 200 });
      for (const [j, s] of order) await market.connect(signers[1]).buy(j, s, MAX, { value: E18 });
      totals.push(await market.totalPaid());
      costs.push(await market.costNow());
    }
    expect(totals[1]).to.equal(totals[0]);
    expect(totals[2]).to.equal(totals[0]);
    expect(costs[1]).to.equal(costs[0]);
    expect(costs[2]).to.equal(costs[0]);
  });

  it("one buy of 1,000 costs exactly the same as 10 buys of 100", async function () {
    const a = await deployMarket({ b: 1000 });
    const b = await deployMarket({ b: 1000 });
    await a.market.connect(a.signers[1]).buy(7, 1000, MAX, { value: E18 });
    for (let k = 0; k < 10; k++) await b.market.connect(b.signers[1]).buy(7, 100, MAX, { value: E18 });
    expect(await b.market.totalPaid()).to.equal(await a.market.totalPaid());
  });

  it("total paid always equals C(q) - C(q0) from costOf()", async function () {
    const { market, signers } = await deployMarket({ b: 77 });
    const r = rng(3);
    const c0 = await market.costOf(new Array(12).fill(0));
    for (let k = 0; k < 20; k++) {
      await market.connect(signers[1 + (k % 3)]).buy(Math.floor(r() * 12), 1 + Math.floor(r() * 200), MAX, { value: E18 });
      const q = await market.getQuantities();
      expect(await market.totalPaid()).to.equal((await market.costOf([...q])) - c0);
    }
  });
});

describe("02 market: atomic basket for T >= 90", function () {
  it("buys every bracket at or above 90 in one transaction and emits BasketTrade", async function () {
    const { market, signers } = await deployMarket({ b: 200 });
    const alice = signers[1];
    const quote = await market.quoteBasket(100);
    const call = market.connect(alice).buyBasket(100, quote, { value: quote });
    await expect(call).to.emit(market, "BasketTrade").withArgs(alice.address, 6n, 11n, 100n, quote);
    await tx("buyBasket (6 brackets >= 90)", call);
    for (let j = 0; j < 12; j++) expect(await market.sharesOf(alice.address, j)).to.equal(j >= 6 ? 100n : 0n);
    // float reference
    const q1 = new Array(12).fill(0).map((_, j) => (j >= 6 ? 100 : 0));
    const ref = (costF(q1, 200) - costF(new Array(12).fill(0), 200)) * 1e12;
    expect(Number(quote)).to.be.closeTo(ref, 1e3);
  });

  it("basket cost equals the sum of six sequential single buys, to the wei", async function () {
    for (const [b, size] of [[50, 10], [50, 1000], [200, 100], [1000, 1000], [5000, 10]]) {
      const a = await deployMarket({ b });
      const c = await deployMarket({ b });
      // same starting state in both markets
      for (const m of [a, c]) {
        await m.market.connect(m.signers[2]).buy(2, 37, MAX, { value: E18 });
        await m.market.connect(m.signers[2]).buy(8, 11, MAX, { value: E18 });
      }
      const before = await a.market.totalPaid();
      await a.market.connect(a.signers[1]).buyBasket(size, MAX, { value: E18 });
      for (let j = 6; j < 12; j++) await c.market.connect(c.signers[1]).buy(j, size, MAX, { value: E18 });
      expect(await c.market.totalPaid(), `b=${b} size=${size}`).to.equal(await a.market.totalPaid());
      expect(await a.market.paid(a.signers[1].address)).to.equal((await a.market.totalPaid()) - before);
      expect(await c.market.costNow()).to.equal(await a.market.costNow());
    }
  });

  it("basket average price lies between P(T>=90) before and after the trade", async function () {
    const { market, signers, unit } = await deployMarket({ b: 200 });
    const pb = await market.priceAtOrAboveStrike();
    const cost = await market.quoteBasket(100);
    await market.connect(signers[1]).buyBasket(100, cost, { value: cost });
    const pa = await market.priceAtOrAboveStrike();
    const avg = (cost * E18) / (100n * unit);
    expect(avg).to.be.gt(pb);
    expect(avg).to.be.lt(pa);
  });

  it("is atomic: if the basket reverts, no leg is filled", async function () {
    const { market, signers } = await deployMarket({ b: 200 });
    const quote = await market.quoteBasket(100);
    await expect(market.connect(signers[1]).buyBasket(100, quote - 1n, { value: quote })).to.be.revertedWith("Cost above slippage limit");
    expect((await market.getSold()).every((x) => x === 0n)).to.equal(true);
    expect(await market.totalPaid()).to.equal(0n);
  });
});

describe("02 market: slippage limit and payment", function () {
  it("reverts above maxCost, passes at maxCost, for single buys and baskets", async function () {
    const { market, signers } = await deployMarket({ b: 200 });
    const q1 = await market.quoteBuy(6, 50);
    await expect(market.connect(signers[1]).buy(6, 50, q1 - 1n, { value: q1 })).to.be.revertedWith("Cost above slippage limit");
    await market.connect(signers[1]).buy(6, 50, q1, { value: q1 });
    const q2 = await market.quoteBasket(50);
    await expect(market.connect(signers[1]).buyBasket(50, q2 - 1n, { value: q2 })).to.be.revertedWith("Cost above slippage limit");
    await market.connect(signers[1]).buyBasket(50, q2, { value: q2 });
  });

  it("protects against a trade that lands first (price moved since the quote)", async function () {
    const { market, signers } = await deployMarket({ b: 200 });
    const quote = await market.quoteBasket(100);
    await market.connect(signers[2]).buyBasket(500, MAX, { value: E18 }); // someone else moves the price
    await expect(market.connect(signers[1]).buyBasket(100, quote, { value: E18 })).to.be.revertedWith("Cost above slippage limit");
    const slack = quote * 2n; // a wider limit goes through
    const requote = await market.quoteBasket(100);
    expect(requote).to.be.gt(quote);
    expect(requote).to.be.lte(slack);
    await market.connect(signers[1]).buyBasket(100, slack, { value: E18 });
  });

  it("reverts when msg.value is below the cost and returns any excess", async function () {
    const { market, signers } = await deployMarket({ b: 200 });
    const alice = signers[1];
    const quote = await market.quoteBuy(4, 80);
    await expect(market.connect(alice).buy(4, 80, MAX, { value: quote - 1n })).to.be.revertedWith("Insufficient payment");
    const call = market.connect(alice).buy(4, 80, MAX, { value: quote + 12345n });
    await expect(call).to.changeEtherBalances([alice, market], [-quote, quote]);
  });
});

describe("02 market: collateral sufficiency", function () {
  it("contract balance covers the largest possible payout after every trade (uniform and seeded, 5 values of b)", async function () {
    const r = rng(4);
    for (const b of [1, 50, 200, 1000, 5000]) {
      for (const seeded of [false, true]) {
        const initialQ = seeded ? [0, ...Array.from({ length: 11 }, () => Math.floor(r() * 3 * b))] : [];
        const { market, signers, unit } = await deployMarket({ b, initialQ });
        const need = await market.requiredFunding();
        // fund with the bare minimum to make the test as tight as possible
        const tight = await deployMarket({ b, initialQ, value: need });
        for (const m of [market, tight.market]) {
          for (let k = 0; k < 15; k++) {
            const basket = r() < 0.3;
            const shares = 1 + Math.floor(r() * 6 * b);
            if (basket) await m.connect(signers[1 + (k % 4)]).buyBasket(shares, MAX, { value: 10n * E18 });
            else await m.connect(signers[1 + (k % 4)]).buy(Math.floor(r() * 12), shares, MAX, { value: 10n * E18 });
            const bal = await ethers.provider.getBalance(await m.getAddress());
            const sold = await m.getSold();
            const top = sold.reduce((a, x) => (x > a ? x : a), 0n);
            expect(bal, `b=${b} seeded=${seeded} trade ${k}`).to.be.gte(top * unit);
            expect(bal).to.be.gte(await m.maxLiability());
            expect(bal).to.be.gte(await m.totalPaid());
          }
        }
      }
    }
  });
});

describe("02 market: non-uniform prior (seed quantities)", function () {
  it("starts at the seeded prices, and seed shares pay nobody", async function () {
    const V = require("./helpers").vectors();
    const prior = V.climatology_prior;
    const seed = V.climatology_seeds["200"].map(BigInt);
    const { market, signers, unit, oracle, day, observationEnd } = await deployMarket({ b: 200, initialQ: seed, gasLabel: "deploy BracketLMSR (n=12, seeded prior)" });
    const p = await market.prices();
    // integer seed shares: prices are within 1/b of the prior
    for (let j = 0; j < 12; j++) expect(Number(p[j]) / 1e18).to.be.closeTo(prior[j], prior[j] * 0.006);
    expect((await market.getSold()).every((x) => x === 0n)).to.equal(true);
    // required funding = C(q0) = b ln(1/p_min) up to the integer rounding of the seed
    const pmin = Math.min(...prior);
    expect(Number(await market.requiredFunding()) / 1e12).to.be.closeTo(200 * Math.log(1 / pmin), 1.0);
    // settle with no trades: nothing is owed, the sponsor gets everything back
    await setTime(observationEnd);
    await oracle.setReport("USW00014734", day, 95);
    await market.settle();
    expect(await market.reserved()).to.equal(0n);
    const bal = await ethers.provider.getBalance(await market.getAddress());
    await expect(market.sponsorWithdraw()).to.changeEtherBalance(signers[0], bal);
    void unit;
  });
});
