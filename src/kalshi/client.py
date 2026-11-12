"""Read-only Kalshi public API client with on-disk caching.

No account, no auth, no trading. Every response is cached under data/raw/kalshi/
(git-ignored). Raw rows must never be copied into results/ or docs/.

Politeness: a global gap between requests (floor 0.25 s, so never more than 4 per
second, also across threads). The gap adapts: it widens on HTTP 429 and narrows
slowly on success. Exponential backoff on 429 and 5xx.
"""
from __future__ import annotations

import json
import re
import threading
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import requests

BASE = "https://api.elections.kalshi.com/trade-api/v2"
REPO = Path(__file__).resolve().parents[2]
RAW = REPO / "data" / "raw" / "kalshi"

MONTHS = {m: i + 1 for i, m in enumerate(
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"])}
_EVT_RE = re.compile(r"-(\d{2})([A-Z]{3})(\d{2})$")


def event_date_from_ticker(event_ticker: str) -> date:
    """'KXHIGHNY-26AUG14' -> date(2026, 8, 14). Raises ValueError if it does not parse."""
    m = _EVT_RE.search(event_ticker)
    if not m or m.group(2) not in MONTHS:
        raise ValueError(f"cannot parse event date from {event_ticker!r}")
    return date(2000 + int(m.group(1)), MONTHS[m.group(2)], int(m.group(3)))


def parse_ts(s: str) -> int:
    """ISO-8601 UTC string -> unix seconds."""
    return int(datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc).timestamp())


class KalshiError(RuntimeError):
    pass


class KalshiClient:
    def __init__(self, raw_dir: Path = RAW, min_gap: float = 0.25, max_retries: int = 12, max_gap: float = 1.5,
                 session: requests.Session | None = None):
        self.raw = Path(raw_dir)
        self.min_gap = min_gap
        self.gap = min_gap
        self.max_gap = max(max_gap, min_gap)
        self.max_retries = max_retries
        self.s = session or requests.Session()
        self.s.headers["User-Agent"] = "course-research-readonly/0.1"
        self._next = 0.0
        self._lock = threading.Lock()
        self.n_requests = 0
        self.n_429 = 0

    # ---- low level -------------------------------------------------------
    def get(self, path: str, params: dict[str, Any] | None = None, ok_404: bool = False) -> dict | None:
        """GET with adaptive rate limit and backoff. Returns parsed JSON, or None on 404 if ok_404.

        The gap between requests grows by 10% on each HTTP 429 (cap max_gap) and
        shrinks by 2% on each success (floor min_gap). Observed 2026-11-11: the public
        endpoints return 429 irregularly even at 1 request per second, so a hard
        exponential slowdown only wastes time; a short pause and retry is enough.
        """
        url = BASE + path
        delay = 1.0
        for _attempt in range(self.max_retries):
            with self._lock:  # thread-safe: hand out send slots `gap` apart
                slot = max(time.monotonic(), self._next)
                self._next = slot + self.gap
                self.n_requests += 1
            wait = slot - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            try:
                r = self.s.get(url, params=params, timeout=30)
            except requests.RequestException:
                time.sleep(delay)
                delay = min(delay * 2, 60)
                continue
            if r.status_code == 200:
                with self._lock:
                    self.gap = max(self.min_gap, self.gap * 0.98)
                return r.json()
            if r.status_code == 404 and ok_404:
                return None
            if r.status_code == 429 or r.status_code >= 500:
                with self._lock:
                    self.n_429 += r.status_code == 429
                    self.gap = min(self.max_gap, self.gap * 1.1)
                    self._next = max(self._next, time.monotonic() + delay)  # pause all threads
                time.sleep(delay)
                delay = min(delay * 1.5, 30)
                continue
            raise KalshiError(f"HTTP {r.status_code} for {url} {params}: {r.text[:200]}")
        raise KalshiError(f"gave up after {self.max_retries} tries: {url} {params}")

    def _paged(self, path: str, params: dict[str, Any], key: str) -> Iterator[dict]:
        params = dict(params)
        while True:
            d = self.get(path, params)
            rows = d.get(key) or []
            yield from rows
            cur = d.get("cursor")
            if not cur or not rows:
                return
            params["cursor"] = cur

    # ---- cached endpoints ------------------------------------------------
    def series(self, ticker: str, refresh: bool = False) -> dict:
        p = self.raw / "series" / f"{ticker}.json"
        if p.exists() and not refresh:
            return json.loads(p.read_text())
        d = self.get(f"/series/{ticker}")
        _write_json(p, d)
        return d

    def cutoff(self) -> dict:
        d = self.get("/historical/cutoff")
        _write_json(self.raw / "historical_cutoff.json", d)
        return d

    def events(self, series_ticker: str, refresh: bool = False) -> list[dict]:
        """All settled events of a series (live endpoint, cursor paging)."""
        p = self.raw / "events" / f"{series_ticker}.json"
        if p.exists() and not refresh:
            return json.loads(p.read_text())
        rows = list(self._paged("/events", {"series_ticker": series_ticker, "limit": 200,
                                            "status": "settled"}, "events"))
        _write_json(p, rows)
        return rows

    def markets(self, series_ticker: str, refresh: bool = False) -> list[dict]:
        """All settled markets of a series: historical tier plus live tier, de-duplicated.

        Each row gets a '_tier' field ('historical' or 'live') that says which
        candlestick endpoint serves it.
        """
        p = self.raw / "markets" / f"{series_ticker}.json"
        if p.exists() and not refresh:
            return json.loads(p.read_text())
        out: dict[str, dict] = {}
        for m in self._paged("/historical/markets", {"series_ticker": series_ticker, "limit": 1000},
                             "markets"):
            m["_tier"] = "historical"
            out[m["ticker"]] = m
        for m in self._paged("/markets", {"series_ticker": series_ticker, "limit": 1000,
                                          "status": "settled"}, "markets"):
            if m["ticker"] not in out:
                m["_tier"] = "live"
                out[m["ticker"]] = m
        rows = list(out.values())
        _write_json(p, rows)
        return rows

    def candles_path(self, series_ticker: str, market_ticker: str) -> Path:
        return self.raw / "candles" / series_ticker / f"{market_ticker}.json"

    def candles(self, series_ticker: str, market: dict, refresh: bool = False) -> list[dict]:
        """Hourly candles over the market's whole life (open_time .. close_time). Cached per market."""
        p = self.candles_path(series_ticker, market["ticker"])
        if p.exists() and not refresh:
            return json.loads(p.read_text())["candlesticks"]
        start, end = parse_ts(market["open_time"]), parse_ts(market["close_time"])
        params = {"start_ts": start - 3600, "end_ts": end + 3600, "period_interval": 60}
        t = market["ticker"]
        order = ["historical", "live"] if market.get("_tier", "historical") == "historical" else ["live", "historical"]
        d = None
        for tier in order:
            path = (f"/historical/markets/{t}/candlesticks" if tier == "historical"
                    else f"/series/{series_ticker}/markets/{t}/candlesticks")
            d = self.get(path, params, ok_404=True)
            if d is not None:
                break
        if d is None:
            d = {"candlesticks": [], "_not_found": True}
        d["_params"] = params
        _write_json(p, d)
        return d["candlesticks"]


    def candles_batch(self, series_ticker: str, markets: list[dict]) -> int:
        """Live-tier only: one call for several markets (GET /markets/candlesticks).

        Writes one cache file per market, same format as candles(). Keep batches to
        about 5 events (30 markets); larger windows were rejected with HTTP 400.
        Returns the number of files written.
        """
        start = min(parse_ts(m["open_time"]) for m in markets) - 3600
        end = max(parse_ts(m["close_time"]) for m in markets) + 3600
        params = {"market_tickers": ",".join(m["ticker"] for m in markets),
                  "start_ts": start, "end_ts": end, "period_interval": 60}
        d = self.get("/markets/candlesticks", params)
        got = {x["market_ticker"]: x["candlesticks"] for x in d.get("markets", [])}
        n = 0
        for m in markets:
            if m["ticker"] in got:
                _write_json(self.candles_path(series_ticker, m["ticker"]),
                            {"candlesticks": got[m["ticker"]], "_batch": True,
                             "_params": {"start_ts": start, "end_ts": end, "period_interval": 60}})
                n += 1
        return n


def _write_json(p: Path, obj: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj))
    tmp.replace(p)
