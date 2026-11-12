// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/*
    Mock oracle for tests only. Never deploy this for a real market.
    Anyone can store any report with any timestamp, overwrite it, delete it,
    or make getReport revert. This lets the tests reach every oracle path
    of BracketLMSR (on time, late, missing, stale, wrong day, broken).
*/
contract MockOracle {
    struct Report {
        int16 tempF;
        uint64 reportedAt;
        bool exists;
    }

    mapping(bytes32 => mapping(uint32 => Report)) private reports;
    bool public broken;

    /// Store a report stamped with the current block time.
    function setReport(string calldata station, uint32 day, int16 tempF) external {
        reports[keccak256(bytes(station))][day] = Report(tempF, uint64(block.timestamp), true);
    }

    /// Store a report with an arbitrary timestamp (to fake stale or late reports).
    function setReportAt(string calldata station, uint32 day, int16 tempF, uint64 reportedAt) external {
        reports[keccak256(bytes(station))][day] = Report(tempF, reportedAt, true);
    }

    function clearReport(string calldata station, uint32 day) external {
        delete reports[keccak256(bytes(station))][day];
    }

    function setBroken(bool _broken) external {
        broken = _broken;
    }

    function getReport(string calldata station, uint32 day)
        external
        view
        returns (bool exists, int16 tempF, uint64 reportedAt)
    {
        require(!broken, "Oracle broken");
        Report storage r = reports[keccak256(bytes(station))][day];
        return (r.exists, r.tempF, r.reportedAt);
    }
}
