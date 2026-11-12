"""Phase 0 Kalshi rain probe, step 2: market listings for selected rain series.

Read-only. For each series: historical tier (/historical/markets) plus live tier
(/markets, every status). Raw rows are cached in data/raw/kalshi/rain/markets_<series>.json.
Usage: python scripts/p0_kalshi_markets.py SERIES [SERIES ...]
"""
import json, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from src.kalshi.client import KalshiClient, RAW

c = KalshiClient(min_gap=1.0, max_gap=3.0)
for s in sys.argv[1:]:
    p = RAW / "rain" / f"markets_{s}.json"
    if p.exists():
        rows = json.loads(p.read_text())
        print(s, "cached", len(rows)); continue
    out = {}
    for m in c._paged("/historical/markets", {"series_ticker": s, "limit": 1000}, "markets"):
        m["_tier"] = "historical"; out[m["ticker"]] = m
    nh = len(out)
    for m in c._paged("/markets", {"series_ticker": s, "limit": 1000}, "markets"):
        if m["ticker"] not in out:
            m["_tier"] = "live"; out[m["ticker"]] = m
    rows = list(out.values())
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(rows))
    print(s, "historical", nh, "live", len(rows) - nh, "requests", c.n_requests, "429s", c.n_429, flush=True)
