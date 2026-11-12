// SeasonCountOracle, settlement, every oracle path, dispute delay, cancel and refund,
// unclaimed funds, reentrancy, and the review's stuck-funds cases (M1).
const { expect } = require("chai");
const { ethers, deployRain, deploy, deployMarket, setTime, setNextTime, now, snapshot, revertTo, balanceOf, bucketOf,
  EDGES, STATION, SEASON, SEASON_DAYS, DAYS, CLAIM_PERIOD } = require("./rain_helpers");

const MAX = ethers.MaxUint256;
const E18 = 10n ** 18n;
const STEPPED = [0n, 0n, 0n, 1n, 2n, 3n];

/** Three buyers: alice holds the stepped hedge x100, bob 150 of bucket 2, carol 80 of bucket 0. */
async function withBuyers(o = {}) {
  const m = await deployRain(o);
  const paid = {};
  const buy = async (who, v) => {
    const c = await m.market.quoteBasket(v);
    await m.market.connect(who).buyBasket(v, c, { value: c });
    return c;
  };
  paid.alice = await buy(m.alice, STEPPED.map((x) => x * 100n));
  paid.bob = await buy(m.bob, [0n, 0n, 150n, 0n, 0n, 0n]);
  paid.carol = await buy(m.carol, [80n, 0n, 0n, 0n, 0n, 0n]);
  paid.total = paid.alice + paid.bob + paid.carol;
  return { ...m, paid };
}

/** Check that every buyer is refunded the exact cost basis and the sponsor gets the funding back. */
async function expectFullRefunds(m) {
  for (const who of ["alice", "bob", "carol"]) {
    await expect(m.market.connect(m[who]).claimRefund()).to.changeEtherBalance(m[who], m.paid[who]);
  }
  await expect(m.market.connect(m.sponsor).sponsorWithdraw()).to.changeEtherBalance(m.sponsor, m.value);
  expect(await balanceOf(m.market)).to.equal(0n);
  expect(await m.market.reserved()).to.equal(0n);
}

describe("13 SeasonCountOracle", function () {
  let oracle, owner, other, stranger, t0;
  beforeEach(async function () {
    [, owner, other, stranger] = await ethers.getSigners();
    oracle = await deploy("SeasonCountOracle", [], {}, owner);
    t0 = await now();
  });

  it("the deployer is owner and first reporter; currentTime() is the block time", async function () {
    expect(await oracle.owner()).to.equal(owner.address);
    expect(await oracle.isReporter(owner.address)).to.equal(true);
    expect(await oracle.isReporter(other.address)).to.equal(false);
    expect(await oracle.currentTime()).to.equal(BigInt(await now()));
  });

  it("openSeason: owner only, once per key, sane arguments, emits SeasonOpened", async function () {
    await expect(oracle.connect(stranger).openSeason(STATION, SEASON, t0 + 100, t0 + 200, 102)).to.be.revertedWith("Not owner");
    await expect(oracle.connect(owner).openSeason(STATION, SEASON, t0 + 200, t0 + 200, 102)).to.be.revertedWith("Start must be before end");
    await expect(oracle.connect(owner).openSeason(STATION, SEASON, t0 - 500, t0 - 100, 102)).to.be.revertedWith("Season end in the past");
    await expect(oracle.connect(owner).openSeason(STATION, SEASON, t0 + 100, t0 + 200, 0)).to.be.revertedWith("Season has no days");
    await expect(oracle.connect(owner).openSeason(STATION, SEASON, t0 + 100, t0 + 200, 102))
      .to.emit(oracle, "SeasonOpened").withArgs(STATION, SEASON, t0 + 100, t0 + 200, 102);
    await expect(oracle.connect(owner).openSeason(STATION, SEASON, t0 + 100, t0 + 900, 50)).to.be.revertedWith("Season already opened");
    const s = await oracle.getSeason(STATION, SEASON);
    expect([s.opened, Number(s.seasonStart), Number(s.seasonEnd), Number(s.seasonDays), s.reported, Number(s.count), Number(s.reportedAt)])
      .to.deep.equal([true, t0 + 100, t0 + 200, 102, false, 0, 0]);
    expect((await oracle.getSeason("PHL", SEASON)).opened).to.equal(false);
  });

  it("M3: a report before the season end is refused; the first second of the season end is accepted", async function () {
    await oracle.connect(owner).openSeason(STATION, SEASON, t0 + 100, t0 + 200, 102);
    await expect(oracle.connect(owner).reportCount(STATION, SEASON, 5)).to.be.revertedWith("Season not over");
    await setNextTime(t0 + 150); // mid-season
    await expect(oracle.connect(owner).reportCount(STATION, SEASON, 5)).to.be.revertedWith("Season not over");
    await setNextTime(t0 + 199);
    await expect(oracle.connect(owner).reportCount(STATION, SEASON, 5)).to.be.revertedWith("Season not over");
    expect((await oracle.getSeason(STATION, SEASON)).reported).to.equal(false);
    await setNextTime(t0 + 200);
    await expect(oracle.connect(owner).reportCount(STATION, SEASON, 5))
      .to.emit(oracle, "CountReported").withArgs(STATION, SEASON, 5, owner.address, t0 + 200);
    const s = await oracle.getSeason(STATION, SEASON);
    expect([s.reported, Number(s.count), Number(s.reportedAt)]).to.deep.equal([true, 5, t0 + 200]);
    const info = await oracle.reportInfo(STATION, SEASON);
    expect([info.reporter, info.wasReported, info.voided]).to.deep.equal([owner.address, true, false]);
  });

  it("unauthorised: a stranger can not report; only the owner can authorise or remove a reporter", async function () {
    await oracle.connect(owner).openSeason(STATION, SEASON, t0 + 100, t0 + 200, 102);
    await setTime(t0 + 300);
    await expect(oracle.connect(stranger).reportCount(STATION, SEASON, 5)).to.be.revertedWith("Not an authorised reporter");
    await expect(oracle.connect(stranger).setReporter(stranger.address, true)).to.be.revertedWith("Not owner");
    await expect(oracle.connect(owner).setReporter(other.address, true)).to.emit(oracle, "ReporterSet").withArgs(other.address, true);
    await oracle.connect(owner).setReporter(other.address, false);
    await expect(oracle.connect(other).reportCount(STATION, SEASON, 5)).to.be.revertedWith("Not an authorised reporter");
    await oracle.connect(owner).setReporter(other.address, true);
    await oracle.connect(other).reportCount(STATION, SEASON, 5);
    expect((await oracle.reportInfo(STATION, SEASON)).reporter).to.equal(other.address);
  });

  it("duplicate: a second report for the same key is refused, even with the same value", async function () {
    await oracle.connect(owner).openSeason(STATION, SEASON, t0 + 100, t0 + 200, 102);
    await setTime(t0 + 300);
    await oracle.connect(owner).reportCount(STATION, SEASON, 5);
    await expect(oracle.connect(owner).reportCount(STATION, SEASON, 5)).to.be.revertedWith("Already reported");
    await expect(oracle.connect(owner).reportCount(STATION, SEASON, 6)).to.be.revertedWith("Already reported");
    expect((await oracle.getSeason(STATION, SEASON)).count).to.equal(5n);
  });

  it("range: counts 0 and seasonDays are accepted, seasonDays + 1 is refused; an unopened season is refused", async function () {
    await oracle.connect(owner).openSeason(STATION, SEASON, t0 + 100, t0 + 200, 102);
    await oracle.connect(owner).openSeason("PHL", SEASON, t0 + 100, t0 + 200, 102);
    await oracle.connect(owner).openSeason("ABE", SEASON, t0 + 100, t0 + 200, 102);
    await setTime(t0 + 300);
    await expect(oracle.connect(owner).reportCount(STATION, SEASON, 103)).to.be.revertedWith("Count above season days");
    await expect(oracle.connect(owner).reportCount(STATION, SEASON, 65535)).to.be.revertedWith("Count above season days");
    await oracle.connect(owner).reportCount(STATION, SEASON, 102);
    await oracle.connect(owner).reportCount("PHL", SEASON, 0);
    await expect(oracle.connect(owner).reportCount("EWR", SEASON, 5)).to.be.revertedWith("Season not opened");
    await expect(oracle.connect(owner).reportCount(STATION, SEASON + 1, 5)).to.be.revertedWith("Season not opened");
    // keys are separate per station and per season
    expect((await oracle.getSeason(STATION, SEASON)).count).to.equal(102n);
    expect((await oracle.getSeason("PHL", SEASON)).reported).to.equal(true);
    expect((await oracle.getSeason("ABE", SEASON)).reported).to.equal(false);
  });

  it("voidReport: owner only, needs a report, final, and the season can not be reported again", async function () {
    await oracle.connect(owner).openSeason(STATION, SEASON, t0 + 100, t0 + 200, 102);
    await oracle.connect(owner).setReporter(other.address, true);
    await setTime(t0 + 300);
    await expect(oracle.connect(owner).voidReport(STATION, SEASON)).to.be.revertedWith("No report");
    await oracle.connect(other).reportCount(STATION, SEASON, 9);
    await expect(oracle.connect(other).voidReport(STATION, SEASON)).to.be.revertedWith("Not owner");
    await expect(oracle.connect(owner).voidReport(STATION, SEASON)).to.emit(oracle, "ReportVoided").withArgs(STATION, SEASON, 9, owner.address);
    const s = await oracle.getSeason(STATION, SEASON);
    expect([s.opened, s.reported, Number(s.count), Number(s.reportedAt)]).to.deep.equal([true, false, 0, 0]);
    expect((await oracle.reportInfo(STATION, SEASON)).voided).to.equal(true);
    await expect(oracle.connect(owner).voidReport(STATION, SEASON)).to.be.revertedWith("Already voided");
    await expect(oracle.connect(other).reportCount(STATION, SEASON, 5)).to.be.revertedWith("Already reported");
  });
});

describe("13 settlement with the real oracle (on-time report)", function () {
  it("settles once, pays winners 1 unit per share, the sponsor takes the rest, the balance ends at 0", async function () {
    const m = await withBuyers({ real: true });
    await expect(m.market.settle()).to.be.revertedWith("No valid report"); // nothing reported yet
    expect(await m.market.hasValidReport()).to.equal(false);
    await setNextTime(m.seasonEnd + 10);
    await m.oracle.connect(m.reporter).reportCount(STATION, SEASON, 9); // bucket 4 (9-10)
    expect(await m.market.hasValidReport()).to.equal(true);
    const pool = await balanceOf(m.market);
    const owed = 200n * m.unit; // alice holds 200 shares of bucket 4
    await setNextTime(m.seasonEnd + 20);
    await expect(m.market.connect(m.stranger).settle())
      .to.emit(m.market, "Settled").withArgs(9, 4n, m.seasonEnd + 10, owed, m.seasonEnd + 20 + CLAIM_PERIOD);
    expect(await m.market.state()).to.equal(1n);
    expect(await m.market.settledCount()).to.equal(9n);
    expect(await m.market.winningBucket()).to.equal(4n);
    expect(await m.market.reserved()).to.equal(owed);
    expect(await m.market.claimDeadline()).to.equal(BigInt(m.seasonEnd + 20 + CLAIM_PERIOD));

    const r = m.market.connect(m.alice).redeem();
    await expect(r).to.emit(m.market, "Redeemed").withArgs(m.alice.address, 200n, owed);
    await expect(r).to.changeEtherBalances([m.alice, m.market], [owed, -owed]);
    // redeem twice is refused; losers have nothing to redeem
    await expect(m.market.connect(m.alice).redeem()).to.be.revertedWith("Nothing to redeem");
    await expect(m.market.connect(m.bob).redeem()).to.be.revertedWith("Nothing to redeem");
    await expect(m.market.connect(m.stranger).redeem()).to.be.revertedWith("Nothing to redeem");

    const leftover = pool - owed;
    await expect(m.market.connect(m.alice).sponsorWithdraw()).to.be.revertedWith("Not sponsor");
    const w = m.market.connect(m.sponsor).sponsorWithdraw();
    await expect(w).to.emit(m.market, "SponsorWithdrawal").withArgs(m.sponsor.address, leftover);
    await expect(w).to.changeEtherBalance(m.sponsor, leftover);
    await expect(m.market.connect(m.sponsor).sponsorWithdraw()).to.be.revertedWith("Nothing to withdraw");
    expect(await balanceOf(m.market)).to.equal(0n);
    // sponsor result = paid by buyers - payout
    expect(leftover - m.value).to.equal(m.paid.total - owed);
  });

  it("stepped payout: a holder of 1, 2, 3 units of the top three buckets gets the right amount for every count 0..102", async function () {
    const m = await deployRain(); // mock oracle, so each count can be tried from one snapshot
    const v = [0n, 0n, 0n, 1n, 2n, 3n];
    const c = await m.market.quoteBasket(v);
    await m.market.connect(m.alice).buyBasket(v, c, { value: c });
    await m.market.connect(m.bob).buyBasket([5n, 5n, 5n, 5n, 5n, 5n], MAX, { value: E18 });
    await setTime(m.seasonEnd + 1);
    const seen = {};
    for (let count = 0; count <= SEASON_DAYS; count++) {
      const id = await snapshot();
      await m.oracle.setReport(STATION, SEASON, count);
      await m.market.settle();
      // expected steps for edges [2,4,6,8,10]: 0 for 0-6, 1 for 7-8, 2 for 9-10, 3 for 11+
      const want = count <= 6 ? 0n : count <= 8 ? 1n : count <= 10 ? 2n : 3n;
      expect(want).to.equal(v[bucketOf(count)]);
      if (want === 0n) {
        await expect(m.market.connect(m.alice).redeem(), `count ${count}`).to.be.revertedWith("Nothing to redeem");
      } else {
        await expect(m.market.connect(m.alice).redeem(), `count ${count}`).to.changeEtherBalance(m.alice, want * m.unit);
      }
      // the other buyer holds 5 of every bucket and always gets 5 units; then nothing is owed
      await expect(m.market.connect(m.bob).redeem()).to.changeEtherBalance(m.bob, 5n * m.unit);
      expect(await m.market.reserved()).to.equal(0n);
      seen[want] = (seen[want] || 0) + 1;
      await revertTo(id);
    }
    expect(seen).to.deep.equal({ 0: 7, 1: 2, 2: 2, 3: 92 });
  });

  it("settles in the right bucket at every bucket edge (2/3, 4/5, 6/7, 8/9, 10/11), at 0 and at the maximum", async function () {
    const m = await deployRain();
    await m.market.connect(m.alice).buyBasket([1n, 2n, 3n, 4n, 5n, 6n], MAX, { value: E18 });
    await setTime(m.seasonEnd + 1);
    const cases = [[0, 0], [2, 0], [3, 1], [4, 1], [5, 2], [6, 2], [7, 3], [8, 3], [9, 4], [10, 4], [11, 5], [SEASON_DAYS, 5]];
    for (const [count, bucket] of cases) {
      const id = await snapshot();
      await m.oracle.setReport(STATION, SEASON, count);
      await m.market.settle();
      expect(await m.market.winningBucket(), `count ${count}`).to.equal(BigInt(bucket));
      expect(await m.market.settledCount()).to.equal(BigInt(count));
      expect(await m.market.reserved()).to.equal(BigInt(bucket + 1) * m.unit);
      await expect(m.market.connect(m.alice).redeem()).to.changeEtherBalance(m.alice, BigInt(bucket + 1) * m.unit);
      await revertTo(id);
    }
  });

  it("a report made exactly at the season end or exactly at the deadline is valid", async function () {
    for (const at of ["seasonEnd", "reportDeadline"]) {
      const m = await withBuyers({ real: true });
      await setNextTime(m[at]);
      await m.oracle.connect(m.reporter).reportCount(STATION, SEASON, 11);
      await m.market.settle();
      expect(await m.market.winningBucket()).to.equal(5n);
    }
  });

  it("an on-time report can still be settled after the deadline, and then a cancel is refused", async function () {
    const m = await withBuyers({ real: true });
    await setNextTime(m.seasonEnd + 5);
    await m.oracle.connect(m.reporter).reportCount(STATION, SEASON, 7);
    await setTime(m.reportDeadline + 500);
    await expect(m.market.cancelAfterDeadline()).to.be.revertedWith("Valid report exists, call settle");
    await m.market.settle();
    await expect(m.market.cancelAfterDeadline()).to.be.revertedWith("Not open");
  });

  it("after settlement: a second settle, buys, cancels and refunds are all refused", async function () {
    const m = await withBuyers({ real: true });
    await setNextTime(m.seasonEnd + 5);
    await m.oracle.connect(m.reporter).reportCount(STATION, SEASON, 7);
    await m.market.settle();
    await expect(m.market.settle()).to.be.revertedWith("Not open");
    await expect(m.market.connect(m.alice).buy(0, 1, MAX, { value: E18 })).to.be.revertedWith("Not open");
    await expect(m.market.connect(m.alice).buyBasket([1, 1, 1, 1, 1, 1], MAX, { value: E18 })).to.be.revertedWith("Not open");
    await expect(m.market.connect(m.sponsor).emergencyCancel()).to.be.revertedWith("Not open");
    await expect(m.market.connect(m.alice).claimRefund()).to.be.revertedWith("Not cancelled");
  });

  it("while the market is open: redeem, refund, withdraw and sweep are refused", async function () {
    const m = await withBuyers({ real: true });
    await expect(m.market.connect(m.alice).redeem()).to.be.revertedWith("Not settled");
    await expect(m.market.connect(m.alice).claimRefund()).to.be.revertedWith("Not cancelled");
    await expect(m.market.connect(m.sponsor).sponsorWithdraw()).to.be.revertedWith("Market still open");
    await expect(m.market.connect(m.sponsor).sweepUnclaimed()).to.be.revertedWith("Market still open");
  });
});

describe("13 oracle paths that end in a cancel", function () {
  it("M3: with the real oracle a premature report is impossible, so the season can still settle later", async function () {
    const m = await withBuyers({ real: true });
    await setNextTime(m.seasonStart + 100); // somebody clicks "report" in mid-season
    await expect(m.oracle.connect(m.reporter).reportCount(STATION, SEASON, 3)).to.be.revertedWith("Season not over");
    await setNextTime(m.seasonEnd - 1);
    await expect(m.oracle.connect(m.reporter).reportCount(STATION, SEASON, 3)).to.be.revertedWith("Season not over");
    await expect(m.market.settle()).to.be.revertedWith("No valid report");
    await setNextTime(m.seasonEnd + 60);
    await m.oracle.connect(m.reporter).reportCount(STATION, SEASON, 8);
    await m.market.settle();
    expect(await m.market.winningBucket()).to.equal(3n);
  });

  it("a report stamped before the season end (only a faulty oracle can produce one) never settles; cancel after the deadline", async function () {
    const m = await withBuyers();
    await m.oracle.setReportAt(STATION, SEASON, 9, m.seasonEnd - 1);
    await setTime(m.seasonEnd + 10);
    expect(await m.market.hasValidReport()).to.equal(false);
    await expect(m.market.settle()).to.be.revertedWith("No valid report");
    await expect(m.market.cancelAfterDeadline()).to.be.revertedWith("Deadline not passed");
    await setTime(m.reportDeadline + 1);
    await m.market.cancelAfterDeadline();
    await expectFullRefunds(m);
  });

  it("missing report: nobody can cancel at the deadline second; one second later anyone can; refunds are the exact cost basis", async function () {
    const m = await withBuyers({ real: true });
    await setNextTime(m.reportDeadline);
    await expect(m.market.connect(m.stranger).cancelAfterDeadline()).to.be.revertedWith("Deadline not passed");
    await setNextTime(m.reportDeadline + 1);
    await expect(m.market.connect(m.stranger).cancelAfterDeadline())
      .to.emit(m.market, "Cancelled")
      .withArgs(m.stranger.address, "No valid report by deadline", m.paid.total, m.reportDeadline + 1 + CLAIM_PERIOD);
    expect(await m.market.state()).to.equal(2n);
    expect(await m.market.reserved()).to.equal(m.paid.total);
    await expect(m.market.settle()).to.be.revertedWith("Not open");
    await expect(m.market.connect(m.alice).redeem()).to.be.revertedWith("Not settled");
    const r = m.market.connect(m.alice).claimRefund();
    await expect(r).to.emit(m.market, "Refunded").withArgs(m.alice.address, m.paid.alice);
    await expect(r).to.changeEtherBalance(m.alice, m.paid.alice);
    await expect(m.market.connect(m.alice).claimRefund()).to.be.revertedWith("Nothing to refund");
    await expect(m.market.connect(m.stranger).claimRefund()).to.be.revertedWith("Nothing to refund");
    // the sponsor can withdraw before the others claim, and only the funding
    await expect(m.market.connect(m.sponsor).sponsorWithdraw()).to.changeEtherBalance(m.sponsor, m.value);
    await expect(m.market.connect(m.bob).claimRefund()).to.changeEtherBalance(m.bob, m.paid.bob);
    await expect(m.market.connect(m.carol).claimRefund()).to.changeEtherBalance(m.carol, m.paid.carol);
    expect(await balanceOf(m.market)).to.equal(0n);
  });

  it("late report (real oracle, after the deadline): settle refuses it, cancel and refunds work", async function () {
    const m = await withBuyers({ real: true });
    await setNextTime(m.reportDeadline + 1);
    await m.oracle.connect(m.reporter).reportCount(STATION, SEASON, 9); // the oracle accepts it, the market does not
    expect(await m.market.hasValidReport()).to.equal(false);
    await expect(m.market.settle()).to.be.revertedWith("No valid report");
    await m.market.connect(m.stranger).cancelAfterDeadline();
    await expectFullRefunds(m);
  });

  it("a report after a cancel can not settle the market", async function () {
    const m = await withBuyers({ real: true });
    await setTime(m.reportDeadline + 1);
    await m.market.cancelAfterDeadline();
    await m.oracle.connect(m.reporter).reportCount(STATION, SEASON, 9);
    await expect(m.market.settle()).to.be.revertedWith("Not open");
  });

  it("wrong key: reports for another station or season never settle this market", async function () {
    const m = await withBuyers({ real: true });
    await m.oracle.connect(m.reporter).openSeason("PHL", SEASON, m.seasonStart, m.seasonEnd, SEASON_DAYS);
    await m.oracle.connect(m.reporter).openSeason(STATION, SEASON + 1, m.seasonStart, m.seasonEnd, SEASON_DAYS);
    await setTime(m.seasonEnd + 5);
    await m.oracle.connect(m.reporter).reportCount("PHL", SEASON, 9);
    await m.oracle.connect(m.reporter).reportCount(STATION, SEASON + 1, 9);
    await expect(m.market.settle()).to.be.revertedWith("No valid report");
    await setTime(m.reportDeadline + 1);
    await m.market.cancelAfterDeadline();
    await expectFullRefunds(m);
  });

  it("an impossible count (above the season days, from a faulty oracle) is not a valid report", async function () {
    const m = await withBuyers();
    await setTime(m.seasonEnd + 5);
    await m.oracle.setReport(STATION, SEASON, SEASON_DAYS + 1);
    await expect(m.market.settle()).to.be.revertedWith("No valid report");
    await m.oracle.setReport(STATION, SEASON, SEASON_DAYS); // the largest possible count is fine
    expect(await m.market.hasValidReport()).to.equal(true);
    await m.oracle.setReport(STATION, SEASON, 65535);
    await setTime(m.reportDeadline + 1);
    await m.market.cancelAfterDeadline();
    await expectFullRefunds(m);
  });

  it("mock oracle: a report that changes after settlement has no effect (settlement happens once)", async function () {
    const m = await withBuyers();
    await setTime(m.seasonEnd + 5);
    await m.oracle.setReport(STATION, SEASON, 9);
    await m.market.settle();
    await m.oracle.setReport(STATION, SEASON, 0);
    expect(await m.market.winningBucket()).to.equal(4n);
    await expect(m.market.connect(m.carol).redeem()).to.be.revertedWith("Nothing to redeem");
    await expect(m.market.connect(m.alice).redeem()).to.changeEtherBalance(m.alice, 200n * m.unit);
  });
});

describe("13 dispute delay (review M2: disclosed, with an optional window)", function () {
  it("delay 0: settle works in the block right after the report", async function () {
    const m = await withBuyers({ real: true, disputeDelay: 0 });
    await setNextTime(m.seasonEnd + 5);
    await m.oracle.connect(m.reporter).reportCount(STATION, SEASON, 9);
    await setNextTime(m.seasonEnd + 6); // the next block, one second later
    await m.market.settle();
  });

  it("delay of 1 day: settle is refused until reportedAt + delay, to the second", async function () {
    const t = await now();
    const m = await withBuyers({ real: true, disputeDelay: DAYS, reportDeadline: t + 2000 + 10 * DAYS });
    expect(await m.market.disputeDelay()).to.equal(BigInt(DAYS));
    const at = m.seasonEnd + 100;
    await setNextTime(at);
    await m.oracle.connect(m.reporter).reportCount(STATION, SEASON, 9);
    await expect(m.market.settle()).to.be.revertedWith("Dispute window still open");
    await setNextTime(at + DAYS - 1);
    await expect(m.market.settle()).to.be.revertedWith("Dispute window still open");
    await setNextTime(at + DAYS);
    await expect(m.market.settle()).to.emit(m.market, "Settled").withArgs(9, 4n, at, 200n * m.unit, at + DAYS + CLAIM_PERIOD);
  });

  it("a wrong report voided by the oracle owner inside the window does not settle; buyers are refunded after the deadline", async function () {
    const t = await now();
    const m = await withBuyers({ real: true, disputeDelay: DAYS, reportDeadline: t + 2000 + 3 * DAYS });
    await setNextTime(m.seasonEnd + 100);
    await m.oracle.connect(m.reporter).reportCount(STATION, SEASON, 0); // wrong count
    await expect(m.market.settle()).to.be.revertedWith("Dispute window still open");
    await m.oracle.connect(m.reporter).voidReport(STATION, SEASON); // owner (here the same test account) voids it
    await setTime(m.seasonEnd + 100 + DAYS + 1);
    await expect(m.market.settle()).to.be.revertedWith("No valid report");
    await expect(m.market.cancelAfterDeadline()).to.be.revertedWith("Deadline not passed");
    await setTime(m.reportDeadline + 1);
    await m.market.cancelAfterDeadline();
    await expectFullRefunds(m);
  });

  it("without a void, the wrong report settles after the window: one reporter decides (this is the disclosed limit)", async function () {
    const t = await now();
    const m = await withBuyers({ real: true, disputeDelay: DAYS, reportDeadline: t + 2000 + 3 * DAYS });
    await setNextTime(m.seasonEnd + 100);
    await m.oracle.connect(m.reporter).reportCount(STATION, SEASON, 0); // wrong, and nobody voids it
    await setTime(m.seasonEnd + 100 + DAYS);
    await m.market.settle();
    expect(await m.market.winningBucket()).to.equal(0n);
    // a void after settlement changes nothing
    await m.oracle.connect(m.reporter).voidReport(STATION, SEASON);
    expect(await m.market.state()).to.equal(1n);
    await expect(m.market.connect(m.carol).redeem()).to.changeEtherBalance(m.carol, 80n * m.unit);
  });

  it("a window that runs past the report deadline: no cancel while the valid report stands, settle when the window ends", async function () {
    const m = await withBuyers({ real: true, disputeDelay: DAYS }); // deadline is seasonEnd + 1000 s
    await setNextTime(m.reportDeadline - 10);
    await m.oracle.connect(m.reporter).reportCount(STATION, SEASON, 12);
    await setTime(m.reportDeadline + 100);
    await expect(m.market.settle()).to.be.revertedWith("Dispute window still open");
    await expect(m.market.cancelAfterDeadline()).to.be.revertedWith("Valid report exists, call settle");
    await setTime(m.reportDeadline - 10 + DAYS);
    await m.market.settle();
    expect(await m.market.winningBucket()).to.equal(5n);
  });
});

describe("13 review M1: a wrong oracle address can not lock funds", function () {
  it("REPRODUCTION on the earlier BracketLMSR: oracle = EOA, empty-fallback contract, one-word contract. Funds are stuck", async function () {
    const signers = await ethers.getSigners();
    const targets = {
      "EOA": signers[9].address,
      "empty fallback": await (await deploy("EmptyFallbackOracle")).getAddress(),
      "one word": await (await deploy("OneWordOracle")).getAddress(),
    };
    for (const [name, address] of Object.entries(targets)) {
      const m = await deployMarket({ oracle: { getAddress: async () => address } }); // the old constructor accepts it
      await m.market.connect(signers[2]).buy(6, 100, MAX, { value: E18 });
      const locked = await balanceOf(m.market);
      expect(locked).to.be.gt(m.value);
      await setTime(m.reportDeadline + 100);
      await expect(m.market.settle(), name).to.be.reverted;
      await expect(m.market.cancelAfterDeadline(), name).to.be.reverted;
      await expect(m.market.emergencyCancel(), name).to.be.revertedWith("Trading closed, wait for the oracle");
      expect(await m.market.state()).to.equal(0n); // still Open, for ever
      expect(await balanceOf(m.market)).to.equal(locked);
    }
  });

  it("FIX at deployment: the new constructor refuses an EOA, the zero address, an empty-fallback contract and a one-word contract", async function () {
    const signers = await ethers.getSigners();
    const mock = await deploy("MockCountOracle");
    await expect(deployRain({ oracle: mock, oracleAddress: signers[9].address })).to.be.revertedWith("Oracle has no code");
    await expect(deployRain({ oracle: mock, oracleAddress: ethers.ZeroAddress })).to.be.revertedWith("Oracle has no code");
    const empty = await deploy("EmptyFallbackOracle");
    await expect(deployRain({ oracle: empty })).to.be.revertedWith("Oracle read failed");
    const oneWord = await deploy("OneWordOracle");
    await expect(deployRain({ oracle: oneWord })).to.be.revertedWith("Oracle read failed");
    // a different contract with code but no getSeason (here: the temperature oracle) reverts on the read
    const other = await deploy("TemperatureOracle");
    await expect(deployRain({ oracle: other })).to.be.revertedWith("Oracle read failed");
  });

  it("FIX at deployment: the season must be opened and not yet reported; a misbehaving oracle is refused in every mode", async function () {
    await expect(deployRain({ open: false })).to.be.revertedWith("Season not opened in oracle");
    await expect(deployRain({ real: true, open: false })).to.be.revertedWith("Season not opened in oracle");
    const t = await now();
    const times = { tradingClose: t + 900, reportDeadline: t + 3000 };
    const mock = await deploy("MockCountOracle");
    await mock.openSeason(STATION, SEASON, t + 1000, t + 2000, SEASON_DAYS);
    await mock.setReport(STATION, SEASON, 4);
    await expect(deployRain({ oracle: mock, ...times })).to.be.revertedWith("Season already reported");
    await mock.clearReport(STATION, SEASON);
    for (let mode = 1; mode <= 6; mode++) {
      await mock.setMode(mode);
      await expect(deployRain({ oracle: mock, ...times }), `mode ${mode}`).to.be.revertedWith("Oracle read failed");
    }
    await mock.setMode(0);
    await mock.openSeason(STATION, SEASON, t + 2000, t + 1000, SEASON_DAYS); // start after end
    await expect(deployRain({ oracle: mock, ...times })).to.be.revertedWith("Bad season in oracle");
    await mock.openSeason(STATION, SEASON, t + 1000, t + 2000, 0);
    await expect(deployRain({ oracle: mock, ...times })).to.be.revertedWith("Bad season in oracle");
    await mock.openSeason(STATION, SEASON, t + 1000, t + 2000, SEASON_DAYS);
    await deployRain({ oracle: mock, ...times }); // and a sane season is accepted
  });

  const modes = { 1: "reverts", 2: "returns nothing", 3: "returns one word (too short)", 4: "returns eight words (too long)",
    5: "returns seven words of 0xff (impossible values)", 6: "burns all its gas" };
  for (const [mode, label] of Object.entries(modes)) {
    it(`FIX at run time: an oracle that ${label} can not settle and can not block the refund`, async function () {
      const m = await withBuyers();
      await setTime(m.seasonEnd + 5);
      await m.oracle.setReport(STATION, SEASON, 9);
      await m.oracle.setMode(Number(mode));
      expect(await m.market.hasValidReport()).to.equal(false);
      await expect(m.market.settle()).to.be.revertedWith("No valid report");
      await expect(m.market.cancelAfterDeadline()).to.be.revertedWith("Deadline not passed");
      await setTime(m.reportDeadline + 1);
      await expect(m.market.connect(m.stranger).cancelAfterDeadline()).to.emit(m.market, "Cancelled");
      await expectFullRefunds(m);
    });
  }

  it("an oracle that fails for a while and then answers again before settlement still settles", async function () {
    const m = await withBuyers();
    await setTime(m.seasonEnd + 5);
    await m.oracle.setReport(STATION, SEASON, 9);
    await m.oracle.setMode(1);
    await expect(m.market.settle()).to.be.revertedWith("No valid report");
    await m.oracle.setMode(0);
    await m.market.settle();
    expect(await m.market.winningBucket()).to.equal(4n);
  });

  it("gas starvation: a caller can not make a good oracle look broken by sending little gas", async function () {
    const m = await withBuyers({ real: true });
    await setNextTime(m.seasonEnd + 5);
    await m.oracle.connect(m.reporter).reportCount(STATION, SEASON, 9);
    await setTime(m.reportDeadline + 1);
    // every gas limit from 30,000 to 300,000 in steps of 3,000: the cancel must fail each time
    for (let gasLimit = 30000; gasLimit <= 300000; gasLimit += 3000) {
      let ok = true;
      try {
        await (await m.market.connect(m.sponsor).cancelAfterDeadline({ gasLimit })).wait();
      } catch (e) {
        ok = false;
      }
      expect(ok, `gas ${gasLimit}`).to.equal(false);
    }
    expect(await m.market.state()).to.equal(0n);
    await expect(m.market.connect(m.sponsor).cancelAfterDeadline({ gasLimit: 300000 })).to.be.revertedWith("Valid report exists, call settle");
    await expect(m.market.connect(m.sponsor).cancelAfterDeadline({ gasLimit: 100000 })).to.be.revertedWith("Send more gas");
    await m.market.settle();
    expect(await m.market.state()).to.equal(1n);
  });
});

describe("13 emergency cancel by the sponsor", function () {
  it("only the sponsor can cancel; trading stops; refunds are the exact cost basis; the sponsor gets the funding back", async function () {
    const m = await withBuyers({ real: true });
    await expect(m.market.connect(m.alice).emergencyCancel()).to.be.revertedWith("Not sponsor");
    const t = (await now()) + 5;
    await setNextTime(t);
    await expect(m.market.connect(m.sponsor).emergencyCancel())
      .to.emit(m.market, "Cancelled").withArgs(m.sponsor.address, "Emergency cancel by sponsor", m.paid.total, t + CLAIM_PERIOD);
    await expect(m.market.connect(m.alice).buy(0, 1, MAX, { value: E18 })).to.be.revertedWith("Not open");
    await expect(m.market.connect(m.sponsor).emergencyCancel()).to.be.revertedWith("Not open");
    await expectFullRefunds(m);
  });

  it("the sponsor can not cancel once trading has closed (which is at or before the first season day)", async function () {
    const m = await withBuyers({ real: true });
    await setNextTime(m.tradingClose);
    await expect(m.market.connect(m.sponsor).emergencyCancel()).to.be.revertedWith("Trading closed, wait for the oracle");
    await setNextTime(m.seasonEnd + 1);
    await expect(m.market.connect(m.sponsor).emergencyCancel()).to.be.revertedWith("Trading closed, wait for the oracle");
  });
});

describe("13 unclaimed funds (review m5)", function () {
  it("after settlement: no sweep before the claim deadline; after it the sponsor takes what is left and late claims are refused", async function () {
    const m = await withBuyers();
    await m.market.connect(m.bob).buy(4, 50, MAX, { value: E18 }); // a second winner
    await setTime(m.seasonEnd + 5);
    await m.oracle.setReport(STATION, SEASON, 10);
    await m.market.settle();
    const deadline = Number(await m.market.claimDeadline());
    await m.market.connect(m.bob).redeem(); // bob claims in time, alice never does
    await m.market.connect(m.sponsor).sponsorWithdraw();
    const left = await balanceOf(m.market);
    expect(left).to.equal(200n * m.unit);
    await expect(m.market.connect(m.alice).sweepUnclaimed()).to.be.revertedWith("Not sponsor");
    await setNextTime(deadline);
    await expect(m.market.connect(m.sponsor).sweepUnclaimed()).to.be.revertedWith("Claim period not over");
    await setNextTime(deadline + 1);
    const s = m.market.connect(m.sponsor).sweepUnclaimed();
    await expect(s).to.emit(m.market, "UnclaimedSwept").withArgs(m.sponsor.address, left);
    await expect(s).to.changeEtherBalance(m.sponsor, left);
    expect(await m.market.swept()).to.equal(true);
    expect(await m.market.reserved()).to.equal(0n);
    expect(await balanceOf(m.market)).to.equal(0n);
    await expect(m.market.connect(m.alice).redeem()).to.be.revertedWith("Unclaimed funds were swept");
    await expect(m.market.connect(m.sponsor).sweepUnclaimed()).to.be.revertedWith("Already swept");
  });

  it("a winner who claims on the last second of the claim period is still paid", async function () {
    const m = await withBuyers();
    await setTime(m.seasonEnd + 5);
    await m.oracle.setReport(STATION, SEASON, 10);
    await m.market.settle();
    await setNextTime(Number(await m.market.claimDeadline()) + 500); // late, but nobody swept yet
    await expect(m.market.connect(m.alice).redeem()).to.changeEtherBalance(m.alice, 200n * m.unit);
  });

  it("after a cancel: unclaimed refunds can be swept only after the claim period", async function () {
    const m = await withBuyers();
    await m.market.connect(m.sponsor).emergencyCancel();
    await m.market.connect(m.alice).claimRefund();
    await expect(m.market.connect(m.sponsor).sweepUnclaimed()).to.be.revertedWith("Claim period not over");
    await setTime(Number(await m.market.claimDeadline()) + 1);
    await expect(m.market.connect(m.sponsor).sweepUnclaimed()).to.changeEtherBalance(m.sponsor, m.value + m.paid.bob + m.paid.carol);
    await expect(m.market.connect(m.bob).claimRefund()).to.be.revertedWith("Unclaimed funds were swept");
  });

  it("a winner contract that can not receive ETH does not block the other winners or the sponsor; its payout is swept later", async function () {
    const m = await deployRain();
    const rej = await deploy("RejectingTrader", [await m.market.getAddress()]);
    const c1 = await m.market.quoteBuy(5, 40);
    await rej.buyExact(5, 40, { value: c1 });
    await m.market.connect(m.alice).buy(5, 60, MAX, { value: E18 });
    await setTime(m.seasonEnd + 5);
    await m.oracle.setReport(STATION, SEASON, 20);
    await m.market.settle();
    await expect(rej.redeem()).to.be.revertedWith("Transfer failed");
    await expect(m.market.connect(m.alice).redeem()).to.changeEtherBalance(m.alice, 60n * m.unit);
    await m.market.connect(m.sponsor).sponsorWithdraw();
    expect(await balanceOf(m.market)).to.equal(40n * m.unit); // still reserved for the contract
    await setTime(Number(await m.market.claimDeadline()) + 1);
    await expect(m.market.connect(m.sponsor).sweepUnclaimed()).to.changeEtherBalance(m.sponsor, 40n * m.unit);
    expect(await balanceOf(m.market)).to.equal(0n);
  });
});

describe("13 reentrancy", function () {
  it("a contract that re-enters redeem() is paid once", async function () {
    const m = await deployRain();
    const bad = await deploy("ReentrantTrader", [await m.market.getAddress()]);
    await bad.buy(5, 100, { value: E18 });
    await bad.setMode(0);
    await m.market.connect(m.alice).buy(5, 100, MAX, { value: E18 });
    await setTime(m.seasonEnd + 5);
    await m.oracle.setReport(STATION, SEASON, 30);
    await m.market.settle();
    await bad.setMode(1);
    const before = await balanceOf(bad);
    await bad.redeem();
    expect((await balanceOf(bad)) - before).to.equal(100n * m.unit);
    expect(await bad.attempts()).to.equal(1n);
    expect(await bad.reentrySucceeded()).to.equal(false);
    await expect(m.market.connect(m.alice).redeem()).to.changeEtherBalance(m.alice, 100n * m.unit);
  });

  it("a contract that re-enters claimRefund() is refunded once", async function () {
    const m = await deployRain();
    const bad = await deploy("ReentrantTrader", [await m.market.getAddress()]);
    await bad.buy(5, 100, { value: E18 });
    const paid = await m.market.paid(await bad.getAddress());
    await m.market.connect(m.alice).buy(2, 100, MAX, { value: E18 });
    await m.market.connect(m.sponsor).emergencyCancel();
    await bad.setMode(2);
    const before = await balanceOf(bad);
    await bad.claimRefund();
    expect((await balanceOf(bad)) - before).to.equal(paid);
    expect(await bad.reentrySucceeded()).to.equal(false);
    expect(await m.market.reserved()).to.equal(await m.market.paid(m.alice.address));
  });

  it("a contract that re-enters buy() from the excess refund is blocked", async function () {
    const m = await deployRain();
    const bad = await deploy("ReentrantTrader", [await m.market.getAddress()]);
    await bad.setMode(3);
    await bad.buy(5, 100, { value: E18 }); // the excess comes back and triggers the re-entry attempt
    expect(await bad.attempts()).to.equal(1n);
    expect(await bad.reentrySucceeded()).to.equal(false);
    expect((await m.market.getQuantities()).map(Number)).to.deep.equal([0, 0, 0, 0, 0, 100]);
  });
});
