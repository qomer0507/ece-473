// Rehearsal of docs/deploy_sepolia.md in the local Hardhat EVM, with the guide's own numbers.
// Three accounts (Reporter, Sponsor, Buyer), the real SeasonCountOracle, the demo times.
// If this file fails, the guide is wrong: fix both together.
const { expect } = require("chai");
const { ethers, deploy, now, setNextTime, setTime, balanceOf } = require("./rain_helpers");

describe("16 deploy guide rehearsal (docs/deploy_sepolia.md, local EVM only)", function () {
  it("steps 1-23: deploy with the registered edges, buy the stepped hedge, report the 2025 count (5), settle, redeem, withdraw, with the guide's numbers", async function () {
    const [sponsor, reporter, buyer, anyone] = await ethers.getSigners();
    // Reporter
    const oracle = await deploy("SeasonCountOracle", [], {}, reporter);
    const T = Number(await oracle.currentTime());
    await oracle.connect(reporter).openSeason("TTN", 2025, T + 900, T + 1500, 102);
    expect((await oracle.getSeason("TTN", 2025)).opened).to.equal(true);
    // Sponsor
    const value = 18000000000000000n;
    const market = await deploy("RainCountLMSR",
      [await oracle.getAddress(), "TTN", 2025, [2, 4, 5, 6, 8], 100, 100000000000000n, T + 900, T + 3300, 0, 604800], { value }, sponsor);
    expect(await market.requiredFunding()).to.equal(17917594692280550n);
    expect(await market.requiredFundingFor(100, 100000000000000n)).to.equal(17917594692280550n);
    expect(await market.funding()).to.equal(value);
    expect(await market.state()).to.equal(0n);
    for (const p of await market.prices()) expect(p).to.be.closeTo(166666666666666666n, 2n);
    expect((await market.getEdges()).map(Number)).to.deep.equal([2, 4, 5, 6, 8]);
    expect(await market.bucketOf(5)).to.equal(2n);
    expect(await balanceOf(market)).to.equal(value); // 0.018 ETH
    // Buyer
    const v = [0, 2, 6, 9, 15, 27]; // 3 x max(m_j - 3, 0), m = [1.75, 3.667, 5, 6, 8, 12]
    const quote = await market.quoteBasket(v);
    expect(quote).to.be.closeTo(1025582224601672n, 2n);
    const maxCost = 1050000000000000n; // the guide's round number, about 2.4% above the quote
    expect(maxCost > quote && maxCost < (quote * 103n) / 100n).to.equal(true);
    await expect(market.connect(buyer).buyBasket(v, maxCost, { value: maxCost })).to.changeEtherBalance(buyer, -quote);
    expect((await market.sharesOfAll(buyer.address)).map(Number)).to.deep.equal(v);
    expect(await market.paid(buyer.address)).to.equal(quote);
    expect(await market.totalPaid()).to.equal(quote);
    expect(Number(await balanceOf(market)) / 1e18).to.be.closeTo(0.019025582, 1e-9);
    // maxCost values the guide gives for the other deductibles are above their quotes, by less than 3%
    for (const [q, m] of [[1281027009166992n, 1310000000000000n], [786628457016825n, 805000000000000n]])
      expect(m > q && m < (q * 103n) / 100n).to.equal(true);
    const after = (await market.prices()).map((p) => Number(p) / 1e18);
    [0.1504, 0.1535, 0.1597, 0.1646, 0.1748, 0.197].forEach((p, j) => expect(after[j]).to.be.closeTo(p, 0.00006));
    // the guide's alternative baskets for d = 2 and d = 4 (quotes from a fresh market)
    const fresh = await deploy("RainCountLMSR",
      [await oracle.getAddress(), "TTN", 2025, [2, 4, 5, 6, 8], 100, 100000000000000n, T + 900, T + 3300, 0, 604800], { value }, sponsor);
    expect(await fresh.quoteBasket([0, 5, 9, 12, 18, 30])).to.be.closeTo(1281027009166992n, 2n);
    expect(await fresh.quoteBasket([0, 0, 3, 6, 12, 24])).to.be.closeTo(786628457016825n, 2n);
    // early report refused
    await expect(oracle.connect(reporter).reportCount("TTN", 2025, 5)).to.be.revertedWith("Season not over");
    // Reporter, after the season end
    await setNextTime(T + 1501);
    await expect(oracle.connect(buyer).reportCount("TTN", 2025, 5)).to.be.revertedWith("Not an authorised reporter");
    await oracle.connect(reporter).reportCount("TTN", 2025, 5);
    expect((await oracle.getSeason("TTN", 2025)).count).to.equal(5n);
    await expect(oracle.connect(reporter).reportCount("TTN", 2025, 5)).to.be.revertedWith("Already reported");
    expect(await market.hasValidReport()).to.equal(true);
    // anyone settles
    await market.connect(anyone).settle();
    expect(await market.state()).to.equal(1n);
    expect(await market.settledCount()).to.equal(5n);
    expect(await market.winningBucket()).to.equal(2n);
    expect(await market.reserved()).to.equal(600000000000000n);
    // Buyer redeems 6 shares x 0.0001 ETH = 0.0006 ETH
    await expect(market.connect(buyer).redeem()).to.changeEtherBalance(buyer, 600000000000000n);
    await expect(market.connect(buyer).redeem()).to.be.revertedWith("Nothing to redeem");
    expect(await market.reserved()).to.equal(0n);
    expect(Number(await balanceOf(market)) / 1e18).to.be.closeTo(0.018425582, 1e-9);
    await expect(market.connect(buyer).sponsorWithdraw()).to.be.revertedWith("Not sponsor");
    // the guide's "wet season" sentence: 12 loss days is bucket 5, 27 shares; the sponsor would lose 0.001674 ETH
    expect(await market.bucketOf(12)).to.equal(5n);
    expect(Number(27n * 100000000000000n - quote) / 1e18).to.be.closeTo(0.001674, 0.000001);
    // Sponsor withdraws funding + paid - payout
    const back = value + quote - 600000000000000n;
    expect(back).to.be.closeTo(18425582224601672n, 2n);
    await expect(market.connect(sponsor).sponsorWithdraw()).to.changeEtherBalance(sponsor, back);
    expect(Number(back - value) / 1e18).to.be.closeTo(0.000426, 0.000001); // the sponsor's GAIN on this market (2025 was a mild season)
    expect(await balanceOf(market)).to.equal(0n);
  });

  it("steps 24-28: cancel rehearsal with a 10-minute market", async function () {
    const [sponsor, reporter, buyer, anyone] = await ethers.getSigners();
    const oracle = await deploy("SeasonCountOracle", [], {}, reporter);
    const T2 = Number(await oracle.currentTime());
    await oracle.connect(reporter).openSeason("TTN", 2028, T2 + 300, T2 + 420, 102);
    const value = 18000000000000000n;
    const market = await deploy("RainCountLMSR",
      [await oracle.getAddress(), "TTN", 2028, [2, 4, 5, 6, 8], 100, 100000000000000n, T2 + 300, T2 + 600, 0, 604800], { value }, sponsor);
    const quote = await market.quoteBasket([0, 2, 6, 9, 15, 27]);
    await expect(market.connect(buyer).buyBasket([0, 2, 6, 9, 15, 27], 1050000000000000n, { value: 1050000000000000n }))
      .to.changeEtherBalance(buyer, -quote);
    await expect(oracle.connect(reporter).openSeason("TTN", 2028, T2 + 300, T2 + 420, 102)).to.be.revertedWith("Season already opened");
    await setNextTime(T2 + 600);
    await expect(market.connect(anyone).cancelAfterDeadline()).to.be.revertedWith("Deadline not passed");
    await market.connect(anyone).cancelAfterDeadline(); // one second later
    expect(await market.state()).to.equal(2n);
    await expect(market.connect(buyer).claimRefund()).to.changeEtherBalance(buyer, quote);
    await expect(market.connect(sponsor).sponsorWithdraw()).to.changeEtherBalance(sponsor, value);
    expect(await balanceOf(market)).to.equal(0n);
  });
});
