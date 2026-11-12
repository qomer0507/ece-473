// Gas per function of RainCountLMSR and SeasonCountOracle. This file measures everything
// itself, so it passes when run alone:  npx hardhat test --no-compile test/15_rain_gas.test.js
// Gas is measured in the local Hardhat EVM (Cancun rules, solc 0.8.26, optimizer 200 runs).
// It was NOT measured on Sepolia. The same call in the same state costs the same gas there.
const fs = require("fs");
const path = require("path");
const { expect } = require("chai");
const { ethers, deployRain, deploy, artifact, setTime, setNextTime, now, safeFunding, STATION, SEASON, SEASON_DAYS, EDGES, CLAIM_PERIOD } = require("./rain_helpers");

const MAX = ethers.MaxUint256;
const E18 = 10n ** 18n;
const STEPPED = [0n, 0n, 0n, 1n, 2n, 3n];

describe("15 rain gas report (self-contained)", function () {
  const log = {};
  async function gas(label, promise) {
    const receipt = await (await promise).wait();
    (log[label] = log[label] || []).push(Number(receipt.gasUsed));
    return receipt;
  }

  it("measures one full life cycle, both cancel paths and the sweep", async function () {
    const signers = await ethers.getSigners();
    const [sponsor, reporter, alice, bob, carol, dave] = signers;

    // --- deployment, exactly as in docs/deploy_sepolia.md: oracle, openSeason, market ---
    const t0 = await now();
    const f = new ethers.ContractFactory(artifact("SeasonCountOracle").abi, artifact("SeasonCountOracle").bytecode, reporter);
    const oracle = await f.deploy();
    log["deploy SeasonCountOracle"] = [Number((await oracle.deploymentTransaction().wait()).gasUsed)];
    await gas("oracle.openSeason", oracle.openSeason(STATION, SEASON, t0 + 1000, t0 + 2000, SEASON_DAYS));
    await gas("oracle.setReporter", oracle.setReporter(dave.address, true));
    const b = 100n, unit = 10n ** 14n;
    const mf = new ethers.ContractFactory(artifact("RainCountLMSR").abi, artifact("RainCountLMSR").bytecode, sponsor);
    const market = await mf.deploy(await oracle.getAddress(), STATION, SEASON, EDGES, b, unit, t0 + 1000, t0 + 3000, 0, CLAIM_PERIOD,
      { value: safeFunding(b, unit) });
    log["deploy RainCountLMSR"] = [Number((await market.deploymentTransaction().wait()).gasUsed)];

    // --- trading ---
    await gas("buy (one bucket, first buy of this buyer)", market.connect(alice).buy(4, 10, MAX, { value: E18 }));
    await gas("buy (one bucket, repeat)", market.connect(alice).buy(4, 100, MAX, { value: E18 }));
    await gas("buy (one bucket, repeat)", market.connect(alice).buy(4, 1000, MAX, { value: E18 }));
    for (const [who, size] of [[bob, 10n], [carol, 100n], [dave, 1000n]]) {
      await gas("buyBasket stepped [0,0,0,1,2,3] x size (first buy of this buyer)",
        market.connect(who).buyBasket(STEPPED.map((x) => x * size), MAX, { value: 10n * E18 }));
    }
    for (const size of [10n, 100n, 1000n]) {
      await gas("buyBasket stepped [0,0,0,1,2,3] x size (repeat)",
        market.connect(bob).buyBasket(STEPPED.map((x) => x * size), MAX, { value: 10n * E18 }));
    }
    await gas("buyBasket all six buckets (first buy of this buyer)", market.connect(signers[6]).buyBasket([5, 4, 3, 2, 1, 6], MAX, { value: E18 }));
    await gas("buyBasket all six buckets (repeat)", market.connect(signers[6]).buyBasket([5, 4, 3, 2, 1, 6], MAX, { value: E18 }));
    // One basket against the same position by three single buys, each in a fresh market.
    const one = await deployRain({ b: 100, unit: 10n ** 14n });
    await gas("stepped x100 as ONE basket (fresh market)", one.market.connect(one.alice).buyBasket(STEPPED.map((x) => x * 100n), MAX, { value: E18 }));
    const legs = await deployRain({ b: 100, unit: 10n ** 14n });
    let three = 0;
    for (const [j, s] of [[3, 100], [4, 200], [5, 300]]) {
      const r = await (await legs.market.connect(legs.alice).buy(j, s, MAX, { value: E18 })).wait();
      three += Number(r.gasUsed);
    }
    log["stepped x100 by THREE single buys (fresh market, sum)"] = [three];
    expect(await legs.market.totalPaid()).to.equal(await one.market.totalPaid());

    // --- report, settle, redeem, withdraw ---
    await setNextTime(t0 + 2000);
    await gas("oracle.reportCount", oracle.reportCount(STATION, SEASON, 9));
    await gas("settle", market.connect(carol).settle());
    await gas("redeem", market.connect(bob).redeem());
    await gas("redeem", market.connect(carol).redeem());
    await gas("sponsorWithdraw", market.sponsorWithdraw());
    await setTime(Number(await market.claimDeadline()) + 1);
    await gas("sweepUnclaimed", market.sweepUnclaimed());

    // --- cancel paths ---
    const m2 = await deployRain({ b: 100, unit: 10n ** 14n });
    await m2.market.connect(m2.alice).buyBasket(STEPPED.map((x) => x * 100n), MAX, { value: E18 });
    await gas("emergencyCancel", m2.market.connect(m2.sponsor).emergencyCancel());
    await gas("claimRefund", m2.market.connect(m2.alice).claimRefund());
    const m3 = await deployRain({ b: 100, unit: 10n ** 14n, real: true });
    await m3.market.connect(m3.alice).buyBasket(STEPPED.map((x) => x * 100n), MAX, { value: E18 });
    await setTime(m3.reportDeadline + 1);
    await gas("cancelAfterDeadline", m3.market.connect(m3.alice).cancelAfterDeadline());
    await gas("claimRefund", m3.market.connect(m3.alice).claimRefund());
    await gas("sponsorWithdraw", m3.market.connect(m3.sponsor).sponsorWithdraw());
    const m4 = await deployRain({ real: true });
    await setTime(m4.seasonEnd + 1);
    await m4.oracle.connect(m4.reporter).reportCount(STATION, SEASON, 3);
    await gas("oracle.voidReport", m4.oracle.connect(m4.reporter).voidReport(STATION, SEASON));
  });

  it("reports gas per function, checks sane ranges, writes results/market/gas_report.json", function () {
    const rows = {};
    for (const [label, xs] of Object.entries(log)) {
      const sorted = xs.slice().sort((a, c) => a - c);
      rows[label] = { calls: xs.length, min: sorted[0], median: sorted[Math.floor(sorted.length / 2)], max: sorted[sorted.length - 1] };
    }
    expect(Object.keys(rows).length).to.equal(21);
    for (const [label, r] of Object.entries(rows)) {
      // every transaction costs at least the 21,000 base; none may come near a block
      expect(r.min, label).to.be.gt(21000);
      expect(r.max, label).to.be.lt(label.startsWith("deploy RainCountLMSR") ? 5000000 : label.startsWith("deploy") ? 1500000 : label.includes("THREE") ? 1200000 : 400000);
    }
    // one basket must be cheaper than the same position by three single buys
    expect(rows["stepped x100 as ONE basket (fresh market)"].max)
      .to.be.lt(rows["stepped x100 by THREE single buys (fresh market, sum)"].min);
    // the size of the trade must not change the gas much (same storage pattern)
    const rep = rows["buyBasket stepped [0,0,0,1,2,3] x size (repeat)"];
    expect(rep.max - rep.min).to.be.lt(15000);

    console.log("\n      gas per function (local Hardhat EVM, not Sepolia; six buckets, b = 100, unit = 1e14 wei)");
    console.log("      " + "function".padEnd(66) + "calls".padStart(6) + "min".padStart(10) + "median".padStart(10) + "max".padStart(10));
    for (const [label, r] of Object.entries(rows).sort()) {
      console.log("      " + label.padEnd(66) + String(r.calls).padStart(6) + String(r.min).padStart(10) + String(r.median).padStart(10) + String(r.max).padStart(10));
    }
    const out = {
      note: "Gas measured in the local Hardhat EVM by contracts/test/15_rain_gas.test.js. Not measured on Sepolia.",
      evm: "hardhat network, hardfork cancun",
      compiler: artifact("RainCountLMSR").compiler,
      optimizer: artifact("RainCountLMSR").settings.optimizer,
      buckets: 6,
      deployedBytes: {
        RainCountLMSR: (artifact("RainCountLMSR").deployedBytecode.length - 2) / 2,
        SeasonCountOracle: (artifact("SeasonCountOracle").deployedBytecode.length - 2) / 2,
      },
      gas: rows,
    };
    const dir = path.join(__dirname, "..", "..", "results", "market");
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(path.join(dir, "gas_report.json"), JSON.stringify(out, null, 1));
  });
});
