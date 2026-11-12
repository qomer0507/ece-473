// Shared helpers for the BracketLMSR tests.
const fs = require("fs");
const path = require("path");
const hre = require("hardhat");
const { ethers } = hre;

const ART = path.join(__dirname, "..", "artifacts");
const VEC = path.join(__dirname, "vectors");
const BOUNDS = [80, 82, 84, 86, 88, 90, 92, 94, 96, 98, 100]; // n = 12
const STRIKE = 90;
const STATION = "USW00014734";
const DAY = 86400;

function artifact(name) {
  return JSON.parse(fs.readFileSync(path.join(ART, name + ".json"), "utf8"));
}

async function factory(name, signer) {
  const a = artifact(name);
  return new ethers.ContractFactory(a.abi, a.bytecode, signer || (await ethers.getSigners())[0]);
}

// ---- gas bookkeeping -------------------------------------------------
const gasLog = {};
function recordGas(label, gasUsed) {
  (gasLog[label] = gasLog[label] || []).push(Number(gasUsed));
}
/** Send a transaction, wait, record its gas under `label`, return the receipt. */
async function tx(label, promise) {
  const sent = await promise;
  const receipt = await sent.wait();
  if (label) recordGas(label, receipt.gasUsed);
  return receipt;
}

async function deploy(name, args = [], opts = {}, signer, label) {
  const f = await factory(name, signer);
  const c = await f.deploy(...args, opts);
  const receipt = await c.deploymentTransaction().wait();
  if (label) recordGas(label, receipt.gasUsed);
  return c;
}

// ---- time ------------------------------------------------------------
async function now() {
  return (await ethers.provider.getBlock("latest")).timestamp;
}
async function setTime(t) {
  await ethers.provider.send("evm_setNextBlockTimestamp", [Number(t)]);
  await ethers.provider.send("evm_mine", []);
}
async function setNextTime(t) {
  await ethers.provider.send("evm_setNextBlockTimestamp", [Number(t)]);
}

/** Top up a test account (hardhat_setBalance) so that it can send `need` wei plus gas. */
async function ensureBalance(signer, need) {
  const addr = await signer.getAddress();
  const have = await ethers.provider.getBalance(addr);
  const want = BigInt(need) + 10n ** 21n;
  if (have < want) await ethers.provider.send("hardhat_setBalance", [addr, "0x" + (want * 2n).toString(16)]);
}

// ---- float reference (double precision) --------------------------------
function costF(q, b) {
  const top = Math.max(...q);
  let s = 0;
  for (const x of q) s += Math.exp((x - top) / b);
  return top + b * Math.log(s);
}
function pricesF(q, b) {
  const top = Math.max(...q);
  const w = q.map((x) => Math.exp((x - top) / b));
  const s = w.reduce((a, c) => a + c, 0);
  return w.map((x) => x / s);
}

// ---- deterministic random numbers (mulberry32, seed 473) ---------------
function rng(seed = 473) {
  let a = seed >>> 0;
  return function () {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * Deploy a market. Times are relative to the latest block:
 * trading closes at +1000 s, observation ends at +2000 s, report deadline at +3000 s.
 */
async function deployMarket(o = {}) {
  const signers = await ethers.getSigners();
  const sponsor = o.sponsor || signers[0];
  const oracle = o.oracle || (await deploy(o.mock === false ? "TemperatureOracle" : "MockOracle", [], {}, sponsor));
  const t0 = await now();
  const b = BigInt(o.b ?? 200);
  const unit = BigInt(o.unit ?? 10n ** 12n);
  const bounds = o.bounds || BOUNDS;
  const n = bounds.length + 1;
  const initialQ = o.initialQ || [];
  const times = {
    tradingClose: o.tradingClose ?? t0 + 1000,
    observationEnd: o.observationEnd ?? t0 + 2000,
    reportDeadline: o.reportDeadline ?? t0 + 3000,
  };
  const day = o.day ?? Math.floor(t0 / DAY);
  // Fund generously by default (ceil of ln(n) * b * unit, or more for a seed); tests that need
  // the exact requirement pass `value`.
  let value = o.value;
  if (value === undefined) {
    const q0 = initialQ.length ? initialQ.map(Number) : new Array(n).fill(0);
    const c0 = b > 0n ? costF(q0, Number(b)) : 0;
    value = BigInt(Math.ceil(c0 * 1.0001 * 1e6 + 1)) * unit / 1000000n + 1n;
  }
  const args = [
    await oracle.getAddress(), o.station ?? STATION, day, bounds, o.strike ?? STRIKE, b, unit, initialQ,
    times.tradingClose, times.observationEnd, times.reportDeadline,
  ];
  await ensureBalance(sponsor, value);
  const market = await deploy("BracketLMSR", args, { value }, sponsor, o.gasLabel);
  return { market, oracle, sponsor, signers, b, unit, n, day, value, ...times };
}

function vectors() {
  return JSON.parse(fs.readFileSync(path.join(VEC, "reference.json"), "utf8"));
}

module.exports = {
  hre, ethers, ensureBalance, artifact, factory, deploy, deployMarket, tx, recordGas, gasLog, now, setTime, setNextTime,
  costF, pricesF, rng, vectors, BOUNDS, STRIKE, STATION, DAY, VEC,
};
