// Every oracle path, settlement, redemption, cancel, refunds, withdrawal, reentrancy.
const { expect } = require("chai");
const { ethers, deploy, deployMarket, tx, now, setTime, setNextTime, STATION, DAY } = require("./helpers");

const MAX = ethers.MaxUint256;
const E18 = 10n ** 18n;
const bal = async (c) => ethers.provider.getBalance(await c.getAddress());

/** Market on the real TemperatureOracle with three traders holding positions. */
async function tradedMarket(o = {}) {
  const m = await deployMarket({ mock: false, b: 200, ...o });
  const [sponsor, alice, bob, carol, reporter, stranger] = m.signers;
  await m.market.connect(alice).buyBasket(100, MAX, { value: E18 });   // 100 of every bracket >= 90
  await m.market.connect(bob).buy(3, 250, MAX, { value: E18 });        // 84-85
  await m.market.connect(carol).buy(6, 40, MAX, { value: E18 });       // 90-91
  await m.market.connect(carol).buy(0, 10, MAX, { value: E18 });       // <80
  return { ...m, sponsor, alice, bob, carol, reporter, stranger };
}

describe("03 TemperatureOracle", function () {
  let oracle, owner, reporter, stranger, day;
  beforeEach(async function () {
    [owner, , , , reporter, stranger] = await ethers.getSigners();
    oracle = await deploy("TemperatureOracle", [], {}, owner, "deploy TemperatureOracle");
    day = Math.floor((await now()) / DAY);
  });

  it("the deployer is owner and first reporter; currentDay() is the UTC day number", async function () {
    expect(await oracle.owner()).to.equal(owner.address);
    expect(await oracle.isReporter(owner.address)).to.equal(true);
    expect(await oracle.currentDay()).to.equal(BigInt(Math.floor((await now()) / DAY)));
  });

  it("an authorised reporter stores one timestamped report and emits Reported", async function () {
    await tx("oracle.setReporter", oracle.setReporter(reporter.address, true));
    const call = oracle.connect(reporter).reportTemperature(STATION, day, 93);
    await expect(call).to.emit(oracle, "Reported");
    const receipt = await tx("oracle.reportTemperature", call);
    const ts = (await ethers.provider.getBlock(receipt.blockNumber)).timestamp;
    const [exists, temp, at] = await oracle.getReport(STATION, day);
    expect(exists).to.equal(true);
    expect(temp).to.equal(93n);
    expect(at).to.equal(BigInt(ts));
  });

  it("unauthorised: a stranger cannot report, and only the owner can authorise", async function () {
    await expect(oracle.connect(stranger).reportTemperature(STATION, day, 93)).to.be.revertedWith("Not an authorised reporter");
    await expect(oracle.connect(stranger).setReporter(stranger.address, true)).to.be.revertedWith("Not owner");
    await oracle.setReporter(reporter.address, true);
    await oracle.setReporter(reporter.address, false);
    await expect(oracle.connect(reporter).reportTemperature(STATION, day, 93)).to.be.revertedWith("Not an authorised reporter");
  });

  it("duplicate: a second report for the same station and day is rejected, even with the same value", async function () {
    await oracle.reportTemperature(STATION, day, 93);
    await expect(oracle.reportTemperature(STATION, day, 93)).to.be.revertedWith("Already reported");
    await expect(oracle.reportTemperature(STATION, day, 71)).to.be.revertedWith("Already reported");
    expect((await oracle.getReport(STATION, day))[1]).to.equal(93n);
  });

  it("reports are separate per station and per day", async function () {
    await oracle.reportTemperature(STATION, day, 93);
    await oracle.reportTemperature("USW00094728", day, 88);
    await oracle.reportTemperature(STATION, day - 1, 70);
    expect((await oracle.getReport(STATION, day))[1]).to.equal(93n);
    expect((await oracle.getReport("USW00094728", day))[1]).to.equal(88n);
    expect((await oracle.getReport(STATION, day - 1))[1]).to.equal(70n);
    expect((await oracle.getReport(STATION, day - 2))[0]).to.equal(false);
  });

  it("rejects a day that has not started and implausible temperatures", async function () {
    await expect(oracle.reportTemperature(STATION, day + 1, 93)).to.be.revertedWith("Day has not started");
    await expect(oracle.reportTemperature(STATION, day, 141)).to.be.revertedWith("Implausible temperature");
    await expect(oracle.reportTemperature(STATION, day, -81)).to.be.revertedWith("Implausible temperature");
    await oracle.reportTemperature(STATION, day, 140);
    await oracle.reportTemperature(STATION, day - 1, -80);
  });
});

describe("03 settlement: on-time report", function () {
  it("settles once, pays winners 1 unit per share, sponsor takes the rest, balance ends at 0 (payout conservation)", async function () {
    const m = await tradedMarket();
    const { market, oracle, alice, bob, carol, sponsor, unit, day } = m;
    const pool = await bal(market);
    expect(pool).to.equal(m.value + (await market.totalPaid()));

    await expect(market.settle()).to.be.revertedWith("Observation not over");
    await setTime(m.observationEnd + 10);
    await expect(market.settle()).to.be.revertedWith("No report for market day");
    await tx("oracle.reportTemperature", oracle.reportTemperature(STATION, day, 91));
    const call = market.connect(m.stranger).settle(); // anyone may call
    await expect(call).to.emit(market, "Settled");
    await tx("settle", call);

    expect(await market.state()).to.equal(1n);
    expect(await market.settledTemp()).to.equal(91n);
    expect(await market.winningBracket()).to.equal(6n);
    expect(await market.reserved()).to.equal(140n * unit); // alice 100 + carol 40

    // redemptions
    const rA = market.connect(alice).redeem();
    await expect(rA).to.emit(market, "Redeemed").withArgs(alice.address, 100n, 100n * unit);
    await expect(rA).to.changeEtherBalances([alice, market], [100n * unit, -100n * unit]);
    await tx("redeem", rA);
    await expect(market.connect(alice).redeem()).to.be.revertedWith("Nothing to redeem");
    await expect(market.connect(bob).redeem()).to.be.revertedWith("Nothing to redeem"); // bob lost

    // the sponsor can withdraw before everyone has redeemed, but never the reserved part
    const leftover = (await bal(market)) - 40n * unit;
    const w = market.connect(sponsor).sponsorWithdraw();
    await expect(w).to.emit(market, "SponsorWithdrawal").withArgs(sponsor.address, leftover);
    await expect(w).to.changeEtherBalance(sponsor, leftover);
    await tx("sponsorWithdraw", w);
    await expect(market.connect(sponsor).sponsorWithdraw()).to.be.revertedWith("Nothing to withdraw");
    expect(await bal(market)).to.equal(40n * unit);

    await expect(market.connect(carol).redeem()).to.changeEtherBalance(carol, 40n * unit);
    expect(await bal(market)).to.equal(0n);
    expect(await market.reserved()).to.equal(0n);
    // conservation: everything that came in went out
    expect(100n * unit + 40n * unit + leftover).to.equal(pool);
  });

  it("the basket pays if and only if T >= 90 (boundary at 89 / 90)", async function () {
    for (const [temp, pays] of [[89, false], [90, true], [99, true], [100, true], [112, true], [45, false]]) {
      const m = await tradedMarket();
      await setTime(m.observationEnd);
      await m.oracle.reportTemperature(STATION, m.day, temp);
      await m.market.settle();
      if (pays) await expect(m.market.connect(m.alice).redeem()).to.changeEtherBalance(m.alice, 100n * m.unit);
      else await expect(m.market.connect(m.alice).redeem()).to.be.revertedWith("Nothing to redeem");
    }
  });

  it("duplicate settlement is rejected, and so is buying, cancelling or refunding after settlement", async function () {
    const m = await tradedMarket();
    await setTime(m.observationEnd);
    await m.oracle.reportTemperature(STATION, m.day, 85);
    await m.market.settle();
    await expect(m.market.settle()).to.be.revertedWith("Not open");
    await expect(m.market.emergencyCancel()).to.be.revertedWith("Not open");
    await setTime(m.reportDeadline + 1);
    await expect(m.market.cancelAfterDeadline()).to.be.revertedWith("Not open");
    await expect(m.market.connect(m.alice).claimRefund()).to.be.revertedWith("Not cancelled");
    expect(await m.market.winningBracket()).to.equal(3n);
    await expect(m.market.connect(m.bob).redeem()).to.changeEtherBalance(m.bob, 250n * m.unit);
  });

  it("a report made exactly at observationEnd or exactly at the deadline is valid", async function () {
    for (const which of ["observationEnd", "reportDeadline"]) {
      const m = await tradedMarket();
      await setNextTime(m[which]);
      await m.oracle.reportTemperature(STATION, m.day, 93);
      await m.market.settle();
      expect(await m.market.state()).to.equal(1n);
    }
  });

  it("an on-time report can still be settled after the deadline, and then cancel is refused", async function () {
    const m = await tradedMarket();
    await setTime(m.observationEnd + 5);
    await m.oracle.reportTemperature(STATION, m.day, 93);
    await setTime(m.reportDeadline + 500);
    await expect(m.market.cancelAfterDeadline()).to.be.revertedWith("Valid report exists, call settle");
    await m.market.settle();
    expect(await m.market.winningBracket()).to.equal(7n);
  });

  it("redeem, refund and withdraw are refused while the market is open", async function () {
    const m = await tradedMarket();
    await expect(m.market.connect(m.alice).redeem()).to.be.revertedWith("Not settled");
    await expect(m.market.connect(m.alice).claimRefund()).to.be.revertedWith("Not cancelled");
    await expect(m.market.sponsorWithdraw()).to.be.revertedWith("Market still open");
    await expect(m.market.connect(m.alice).sponsorWithdraw()).to.be.revertedWith("Not sponsor");
  });
});

describe("03 settlement: late, missing, stale and wrong-day reports", function () {
  it("missing report: after the deadline anyone cancels and every trader is refunded their cost basis", async function () {
    const m = await tradedMarket();
    const { market, alice, bob, carol, sponsor } = m;
    const paid = { a: await market.paid(alice.address), b: await market.paid(bob.address), c: await market.paid(carol.address) };
    await setTime(m.reportDeadline - 1); // the next transaction is mined exactly at the deadline
    await expect(market.cancelAfterDeadline()).to.be.revertedWith("Deadline not passed");
    expect(await market.state()).to.equal(0n);
    await setTime(m.reportDeadline + 1);
    const call = market.connect(m.stranger).cancelAfterDeadline();
    await expect(call).to.emit(market, "Cancelled").withArgs(m.stranger.address, "No valid report by deadline", paid.a + paid.b + paid.c);
    await tx("cancelAfterDeadline", call);
    expect(await market.state()).to.equal(2n);
    await expect(market.settle()).to.be.revertedWith("Not open");
    await expect(market.connect(alice).redeem()).to.be.revertedWith("Not settled");

    const rA = market.connect(alice).claimRefund();
    await expect(rA).to.emit(market, "Refunded").withArgs(alice.address, paid.a);
    await expect(rA).to.changeEtherBalance(alice, paid.a);
    await tx("claimRefund", rA);
    await expect(market.connect(alice).claimRefund()).to.be.revertedWith("Nothing to refund");
    await expect(market.connect(bob).claimRefund()).to.changeEtherBalance(bob, paid.b);
    // the sponsor gets exactly the funding back, and cannot touch carol's refund
    await expect(market.connect(sponsor).sponsorWithdraw()).to.changeEtherBalance(sponsor, m.value);
    expect(await bal(market)).to.equal(paid.c);
    await expect(market.connect(carol).claimRefund()).to.changeEtherBalance(carol, paid.c);
    expect(await bal(market)).to.equal(0n);
  });

  it("late report (after the deadline): settle rejects it, cancel and refunds work", async function () {
    const m = await tradedMarket();
    await setTime(m.reportDeadline + 1);
    await m.oracle.reportTemperature(STATION, m.day, 95);
    await expect(m.market.settle()).to.be.revertedWith("Late report");
    await m.market.cancelAfterDeadline();
    await expect(m.market.connect(m.alice).claimRefund()).to.changeEtherBalance(m.alice, await m.market.paid(m.alice.address));
  });

  it("stale report (made before the day's observation ended): settle rejects it, then cancel", async function () {
    const m = await tradedMarket();
    await m.oracle.reportTemperature(STATION, m.day, 95); // too early, e.g. a forecast or a running maximum
    await setTime(m.observationEnd + 1);
    await expect(m.market.settle()).to.be.revertedWith("Stale report");
    // the oracle allows one report per day, so the early report cannot be replaced
    await expect(m.oracle.reportTemperature(STATION, m.day, 96)).to.be.revertedWith("Already reported");
    await expect(m.market.cancelAfterDeadline()).to.be.revertedWith("Deadline not passed");
    await setTime(m.reportDeadline + 1);
    await m.market.cancelAfterDeadline();
    expect(await m.market.state()).to.equal(2n);
  });

  it("wrong day or wrong station: reports for another day or station never settle this market", async function () {
    const m = await tradedMarket();
    await setTime(m.observationEnd + 1);
    await m.oracle.reportTemperature(STATION, m.day - 1, 95);        // yesterday
    await m.oracle.reportTemperature("USW00094728", m.day, 95);      // another station
    await expect(m.market.settle()).to.be.revertedWith("No report for market day");
    await setTime(m.reportDeadline + 1);
    await m.market.cancelAfterDeadline();
    expect(await m.market.state()).to.equal(2n);
  });

  it("mock oracle: stale and late timestamps are rejected; a broken oracle cannot block refunds", async function () {
    const m = await deployMarket({ b: 200 });
    const [, alice] = m.signers;
    await m.market.connect(alice).buyBasket(10, MAX, { value: E18 });
    await setTime(m.observationEnd + 1);
    await m.oracle.setReportAt(STATION, m.day, 95, m.observationEnd - 1);
    await expect(m.market.settle()).to.be.revertedWith("Stale report");
    await m.oracle.setReportAt(STATION, m.day, 95, m.reportDeadline + 1);
    await expect(m.market.settle()).to.be.revertedWith("Late report");
    await m.oracle.clearReport(STATION, m.day);
    await expect(m.market.settle()).to.be.revertedWith("No report for market day");
    await m.oracle.setBroken(true);
    await expect(m.market.settle()).to.be.reverted;
    await setTime(m.reportDeadline + 1);
    await m.market.cancelAfterDeadline(); // works although getReport reverts
    await expect(m.market.connect(alice).claimRefund()).to.changeEtherBalance(alice, await m.market.paid(alice.address));
  });

  it("mock oracle: a changed report after settlement has no effect (one-time settlement)", async function () {
    const m = await deployMarket({ b: 200 });
    const [, alice] = m.signers;
    await m.market.connect(alice).buyBasket(10, MAX, { value: E18 });
    await setTime(m.observationEnd + 1);
    await m.oracle.setReport(STATION, m.day, 95);
    await m.market.settle();
    await m.oracle.setReport(STATION, m.day, 60);
    await expect(m.market.settle()).to.be.revertedWith("Not open");
    expect(await m.market.settledTemp()).to.equal(95n);
    await expect(m.market.connect(alice).redeem()).to.changeEtherBalance(alice, 10n * m.unit);
  });
});

describe("03 emergency cancel", function () {
  it("only the sponsor can cancel; trading stops; refunds are the exact cost basis", async function () {
    const m = await tradedMarket();
    const { market, alice, bob, carol, sponsor } = m;
    await expect(market.connect(alice).emergencyCancel()).to.be.revertedWith("Not sponsor");
    const total = await market.totalPaid();
    const call = market.connect(sponsor).emergencyCancel();
    await expect(call).to.emit(market, "Cancelled").withArgs(sponsor.address, "Emergency cancel by sponsor", total);
    await tx("emergencyCancel", call);
    await expect(market.connect(alice).buy(0, 1, MAX, { value: E18 })).to.be.revertedWith("Not open");
    await expect(market.connect(alice).buyBasket(1, MAX, { value: E18 })).to.be.revertedWith("Not open");
    await expect(market.emergencyCancel()).to.be.revertedWith("Not open");
    let out = 0n;
    for (const t of [alice, bob, carol]) {
      const p = await market.paid(t.address);
      await expect(market.connect(t).claimRefund()).to.changeEtherBalance(t, p);
      out += p;
    }
    expect(out).to.equal(total);
    await expect(market.connect(sponsor).sponsorWithdraw()).to.changeEtherBalance(sponsor, m.value);
    expect(await bal(market)).to.equal(0n);
  });

  it("the sponsor cannot cancel after trading has closed (no escape once the day is observed)", async function () {
    const m = await tradedMarket();
    await setTime(m.tradingClose - 1); // next transaction is mined exactly at tradingClose
    await expect(m.market.emergencyCancel()).to.be.revertedWith("Trading closed, wait for the oracle");
    await setTime(m.observationEnd + 1);
    await expect(m.market.emergencyCancel()).to.be.revertedWith("Trading closed, wait for the oracle");
    await m.oracle.reportTemperature(STATION, m.day, 95);
    await m.market.settle();
    await expect(m.market.connect(m.alice).redeem()).to.changeEtherBalance(m.alice, 100n * m.unit);
  });

  it("a report that arrives after a cancel cannot settle the market", async function () {
    const m = await tradedMarket();
    await m.market.emergencyCancel();
    await setTime(m.observationEnd + 1);
    await m.oracle.reportTemperature(STATION, m.day, 95);
    await expect(m.market.settle()).to.be.revertedWith("Not open");
  });
});

describe("03 reentrancy and failed transfers", function () {
  it("a contract that re-enters redeem() gets paid once", async function () {
    const m = await deployMarket({ b: 200 });
    const attacker = await deploy("ReentrantTrader", [await m.market.getAddress()]);
    await attacker.buy(6, 50, { value: E18 });
    await m.market.connect(m.signers[1]).buy(6, 50, MAX, { value: E18 });
    await setTime(m.observationEnd + 1);
    await m.oracle.setReport(STATION, m.day, 90);
    await m.market.settle();
    await attacker.setMode(1);
    await expect(attacker.redeem()).to.changeEtherBalance(attacker, 50n * m.unit);
    expect(await attacker.attempts()).to.equal(1n);
    expect(await attacker.reentrySucceeded()).to.equal(false);
    await expect(m.market.connect(m.signers[1]).redeem()).to.changeEtherBalance(m.signers[1], 50n * m.unit);
  });

  it("a contract that re-enters claimRefund() gets refunded once", async function () {
    const m = await deployMarket({ b: 200 });
    const attacker = await deploy("ReentrantTrader", [await m.market.getAddress()]);
    await attacker.buy(6, 50, { value: E18 });
    await m.market.connect(m.signers[1]).buy(2, 50, MAX, { value: E18 });
    const paid = await m.market.paid(await attacker.getAddress());
    await m.market.emergencyCancel();
    await attacker.setMode(2);
    await expect(attacker.claimRefund()).to.changeEtherBalance(attacker, paid);
    expect(await attacker.reentrySucceeded()).to.equal(false);
    expect(await bal(m.market)).to.equal(m.value + (await m.market.paid(m.signers[1].address)));
  });

  it("a contract that re-enters buy() from the excess refund is blocked", async function () {
    const m = await deployMarket({ b: 200 });
    const attacker = await deploy("ReentrantTrader", [await m.market.getAddress()]);
    await attacker.setMode(3);
    await attacker.buy(6, 50, { value: E18 }); // sends too much, the refund triggers the re-entry attempt
    expect(await attacker.attempts()).to.equal(1n);
    expect(await attacker.reentrySucceeded()).to.equal(false);
    expect(await m.market.sharesOf(await attacker.getAddress(), 6)).to.equal(50n);
    expect(await m.market.sharesOf(await attacker.getAddress(), 0)).to.equal(0n);
  });

  it("a winner that cannot receive ETH does not lock the other winners or the sponsor", async function () {
    const m = await deployMarket({ b: 200 });
    const rejecting = await deploy("RejectingTrader", [await m.market.getAddress()]);
    const cost = await m.market.quoteBuy(6, 30);
    await rejecting.buyExact(6, 30, { value: cost });
    await m.market.connect(m.signers[1]).buy(6, 70, MAX, { value: E18 });
    await setTime(m.observationEnd + 1);
    await m.oracle.setReport(STATION, m.day, 91);
    await m.market.settle();
    await expect(rejecting.redeem()).to.be.revertedWith("Transfer failed");
    await expect(m.market.connect(m.signers[1]).redeem()).to.changeEtherBalance(m.signers[1], 70n * m.unit);
    await m.market.sponsorWithdraw();
    expect(await bal(m.market)).to.equal(30n * m.unit); // still reserved for the stuck winner
  });
});
