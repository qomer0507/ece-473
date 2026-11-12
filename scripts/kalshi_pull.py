"""Resumable, cached pull of Kalshi daily-high markets and hourly candlesticks.

Read-only public endpoints. Everything lands in data/raw/kalshi/ (git-ignored).
Re-running skips anything already cached. Use --refresh-listings to re-pull
event and market lists (new days appear daily); candles of settled markets never change.

Scope (SPEC v2 / Ehfaz task 1), in priority order:
  1. Newark, Trenton: all events since 2026-08-26.
  2. Philadelphia May-Sep.
  3. NYC May-Sep 2021-2022 (not in the prior cache), plus every 8th NYC May-Sep
     2023-2025 event (sample used to verify the prior cache).
  4. NYC May-Sep 2023-2025, the rest.
  5. Philadelphia remaining days (from 2024-11-20).
  6. Optional (--nyc-all): NYC outside May-Sep and 2026.

Usage:
  python scripts/kalshi_pull.py                 # scope 1-5
  python scripts/kalshi_pull.py --listings-only
  python scripts/kalshi_pull.py --nyc-all
"""
from __future__ import annotations

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.kalshi.client import KalshiClient, event_date_from_ticker  # noqa: E402

SERIES = {"NYC": "KXHIGHNY", "Philadelphia": "KXHIGHPHIL", "Newark": "KXHIGHTEWR", "Trenton": "KXHIGHTTTN"}


def summer(d):
    return 5 <= d.month <= 9


def build_queue(c: KalshiClient, nyc_all: bool, refresh: bool):
    q = []  # (priority, series, market)
    for city, s in SERIES.items():
        c.series(s, refresh=refresh)
        c.events(s, refresh=refresh)
        for m in c.markets(s, refresh=refresh):
            d = event_date_from_ticker(m["event_ticker"])
            if city in ("Newark", "Trenton"):
                pr = 1
            elif city == "Philadelphia":
                pr = 2 if summer(d) else 5
            else:  # NYC
                if summer(d) and 2021 <= d.year <= 2022:
                    pr = 3
                elif summer(d) and 2023 <= d.year <= 2025:
                    pr = 3 if d.toordinal() % 8 == 0 else 4
                elif nyc_all:
                    pr = 6
                else:
                    continue
            q.append((pr, s, m))
    q.sort(key=lambda x: (x[0], x[2]["event_ticker"]))
    return q


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--listings-only", action="store_true")
    ap.add_argument("--refresh-listings", action="store_true")
    ap.add_argument("--nyc-all", action="store_true")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--max-priority", type=int, default=5, help="1..6, see scope list above")
    ap.add_argument("--min-gap", type=float, default=0.6, help="seconds between requests (global)")
    a = ap.parse_args()

    c = KalshiClient(min_gap=a.min_gap)
    c.cutoff()
    q = build_queue(c, a.nyc_all, a.refresh_listings)
    q = [x for x in q if x[0] <= a.max_priority]
    todo = [(p, s, m) for p, s, m in q if not c.candles_path(s, m["ticker"]).exists()]
    print(f"markets in scope: {len(q)}; candle files missing: {len(todo)}", flush=True)
    if a.listings_only or not todo:
        return
    t0, done, fail = time.time(), 0, 0

    def progress():
        if (done + fail) % 250 < 6:
            print(f"{done + fail}/{len(todo)} done, {fail} failed, {c.n_429} x 429, gap {c.gap:.2f}s, "
                  f"{time.time() - t0:.0f}s", flush=True)

    # Live-tier markets: batch endpoint, 5 events per call, same series per call.
    live = [(p, s, m) for p, s, m in todo if m.get("_tier") == "live"]
    rest = [(p, s, m) for p, s, m in todo if m.get("_tier") != "live"]
    by_series: dict[str, dict[str, list[dict]]] = {}
    for _, s, m in live:
        by_series.setdefault(s, {}).setdefault(m["event_ticker"], []).append(m)
    for s, evs in by_series.items():
        keys = sorted(evs, key=lambda e: event_date_from_ticker(e))
        for i in range(0, len(keys), 5):
            ms = [m for k in keys[i:i + 5] for m in evs[k]]
            try:
                n = c.candles_batch(s, ms)
                done += n
                # anything the batch did not return falls back to single calls
                rest += [(9, s, m) for m in ms if not c.candles_path(s, m["ticker"]).exists()]
            except Exception as e:
                print("BATCH FAIL", s, keys[i], e, flush=True)
                rest += [(9, s, m) for m in ms]
            progress()

    with ThreadPoolExecutor(a.workers) as ex:
        futs = {ex.submit(c.candles, s, m): m["ticker"] for _, s, m in rest}
        for f in as_completed(futs):
            try:
                f.result()
                done += 1
            except Exception as e:  # keep going; rerun picks up the rest
                fail += 1
                print("FAIL", futs[f], e, flush=True)
            progress()
    print(f"finished: {done} pulled, {fail} failed, requests={c.n_requests}, 429s={c.n_429}", flush=True)


if __name__ == "__main__":
    main()
