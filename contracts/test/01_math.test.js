// Fixed-point accuracy of the ABDK 64.64 functions and of the cost function,
// against 60-digit decimal references written by `python -m sim.make_vectors`.
const { expect } = require("chai");
const { deploy, deployMarket, vectors, artifact } = require("./helpers");

const abs = (x) => (x < 0n ? -x : x);
const TWO64 = 2n ** 64n;

describe("01 fixed-point maths (ABDK 64.64) against a 60-digit reference", function () {
  let h, V;
  const stats = {};
  before(async function () {
    h = await deploy("MathHarness");
    V = vectors();
  });
  after(function () {
    console.log("      max errors:", JSON.stringify(stats));
  });

  it("exp(x) on [-44, 0]: absolute error below 2^-60", async function () {
    let worst = 0n;
    for (const c of V.exp) {
      const got = await h.exp(BigInt(c.x));
      const err = abs(got - BigInt(c.y));
      if (err > worst) worst = err;
    }
    stats.exp_ulp = worst.toString();
    expect(worst).to.be.lte(16n); // 16 * 2^-64 = 2^-60
  });

  it("exp(0) is exactly 1 and exp(x) is 0 below the cutoff", async function () {
    expect(await h.exp(0n)).to.equal(TWO64);
    expect(await h.exp(-45n * TWO64)).to.equal(0n);
    expect(await h.weight(45n, 1n)).to.equal(0n);
    expect(await h.weight(44n, 1n)).to.be.gt(0n);
  });

  it("ln(x) on [1, 32]: absolute error below 2^-60", async function () {
    let worst = 0n;
    for (const c of V.ln) {
      const got = await h.ln(BigInt(c.x));
      const err = abs(got - BigInt(c.y));
      if (err > worst) worst = err;
    }
    stats.ln_ulp = worst.toString();
    expect(await h.ln(TWO64)).to.equal(0n);
    expect(worst).to.be.lte(16n);
  });

  it("weight exp(-d/b): absolute error below 2^-60", async function () {
    let worst = 0n;
    for (const c of V.weight) {
      const got = await h.weight(BigInt(c.d), BigInt(c.b));
      const err = abs(got - BigInt(c.y));
      if (err > worst) worst = err;
    }
    stats.weight_ulp = worst.toString();
    expect(worst).to.be.lte(16n);
  });

  it("C(q) in wei matches the reference within b*unit*2^-60 + 1 wei (36 cases, b from 1 to 1e12)", async function () {
    const markets = {};
    let worstRel = 0;
    for (const c of V.cost) {
      const key = c.b + ":" + c.unit;
      if (!markets[key]) markets[key] = (await deployMarket({ b: c.b, unit: c.unit })).market;
      const got = await markets[key].costOf(c.q.map(BigInt));
      const ref = BigInt(c.cost);
      const err = abs(got - ref);
      const tol = (BigInt(c.b) * BigInt(c.unit)) / 2n ** 60n + 1n;
      expect(err, `b=${c.b} unit=${c.unit} ${c.kind}`).to.be.lte(tol);
      const scaled = Number(err) / (Number(c.b) * Number(c.unit));
      if (scaled > worstRel) worstRel = scaled;
    }
    stats.cost_err_over_b_unit = worstRel.toExponential(2);
  });

  it("prices match the reference within 2e-18 and sum to 1 within 13e-18 (n = 12)", async function () {
    let worst = 0n, worstSum = 0n;
    for (const c of V.cost) {
      // A market seeded with q - min(q) has the same prices as q.
      const q = c.q.map(BigInt);
      const lo = q.reduce((a, x) => (x < a ? x : a));
      const { market } = await deployMarket({ b: c.b, unit: c.unit, initialQ: q.map((x) => x - lo) });
      const p = await market.prices();
      let sum = 0n;
      for (let j = 0; j < p.length; j++) {
        sum += p[j];
        const err = abs(p[j] - BigInt(c.prices[j]));
        if (err > worst) worst = err;
      }
      const gap = abs(10n ** 18n - sum);
      if (gap > worstSum) worstSum = gap;
    }
    stats.price_err_1e18 = worst.toString();
    stats.price_sum_gap_1e18 = worstSum.toString();
    expect(worst).to.be.lte(2n);
    expect(worstSum).to.be.lte(13n);
  });

  it("deployed bytecode is under the 24,576-byte limit", function () {
    const size = (artifact("BracketLMSR").deployedBytecode.length - 2) / 2;
    expect(size).to.be.lt(24576);
  });
});
