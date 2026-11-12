"""Phase 1 Kalshi rain: market scope, quotes at fixed decision times, fees, calibration bins.

Pure functions (no network). Raw per-market rows built from these stay under
data/raw/kalshi/rain/ (git-ignored); only aggregates go to data/processed/kalshi_rain/.

Rules fixed here
- Decision times: 36, 24, 12 and 2 hours before the market's close_time.
- Quote at a decision time = the close quote of the last hourly candle that ENDED at or before
  that time (carry-forward; a candle that ends after the decision time is never used).
- Stale: the carried quote is older than 6 hours (age > 6 h). A stale quote is not usable.
- One-sided book: ask = 1.00 (nobody offers to sell) or bid = 0.00 (nobody bids).
- buyable = fresh quote and ask < 1.00.  two_sided = fresh, ask < 1.00 and bid > 0.00.
- Taker fee = round_up_to_cent(0.07 * C * P * (1 - P)) per order (docs/contract_spec.md section 3).
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Iterable, Sequence

from .client import RAW, event_date_from_ticker, parse_ts

DECISION_HOURS = (36, 24, 12, 2)
STALE_HOURS = 6.0
CITIES = {"TTN": "KTTN", "PHIL": "KPHL", "EWR": "KEWR", "NYC": "KNYC"}  # Kalshi city code -> NWS CLI station
GHCN = {"TTN": "USW00014792", "PHIL": "USW00013739", "EWR": "USW00014734", "NYC": "USW00094728"}
FEE_RATE = 0.07


# ---------------------------------------------------------------- scope
def scope_markets(raw: Path = RAW) -> list[dict]:
    """Markets in the Phase 1 pull, in pull order. Adds _series, _city, _date, _group to each row."""
    out: list[dict] = []
    kx = json.loads((raw / "rain" / "markets_KXRAIN.json").read_text())
    by_city: dict[str, list[dict]] = {c: [] for c in ("TTN", "PHIL", "EWR", "NYC")}
    for m in kx:
        city = m["ticker"].split("-")[-1]
        if city not in by_city or m.get("result") not in ("yes", "no"):
            continue
        d = event_date_from_ticker(m["event_ticker"])
        if 5 <= d.month <= 9:
            m.update(_series="KXRAIN", _city=city, _date=d.isoformat(), _group=f"KXRAIN-{city}-{d.year}")
            by_city[city].append(m)
    for city in ("TTN", "PHIL", "EWR", "NYC"):
        out += sorted(by_city[city], key=lambda m: m["_date"])
    nyc = json.loads((raw / "rain" / "markets_KXRAINNYC.json").read_text())
    by_year: dict[int, list[dict]] = {}
    for m in nyc:
        if not m["ticker"].endswith(("-T0", "-T0.00")) or m.get("result") not in ("yes", "no"):
            continue
        d = event_date_from_ticker(m["event_ticker"])
        if 5 <= d.month <= 9:
            m.update(_series="KXRAINNYC", _city="NYC", _date=d.isoformat(), _group=f"KXRAINNYC-NYC-{d.year}")
            by_year.setdefault(d.year, []).append(m)
    for y in (2026, 2025, 2022, 2021):
        out += sorted(by_year.get(y, []), key=lambda m: m["_date"])
    return out


# ---------------------------------------------------------------- quotes
def _num(x) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(v) else v


def side_close(side) -> float | None:
    """Close of a candle's yes_bid / yes_ask block, in dollars. None if absent."""
    if not isinstance(side, dict):
        return None
    if side.get("close_dollars") is not None:
        return _num(side["close_dollars"])
    v = _num(side.get("close"))
    if v is None:
        return None
    return v / 100.0 if v > 1.0 else v  # integer cents in the oldest API format


def candle_quotes(candles: Iterable[dict]) -> list[tuple[int, float | None, float | None]]:
    """[(end_period_ts, bid, ask)] sorted by time."""
    q = [(int(k["end_period_ts"]), side_close(k.get("yes_bid")), side_close(k.get("yes_ask"))) for k in candles]
    return sorted(q, key=lambda r: r[0])


def quote_at(quotes: Sequence[tuple[int, float | None, float | None]], close_ts: int, hours_before: float,
             stale_hours: float = STALE_HOURS) -> dict:
    """Quote carried forward to `hours_before` hours before close.

    Returns bid, ask, age_hours, and flags:
      has_quote   a candle with both bid and ask ended at or before the decision time
      stale       has_quote and age > stale_hours
      ask_is_1    ask >= 1.00 (no seller)        bid_is_0   bid <= 0.00 (no bidder)
      buyable     has_quote, not stale, ask < 1.00
      two_sided   buyable and bid > 0.00
      spread, mid only when two_sided (else None)
    """
    t = close_ts - int(round(hours_before * 3600))
    last = None
    for ts, b, a in quotes:
        if ts > t:
            break
        if b is not None and a is not None:
            last = (ts, b, a)
    r = {"bid": None, "ask": None, "age_hours": None, "has_quote": False, "stale": False, "ask_is_1": False,
         "bid_is_0": False, "buyable": False, "two_sided": False, "spread": None, "mid": None}
    if last is None:
        return r
    ts, b, a = last
    age = (t - ts) / 3600.0
    fresh = age <= stale_hours
    r.update(bid=b, ask=a, age_hours=age, has_quote=True, stale=not fresh,
             ask_is_1=a >= 1.0 - 1e-9, bid_is_0=b <= 1e-9)
    r["buyable"] = fresh and not r["ask_is_1"]
    r["two_sided"] = r["buyable"] and not r["bid_is_0"]
    if r["two_sided"]:
        r["spread"] = round(a - b, 4)
        r["mid"] = round((a + b) / 2, 4)
    return r


def market_row(m: dict, candles: list[dict] | None) -> dict:
    """One row of the per-market quote table (raw; never published)."""
    close = parse_ts(m["close_time"])
    row = {"series": m["_series"], "city": m["_city"], "date": m["_date"], "year": int(m["_date"][:4]),
           "ticker": m["ticker"], "group": m["_group"], "result": 1 if m["result"] == "yes" else 0,
           "close_time": m["close_time"], "life_hours": round((close - parse_ts(m["open_time"])) / 3600, 1),
           "pulled": candles is not None, "n_candles": len(candles) if candles is not None else None}
    q = candle_quotes(candles or [])
    for h in DECISION_HOURS:
        for k, v in quote_at(q, close, h).items():
            row[f"{k}_{h}"] = v
    return row


# ---------------------------------------------------------------- fee
def taker_fee(price: float, contracts: int = 1, rate: float = FEE_RATE) -> float:
    """Kalshi taker fee in dollars for one order: round_up_to_cent(rate * C * P * (1 - P)).

    Whole-cent rounding per order (the reading used in docs/contract_spec.md; whether rounding is
    per order or per fill is unverified there). Zero at P = 0 or 1.
    """
    if not 0.0 <= price <= 1.0:
        raise ValueError("price must be in [0, 1] dollars")
    if contracts < 0:
        raise ValueError("contracts must be >= 0")
    cents = rate * contracts * price * (1.0 - price) * 100.0
    return math.ceil(round(cents, 6)) / 100.0  # round() removes binary noise such as 1.7500000000000002


def taker_fee_per_contract(price: float, contracts: int = 1, rate: float = FEE_RATE) -> float:
    return taker_fee(price, contracts, rate) / contracts if contracts else 0.0


# ---------------------------------------------------------------- calibration
def calibration_table(prices: Sequence[float], outcomes: Sequence[int],
                      edges: Sequence[float] = (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)) -> list[dict]:
    """Price bins vs realised frequency. Bins are [lo, hi); the last bin also includes hi.

    Returns one dict per bin: lo, hi, n, mean_price, yes_share (None when n = 0).
    """
    if len(prices) != len(outcomes):
        raise ValueError("prices and outcomes differ in length")
    nb = len(edges) - 1
    acc = [[0, 0.0, 0] for _ in range(nb)]
    for p, y in zip(prices, outcomes):
        if p is None or p != p or p < edges[0] or p > edges[-1]:
            raise ValueError(f"price {p!r} outside [{edges[0]}, {edges[-1]}]")
        i = nb - 1
        for j in range(nb):
            if p < edges[j + 1] - 1e-12:
                i = j
                break
        acc[i][0] += 1; acc[i][1] += p; acc[i][2] += int(y)
    return [{"lo": edges[i], "hi": edges[i + 1], "n": n,
             "mean_price": (s / n if n else None), "yes_share": (k / n if n else None)}
            for i, (n, s, k) in enumerate(acc)]


def brier(prob: Sequence[float], outcomes: Sequence[int]) -> float:
    n = len(prob)
    return sum((p - y) ** 2 for p, y in zip(prob, outcomes)) / n if n else float("nan")
