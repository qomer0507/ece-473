// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Same fixed-point library as Labs 7 and 8 (signed 64.64 numbers).
import "abdk-libraries-solidity/ABDKMath64x64.sol";
// Same guard as the Lab 13 oracle (OpenZeppelin 4.9.6).
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

/// Read interface of the temperature oracle (see TemperatureOracle.sol).
interface ITemperatureOracle {
    /// @return exists     true if a report was stored for (station, day)
    /// @return tempF      daily maximum temperature, whole deg F
    /// @return reportedAt block timestamp of the report
    function getReport(string calldata station, uint32 day)
        external
        view
        returns (bool exists, int16 tempF, uint64 reportedAt);
}

/*
    Multi-outcome LMSR market on one station's daily maximum temperature.
    TESTNET ONLY. Class project (ECE 473). Not audited.

    Brackets
      `bounds` holds n-1 strictly increasing whole-degree boundaries.
        bracket 0     : T <  bounds[0]
        bracket j     : bounds[j-1] <= T < bounds[j]
        bracket n-1   : T >= bounds[n-2]
      The brackets are exhaustive and do not overlap. `strike` (90) must be
      one of the boundaries, so "T >= strike" is exactly the brackets
      strikeIndex .. n-1.

    Units
      Shares are whole numbers. One winning share pays `unit` wei.
      `b` is the LMSR liquidity parameter in shares (as in Lab 7).

    Cost function (log-sum-exp form, as in Lab 8, extended to n outcomes)
      C(q) = b * ln( sum_j exp(q_j / b) )
           = max(q) + b * ln( sum_j exp( (q_j - max(q)) / b ) )
      Every exponent is <= 0, so exp never overflows. The term of the
      largest q_j is exactly 1, so the sum is in [1, n] and ln is in [0, ln n].

    Charging rule
      costNow = C(q) is stored. A buy is charged C(q_new) - costNow.
      The charges telescope, so the total paid by traders is exactly
      C(q) - C(q0), whatever the order of the trades.

    Collateral rule
      The sponsor funds at least C(q0) at creation (q0 = 0 gives b*ln(n)).
      Then balance >= C(q) >= max(q) * unit >= any possible payout.
*/
contract BracketLMSR is ReentrancyGuard {
    using ABDKMath64x64 for int128;

    enum State { Open, Settled, Cancelled }

    // ---- input bounds (see docs/status/viktor.md) ----
    uint256 public constant MAX_BRACKETS = 32;
    uint256 public constant MAX_B = 1e12;        // shares
    uint256 public constant MAX_UNIT = 1 ether;  // wei per winning share
    uint256 public constant MAX_Q = 1e15;        // shares per bracket
    // exp(-x) is below 2^-64 for x >= 45 and is treated as 0.
    uint256 private constant EXP_CUTOFF = 45;
    int128 private constant ONE = 0x10000000000000000; // 1.0 in 64.64

    // ---- market definition ----
    address public immutable sponsor;
    ITemperatureOracle public immutable oracle;
    string public station;                 // e.g. "USW00014734"
    uint32 public immutable marketDay;     // UTC day number = unix time / 86400
    int16 public immutable strike;         // 90
    uint256 public immutable strikeIndex;  // first bracket with T >= strike
    uint256 public immutable b;            // liquidity parameter, in shares
    uint256 public immutable unit;         // wei paid per winning share
    uint64 public immutable tradingClose;    // buys allowed before this time
    uint64 public immutable observationEnd;  // a report must be made at or after this time
    uint64 public immutable reportDeadline;  // a report must be made at or before this time
    int16[] private bounds;

    // ---- market state ----
    State public state;
    uint256[] private q;        // LMSR quantities (seed q0 + shares sold)
    uint256[] private seed;     // q0, the sponsor's prior. Pays nobody.
    uint256 public costNow;     // C(q) in wei
    uint256 public requiredFunding; // C(q0) in wei
    uint256 public funding;     // wei sent by the sponsor at creation
    uint256 public totalPaid;   // wei paid by all traders
    uint256 public reserved;    // wei still owed to traders after settle/cancel
    int16 public settledTemp;
    uint256 public winningBracket;

    mapping(address => mapping(uint256 => uint256)) public sharesOf; // trader => bracket => shares
    mapping(address => uint256) public paid;                          // trader => wei paid (cost basis)

    // ---- events (one per state change) ----
    event MarketCreated(address indexed sponsor, address indexed oracle, string station, uint32 marketDay,
        uint256 numBrackets, int16 strike, uint256 b, uint256 unit, uint256 funding, uint256 requiredFunding);
    event Trade(address indexed trader, uint256 indexed bracket, uint256 shares, uint256 cost);
    event BasketTrade(address indexed trader, uint256 firstBracket, uint256 lastBracket, uint256 sharesEach, uint256 cost);
    event Settled(int16 tempF, uint256 indexed winningBracket, uint64 reportedAt, uint256 owedToWinners);
    event Cancelled(address indexed caller, string reason, uint256 owedToTraders);
    event Redeemed(address indexed trader, uint256 shares, uint256 amount);
    event Refunded(address indexed trader, uint256 amount);
    event SponsorWithdrawal(address indexed sponsor, uint256 amount);

    modifier onlySponsor() {
        require(msg.sender == sponsor, "Not sponsor");
        _;
    }

    /// @param _oracle         TemperatureOracle (or MockOracle in tests)
    /// @param _station        station id the oracle reports under
    /// @param _marketDay      UTC day number (unix time / 86400) of the settled day
    /// @param _bounds         n-1 increasing bracket boundaries in deg F
    /// @param _strike         boundary used by the basket ("T >= strike"), 90
    /// @param _b              LMSR liquidity parameter, in shares
    /// @param _unit           wei paid per winning share
    /// @param _initialQ       empty for a uniform prior, or n seed quantities with minimum 0
    /// @param _tradingClose   unix time, end of trading
    /// @param _observationEnd unix time, end of the observed day (>= _tradingClose)
    /// @param _reportDeadline unix time, last moment for a valid report
    /// msg.value must cover the worst-case loss C(q0) (= b*ln(n)*unit for a uniform prior).
    constructor(
        address _oracle,
        string memory _station,
        uint32 _marketDay,
        int16[] memory _bounds,
        int16 _strike,
        uint256 _b,
        uint256 _unit,
        uint256[] memory _initialQ,
        uint64 _tradingClose,
        uint64 _observationEnd,
        uint64 _reportDeadline
    ) payable {
        require(_oracle != address(0), "Zero oracle");
        require(_b > 0 && _b <= MAX_B, "b out of range");
        require(_unit > 0 && _unit <= MAX_UNIT, "unit out of range");
        require(_tradingClose > block.timestamp, "Trading close in the past");
        require(_observationEnd >= _tradingClose, "Observation ends before trading");
        require(_reportDeadline > _observationEnd, "Deadline before observation end");

        sponsor = msg.sender;
        oracle = ITemperatureOracle(_oracle);
        station = _station;
        marketDay = _marketDay;
        strike = _strike;
        b = _b;
        unit = _unit;
        tradingClose = _tradingClose;
        observationEnd = _observationEnd;
        reportDeadline = _reportDeadline;

        strikeIndex = _checkBounds(_bounds, _strike);
        bounds = _bounds;

        uint256 n = _bounds.length + 1;
        uint256[] memory q0 = new uint256[](n);
        if (_initialQ.length != 0) {
            require(_initialQ.length == n, "initialQ length");
            uint256 lowest = type(uint256).max;
            for (uint256 j = 0; j < n; j++) {
                require(_initialQ[j] <= MAX_Q, "initialQ too large");
                if (_initialQ[j] < lowest) lowest = _initialQ[j];
                q0[j] = _initialQ[j];
            }
            require(lowest == 0, "initialQ minimum must be 0");
        }
        q = q0;
        seed = q0;

        uint256 c0 = _cost(q0, _b, _unit);
        require(msg.value >= c0, "Funding below worst-case loss");
        costNow = c0;
        requiredFunding = c0;
        funding = msg.value;

        emit MarketCreated(msg.sender, _oracle, _station, _marketDay, n, _strike, _b, _unit, msg.value, c0);
    }

    // ------------------------------------------------------------------
    // Views
    // ------------------------------------------------------------------

    function numBrackets() public view returns (uint256) {
        return q.length;
    }

    function getBounds() external view returns (int16[] memory) {
        return bounds;
    }

    /// LMSR quantities per bracket (seed + sold).
    function getQuantities() external view returns (uint256[] memory) {
        return q;
    }

    /// Shares sold to traders per bracket (these are the only shares that pay).
    function getSold() public view returns (uint256[] memory sold) {
        uint256 n = q.length;
        sold = new uint256[](n);
        for (uint256 j = 0; j < n; j++) sold[j] = q[j] - seed[j];
    }

    /// Bracket index that contains temperature `tempF`.
    function bracketOf(int16 tempF) public view returns (uint256) {
        uint256 m = bounds.length;
        for (uint256 j = 0; j < m; j++) {
            if (tempF < bounds[j]) return j;
        }
        return m;
    }

    /// LMSR cost C(q) in wei for an arbitrary quantity vector (testing aid).
    function costOf(uint256[] memory quantities) external view returns (uint256) {
        require(quantities.length == q.length, "Length");
        return _cost(quantities, b, unit);
    }

    /// Instantaneous prices of all brackets, 1e18 = 100%. They sum to 1 up to rounding down.
    function prices() public view returns (uint256[] memory p) {
        uint256 n = q.length;
        uint256[] memory qm = q;
        (int128[] memory e, int128 sum) = _weights(qm, b);
        p = new uint256[](n);
        for (uint256 j = 0; j < n; j++) p[j] = e[j].div(sum).mulu(1e18);
    }

    /// Instantaneous price of one bracket, 1e18 = 100%.
    function price(uint256 bracket) external view returns (uint256) {
        require(bracket < q.length, "Bad bracket");
        return prices()[bracket];
    }

    /// Instantaneous price of "T >= strike" (sum of the basket brackets), 1e18 = 100%.
    function priceAtOrAboveStrike() external view returns (uint256 total) {
        uint256[] memory p = prices();
        for (uint256 j = strikeIndex; j < p.length; j++) total += p[j];
    }

    /// Wei needed to buy `shares` of one bracket now.
    function quoteBuy(uint256 bracket, uint256 shares) public view returns (uint256) {
        require(bracket < q.length, "Bad bracket");
        (uint256 cost, ) = _quote(bracket, bracket, shares);
        return cost;
    }

    /// Wei needed to buy `sharesEach` of every bracket at or above the strike now.
    /// The basket pays sharesEach * unit if T >= strike, else 0.
    function quoteBasket(uint256 sharesEach) public view returns (uint256) {
        (uint256 cost, ) = _quote(strikeIndex, q.length - 1, sharesEach);
        return cost;
    }

    /// Largest amount the contract could owe to traders right now, in wei.
    function maxLiability() public view returns (uint256) {
        if (state != State.Open) return reserved;
        uint256 n = q.length;
        uint256 top = 0;
        for (uint256 j = 0; j < n; j++) {
            uint256 s = q[j] - seed[j];
            if (s > top) top = s;
        }
        uint256 payout = top * unit;
        // On a cancel the traders get their cost basis back instead.
        return payout > totalPaid ? payout : totalPaid;
    }

    // ------------------------------------------------------------------
    // Trading
    // ------------------------------------------------------------------

    /// Buy whole shares of one bracket. Reverts if the cost exceeds `maxCost`.
    /// Send at least the cost; the excess is returned.
    function buy(uint256 bracket, uint256 shares, uint256 maxCost) external payable nonReentrant {
        require(bracket < q.length, "Bad bracket");
        uint256 cost = _buyRange(bracket, bracket, shares, maxCost);
        emit Trade(msg.sender, bracket, shares, cost);
        _refundExcess(cost);
    }

    /// Buy `sharesEach` of every bracket at or above the strike in one transaction.
    /// All legs fill or none. Reverts if the total cost exceeds `maxCost`.
    function buyBasket(uint256 sharesEach, uint256 maxCost) external payable nonReentrant {
        uint256 last = q.length - 1;
        uint256 cost = _buyRange(strikeIndex, last, sharesEach, maxCost);
        emit BasketTrade(msg.sender, strikeIndex, last, sharesEach, cost);
        _refundExcess(cost);
    }

    // ------------------------------------------------------------------
    // Settlement and cancellation
    // ------------------------------------------------------------------

    /// Settle with the oracle's report for the market day. Anyone may call.
    /// The report must exist, be made at or after observationEnd (not stale)
    /// and at or before reportDeadline (not late). Works once.
    function settle() external nonReentrant {
        require(state == State.Open, "Not open");
        require(block.timestamp >= observationEnd, "Observation not over");
        (bool exists, int16 tempF, uint64 reportedAt) = oracle.getReport(station, marketDay);
        require(exists, "No report for market day");
        require(reportedAt >= observationEnd, "Stale report");
        require(reportedAt <= reportDeadline, "Late report");

        uint256 w = bracketOf(tempF);
        state = State.Settled;
        settledTemp = tempF;
        winningBracket = w;
        reserved = (q[w] - seed[w]) * unit;
        emit Settled(tempF, w, reportedAt, reserved);
    }

    /// After the deadline, anyone may cancel if there is no valid report.
    /// A missing, stale, late or unreadable report all end here.
    function cancelAfterDeadline() external nonReentrant {
        require(state == State.Open, "Not open");
        require(block.timestamp > reportDeadline, "Deadline not passed");
        require(!_hasValidReport(), "Valid report exists, call settle");
        _cancel("No valid report by deadline");
    }

    /// Emergency stop: the sponsor may cancel while trading is still open.
    /// Not allowed after tradingClose, so the sponsor cannot cancel a market
    /// once the temperature is being observed and a loss is in sight.
    /// After tradingClose the only exits are settle() and cancelAfterDeadline().
    function emergencyCancel() external onlySponsor nonReentrant {
        require(state == State.Open, "Not open");
        require(block.timestamp < tradingClose, "Trading closed, wait for the oracle");
        _cancel("Emergency cancel by sponsor");
    }

    // ------------------------------------------------------------------
    // Payouts
    // ------------------------------------------------------------------

    /// After settlement: winning shares pay `unit` wei each.
    function redeem() external nonReentrant {
        require(state == State.Settled, "Not settled");
        uint256 shares = sharesOf[msg.sender][winningBracket];
        require(shares > 0, "Nothing to redeem");
        uint256 amount = shares * unit;
        sharesOf[msg.sender][winningBracket] = 0;
        reserved -= amount;
        emit Redeemed(msg.sender, shares, amount);
        _send(msg.sender, amount);
    }

    /// After a cancel: each trader gets back exactly what they paid (cost basis).
    function claimRefund() external nonReentrant {
        require(state == State.Cancelled, "Not cancelled");
        uint256 amount = paid[msg.sender];
        require(amount > 0, "Nothing to refund");
        paid[msg.sender] = 0;
        reserved -= amount;
        emit Refunded(msg.sender, amount);
        _send(msg.sender, amount);
    }

    /// After settlement or cancel: the sponsor takes everything not owed to traders.
    function sponsorWithdraw() external onlySponsor nonReentrant {
        require(state != State.Open, "Market still open");
        uint256 amount = address(this).balance - reserved;
        require(amount > 0, "Nothing to withdraw");
        emit SponsorWithdrawal(msg.sender, amount);
        _send(msg.sender, amount);
    }

    // ------------------------------------------------------------------
    // Internals
    // ------------------------------------------------------------------

    function _checkBounds(int16[] memory _bounds, int16 _strike) private pure returns (uint256 idx) {
        uint256 m = _bounds.length;
        require(m >= 1 && m + 1 <= MAX_BRACKETS, "Bad number of brackets");
        bool found = false;
        for (uint256 j = 0; j < m; j++) {
            if (j > 0) require(_bounds[j] > _bounds[j - 1], "Bounds not increasing");
            if (_bounds[j] == _strike) {
                found = true;
                idx = j + 1; // bracket j+1 starts at bounds[j]
            }
        }
        require(found, "Strike is not a boundary");
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

    /// C(q) in wei = max(q)*unit + floor( ln(sum) * b * unit ).
    function _cost(uint256[] memory qm, uint256 _b, uint256 _unit) private pure returns (uint256) {
        uint256 n = qm.length;
        uint256 top = 0;
        for (uint256 j = 0; j < n; j++) if (qm[j] > top) top = qm[j];
        (, int128 sum) = _weights(qm, _b);
        return top * _unit + sum.ln().mulu(_b * _unit);
    }

    /// Cost of adding `shares` to every bracket in [first, last], and the new C(q).
    function _quote(uint256 first, uint256 last, uint256 shares) private view returns (uint256 cost, uint256 newCost) {
        require(shares > 0, "Zero shares");
        uint256[] memory qm = q;
        for (uint256 j = first; j <= last; j++) {
            qm[j] += shares;
            require(qm[j] <= MAX_Q, "Quantity too large");
        }
        newCost = _cost(qm, b, unit);
        // C is increasing in q. The guard only matters for rounding at the last wei.
        cost = newCost > costNow ? newCost - costNow : 0;
    }

    function _buyRange(uint256 first, uint256 last, uint256 shares, uint256 maxCost) private returns (uint256 cost) {
        require(state == State.Open, "Not open");
        require(block.timestamp < tradingClose, "Trading closed");
        uint256 newCost;
        (cost, newCost) = _quote(first, last, shares);
        require(cost <= maxCost, "Cost above slippage limit");
        require(msg.value >= cost, "Insufficient payment");

        // effects
        for (uint256 j = first; j <= last; j++) {
            q[j] += shares;
            sharesOf[msg.sender][j] += shares;
        }
        if (newCost > costNow) costNow = newCost;
        paid[msg.sender] += cost;
        totalPaid += cost;
    }

    function _hasValidReport() private view returns (bool) {
        try oracle.getReport(station, marketDay) returns (bool exists, int16, uint64 reportedAt) {
            return exists && reportedAt >= observationEnd && reportedAt <= reportDeadline;
        } catch {
            return false; // a broken oracle must not block refunds
        }
    }

    function _cancel(string memory reason) private {
        state = State.Cancelled;
        reserved = totalPaid;
        emit Cancelled(msg.sender, reason, totalPaid);
    }

    function _refundExcess(uint256 cost) private {
        if (msg.value > cost) _send(msg.sender, msg.value - cost);
    }

    function _send(address to, uint256 amount) private {
        (bool ok, ) = payable(to).call{value: amount}("");
        require(ok, "Transfer failed");
    }
}
