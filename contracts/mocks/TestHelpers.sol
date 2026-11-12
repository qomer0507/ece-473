// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "abdk-libraries-solidity/ABDKMath64x64.sol";

// Test-only contracts. Never deploy these for a real market.

/// Exposes the ABDK functions the market uses, so tests can check their accuracy.
contract MathHarness {
    function exp(int128 x) external pure returns (int128) {
        return ABDKMath64x64.exp(x);
    }

    function ln(int128 x) external pure returns (int128) {
        return ABDKMath64x64.ln(x);
    }

    /// exp(-d/b) exactly as BracketLMSR computes a weight.
    function weight(uint256 d, uint256 b) external pure returns (int128) {
        return ABDKMath64x64.exp(ABDKMath64x64.neg(ABDKMath64x64.divu(d, b)));
    }
}

interface IMarket {
    function buy(uint256 bracket, uint256 shares, uint256 maxCost) external payable;
    function buyBasket(uint256 sharesEach, uint256 maxCost) external payable;
    function redeem() external;
    function claimRefund() external;
    function sponsorWithdraw() external;
}

/// A trader contract that tries to re-enter the market whenever it receives ETH.
contract ReentrantTrader {
    IMarket public market;
    uint8 public mode; // 0 = accept quietly, 1 = re-enter redeem, 2 = re-enter claimRefund, 3 = re-enter buy
    bool public reentrySucceeded;
    uint256 public attempts;

    constructor(address _market) {
        market = IMarket(_market);
    }

    function setMode(uint8 _mode) external {
        mode = _mode;
    }

    function buy(uint256 bracket, uint256 shares) external payable {
        market.buy{value: msg.value}(bracket, shares, type(uint256).max);
    }

    function redeem() external {
        market.redeem();
    }

    function claimRefund() external {
        market.claimRefund();
    }

    receive() external payable {
        if (mode == 0) return;
        attempts++;
        if (mode == 1) {
            try market.redeem() { reentrySucceeded = true; } catch {}
        } else if (mode == 2) {
            try market.claimRefund() { reentrySucceeded = true; } catch {}
        } else {
            try market.buy{value: msg.value}(0, 1, type(uint256).max) { reentrySucceeded = true; } catch {}
        }
    }
}

/// A trader that cannot receive ETH. Its failed payout must not lock other users' funds.
contract RejectingTrader {
    IMarket public market;

    constructor(address _market) {
        market = IMarket(_market);
    }

    function buyExact(uint256 bracket, uint256 shares) external payable {
        market.buy{value: msg.value}(bracket, shares, type(uint256).max);
    }

    function redeem() external {
        market.redeem();
    }
}
