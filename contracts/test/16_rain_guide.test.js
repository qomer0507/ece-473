// Rehearsal of docs/deploy_sepolia.md in the local Hardhat EVM, with the guide's own numbers.
// Three accounts (Reporter, Sponsor, Buyer), the real SeasonCountOracle, the demo times.
// If this file fails, the guide is wrong: fix both together.
const { expect } = require("chai");
const { ethers, deploy, now, setNextTime, setTime, balanceOf } = require("./rain_helpers");

describe("16 deploy guide rehearsal (docs/deploy_sepolia.md, local EVM only)", function () {
  it("steps 1-23: deploy, buy the stepped hedge, report 9, settle, redeem, withdraw, with the guide's numbers", async function () {
    const [sponsor, reporter, buyer, anyone] = await ethers.getSigners();
    // Reporter
    const oracle = await deploy("SeasonCountOracle", [], {}, reporter);
    const T = Number(await oracle.currentTime());
    await oracle.connect(reporter).openSeason("TTN", 2027, T + 900, T + 1500, 102);
    expect((await oracle.getSeason("TTN", 2027)).opened).to.equal(true);
    // Sponsor
    const value = 18000000000000000n;
    const market = await deploy("RainCountLMSR",
      [await oracle.getAddress(), "TTN", 2027, [2, 4, 6, 8, 10], 100, 100000000000000n, T + 900, T + 3300, 0, 604800], { value }, sponsor);
    expect(await market.requiredFunding()).to.equal(17917594692280550n);
    expect(await market.requiredFundingFor(100, 100000000000000n)).to.equal(17917594692280550n);
    expect(await market.funding()).to.equal(value);
    expect(await market.state()).to.equal(0n);
    for (const p of await market.prices()) expect(p).to.be.closeTo(166666666666666666n, 2n);
    // Buyer
    const v = [0, 0, 0, 10, 20, 30];
    const quote = await market.quoteBasket(v);
    expect(quote).to.be.closeTo(1068243163504235n, 2n);
    const maxCost = 1089608026774319n; // quote + 2%
    await expect(market.connect(buyer).buyBasket(v, maxCost, { value: maxCost })).to.changeEtherBalance(buyer, -quote);
    expect((await market.sharesOfAll(buyer.address)).map(Number)).to.deep.equal(v);
    expect(await market.paid(buyer.address)).to.equal(quote);
    expect(Number((await market.prices())[5]) / 1e18).to.be.closeTo(0.202, 0.0005);
    // early report refused
    await expect(oracle.connect(reporter).reportCount("TTN", 2027, 9)).to.be.revertedWith("Season not over");
    // Reporter, after the season end
    await setNextTime(T + 1501);
    await oracle.connect(reporter).reportCount("TTN", 2027, 9);
    await expect(oracle.connect(reporter).reportCount("TTN", 2027, 9)).to.be.revertedWith("Already reported");
    expect(await market.hasValidReport()).to.equal(true);
    // anyone settles
    await market.connect(anyone).settle();
    expect(await market.state()).to.equal(1n);
    expect(await market.settledCount()).to.equal(9n);
    expect(await market.winningBucket()).to.equal(4n);
    expect(await market.reserved()).to.equal(2000000000000000n);
    // Buyer redeems 0.002 ETH
    await expect(market.connect(buyer).redeem()).to.changeEtherBalance(buyer, 2000000000000000n);
    await expect(market.connect(buyer).redeem()).to.be.revertedWith("Nothing to redeem");
    // Sponsor withdraws funding + paid - payout
    const back = value + quote - 2000000000000000n;
    expect(Number(back) / 1e18).to.be.closeTo(0.017068, 0.000001);
    await expect(market.connect(sponsor).sponsorWithdraw()).to.changeEtherBalance(sponsor, back);
    expect(Number(value - back) / 1e18).to.be.closeTo(0.000932, 0.000001); // the sponsor's loss on this market
    expect(await balanceOf(market)).to.equal(0n);
  });

  it("steps 24-28: cancel rehearsal with a 10-minute market", async function () {
    const [sponsor, reporter, buyer, anyone] = await ethers.getSigners();
    const oracle = await deploy("SeasonCountOracle", [], {}, reporter);
    const T2 = Number(await oracle.currentTime());
    await oracle.connect(reporter).openSeason("TTN", 2028, T2 + 300, T2 + 420, 102);
    const value = 18000000000000000n;
    const market = await deploy("RainCountLMSR",
      [await oracle.getAddress(), "TTN", 2028, [2, 4, 6, 8, 10], 100, 100000000000000n, T2 + 300, T2 + 600, 0, 604800], { value }, sponsor);
    const quote = await market.quoteBasket([0, 0, 0, 10, 20, 30]);
    await market.connect(buyer).buyBasket([0, 0, 0, 10, 20, 30], quote, { value: quote });
    await setNextTime(T2 + 600);
    await expect(market.connect(anyone).cancelAfterDeadline()).to.be.revertedWith("Deadline not passed");
    await market.connect(anyone).cancelAfterDeadline(); // one second later
    expect(await market.state()).to.equal(2n);
    await expect(market.connect(buyer).claimRefund()).to.changeEtherBalance(buyer, quote);
    await expect(market.connect(sponsor).sponsorWithdraw()).to.changeEtherBalance(sponsor, value);
    expect(await balanceOf(market)).to.equal(0n);
  });
});
