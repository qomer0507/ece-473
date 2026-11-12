// Shared helpers for the RainCountLMSR tests (files 11 to 15).
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const base = require("./helpers");
const { ethers, deploy, ensureBalance, now } = base;

const EDGES = [2, 4, 6, 8, 10]; // example: 0-2, 3-4, 5-6, 7-8, 9-10, 11+
const N = 6;
const STATION = "TTN";
const SEASON = 2027;
const SEASON_DAYS = 102;
const DAYS = 86400;
const CLAIM_PERIOD = 30 * DAYS;

// ln(6) * 1e18, rounded up
const LN6_E18 = 1791759469228055001n;
/** A funding amount that is certainly enough: b ln(6) unit plus a rounding margin. */
function safeFunding(b, unit) {
  const bu = BigInt(b) * BigInt(unit);
  return (bu * LN6_E18) / 10n ** 18n + bu / 2n ** 56n + 2n;
}

/** Bucket of a count for inclusive upper edges (JavaScript copy of the rule, for expectations). */
function bucketOf(count, edges = EDGES) {
  for (let j = 0; j < edges.length; j++) if (count <= edges[j]) return j;
  return edges.length;
}

/**
 * Deploy an oracle (mock by default), open the season, deploy the market.
 * Accounts: signers[0] sponsor, signers[1] oracle owner and reporter, the rest buyers.
 * Times relative to the latest block: trading close and season start +1000 s,
 * season end +2000 s, report deadline +3000 s.
 */
async function deployRain(o = {}) {
  const signers = await ethers.getSigners();
  const sponsor = o.sponsor || signers[0];
  const reporter = signers[1];
  const t0 = await now();
  const times = {
    tradingClose: o.tradingClose ?? t0 + 1000,
    seasonStart: o.seasonStart ?? t0 + 1000,
    seasonEnd: o.seasonEnd ?? t0 + 2000,
    reportDeadline: o.reportDeadline ?? t0 + 3000,
  };
  const station = o.station ?? STATION;
  const season = o.season ?? SEASON;
  const seasonDays = o.seasonDays ?? SEASON_DAYS;
  let oracle = o.oracle;
  if (!oracle) {
    oracle = await deploy(o.real ? "SeasonCountOracle" : "MockCountOracle", [], {}, reporter);
    if (o.open !== false) {
      await (await oracle.connect(reporter).openSeason(station, season, times.seasonStart, times.seasonEnd, seasonDays)).wait();
    }
  }
  const b = BigInt(o.b ?? 200);
  const unit = BigInt(o.unit ?? 10n ** 12n);
  const edges = o.edges || EDGES;
  const disputeDelay = o.disputeDelay ?? 0;
  const claimPeriod = o.claimPeriod ?? CLAIM_PERIOD;
  const value = o.value !== undefined ? BigInt(o.value) : safeFunding(b > 0n ? b : 1n, unit);
  const oracleAddress = o.oracleAddress || (await oracle.getAddress());
  const args = [oracleAddress, station, season, edges, b, unit, times.tradingClose, times.reportDeadline, disputeDelay, claimPeriod];
  await ensureBalance(sponsor, value);
  const market = await deploy("RainCountLMSR", args, { value }, sponsor, o.gasLabel);
  return {
    market, oracle, sponsor, reporter, signers, b, unit, edges, value, station, season, seasonDays, disputeDelay, claimPeriod,
    alice: signers[2], bob: signers[3], carol: signers[4], stranger: signers[5], ...times,
  };
}

async function snapshot() {
  return ethers.provider.send("evm_snapshot", []);
}
async function revertTo(id) {
  await ethers.provider.send("evm_revert", [id]);
}

const balanceOf = async (c) => ethers.provider.getBalance(typeof c === "string" ? c : await c.getAddress());

function rainVectors() {
  return JSON.parse(fs.readFileSync(path.join(base.VEC, "reference_rain.json"), "utf8"));
}

/** sha256 of a contract source file, so the pytest cross-check can tell a stale snapshot. */
function sourceHash(name) {
  return crypto.createHash("sha256").update(fs.readFileSync(path.join(__dirname, "..", name))).digest("hex");
}

module.exports = { ...base, deployRain, safeFunding, bucketOf, snapshot, revertTo, balanceOf, rainVectors, sourceHash,
  EDGES, N, STATION, SEASON, SEASON_DAYS, DAYS, CLAIM_PERIOD };
