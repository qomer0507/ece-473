// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/*
    Season count oracle for the rain-count market (RainCountLMSR.sol).
    TESTNET ONLY. Class project (ECE 473). Not audited.

    What it stores
      One "season" per key (station, season), for example ("TTN", 2027).
      The owner opens a season once and fixes three facts:
        seasonStart  unix time of the first season day
        seasonEnd    unix time after which the count is final
        seasonDays   number of days in the season (the largest possible count)
      A reporter then reports the count of loss days ONCE, and only at or
      after seasonEnd. A report before the season end is refused, so a
      premature report can not happen (review item M3).

    In the spirit of the Lab 13 class oracle: a reporter pushes a value,
    readers pull it with a view call, every change is logged in an event.
    Differences: only authorised reporters may report (no median, no stake),
    and there is one report per key.

    TRUST (read this before using it)
      One reporter decides the count. Nobody checks it on chain.
      A report can not be replaced by another number.
      The only correction is voidReport(): the OWNER can cancel a wrong
      report. A voided season never gets a new report. A market that has
      not settled yet then finds no valid report and refunds its buyers
      after its report deadline. A market that already settled is final.
      So a wrong report is caught only if the owner acts before settle().
      The market's dispute delay exists to leave time for that.
      The oracle owner and reporter must not be the market sponsor.
*/
contract SeasonCountOracle {
    struct Season {
        uint64 seasonStart;
        uint64 seasonEnd;   // "not before" time for the report
        uint64 reportedAt;  // block timestamp of the report
        uint16 seasonDays;
        uint16 count;
        bool opened;
        bool reported;
        bool voided;
        address reporter;
    }

    address public immutable owner;
    mapping(address => bool) public isReporter;
    mapping(bytes32 => Season) private seasons; // key = keccak256(station, season)

    event ReporterSet(address indexed reporter, bool allowed);
    event SeasonOpened(string station, uint32 indexed season, uint64 seasonStart, uint64 seasonEnd, uint16 seasonDays);
    event CountReported(string station, uint32 indexed season, uint16 count, address indexed reporter, uint64 reportedAt);
    event ReportVoided(string station, uint32 indexed season, uint16 count, address indexed owner);

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    /// The deployer is the owner and the first authorised reporter.
    constructor() {
        owner = msg.sender;
        isReporter[msg.sender] = true;
        emit ReporterSet(msg.sender, true);
    }

    function _key(string calldata station, uint32 season) private pure returns (bytes32) {
        return keccak256(abi.encode(station, season));
    }

    /// Owner adds or removes an authorised reporter.
    function setReporter(address reporter, bool allowed) external onlyOwner {
        isReporter[reporter] = allowed;
        emit ReporterSet(reporter, allowed);
    }

    /// Owner defines a season. Works once per (station, season). It can not be changed later.
    /// @param seasonStart unix time of the first season day
    /// @param seasonEnd   unix time after which a report is accepted (must be in the future)
    /// @param seasonDays  number of season days = largest count that can be reported
    function openSeason(string calldata station, uint32 season, uint64 seasonStart, uint64 seasonEnd, uint16 seasonDays)
        external
        onlyOwner
    {
        Season storage s = seasons[_key(station, season)];
        require(!s.opened, "Season already opened");
        require(seasonStart < seasonEnd, "Start must be before end");
        require(seasonEnd > block.timestamp, "Season end in the past");
        require(seasonDays > 0, "Season has no days");
        s.opened = true;
        s.seasonStart = seasonStart;
        s.seasonEnd = seasonEnd;
        s.seasonDays = seasonDays;
        emit SeasonOpened(station, season, seasonStart, seasonEnd, seasonDays);
    }

    /// Report the number of loss days of a season. Works once per (station, season).
    function reportCount(string calldata station, uint32 season, uint16 count) external {
        require(isReporter[msg.sender], "Not an authorised reporter");
        Season storage s = seasons[_key(station, season)];
        require(s.opened, "Season not opened");
        require(block.timestamp >= s.seasonEnd, "Season not over");
        require(!s.reported, "Already reported");
        require(count <= s.seasonDays, "Count above season days");
        s.reported = true;
        s.count = count;
        s.reportedAt = uint64(block.timestamp);
        s.reporter = msg.sender;
        emit CountReported(station, season, count, msg.sender, uint64(block.timestamp));
    }

    /// Owner cancels a wrong report. Final: the season can not be reported again.
    function voidReport(string calldata station, uint32 season) external onlyOwner {
        Season storage s = seasons[_key(station, season)];
        require(s.reported, "No report");
        require(!s.voided, "Already voided");
        s.voided = true;
        emit ReportVoided(station, season, s.count, msg.sender);
    }

    /// Read a season (like readValue() in Lab 13). This is the function the market calls.
    /// `reported` is false if there is no report or if the report was voided.
    function getSeason(string calldata station, uint32 season)
        external
        view
        returns (
            bool opened,
            uint64 seasonStart,
            uint64 seasonEnd,
            uint16 seasonDays,
            bool reported,
            uint16 count,
            uint64 reportedAt
        )
    {
        Season storage s = seasons[_key(station, season)];
        bool live = s.reported && !s.voided;
        return (s.opened, s.seasonStart, s.seasonEnd, s.seasonDays, live, live ? s.count : 0, live ? s.reportedAt : 0);
    }

    /// Who reported, and whether the report was voided (for the record; the market does not use it).
    function reportInfo(string calldata station, uint32 season)
        external
        view
        returns (address reporter, bool wasReported, bool voided)
    {
        Season storage s = seasons[_key(station, season)];
        return (s.reporter, s.reported, s.voided);
    }

    /// Current block time, to pick season times in Remix.
    function currentTime() external view returns (uint64) {
        return uint64(block.timestamp);
    }
}
