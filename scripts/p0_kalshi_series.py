"""Phase 0 Kalshi rain probe, step 1: list every rain series (ticker, title, frequency).

Read-only. Caches the raw list under data/raw/kalshi/rain/ and writes an aggregate
table to data/processed/kalshi_rain_probe/rain_series.csv.
"""
import json, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from src.kalshi.client import KalshiClient, RAW
import pandas as pd

OUT = REPO / "data" / "processed" / "kalshi_rain_probe"
OUT.mkdir(parents=True, exist_ok=True)
raw = RAW / "rain" / "series_list_climate.json"
c = KalshiClient(min_gap=1.0, max_gap=3.0)
if raw.exists():
    d = json.loads(raw.read_text())
else:
    d = c.get("/series", {"category": "Climate and Weather"})
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text(json.dumps(d))
rows = d["series"]
print("series in category:", len(rows), "keys:", sorted(rows[0].keys()))
KEYS = ("RAIN", "PRECIP", "SNOW")
out = []
for s in rows:
    t, title = s["ticker"], s.get("title", "")
    if "RAIN" in t.upper() or "rain" in title.lower() or "precip" in title.lower():
        out.append({"ticker": t, "title": title, "frequency": s.get("frequency"),
                    "tags": "|".join(s.get("tags") or []),
                    "n_settlement_sources": len(s.get("settlement_sources") or []),
                    "settlement_source": "|".join(x.get("name", "") for x in (s.get("settlement_sources") or [])),
                    "contract_terms_url": s.get("contract_terms_url", ""),
                    "contract_url": s.get("contract_url", "")})
df = pd.DataFrame(out).sort_values("ticker")
df.to_csv(OUT / "rain_series.csv", index=False)
pd.set_option("display.width", 250, "display.max_rows", 300, "display.max_colwidth", 60)
print(len(df)); print(df[["ticker", "title", "frequency", "settlement_source"]].to_string())
print(df.frequency.value_counts())
