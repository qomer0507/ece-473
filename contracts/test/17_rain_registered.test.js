// The REGISTERED product (docs/PHASE2_PREREG.md, strategy 3) end to end in the local Hardhat EVM.
// Edges [2,4,5,6,8] = the 1/6..5/6 quantiles of the Trenton TRAIN counts 1999-2014
// (results/market/registered_buckets.csv). Holding per unit of hedge size: h_j = max(m_j - d, 0),
// m = [1.75, 3.667, 5, 6, 8, 12]. The deductible d is not chosen yet, so d = 2, 3 and 4 are all run.
// Shares are whole numbers on the contract: 3 x h_j and 12 x h_j are whole for every d.
// Settlement counts are REAL past seasons from data/processed/rain/season_counts_TTN.csv.
// Local EVM only. Nothing here ran on Sepolia.
const fs = require("fs");
const path = require("path");
const { expect } = require("chai");
const { ethers, deploy, setNextTime, balanceOf, bucketOf, safeFunding, snapshot, revertTo } = require("./rain_helpers");

const EDGES = [2, 4, 5, 6, 8];
const LABELS = ["0-2", "3-4", "5", "6", "7-8", "9+"];
const M12 = [21, 44, 60, 72, 96, 144]; // 12 x m_j
/** Whole shares of a hedge: scale x h_j, where scale x 12 must be divisible so the result is whole. */
function holding(d, per12) {
  return M12.map((m) => {
    const x = Math.max(m - 12 * d, 0) * per12;
    if (x % 12 !== 0) throw new Error("not a whole number of shares");
    return x / 12;
  });
}
const COUNTS_FILE = path.join(__dirname, "..", "..", "data", "processed", "rain", "season_counts_TTN.csv");

/** Usable all_days seasons from the rain workstream's file: { season: lossDays }. */
function realCounts() {
  const lines = fs.readFileSync(COUNTS_FILE, "utf8").trim().split("\n");
  const head = lines[0].split(",");
  const col = (name) => head.indexOf(name);
  const out = {};
  for (const line of lines.slice(1)) {
    const c = line.split(",");
    if (c[col("calendar")] !== "all_days" || c[col("season_usable")] !== "True") continue;
    out[Number(c[col("season")])] = Number(c[col("loss_days")]);
  }
  return out;
}

/** Float reference of the LMSR cost of the first trade in a fresh market, in wei. */
function refCost(v, b, unit) {
  const top = Math.max(...v) / b;
  return (top + Math.log(v.reduce((a, x) => a + Math.exp(x / b - top), 0) / 6)) * b * unit;
}

async function setUp({ b, unit, season, exactFunding = true }) {
  const [sponsor, reporter, buyer, anyone] = await ethers.getSigners();
  const oracle = await deploy("SeasonCountOracle", [], {}, reporter);
  const T = Number(await oracle.currentTime());
  await oracle.connect(reporter).openSeason("TTN", season, T + 900, T + 1500, 102);
  const args = [await oracle.getAddress(), "TTN", season, EDGES, b, unit, T + 900, T + 3300, 0, 604800];
  // The sponsor funds exactly b ln(6) unit: one wei less is refused.
  const probe = await deploy("RainCountLMSR", args, { value: safeFunding(b, unit) }, sponsor);
  const need = await probe.requiredFundingFor(b, unit);
  const value = exactFunding ? need : safeFunding(b, unit);
  const market = await deploy("RainCountLMSR", args, { value }, sponsor);
  return { sponsor, reporter, buyer, anyone, oracle, market, T, need, value, args };
}

describe("17 registered product: edges [2,4,5,6,8], stepped holding max(m_j - d, 0), real season counts (local EVM)", function () {
  let counts;
  before(function () {
    if (!fs.existsSync(COUNTS_FILE)) this.skip();
    counts = realCounts();
  });

  it("the data file still gives the counts the registration used, and 2025 had 5 loss days", function () {
    const train = [];
    for (let y = 1999; y <= 2014; y++) train.push(counts[y]);
    expect(train).to.deep.equal([2, 6, 6, 4, 8, 5, 5, 8, 2, 4, 12, 2, 1, 6, 12, 3]);
    const sorted = [...train].sort((a, b) => a - b);
    // k/6 quantile = smallest count with at least k/6 of the 16 seasons at or below it
    const edges = [1, 2, 3, 4, 5].map((k) => sorted[Math.ceil((k * 16) / 6) - 1]);
    expect(edges).to.deep.equal(EDGES);
    expect(counts[2025]).to.equal(5);
    expect(holding(2, 12)).to.deep.equal([0, 20, 36, 48, 72, 120]);
    expect(holding(3, 3)).to.deep.equal([0, 2, 6, 9, 15, 27]);
  });

  it("the contract puts every count from 0 to 102 in the registered bucket", async function () {
    const { market } = await setUp({ b: 100, unit: 10n ** 14n, season: 2025 });
    expect((await market.getEdges()).map(Number)).to.deep.equal(EDGES);
    const want = (c) => (c <= 2 ? 0 : c <= 4 ? 1 : c === 5 ? 2 : c === 6 ? 3 : c <= 8 ? 4 : 5);
    for (let c = 0; c <= 102; c++) {
      expect(Number(await market.bucketOf(c)), "count " + c).to.equal(want(c));
      expect(bucketOf(c, EDGES)).to.equal(want(c));
    }
    for (const y of Object.keys(counts)) expect(LABELS[Number(await market.bucketOf(counts[y]))]).to.be.a("string");
  });

  // The guide's numbers (docs/deploy_sepolia.md): b = 100, unit = 0.0001 ETH, hedge of size 3.
  // Quotes are from the exact reference model, python -c "from sim import lmsr; lmsr.quote_vector_wei(...)".
  const GUIDE = [
    { d: 2, v: [0, 5, 9, 12, 18, 30], quote: 1281027009166992n },
    { d: 3, v: [0, 2, 6, 9, 15, 27], quote: 1025582224601672n },
    { d: 4, v: [0, 0, 3, 6, 12, 24], quote: 786628457016825n },
  ];
  for (const { d, v, quote: want } of GUIDE) {
    it(`d = ${d}: deploy, fund exactly b ln 6, buy ${JSON.stringify(v)}, report the 2025 count, settle, redeem, sponsor withdraw`, async function () {
      const b = 100, unit = 10n ** 14n;
      expect(holding(d, 3)).to.deep.equal(v);
      const { sponsor, reporter, buyer, anyone, oracle, market, T, need, args } = await setUp({ b, unit, season: 2025 });
      // funding: exactly b ln(6) unit, and one wei less is refused
      expect(need).to.equal(17917594692280550n);
      expect(await market.funding()).to.equal(need);
      expect(await market.requiredFunding()).to.equal(need);
      await expect(deploy("RainCountLMSR", args, { value: need - 1n }, sponsor)).to.be.revertedWith("Funding below worst-case loss");
      // buy the stepped basket
      const quote = await market.quoteBasket(v);
      expect(quote).to.be.closeTo(want, 2n);
      expect(Number(quote)).to.be.closeTo(refCost(v, b, Number(unit)), 1e6); // float check, 1e-9 relative
      await expect(market.connect(buyer).buyBasket(v, quote, { value: quote })).to.changeEtherBalance(buyer, -quote);
      expect((await market.sharesOfAll(buyer.address)).map(Number)).to.deep.equal(v);
      expect(await market.paid(buyer.address)).to.equal(quote);
      // the oracle refuses the count before the season end, then takes the real 2025 count once
      const count = counts[2025];
      await expect(oracle.connect(reporter).reportCount("TTN", 2025, count)).to.be.revertedWith("Season not over");
      await setNextTime(T + 1501);
      await oracle.connect(reporter).reportCount("TTN", 2025, count);
      expect(await market.hasValidReport()).to.equal(true);
      await market.connect(anyone).settle();
      expect(await market.state()).to.equal(1n);
      expect(await market.settledCount()).to.equal(5n);
      expect(await market.winningBucket()).to.equal(2n); // the bucket "5"
      const payout = BigInt(v[2]) * unit;                // 3 x (5 - d) shares x 0.0001 ETH
      expect(payout).to.equal(BigInt(3 * (5 - d)) * unit);
      expect(await market.reserved()).to.equal(payout);
      await expect(market.connect(buyer).redeem()).to.changeEtherBalance(buyer, payout);
      await expect(market.connect(buyer).redeem()).to.be.revertedWith("Nothing to redeem");
      // sponsor: funding + premium - payout. In 2025 the premium was larger than the payout.
      const back = need + quote - payout;
      await expect(market.connect(sponsor).sponsorWithdraw()).to.changeEtherBalance(sponsor, back);
      expect(back > need).to.equal(true);
      expect(await balanceOf(market)).to.equal(0n);
    });
  }

  it("hedge of 10 x L with payout unit L/12 (exact registered fractions), settled on every REPORT season 2015-2026", async function () {
    // unit = L/12, so the shares are 12 x 10 x h_j and b = 12 x 1,000 is b = 1,000 in units of L.
    const unit = 10n ** 12n, b = 12000;
    for (const d of [2, 3, 4]) {
      const v = holding(d, 120);
      const { sponsor, reporter, buyer, oracle, market, T, need } = await setUp({ b, unit, season: 2027 });
      const quote = await market.quoteBasket(v);
      expect(Number(quote)).to.be.closeTo(refCost(v, b, Number(unit)), Number(quote) * 1e-9);
      await market.connect(buyer).buyBasket(v, quote, { value: quote });
      await setNextTime(T + 1501);
      const snap0 = await snapshot();
      let id = snap0;
      for (let y = 2015; y <= 2026; y++) {
        const count = counts[y];
        await oracle.connect(reporter).reportCount("TTN", 2027, count);
        await market.settle();
        const j = bucketOf(count, EDGES);
        expect(Number(await market.winningBucket()), "season " + y).to.equal(j);
        const payout = BigInt(v[j]) * unit; // = 10 x max(m_j - d, 0) x L
        if (payout > 0n) await expect(market.connect(buyer).redeem()).to.changeEtherBalance(buyer, payout);
        else await expect(market.connect(buyer).redeem()).to.be.revertedWith("Nothing to redeem");
        const back = need + quote - payout;
        expect(payout - quote <= need, "season " + y).to.equal(true); // the sponsor never loses more than b ln 6
        await expect(market.connect(sponsor).sponsorWithdraw()).to.changeEtherBalance(sponsor, back);
        expect(await balanceOf(market)).to.equal(0n);
        await revertTo(id);
        id = await snapshot();
      }
    }
  });
});
