"""Phase 0 Kalshi rain probe, step 3: candlestick retrieval test on a small sample.

Read-only; uses the cached client (data/raw/kalshi/candles/<series>/<ticker>.json).
Writes the per-market table to data/raw/kalshi/rain/candle_sample_per_market.csv (git-ignored)
and a grouped summary to data/processed/kalshi_rain_probe/candle_sample_summary.csv.
"""
import json, sys, time
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from src.kalshi.client import KalshiClient, RAW, parse_ts
import pandas as pd

OUT = REPO / "data" / "processed" / "kalshi_rain_probe"
c = KalshiClient(min_gap=1.0, max_gap=3.0)

def load(series):
    return {m["ticker"]: m for m in json.loads((RAW / "rain" / f"markets_{series}.json").read_text())}

SAMPLE = {
    "KXRAINNYC": ["RAINNYC-22JUN15-T0", "RAINNYC-22JUL20-T0", "KXRAINNYC-25MAY14-T0", "KXRAINNYC-25JUN18-T0",
                  "KXRAINNYC-25JUL09-T0", "KXRAINNYC-25AUG13-T0", "KXRAINNYC-25SEP10-T0", "KXRAINNYC-26MAY20-T0",
                  "KXRAINNYC-26JUN17-T0", "KXRAINNYC-26JUL08-T0"],
    "KXRAIN": ["KXRAIN-26JUL22-NYC", "KXRAIN-26JUL22-PHIL", "KXRAIN-26AUG12-NYC", "KXRAIN-26AUG12-PHIL",
               "KXRAIN-26SEP02-NYC", "KXRAIN-26SEP02-PHIL", "KXRAIN-26SEP02-TTN", "KXRAIN-26SEP02-EWR",
               "KXRAIN-26SEP23-NYC", "KXRAIN-26SEP23-PHIL", "KXRAIN-26SEP23-TTN", "KXRAIN-26SEP23-EWR",
               "KXRAIN-26OCT21-NYC", "KXRAIN-26OCT21-PHIL", "KXRAIN-26OCT21-TTN", "KXRAIN-26OCT21-EWR"],
    "KXRAINDNYC": ["KXRAINDNYC-260919-0", "KXRAINDNYC-261031-0", "KXRAINDNYC-261101-0"],
}

def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None

def px(side):
    if not isinstance(side, dict):
        return None
    for k in ("close_dollars", "close"):
        if side.get(k) is not None:
            v = num(side[k])
            return v / 100 if (k == "close" and v is not None and v > 1) else v
    return None

rows = []
t0 = time.time()
for series, tickers in SAMPLE.items():
    mk = load(series)
    for t in tickers:
        if t not in mk:
            rows.append({"series": series, "ticker": t, "status": "not in listing"}); continue
        m = mk[t]
        try:
            cs = c.candles(series, m)
        except Exception as e:  # noqa
            rows.append({"series": series, "ticker": t, "status": f"error {str(e)[:60]}"}); continue
        close = parse_ts(m["close_time"]); opn = parse_ts(m["open_time"])
        q = []
        for k in cs:
            b, a = px(k.get("yes_bid")), px(k.get("yes_ask"))
            q.append({"h": (close - k["end_period_ts"]) / 3600, "bid": b, "ask": a,
                      "vol": num(k.get("volume_fp", k.get("volume"))),
                      "oi": num(k.get("open_interest_fp", k.get("open_interest")))})
        q = pd.DataFrame(q)
        r = {"series": series, "ticker": t, "tier": m.get("_tier"), "status": "ok", "result": m.get("result"),
             "life_hours": round((close - opn) / 3600, 1), "n_candles": len(q)}
        if len(q):
            two = q[q.bid.notna() & q.ask.notna()]
            two_real = two[(two.ask < 1.0) & (two.bid > 0.0)]
            r.update({"n_hours_bid_and_ask": len(two), "n_hours_two_sided_inside": len(two_real),
                      "earliest_quote_hours_before_close": round(two.h.max(), 1) if len(two) else None,
                      "median_spread": round((two.ask - two.bid).median(), 3) if len(two) else None,
                      "median_spread_two_sided": round((two_real.ask - two_real.bid).median(), 3) if len(two_real) else None,
                      "n_hours_with_trades": int((q.vol.fillna(0) > 0).sum()),
                      "max_open_interest": q.oi.max()})
            near = two[(two.h >= 23.5) & (two.h <= 24.5)]
            if len(near):
                x = near.iloc[(near.h - 24).abs().argsort()].iloc[0]
                r.update({"has_quote_24h": True, "ask_24h_below_1": bool(x.ask < 1.0),
                          "spread_24h": round(x.ask - x.bid, 3)})
        rows.append(r)
        print(r, flush=True)
df = pd.DataFrame(rows)
# per-market table stays with the raw data (git-ignored); only the grouped summary is published
df.to_csv(RAW / "rain" / "candle_sample_per_market.csv", index=False)
ok = df[df.status == "ok"].copy()
ok["group"] = ok.ticker.str.extract(r"^(RAINNYC-22|KXRAINNYC-25|KXRAINNYC-26|KXRAIN-26(?:JUL|AUG|SEP)|KXRAIN-26OCT|KXRAINDNYC)")
ok["cover"] = ok.n_candles / ok.life_hours
g = ok.groupby("group").agg(
    n_markets=("ticker", "size"), candles_median=("n_candles", "median"), candles_min=("n_candles", "min"),
    candles_max=("n_candles", "max"), life_hours_median=("life_hours", "median"),
    hours_covered_share=("cover", "median"),
    earliest_quote_h_before_close=("earliest_quote_hours_before_close", "median"),
    median_spread=("median_spread", "median"), median_spread_two_sided=("median_spread_two_sided", "median"),
    n_with_quote_24h=("has_quote_24h", lambda x: int(x.fillna(False).astype(bool).sum())),
    spread_24h_median=("spread_24h", "median"), max_oi_median=("max_open_interest", "median"),
    max_oi_min=("max_open_interest", "min"), max_oi_max=("max_open_interest", "max"))
allrow = pd.DataFrame([{"group": "ALL", "n_markets": len(ok), "candles_median": ok.n_candles.median(),
                        "median_spread": ok.median_spread.median(),
                        "n_with_quote_24h": int(ok.has_quote_24h.fillna(False).astype(bool).sum()),
                        "spread_24h_median": ok.spread_24h.median()}]).set_index("group")
pd.concat([g, allrow]).to_csv(OUT / "candle_sample_summary.csv")
print("requests", c.n_requests, "429s", c.n_429, "seconds", round(time.time() - t0, 1))
