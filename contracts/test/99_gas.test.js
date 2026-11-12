// Prints the gas used per function (collected by the other test files) and writes
// results/part3/gas_report.json. Gas is measured in the local Hardhat EVM (Cancun rules,
// solc 0.8.26, optimizer 200 runs). Sepolia gas for the same call and state is the same
// EVM arithmetic, but storage warm/cold patterns of a given call can differ a little.
const fs = require("fs");
const path = require("path");
const { expect } = require("chai");
const { ethers, gasLog, artifact, deployMarket, tx } = require("./helpers");

describe("99 gas report", function () {
  it("measures repeat purchases (storage slots already non-zero)", async function () {
    const m = await deployMarket({ b: 200 });
    const t = m.signers[1];
    const big = 10n ** 18n;
    await tx("buyBasket (6 brackets >= 90)", m.market.connect(t).buyBasket(10, ethers.MaxUint256, { value: big }));
    await tx("buyBasket (repeat buyer)", m.market.connect(t).buyBasket(100, ethers.MaxUint256, { value: big }));
    await tx("buyBasket (repeat buyer)", m.market.connect(t).buyBasket(1000, ethers.MaxUint256, { value: big }));
    await tx("buy (repeat buyer)", m.market.connect(t).buy(6, 100, ethers.MaxUint256, { value: big }));
    await tx("buy (repeat buyer)", m.market.connect(t).buy(8, 1000, ethers.MaxUint256, { value: big }));
  });

  it("reports gas per function", function () {
    const rows = {};
    for (const [label, xs] of Object.entries(gasLog)) {
      const sorted = xs.slice().sort((a, b) => a - b);
      rows[label] = {
        calls: xs.length,
        min: sorted[0],
        median: sorted[Math.floor(sorted.length / 2)],
        max: sorted[sorted.length - 1],
      };
    }
    for (const need of ["deploy BracketLMSR (n=12)", "buy (single bracket)", "buyBasket (6 brackets >= 90)", "settle",
      "redeem", "claimRefund", "sponsorWithdraw", "cancelAfterDeadline", "emergencyCancel",
      "oracle.reportTemperature", "deploy TemperatureOracle"]) {
      expect(rows[need], need).to.not.equal(undefined);
    }
    console.log("\n      gas per function (local Hardhat EVM, n = 12 brackets)");
    console.log("      " + "function".padEnd(42) + "calls".padStart(6) + "min".padStart(10) + "median".padStart(10) + "max".padStart(10));
    for (const [label, r] of Object.entries(rows).sort()) {
      console.log("      " + label.padEnd(42) + String(r.calls).padStart(6) + String(r.min).padStart(10) + String(r.median).padStart(10) + String(r.max).padStart(10));
    }
    const out = {
      note: "Gas measured in the local Hardhat EVM by `npm test` in contracts/. Not measured on Sepolia.",
      evm: "hardhat network, hardfork cancun",
      compiler: artifact("BracketLMSR").compiler,
      optimizer: artifact("BracketLMSR").settings.optimizer,
      brackets: 12,
      deployedBytes: JSON.parse(fs.readFileSync(path.join(__dirname, "..", "artifacts", "sizes.json"), "utf8")).deployedBytes,
      gas: rows,
    };
    const dir = path.join(__dirname, "..", "..", "results", "part3");
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(path.join(dir, "gas_report.json"), JSON.stringify(out, null, 1));
  });
});
