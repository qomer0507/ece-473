// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Same fixed-point library as Labs 7 and 8 (signed 64.64 numbers).
import "abdk-libraries-solidity/ABDKMath64x64.sol";
// Same guard and same pinned version as the Lab 13 oracle.
import "@openzeppelin/contracts@4.9.6/security/ReentrancyGuard.sol";

/// Read interface of the season count oracle (see SeasonCountOracle.sol).
interface ISeasonCountOracle {
    /// @return opened      true if the oracle owner defined this season
    /// @return seasonStart unix time of the first season day
    /// @return seasonEnd   unix time after which the count may be reported
    /// @return seasonDays  number of season days (largest possible count)
    /// @return reported    true if a count was reported (and not voided)
    /// @return count       number of loss days in the season
    /// @return reportedAt  block timestamp of the report
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
        );
}

/*
    Six-outcome LMSR market on the COUNT of loss days in one season at one station.
    TESTNET ONLY. Class project (ECE 473). Not audited.

    Buckets
      `edges` holds five increasing whole numbers. Each is the LAST count of a bucket.
      Example edges [2, 4, 6, 8, 10]:
        bucket 0: 0-2   bucket 1: 3-4   bucket 2: 5-6
        bucket 3: 7-8   bucket 4: 9-10  bucket 5: 11 or more
      Every count from 0 to seasonDays is in exactly one bucket.
      Edges used in the project for Trenton (docs/PHASE2_PREREG.md) [2, 4, 5, 6, 8]:
        bucket 0: 0-2   bucket 1: 3-4   bucket 2: 5
        bucket 3: 6     bucket 4: 7-8   bucket 5: 9 or more

    Units
      Shares are whole numbers. One share of the winning bucket pays `unit` wei.
      `b` is the LMSR liquidity parameter in shares (as in Lab 7).
      A stepped hedge is a vector of shares, for example [0, 0, 0, 1, 2, 3]:
      it pays 1 unit for 7-8 loss days, 2 units for 9-10, 3 units for 11 or more.

    Cost function (log-sum-exp form, as in Lab 8, for six outcomes)
      C(q) = b * ln( sum_j exp(q_j / b) )
           = max(q) + b * ln( sum_j exp( (q_j - max(q)) / b ) )
      Every exponent is <= 0, so exp can not overflow. The term of the largest
      q_j is exactly 1, so the sum is between 1 and 6 and ln is between 0 and ln 6.

    Charging rule
      costNow = C(q) is stored. A buy is charged C(q_new) - costNow.
      The charges add up to exactly C(q) - C(0), whatever the order of the
      trades. So one basket costs the same as its legs bought one by one.

    Collateral rule (why the contract can always pay)
      The market starts at q = 0 (all six prices 1/6). C(0) = b * ln 6.
      The sponsor must send at least C(0) * unit at deployment.
      Then  balance = funding + paid >= C(q) >= max(q) * unit >= any payout.
      The sponsor's worst-case loss is b * ln(6) * unit and never more.

    Life of a market
      Open      buys until tradingClose (at or before the first season day).
      Settled   after the season the oracle reports the count; anyone calls
                settle(); winners redeem; the sponsor withdraws the rest.
      Cancelled the sponsor may cancel while trading is open (emergencyCancel),
                and anyone may cancel after reportDeadline if there is no valid
                report (cancelAfterDeadline). Every buyer gets back what they paid.

    TRUST. What this contract does NOT guarantee
      - ONE reporter decides the outcome. The contract can not tell a wrong
        count from a right one. A wrong report that arrives on time settles
        the market. settle() is final.
      - The only protection is `disputeDelay`: settle() must wait that long
        after the report. In that time the oracle OWNER can void the report
        (SeasonCountOracle.voidReport). Then the market refunds after the
        deadline. If disputeDelay is 0 there is no such window.
      - The sponsor chooses the oracle address. The sponsor and the oracle
        owner/reporter MUST be different accounts run by different people.
        The contract does not and can not enforce this. If they are the same
        person, that person chooses the winning bucket.
      - The sponsor can cancel while trading is open. Buyers then get their
        money back but have no hedge. Trading closes at or before the first
        season day, so the sponsor can not cancel once the season has started.
      - Buy only. There is no sell function (same as Lab 7).
*/
contract RainCountLMSR is ReentrancyGuard {
    using ABDKMath64x64 for int128;

    enum State { Open, Settled, Cancelled }

    // ---- fixed limits ----
    uint256 public constant NUM_BUCKETS = 6;
    uint256 public constant MAX_B = 1e12;          // shares
    uint256 public constant MIN_UNIT = 1 gwei;     // wei per winning share (smaller units make trades round to 0 wei)
    uint256 public constant MAX_UNIT = 1 ether;
    uint256 public constant MAX_Q = 1e15;          // shares per bucket
    uint64 public constant MAX_DISPUTE_DELAY = 30 days;
    uint64 public constant MIN_CLAIM_PERIOD = 7 days;
    uint64 public constant MAX_CLAIM_PERIOD = 3650 days;
    // Gas given to one oracle read. A normal read needs far less.
    uint256 public constant ORACLE_GAS = 100000;
    // exp(-x) is below 2^-64 for x >= 45 and is treated as 0.
    uint256 private constant EXP_CUTOFF = 45;
    int128 private constant ONE = 0x10000000000000000; // 1.0 in 64.64
    // getSeason returns seven 32-byte words.
    uint256 private constant ORACLE_RETURN_SIZE = 7 * 32;

    // ---- market definition (fixed at deployment) ----
    address public immutable sponsor;
    address public immutable oracle;
    string public station;                  // e.g. "TTN"
    uint32 public immutable season;         // e.g. 2027
    uint256 public immutable b;             // liquidity parameter, in shares
    uint256 public immutable unit;          // wei paid per winning share
    uint64 public immutable tradingClose;   // buys allowed before this time
    uint64 public immutable seasonStart;    // copied from the oracle
    uint64 public immutable seasonEnd;      // copied from the oracle; a report must be made at or after it
    uint16 public immutable seasonDays;     // copied from the oracle; largest valid count
    uint64 public immutable reportDeadline; // a report must be made at or before this time
    uint64 public immutable disputeDelay;   // seconds between the report and settle(); may be 0
    uint64 public immutable claimPeriod;    // seconds winners have to claim before the sponsor may sweep
    uint16[] private edges;                 // five inclusive upper edges

    // ---- market state ----
    State public state;
    uint256[] private q;             // shares sold per bucket
    uint256 public costNow;          // C(q) in wei
    uint256 public requiredFunding;  // C(0) in wei = floor(b * ln 6 * unit)
    uint256 public funding;          // wei sent by the sponsor at deployment
    uint256 public totalPaid;        // wei paid by all buyers
    uint256 public reserved;         // wei still owed to buyers after settle or cancel
    uint16 public settledCount;
    uint256 public winningBucket;
    uint64 public claimDeadline;     // set at settle or cancel
    bool public swept;               // true once the sponsor swept unclaimed funds

    mapping(address => mapping(uint256 => uint256)) public sharesOf; // buyer => bucket => shares
    mapping(address => uint256) public paid;                          // buyer => wei paid (cost basis)

    // ---- events (one per state change) ----
    event MarketCreated(address indexed sponsor, address indexed oracle, string station, uint32 season,
        uint16[] edges, uint256 b, uint256 unit, uint256 funding, uint256 requiredFunding);
    event Trade(address indexed buyer, uint256 indexed bucket, uint256 shares, uint256 cost);
    event BasketTrade(address indexed buyer, uint256[] quantities, uint256 cost);
    event Settled(uint16 count, uint256 indexed winningBucket, uint64 reportedAt, uint256 owedToWinners, uint64 claimDeadline);
    event Cancelled(address indexed caller, string reason, uint256 owedToBuyers, uint64 claimDeadline);
    event Redeemed(address indexed buyer, uint256 shares, uint256 amount);
    event Refunded(address indexed buyer, uint256 amount);
    event SponsorWithdrawal(address indexed sponsor, uint256 amount);
    event UnclaimedSwept(address indexed sponsor, uint256 amount);

    modifier onlySponsor() {
        require(msg.sender == sponsor, "Not sponsor");
        _;
    }

    /// One oracle answer after checking. `ok` is false if the call failed or the data was malformed.
    struct SeasonData {
        bool ok;
        bool opened;
        uint64 seasonStart;
        uint64 seasonEnd;
        uint16 seasonDays;
        bool reported;
        uint16 count;
        uint64 reportedAt;
    }

    /// @param _oracle         SeasonCountOracle address. The season must already be opened there.
    /// @param _station        station id the oracle reports under, e.g. "TTN"
    /// @param _season         season id, e.g. 2027
    /// @param _edges          five increasing inclusive upper edges, e.g. [2,4,6,8,10]
    /// @param _b              LMSR liquidity parameter, in shares
    /// @param _unit           wei paid per winning share (1 gwei to 1 ether)
    /// @param _tradingClose   unix time, end of trading; not after the season start
    /// @param _reportDeadline unix time, last moment for a valid report; after the season end
    /// @param _disputeDelay   seconds settle() must wait after the report (0 to 30 days)
    /// @param _claimPeriod    seconds buyers have to claim after settle or cancel (at least 7 days)
    /// msg.value must be at least requiredFundingFor(_b, _unit) = floor(b * ln(6) * unit).
    /// Anything above that comes back to the sponsor with sponsorWithdraw().
    constructor(
        address _oracle,
        string memory _station,
        uint32 _season,
        uint16[] memory _edges,
        uint256 _b,
        uint256 _unit,
        uint64 _tradingClose,
        uint64 _reportDeadline,
        uint64 _disputeDelay,
        uint64 _claimPeriod
    ) payable {
        require(_b > 0 && _b <= MAX_B, "b out of range");
        require(_unit >= MIN_UNIT && _unit <= MAX_UNIT, "unit out of range");
        require(_disputeDelay <= MAX_DISPUTE_DELAY, "Dispute delay too long");
        require(_claimPeriod >= MIN_CLAIM_PERIOD && _claimPeriod <= MAX_CLAIM_PERIOD, "Claim period out of range");

        // Review item M1: a wrong oracle address must be refused here, not found out after the season.
        // An address without code (a wallet, a typo) can never answer.
        require(_oracle.code.length > 0, "Oracle has no code");
        // One trial read. It must return well-formed data, and the season must exist.
        SeasonData memory s = _readOracle(_oracle, _station, _season);
        require(s.ok, "Oracle read failed");
        require(s.opened, "Season not opened in oracle");
        require(!s.reported, "Season already reported");
        require(s.seasonStart < s.seasonEnd && s.seasonDays > 0, "Bad season in oracle");

        // Review item m1: trading must close at or before the first season day.
        require(_tradingClose > block.timestamp, "Trading close in the past");
        require(_tradingClose <= s.seasonStart, "Trading must close by season start");
        require(_reportDeadline > s.seasonEnd, "Deadline before season end");

        _checkEdges(_edges, s.seasonDays);

        sponsor = msg.sender;
        oracle = _oracle;
        station = _station;
        season = _season;
        b = _b;
        unit = _unit;
        tradingClose = _tradingClose;
        seasonStart = s.seasonStart;
        seasonEnd = s.seasonEnd;
        seasonDays = s.seasonDays;
        reportDeadline = _reportDeadline;
        disputeDelay = _disputeDelay;
        claimPeriod = _claimPeriod;
        edges = _edges;

        // Uniform start: q = 0 in every bucket, so every price is 1/6.
        q = new uint256[](NUM_BUCKETS);
        uint256 c0 = requiredFundingFor(_b, _unit);
        require(msg.value >= c0, "Funding below worst-case loss");
        costNow = c0;
        requiredFunding = c0;
        funding = msg.value;

        emit MarketCreated(msg.sender, _oracle, _station, _season, _edges, _b, _unit, msg.value, c0);
    }

    // ------------------------------------------------------------------
    // Views
    // ------------------------------------------------------------------

    /// Wei the sponsor must send at deployment: floor(b * ln(6) * unit).
    /// This is C(0) and also the sponsor's worst-case loss.
    /// Off chain: b * unit * 1.791759469228055, rounded up to be safe.
    function requiredFundingFor(uint256 _b, uint256 _unit) public pure returns (uint256) {
        require(_b > 0 && _b <= MAX_B, "b out of range");
        require(_unit >= MIN_UNIT && _unit <= MAX_UNIT, "unit out of range");
        return ABDKMath64x64.fromUInt(NUM_BUCKETS).ln().mulu(_b * _unit);
    }

    function getEdges() external view returns (uint16[] memory) {
        return edges;
    }

    /// Shares sold per bucket.
    function getQuantities() external view returns (uint256[] memory) {
        return q;
    }

    /// Shares one buyer holds in each bucket.
    function sharesOfAll(address buyer) external view returns (uint256[] memory held) {
        held = new uint256[](NUM_BUCKETS);
        for (uint256 j = 0; j < NUM_BUCKETS; j++) held[j] = sharesOf[buyer][j];
    }

    /// Bucket index that contains `count` loss days.
    function bucketOf(uint16 count) public view returns (uint256) {
        for (uint256 j = 0; j < NUM_BUCKETS - 1; j++) {
            if (count <= edges[j]) return j;
        }
        return NUM_BUCKETS - 1;
    }

    /// LMSR cost C(q) in wei for any quantity vector (testing aid).
    function costOf(uint256[] memory quantities) external view returns (uint256) {
        require(quantities.length == NUM_BUCKETS, "Need six quantities");
        return _cost(quantities, b, unit);
    }

    /// Current prices of all buckets, 1e18 = 100%. They sum to 1 up to rounding down.
    function prices() public view returns (uint256[] memory p) {
        uint256[] memory qm = q;
        (int128[] memory e, int128 sum) = _weights(qm, b);
        p = new uint256[](NUM_BUCKETS);
        // price_j = exp(q_j / b) / sum_k exp(q_k / b)
        for (uint256 j = 0; j < NUM_BUCKETS; j++) p[j] = e[j].div(sum).mulu(1e18);
    }

    /// Current price of one bucket, 1e18 = 100%.
    function price(uint256 bucket) external view returns (uint256) {
        require(bucket < NUM_BUCKETS, "Bad bucket");
        return prices()[bucket];
    }

    /// Wei needed to buy `shares` of one bucket now.
    function quoteBuy(uint256 bucket, uint256 shares) external view returns (uint256 cost) {
        (cost, ) = _quote(_single(bucket, shares));
    }

    /// Wei needed to buy the vector `quantities` (six numbers, one per bucket) now.
    function quoteBasket(uint256[] calldata quantities) external view returns (uint256 cost) {
        (cost, ) = _quote(quantities);
    }

    /// True if the oracle holds a report this market accepts:
    /// made at or after the season end, at or before the deadline, count in range.
    function hasValidReport() external view returns (bool) {
        (bool valid, , ) = _validReport();
        return valid;
    }

    // ------------------------------------------------------------------
    // Trading
    // ------------------------------------------------------------------

    /// Buy whole shares of one bucket. Reverts if the cost is above `maxCost`.
    /// Send at least the cost; the excess is returned.
    function buy(uint256 bucket, uint256 shares, uint256 maxCost) external payable nonReentrant {
        uint256 cost = _buy(_single(bucket, shares), maxCost);
        emit Trade(msg.sender, bucket, shares, cost);
        _refundExcess(cost);
    }

    /// Buy a vector of shares, one number per bucket, in ONE transaction.
    /// Example [0,0,0,1,2,3] is a stepped hedge. All legs fill or none.
    /// The charge is exactly C(q + quantities) - C(q). Reverts if it is above `maxCost`.
    /// Send at least the cost; the excess is returned.
    function buyBasket(uint256[] calldata quantities, uint256 maxCost) external payable nonReentrant {
        uint256 cost = _buy(quantities, maxCost);
        emit BasketTrade(msg.sender, quantities, cost);
        _refundExcess(cost);
    }

    // ------------------------------------------------------------------
    // Settlement and cancellation
    // ------------------------------------------------------------------

    /// Settle with the oracle's count. Anyone may call. Works once and is final.
    /// The report must be valid (see hasValidReport) and `disputeDelay` seconds old.
    function settle() external nonReentrant {
        require(state == State.Open, "Not open");
        (bool valid, uint16 count, uint64 reportedAt) = _validReport();
        require(valid, "No valid report");
        require(block.timestamp >= uint256(reportedAt) + disputeDelay, "Dispute window still open");

        uint256 w = bucketOf(count);
        state = State.Settled;
        settledCount = count;
        winningBucket = w;
        reserved = q[w] * unit;
        claimDeadline = uint64(block.timestamp) + claimPeriod;
        emit Settled(count, w, reportedAt, reserved, claimDeadline);
    }

    /// After the deadline, anyone may cancel if there is no valid report.
    /// A missing, late, voided, out-of-range or unreadable report all end here.
    function cancelAfterDeadline() external nonReentrant {
        require(state == State.Open, "Not open");
        require(block.timestamp > reportDeadline, "Deadline not passed");
        (bool valid, , ) = _validReport();
        require(!valid, "Valid report exists, call settle");
        _cancel("No valid report by deadline");
    }

    /// Emergency stop: the sponsor may cancel while trading is still open.
    /// Not allowed after tradingClose. Trading closes by the first season day,
    /// so the sponsor can not cancel after watching the season's weather.
    /// (The sponsor can still cancel on a pre-season forecast. Buyers get refunds.)
    function emergencyCancel() external onlySponsor nonReentrant {
        require(state == State.Open, "Not open");
        require(block.timestamp < tradingClose, "Trading closed, wait for the oracle");
        _cancel("Emergency cancel by sponsor");
    }

    // ------------------------------------------------------------------
    // Payouts
    // ------------------------------------------------------------------

    /// After settlement: each share of the winning bucket pays `unit` wei.
    function redeem() external nonReentrant {
        require(state == State.Settled, "Not settled");
        require(!swept, "Unclaimed funds were swept");
        uint256 shares = sharesOf[msg.sender][winningBucket];
        require(shares > 0, "Nothing to redeem");
        uint256 amount = shares * unit;
        sharesOf[msg.sender][winningBucket] = 0;
        reserved -= amount;
        emit Redeemed(msg.sender, shares, amount);
        _send(msg.sender, amount);
    }

    /// After a cancel: each buyer gets back exactly what they paid (cost basis).
    function claimRefund() external nonReentrant {
        require(state == State.Cancelled, "Not cancelled");
        require(!swept, "Unclaimed funds were swept");
        uint256 amount = paid[msg.sender];
        require(amount > 0, "Nothing to refund");
        paid[msg.sender] = 0;
        reserved -= amount;
        emit Refunded(msg.sender, amount);
        _send(msg.sender, amount);
    }

    /// After settlement or cancel: the sponsor takes everything not owed to buyers.
    function sponsorWithdraw() external onlySponsor nonReentrant {
        require(state != State.Open, "Market still open");
        uint256 amount = address(this).balance - reserved;
        require(amount > 0, "Nothing to withdraw");
        emit SponsorWithdrawal(msg.sender, amount);
        _send(msg.sender, amount);
    }

    /// Review item m5: money nobody claimed must not stay locked for ever.
    /// After claimDeadline (settle or cancel time + claimPeriod, at least 7 days)
    /// the sponsor may take what is left. Claims stop working after the sweep.
    function sweepUnclaimed() external onlySponsor nonReentrant {
        require(state != State.Open, "Market still open");
        require(block.timestamp > claimDeadline, "Claim period not over");
        require(!swept, "Already swept");
        uint256 amount = address(this).balance;
        swept = true;
        reserved = 0;
        emit UnclaimedSwept(msg.sender, amount);
        if (amount > 0) _send(msg.sender, amount);
    }

    // ------------------------------------------------------------------
    // Internals: oracle
    // ------------------------------------------------------------------

    /// Read the oracle without trusting it (review item M1).
    /// A plain Solidity call reverts if the target has no code or returns data that
    /// does not decode, and try/catch does not catch that. A low-level staticcall
    /// never reverts here: we get `success` and the raw bytes and check them ourselves.
    /// Any failure gives ok = false, which the callers treat as "no valid report".
    function _readOracle(address _oracle, string memory _station, uint32 _season)
        private
        view
        returns (SeasonData memory s)
    {
        // Make sure the oracle really gets ORACLE_GAS. Otherwise a caller could send
        // too little gas on purpose, make a good oracle fail, and force a cancel.
        require(gasleft() >= ORACLE_GAS + 30000, "Send more gas");
        (bool success, bytes memory data) = _oracle.staticcall{gas: ORACLE_GAS}(
            abi.encodeWithSelector(ISeasonCountOracle.getSeason.selector, _station, _season)
        );
        if (!success || data.length != ORACLE_RETURN_SIZE) return s;
        // Decode as seven plain numbers, then range-check each one.
        // (Decoding straight to bool/uint16/uint64 would revert on bad values.)
        (uint256 opened, uint256 start, uint256 end, uint256 numDays, uint256 reported, uint256 count, uint256 at) =
            abi.decode(data, (uint256, uint256, uint256, uint256, uint256, uint256, uint256));
        if (opened > 1 || reported > 1) return s;
        if (start > type(uint64).max || end > type(uint64).max || at > type(uint64).max) return s;
        if (numDays > type(uint16).max || count > type(uint16).max) return s;
        s.ok = true;
        s.opened = opened == 1;
        s.seasonStart = uint64(start);
        s.seasonEnd = uint64(end);
        s.seasonDays = uint16(numDays);
        s.reported = reported == 1;
        s.count = uint16(count);
        s.reportedAt = uint64(at);
    }

    /// A report is valid if it exists, was made in [seasonEnd, reportDeadline],
    /// and the count is between 0 and seasonDays.
    function _validReport() private view returns (bool valid, uint16 count, uint64 reportedAt) {
        SeasonData memory s = _readOracle(oracle, station, season);
        if (!s.ok || !s.reported) return (false, 0, 0);
        if (s.reportedAt < seasonEnd) return (false, 0, 0);     // too early (the real oracle refuses these)
        if (s.reportedAt > reportDeadline) return (false, 0, 0); // too late
        if (s.count > seasonDays) return (false, 0, 0);          // impossible count
        return (true, s.count, s.reportedAt);
    }

    function _cancel(string memory reason) private {
        state = State.Cancelled;
        reserved = totalPaid;
        claimDeadline = uint64(block.timestamp) + claimPeriod;
        emit Cancelled(msg.sender, reason, totalPaid, claimDeadline);
    }

    // ------------------------------------------------------------------
    // Internals: LMSR maths
    // ------------------------------------------------------------------

    function _checkEdges(uint16[] memory _edges, uint16 _seasonDays) private pure {
        require(_edges.length == NUM_BUCKETS - 1, "Need five edges");
        for (uint256 j = 1; j < _edges.length; j++) {
            require(_edges[j] > _edges[j - 1], "Edges not increasing");
        }
        // The top bucket (above the last edge) must be reachable.
        require(_edges[_edges.length - 1] < _seasonDays, "Last edge must be below season days");
    }

    /// The vector with `shares` in one bucket and 0 elsewhere.
    function _single(uint256 bucket, uint256 shares) private pure returns (uint256[] memory amounts) {
        require(bucket < NUM_BUCKETS, "Bad bucket");
        amounts = new uint256[](NUM_BUCKETS);
        amounts[bucket] = shares;
    }

    /// exp((q_j - max q) / b) for every j, and their sum, as 64.64 numbers.
    function _weights(uint256[] memory qm, uint256 _b) private pure returns (int128[] memory e, int128 sum) {
        uint256 n = qm.length;
        uint256 top = 0;
        uint256 iTop = 0;
        for (uint256 j = 0; j < n; j++) {
            if (qm[j] > top) {
                top = qm[j];
                iTop = j;
            }
        }
        e = new int128[](n);
        for (uint256 j = 0; j < n; j++) {
            if (j == iTop) {
                e[j] = ONE; // exp(0), exact
            } else {
                uint256 d = top - qm[j];
                // Below 2^-64 the weight is 0. The check also keeps divu in range.
                if (d < EXP_CUTOFF * _b) e[j] = ABDKMath64x64.divu(d, _b).neg().exp();
            }
            sum = sum.add(e[j]);
        }
    }

    /// C(q) in wei = max(q) * unit + floor( ln(sum of weights) * b * unit ).
    function _cost(uint256[] memory qm, uint256 _b, uint256 _unit) private pure returns (uint256) {
        uint256 top = 0;
        for (uint256 j = 0; j < qm.length; j++) if (qm[j] > top) top = qm[j];
        (, int128 sum) = _weights(qm, _b);
        return top * _unit + sum.ln().mulu(_b * _unit);
    }

    /// Cost of adding `amounts` to q, and the new C(q).
    function _quote(uint256[] memory amounts) private view returns (uint256 cost, uint256 newCost) {
        require(amounts.length == NUM_BUCKETS, "Need six quantities");
        uint256[] memory qm = q;
        uint256 total = 0;
        for (uint256 j = 0; j < NUM_BUCKETS; j++) {
            // Checked before adding, so an absurd number gives this message and not an overflow panic.
            require(amounts[j] <= MAX_Q, "Quantity too large");
            qm[j] += amounts[j];
            require(qm[j] <= MAX_Q, "Quantity too large");
            total += amounts[j];
        }
        require(total > 0, "Zero quantity");
        newCost = _cost(qm, b, unit);
        // C never decreases when q grows. The guard only matters for rounding at the last wei.
        cost = newCost > costNow ? newCost - costNow : 0;
    }

    function _buy(uint256[] memory amounts, uint256 maxCost) private returns (uint256 cost) {
        require(state == State.Open, "Not open");
        require(block.timestamp < tradingClose, "Trading closed");
        uint256 newCost;
        (cost, newCost) = _quote(amounts);
        // Review item m2: a bucket priced below 2^-64 would cost 0 wei. Nobody gets shares for free.
        require(cost > 0, "Cost rounds to zero");
        require(cost <= maxCost, "Cost above slippage limit");
        require(msg.value >= cost, "Insufficient payment");

        // effects
        for (uint256 j = 0; j < NUM_BUCKETS; j++) {
            if (amounts[j] > 0) {
                q[j] += amounts[j];
                sharesOf[msg.sender][j] += amounts[j];
            }
        }
        costNow = newCost;
        paid[msg.sender] += cost;
        totalPaid += cost;
    }

    function _refundExcess(uint256 cost) private {
        if (msg.value > cost) _send(msg.sender, msg.value - cost);
    }

    function _send(address to, uint256 amount) private {
        (bool ok, ) = payable(to).call{value: amount}("");
        require(ok, "Transfer failed");
    }
}
