"""Phase 1 Kalshi rain: build the per-market quote table from the candle cache (no network).

Output (git-ignored, raw rows): data/raw/kalshi/rain/quote_table.csv
One row per market in scope: quotes carried forward to 36, 24, 12 and 2 hours before close
(stale after 6 hours), bid, ask, spread, one-sided flags, Kalshi result, and the station's rain
outcome from the NWS daily climate report (IEM copy in data/raw/kalshi/iem_cli/).
Markets not yet pulled are kept with pulled = False.
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from src.kalshi.client import KalshiClient, RAW  # noqa: E402
from src.kalshi.rain_quotes import CITIES, market_row, scope_markets  # noqa: E402

OUT = RAW / "rain" / "quote_table.csv"


def station_outcomes() -> pd.DataFrame:
    """NWS CLI daily precipitation per city: class wet / trace / dry / missing."""
    rows = []
    for city, st in CITIES.items():
        for f in sorted(glob.glob(str(RAW / "iem_cli" / f"{st}_*.json"))):
            for r in json.loads(Path(f).read_text())["results"]:
                v = r.get("precip")
                if v == "T":
                    k, x = "trace", 0.0
                elif isinstance(v, (int, float)):
                    k, x = ("wet" if v > 0 else "dry"), float(v)
                else:
                    k, x = "missing", None
                rows.append({"city": city, "date": r["valid"], "station": st, "station_precip_in": x,
                             "station_class": k})
    d = pd.DataFrame(rows).drop_duplicates(["city", "date"])
    d["station_measurable"] = (d.station_class == "wet").astype(int)       # current rule: trace = No
    d["station_rain_or_trace"] = d.station_class.isin(["wet", "trace"]).astype(int)  # old NYC rule
    d.loc[d.station_class == "missing", ["station_measurable", "station_rain_or_trace"]] = None
    return d


def build() -> pd.DataFrame:
    c = KalshiClient()
    rows = []
    for m in scope_markets():
        p = c.candles_path(m["_series"], m["ticker"])
        cs = json.loads(p.read_text())["candlesticks"] if p.exists() else None
        rows.append(market_row(m, cs))
    df = pd.DataFrame(rows).merge(station_outcomes(), on=["city", "date"], how="left")
    df["station_class"] = df.station_class.fillna("no_cli_record")
    # rule in force: trace = Yes on KXRAINNYC, trace = No on KXRAIN
    df["trace_counts"] = df.series == "KXRAINNYC"
    return df


if __name__ == "__main__":
    df = build()
    df.to_csv(OUT, index=False)
    print("rows", len(df), "pulled", int(df.pulled.sum()), "->", OUT)
    print(df.groupby("group", sort=False).agg(markets=("ticker", "size"), pulled=("pulled", "sum"),
                                               empty=("n_candles", lambda x: int((x == 0).sum())),
                                               buyable_24=("buyable_24", "sum"), two_sided_24=("two_sided_24", "sum")))
