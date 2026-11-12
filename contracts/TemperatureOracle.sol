// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/*
    Temperature oracle for the bracket market. TESTNET ONLY.

    In the spirit of the Lab 13 class oracle: reporters push a value, readers
    pull it with a view call, and every report is logged in an event.
    Differences: only authorised reporters may report (no median, no stake),
    and there is exactly one report per (station, day). A report can never
    be changed. If it is wrong or late, the market cancels and refunds.

    `day` is the UTC day number: unix time / 86400 (2026-07-15 is 20649).
    `tempF` is the daily maximum temperature in whole deg F.
*/
contract TemperatureOracle {
    struct Report {
        int16 tempF;
        uint64 reportedAt; // block timestamp of the report
        address reporter;
        bool exists;
    }

    int16 public constant MIN_TEMP_F = -80;
    int16 public constant MAX_TEMP_F = 140;

    address public owner;
    mapping(address => bool) public isReporter;
    mapping(bytes32 => mapping(uint32 => Report)) private reports; // keccak(station) => day => report

    event ReporterSet(address indexed reporter, bool allowed);
    event Reported(string station, uint32 indexed day, int16 tempF, address indexed reporter, uint64 reportedAt);

    constructor() {
        owner = msg.sender;
        isReporter[msg.sender] = true;
        emit ReporterSet(msg.sender, true);
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    /// Owner adds or removes an authorised reporter.
    function setReporter(address reporter, bool allowed) external onlyOwner {
        isReporter[reporter] = allowed;
        emit ReporterSet(reporter, allowed);
    }

    /// Report the daily maximum for one station and one day. Works once per (station, day).
    function reportTemperature(string calldata station, uint32 day, int16 tempF) external {
        require(isReporter[msg.sender], "Not an authorised reporter");
        require(uint256(day) * 1 days <= block.timestamp, "Day has not started");
        require(tempF >= MIN_TEMP_F && tempF <= MAX_TEMP_F, "Implausible temperature");
        Report storage r = reports[keccak256(bytes(station))][day];
        require(!r.exists, "Already reported");
        r.tempF = tempF;
        r.reportedAt = uint64(block.timestamp);
        r.reporter = msg.sender;
        r.exists = true;
        emit Reported(station, day, tempF, msg.sender, uint64(block.timestamp));
    }

    /// Read a report (like readValue() in Lab 13). exists = false if there is none.
    function getReport(string calldata station, uint32 day)
        external
        view
        returns (bool exists, int16 tempF, uint64 reportedAt)
    {
        Report storage r = reports[keccak256(bytes(station))][day];
        return (r.exists, r.tempF, r.reportedAt);
    }

    /// Today's UTC day number, for convenience in Remix.
    function currentDay() external view returns (uint32) {
        return uint32(block.timestamp / 1 days);
    }
}
