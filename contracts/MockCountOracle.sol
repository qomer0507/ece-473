// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/*
    Mock season-count oracle for tests only. Never deploy this for a real market.
    Anyone can set any season and any report with any timestamp, delete the
    report, or switch the oracle into a broken mode. This lets the tests reach
    every oracle path of RainCountLMSR (on time, early, late, missing, broken).

    mode 0  normal answer (7 words)
    mode 1  revert
    mode 2  succeed with empty return data
    mode 3  succeed with one word (too short)
    mode 4  succeed with 8 words (too long)
    mode 5  succeed with 7 words of 0xff..ff (right size, impossible values)
    mode 6  burn all the gas it is given
*/
contract MockCountOracle {
    struct Season {
        bool opened;
        uint64 seasonStart;
        uint64 seasonEnd;
        uint16 seasonDays;
        bool reported;
        uint16 count;
        uint64 reportedAt;
    }

    mapping(bytes32 => Season) private seasons;
    uint8 public mode;

    function _key(string calldata station, uint32 season) private pure returns (bytes32) {
        return keccak256(abi.encode(station, season));
    }

    function openSeason(string calldata station, uint32 season, uint64 seasonStart, uint64 seasonEnd, uint16 seasonDays)
        external
    {
        Season storage s = seasons[_key(station, season)];
        s.opened = true;
        s.seasonStart = seasonStart;
        s.seasonEnd = seasonEnd;
        s.seasonDays = seasonDays;
    }

    /// Store a report stamped with the current block time. No checks at all.
    function setReport(string calldata station, uint32 season, uint16 count) external {
        Season storage s = seasons[_key(station, season)];
        s.reported = true;
        s.count = count;
        s.reportedAt = uint64(block.timestamp);
    }

    /// Store a report with an arbitrary timestamp (to fake early or late reports).
    function setReportAt(string calldata station, uint32 season, uint16 count, uint64 reportedAt) external {
        Season storage s = seasons[_key(station, season)];
        s.reported = true;
        s.count = count;
        s.reportedAt = reportedAt;
    }

    function clearReport(string calldata station, uint32 season) external {
        Season storage s = seasons[_key(station, season)];
        s.reported = false;
        s.count = 0;
        s.reportedAt = 0;
    }

    function setMode(uint8 _mode) external {
        mode = _mode;
    }

    function getSeason(string calldata station, uint32 season)
        external
        view
        returns (bool, uint64, uint64, uint16, bool, uint16, uint64)
    {
        uint8 m = mode;
        if (m == 1) revert("Oracle broken");
        if (m == 2) {
            assembly {
                return(0, 0)
            }
        }
        if (m == 3) {
            assembly {
                mstore(0, 1)
                return(0, 32)
            }
        }
        if (m == 4) {
            assembly {
                let p := mload(0x40)
                for { let i := 0 } lt(i, 8) { i := add(i, 1) } { mstore(add(p, mul(i, 32)), 1) }
                return(p, 256)
            }
        }
        if (m == 5) {
            assembly {
                let p := mload(0x40)
                for { let i := 0 } lt(i, 7) { i := add(i, 1) } { mstore(add(p, mul(i, 32)), not(0)) }
                return(p, 224)
            }
        }
        if (m == 6) {
            uint256 x = 0;
            while (true) {
                x = uint256(keccak256(abi.encode(x)));
            }
        }
        Season storage s = seasons[_key(station, season)];
        return (s.opened, s.seasonStart, s.seasonEnd, s.seasonDays, s.reported, s.count, s.reportedAt);
    }
}
