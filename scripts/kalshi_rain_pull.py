"""Phase 1 Kalshi rain pull: hourly candlesticks (yes_bid, yes_ask) for the daily rain markets, May-Sep.

Scope (about 520 markets):
  KXRAIN city markets TTN, PHIL, EWR, NYC (2026, from each city's first event)
  KXRAINNYC 0-inch-strike markets of 2026, 2025, 2022, 2021
Order of the pull = the order above (Trenton first).

Resumable: one cache file per market under data/raw/kalshi/candles/<series>/<ticker>.json
(git-ignored); a market with a cache file is skipped. Read-only, public endpoints, no auth.
Every attempt is appended to data/raw/kalshi/rain/pull_log.csv.

Usage:
  python scripts/kalshi_rain_pull.py            # pull what is missing
  python scripts/kalshi_rain_pull.py --status   # print cached / missing counts, no network
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from src.kalshi.client import KalshiClient, RAW  # noqa: E402
from src.kalshi.rain_quotes import scope_markets  # noqa: E402

LOG = RAW / "rain" / "pull_log.csv"


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log_row(row: dict) -> None:
    new = not LOG.exists()
    with LOG.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["utc", "group", "ticker", "status", "n_candles", "note"])
        if new:
            w.writeheader()
        w.writerow(row)


def status(c: KalshiClient, mk: list[dict]) -> dict:
    out: dict[str, list[int]] = {}
    for m in mk:
        p = c.candles_path(m["_series"], m["ticker"])
        have = p.exists()
        empty = have and not json.loads(p.read_text()).get("candlesticks")
        s = out.setdefault(m["_group"], [0, 0, 0])
        s[0] += 1
        s[1] += have
        s[2] += bool(empty)
    return out


def print_status(st: dict) -> None:
    print(f"{'group':22s} {'markets':>8s} {'cached':>7s} {'missing':>8s} {'cached_but_empty':>17s}")
    for g, (n, h, e) in st.items():
        print(f"{g:22s} {n:8d} {h:7d} {n - h:8d} {e:17d}")
    n = sum(v[0] for v in st.values()); h = sum(v[1] for v in st.values())
    print(f"{'ALL':22s} {n:8d} {h:7d} {n - h:8d}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--gap", type=float, default=1.0, help="base seconds between requests")
    ap.add_argument("--limit", type=int, default=0, help="stop after this many markets (0 = all)")
    a = ap.parse_args()
    c = KalshiClient(min_gap=a.gap, max_gap=max(3.0, a.gap))
    mk = scope_markets()
    if a.status:
        print_status(status(c, mk)); return
    todo = [m for m in mk if not c.candles_path(m["_series"], m["ticker"]).exists()]
    print(now(), "in scope", len(mk), "to pull", len(todo), flush=True)
    t0 = time.time(); done = 0
    # live-tier KXRAIN markets: batch endpoint, 5 event days per call, per city group
    live = [m for m in todo if m["_series"] == "KXRAIN" and m.get("_tier") == "live"]
    days = sorted({m["event_ticker"] for m in live}, key=lambda e: min(x["close_time"] for x in live if x["event_ticker"] == e))
    for i in range(0, len(days), 5):
        chunk = [m for m in live if m["event_ticker"] in days[i:i + 5]]
        try:
            n = c.candles_batch("KXRAIN", chunk)
            log_row({"utc": now(), "group": "batch", "ticker": f"{days[i]}..{days[min(i + 4, len(days) - 1)]}",
                     "status": "ok", "n_candles": n, "note": f"{len(chunk)} markets asked, {n} files written"})
        except Exception as e:  # noqa: BLE001  (fall through to single calls)
            log_row({"utc": now(), "group": "batch", "ticker": days[i], "status": "error", "n_candles": 0,
                     "note": str(e)[:150]})
    for m in todo:
        p = c.candles_path(m["_series"], m["ticker"])
        if p.exists():
            continue
        try:
            cs = c.candles(m["_series"], m)
            st = "ok" if cs else "empty"
            log_row({"utc": now(), "group": m["_group"], "ticker": m["ticker"], "status": st,
                     "n_candles": len(cs), "note": ""})
        except Exception as e:  # noqa: BLE001
            log_row({"utc": now(), "group": m["_group"], "ticker": m["ticker"], "status": "error",
                     "n_candles": 0, "note": str(e)[:150]})
        done += 1
        if done % 20 == 0:
            print(now(), "pulled", done, "of", len(todo), "requests", c.n_requests, "429s", c.n_429,
                  "sec", round(time.time() - t0), flush=True)
        if a.limit and done >= a.limit:
            break
    print(now(), "finished. requests", c.n_requests, "429s", c.n_429, "sec", round(time.time() - t0), flush=True)
    print_status(status(c, mk))


if __name__ == "__main__":
    main()
