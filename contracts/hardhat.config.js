// Hardhat is used only as an in-process EVM and test runner.
// Compilation is done by scripts/compile.js with solc-js (npm `solc`),
// because compiler downloads are blocked in the build environment.
require("@nomicfoundation/hardhat-ethers");
require("@nomicfoundation/hardhat-chai-matchers");

module.exports = {
  solidity: "0.8.26", // not used: `npm test` runs `hardhat test --no-compile`
  paths: { sources: "./.hh/none", tests: "./test", cache: "./.hh/cache", artifacts: "./.hh/artifacts" },
  networks: {
    hardhat: {
      hardfork: "cancun",
      allowUnlimitedContractSize: false, // keep the real 24,576-byte limit
      accounts: { count: 12, accountsBalance: "1000000000000000000000000" }, // 1,000,000 test ETH each
    },
  },
  mocha: { timeout: 600000 },
};
