// Compile the contracts with solc-js (npm package `solc`). No compiler download needed.
// Writes artifacts/<Name>.json and a flattened single-file copy for Remix in remix/.
// Usage: node scripts/compile.js
const fs = require("fs");
const path = require("path");
const solc = require("solc");

const ROOT = path.join(__dirname, "..");
const SOURCES = [
  "RainCountLMSR.sol", "SeasonCountOracle.sol", "MockCountOracle.sol", "mocks/RainTestHelpers.sol",
  // earlier temperature version, kept for comparison
  "BracketLMSR.sol", "TemperatureOracle.sol", "MockOracle.sol", "mocks/TestHelpers.sol",
];
// Contracts that get a flattened single-file copy in remix/.
const FLATTEN = ["RainCountLMSR.sol", "SeasonCountOracle.sol", "BracketLMSR.sol", "TemperatureOracle.sol"];
// Remix resolves "@openzeppelin/contracts@4.9.6/..." from npm. Locally the same version is in node_modules.
const OZ_PIN = "@openzeppelin/contracts@4.9.6/";
const ozVersion = require("@openzeppelin/contracts/package.json").version;
if (ozVersion !== "4.9.6") {
  console.error("node_modules has OpenZeppelin " + ozVersion + ", the sources pin 4.9.6");
  process.exit(1);
}
const SETTINGS = {
  optimizer: { enabled: true, runs: 200 },
  outputSelection: { "*": { "*": ["abi", "evm.bytecode.object", "evm.deployedBytecode.object"] } },
};

function readImport(p) {
  if (p.startsWith(OZ_PIN)) p = "@openzeppelin/contracts/" + p.slice(OZ_PIN.length);
  for (const base of [ROOT, path.join(ROOT, "node_modules")]) {
    const full = path.join(base, p);
    if (fs.existsSync(full)) return { contents: fs.readFileSync(full, "utf8") };
  }
  return { error: "File not found: " + p };
}

function compile(sources) {
  const input = { language: "Solidity", sources, settings: SETTINGS };
  const out = JSON.parse(solc.compile(JSON.stringify(input), { import: readImport }));
  const errors = (out.errors || []).filter((e) => e.severity === "error");
  for (const e of out.errors || []) if (e.severity !== "error") console.warn(e.formattedMessage);
  if (errors.length) {
    for (const e of errors) console.error(e.formattedMessage);
    process.exit(1);
  }
  return out;
}

// 1. Main build.
const sources = {};
for (const s of SOURCES) sources[s] = { content: fs.readFileSync(path.join(ROOT, s), "utf8") };
const out = compile(sources);
const artDir = path.join(ROOT, "artifacts");
fs.mkdirSync(artDir, { recursive: true });
const sizes = {};
for (const file of SOURCES) {
  for (const [name, c] of Object.entries(out.contracts[file])) {
    if (name.startsWith("I")) continue; // interfaces
    const art = {
      contractName: name,
      sourceName: file,
      compiler: solc.version(),
      settings: { optimizer: SETTINGS.optimizer },
      abi: c.abi,
      bytecode: "0x" + c.evm.bytecode.object,
      deployedBytecode: "0x" + c.evm.deployedBytecode.object,
    };
    fs.writeFileSync(path.join(artDir, name + ".json"), JSON.stringify(art, null, 1));
    sizes[name] = c.evm.deployedBytecode.object.length / 2;
  }
}

// 2. Flattened files for Remix (no imports to resolve).
function flatten(entry) {
  const seen = new Set();
  const parts = [];
  function visit(p) {
    if (seen.has(p)) return;
    seen.add(p);
    const src = p in sources ? sources[p].content : readImport(p).contents;
    const body = [];
    for (const line of src.split("\n")) {
      const m = line.match(/^\s*import\s+(?:.*from\s+)?["']([^"']+)["'];/);
      if (m) {
        const dep = m[1].startsWith(".") ? path.posix.join(path.posix.dirname(p), m[1]) : m[1];
        visit(dep);
      } else if (/^\s*\/\/\s*SPDX-License-Identifier/.test(line) || /^\s*pragma\s+solidity/.test(line)) {
        // one header only
      } else body.push(line);
    }
    parts.push("// ---- begin " + p + " ----\n" + body.join("\n").trim() + "\n// ---- end " + p + " ----\n");
  }
  visit(entry);
  return (
    "// SPDX-License-Identifier: MIT\n" +
    "// FLATTENED by scripts/compile.js from " + entry + ". Do not edit. Edit the source and re-run.\n" +
    "// Bundled libraries keep their own licences: ABDKMath64x64 (BSD-4-Clause, ABDK Consulting),\n" +
    "// OpenZeppelin Contracts 4.9.6 ReentrancyGuard (MIT).\n" +
    "pragma solidity ^0.8.20;\n\n" +
    parts.join("\n")
  );
}
const remixDir = path.join(ROOT, "remix");
fs.mkdirSync(remixDir, { recursive: true });
for (const entry of FLATTEN) {
  const name = entry.replace(".sol", "");
  const flatName = name + "_flat.sol";
  const flat = flatten(entry);
  fs.writeFileSync(path.join(remixDir, flatName), flat);
  const fo = compile({ [flatName]: { content: flat } });
  const flatCode = fo.contracts[flatName][name].evm.deployedBytecode.object;
  // Bytecode ends with a metadata hash that depends on the file name; compare the length only.
  if (flatCode.length / 2 !== sizes[name]) {
    console.error("Flattened " + name + " differs in size from the source build");
    process.exit(1);
  }
}

fs.writeFileSync(path.join(artDir, "sizes.json"), JSON.stringify({ compiler: solc.version(), deployedBytes: sizes }, null, 1));
console.log("solc", solc.version(), "optimizer 200 runs");
console.log("deployed bytecode sizes (bytes, limit 24576):", JSON.stringify(sizes));
