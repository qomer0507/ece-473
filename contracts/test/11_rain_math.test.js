// RainCountLMSR: accuracy of the cost function, prices and funding amount
// against 60-digit decimal references written by `python -m sim.make_vectors`.
const { expect } = require("chai");
const { ethers, deployRain, rainVectors, artifact, ensureBalance, safeFunding } = require("./rain_helpers");

const abs = (x) => (x < 0n ? -x : x);
const MAX = ethers.MaxUint256;
const E18 = 10n ** 18n;
// One cost evaluation is within b*unit*2^-60 + 1 wei of the exact value.
const tol1 = (b, unit) => (BigInt(b) * BigInt(unit)) / 2n ** 60n + 1n;

describe("11 rain maths: six-bucket cost function against a 60-digit reference", function () {
  let V;
  const markets = {};
  const stats = {};
  async function marketFor(b, unit) {
    const key = b + ":" + unit;
    if (!markets[key]) markets[key] = await deployRain({ b, unit });
    return markets[key];
  }
  before(function () {
    V = rainVectors();
  });
  after(function () {
    console.log("      max errors:", JSON.stringify(stats));
  });

  it("funding: requiredFundingFor(b, unit) = floor(b ln(6) unit) within the fixed-point tolerance (10 cases)", async function () {
    for (const f of V.funding) {
      const m = await marketFor(f.b, f.unit);
      const got = await m.market.requiredFundingFor(f.b, f.unit);
      expect(abs(got - BigInt(f.required)), `b=${f.b} unit=${f.unit}`).to.be.lte(tol1(f.b, f.unit));
      // the stored requirement, C(0) and the view are the same number
      expect(await m.market.requiredFunding()).to.equal(got);
      expect(await m.market.costNow()).to.equal(got);
      expect(await m.market.costOf([0, 0, 0, 0, 0, 0])).to.equal(got);
      // the "safe" amounts from Python and from the JS helper are enough
      expect(BigInt(f.safe)).to.be.gte(got);
      expect(safeFunding(f.b, f.unit)).to.be.gte(got);
    }
    // review example: b = 100, unit = 1e14 wei
    const m = await marketFor("100", "100000000000000");
    expect(await m.market.requiredFunding()).to.equal(17917594692280550n);
  });

  it("requiredFundingFor rejects b and unit outside the allowed range", async function () {
    const m = await marketFor("200", "1000000000000");
    await expect(m.market.requiredFundingFor(0, 10n ** 12n)).to.be.revertedWith("b out of range");
    await expect(m.market.requiredFundingFor(10n ** 12n + 1n, 10n ** 12n)).to.be.revertedWith("b out of range");
    await expect(m.market.requiredFundingFor(200, 10n ** 9n - 1n)).to.be.revertedWith("unit out of range");
    await expect(m.market.requiredFundingFor(200, E18 + 1n)).to.be.revertedWith("unit out of range");
  });

  it("C(q) in wei matches the reference within b*unit*2^-60 + 1 wei (40 cases, b from 1 to 1e12)", async function () {
    let worst = 0;
    for (const c of V.cost) {
      const m = await marketFor(c.b, c.unit);
      const got = await m.market.costOf(c.q.map(BigInt));
      const err = abs(got - BigInt(c.cost));
      expect(err, `b=${c.b} unit=${c.unit} ${c.kind}`).to.be.lte(tol1(c.b, c.unit));
      worst = Math.max(worst, Number(err) / (Number(c.b) * Number(c.unit)));
    }
    stats.cost_err_over_b_unit = worst.toExponential(2);
  });

  it("prices match the reference within 2e-18 and sum to 1 within 7e-18, in markets traded to each reference state", async function () {
    let worst = 0n, worstSum = 0n;
    for (const c of V.cost) {
      const q = c.q.map(BigInt);
      const m = await deployRain({ b: c.b, unit: c.unit });
      if (q.some((x) => x > 0n)) {
        const cost = await m.market.quoteBasket(q);
        await ensureBalance(m.alice, cost);
        await m.market.connect(m.alice).buyBasket(q, MAX, { value: cost });
      }
      expect((await m.market.getQuantities()).map(String)).to.deep.equal(c.q);
      const p = await m.market.prices();
      let sum = 0n;
      for (let j = 0; j < 6; j++) {
        sum += p[j];
        const err = abs(p[j] - BigInt(c.prices[j]));
        if (err > worst) worst = err;
        expect(await m.market.price(j)).to.equal(p[j]);
      }
      if (abs(E18 - sum) > worstSum) worstSum = abs(E18 - sum);
    }
    stats.price_err_1e18 = worst.toString();
    stats.price_sum_gap_1e18 = worstSum.toString();
    expect(worst).to.be.lte(2n);
    expect(worstSum).to.be.lte(7n);
  });

  it("vector quotes match the reference C(q + a) - C(q) within two cost tolerances (30 random cases)", async function () {
    let worst = 0n;
    for (const c of V.basket) {
      const m = await deployRain({ b: c.b, unit: c.unit });
      const q = c.q.map(BigInt);
      const first = await m.market.quoteBasket(q);
      await ensureBalance(m.alice, first);
      await m.market.connect(m.alice).buyBasket(q, MAX, { value: first });
      const got = await m.market.quoteBasket(c.amounts.map(BigInt));
      const err = abs(got - BigInt(c.cost));
      if (err > worst) worst = err;
      expect(err, `b=${c.b} unit=${c.unit}`).to.be.lte(2n * tol1(c.b, c.unit));
    }
    stats.basket_quote_err_wei = worst.toString();
  });

  it("deployed bytecode of RainCountLMSR and SeasonCountOracle is under the 24,576-byte limit", function () {
    for (const name of ["RainCountLMSR", "SeasonCountOracle"]) {
      const size = (artifact(name).deployedBytecode.length - 2) / 2;
      expect(size, name).to.be.gt(1000).and.lt(24576);
    }
  });
});
