// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Test-only contracts for the review item M1 (wrong oracle address). Never deploy these.

/// A contract that accepts any call and returns nothing (for example a wallet contract or a wrong contract).
contract EmptyFallbackOracle {
    fallback() external {}
}

/// A contract that answers any call with one 32-byte word (a contract with a different ABI).
contract OneWordOracle {
    fallback() external {
        assembly {
            mstore(0, 1)
            return(0, 32)
        }
    }
}
