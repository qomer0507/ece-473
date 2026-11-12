"""Phase 0 Kalshi rain probe, step 4: aggregates from the cached listings (no network).

Outputs (data/processed/kalshi_rain_probe/, aggregates only):
  daily_coverage.csv        per series and city: first/last event, count, May-Sep events by year
  rule_wordings.csv         normalised rule text per series/city with first and last event date
  base_rate_nyc.csv         May-Sep yes share by year from Kalshi results; station check from NWS CLI (IEM cache)
  liquidity_last30.csv      volume over the last 30 settled events per city; open interest of active markets
  monthly_structure.csv     monthly series: events, strikes per event, strike range
  prior_cache_ask24.csv     share of May-Sep days with an ask 24 h before close in the prior cache
"""
import glob, json, re, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from src.kalshi.client import RAW, event_date_from_ticker
import pandas as pd

OUT = REPO / "data" / "processed" / "kalshi_rain_probe"
OUT.mkdir(parents=True, exist_ok=True)
MON = r"(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept|Sep|Oct|Nov|Dec)"

def load(s):
    df = pd.DataFrame(json.loads((RAW / "rain" / f"markets_{s}.json").read_text()))
    for c in ("cap_strike", "floor_strike", "strike_type", "result"):
        if c not in df:
            df[c] = None
    df["volume"] = pd.to_numeric(df.volume_fp, errors="coerce")
    df["oi"] = pd.to_numeric(df.open_interest_fp, errors="coerce")
    return df

def title_date(t):
    m = re.search(MON + r" (\d{1,2}), (\d{4})", t)
    return pd.to_datetime(f"{m.group(1)[:3]} {m.group(2)} {m.group(3)}", format="%b %d %Y") if m else pd.NaT

def norm(s):
    if not isinstance(s, str):
        return ""
    s = re.sub(MON + r"\.? \d{1,2}, \d{4}", "<DATE>", s)
    s = re.sub(r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)", "<DOW>", s)
    s = re.sub(r"greater than [0-9.]+", "greater than <X>", s)
    s = re.sub(r"\(the \d+\w+\)", "(the <N>)", s)
    return re.sub(r"\s+", " ", s).strip()

# ---------- daily series ----------
nyc = load("KXRAINNYC")
nyc["date"] = pd.to_datetime(nyc.event_ticker.map(event_date_from_ticker))
nyc["city"] = "NYC"; nyc["series"] = "KXRAINNYC"
nyc["zero"] = nyc.ticker.str.endswith(("-T0", "-T0.00"))
kx = load("KXRAIN")
kx["date"] = pd.to_datetime(kx.event_ticker.map(event_date_from_ticker))
kx["city"] = kx.ticker.str.split("-").str[-1]; kx["series"] = "KXRAIN"; kx["zero"] = kx.floor_strike.astype(float) == 0
parts = [nyc, kx]
for s in ("KXRAINDNYC", "KXRAINDPHIL", "KXRAINDPIT"):
    d = load(s); d["date"] = d.title.map(title_date); d["city"] = s.replace("KXRAIND", ""); d["series"] = s
    d["zero"] = d.floor_strike.astype(float) == 0
    parts.append(d)
allm = pd.concat(parts, ignore_index=True)
CITIES = ["NYC", "PHIL", "EWR", "TTN", "PIT"]
cov = []
for (s, city), g in allm[allm.city.isin(CITIES)].groupby(["series", "city"]):
    ev = g.drop_duplicates("event_ticker")
    r = {"series": s, "city": city, "n_events": len(ev), "n_markets": len(g),
         "n_settled_events": int(ev.status.isin(["finalized", "settled"]).sum()),
         "first_event": ev.date.min().date(), "last_event": ev.date.max().date(),
         "markets_per_event_max": int(g.groupby("event_ticker").size().max()),
         "strike_zero_share": round(g.zero.mean(), 3)}
    ms = ev[ev.date.dt.month.between(5, 9)]
    for y in range(2021, 2027):
        r[f"may_sep_{y}"] = int((ms.date.dt.year == y).sum())
    cov.append(r)
cov = pd.DataFrame(cov)
cov.to_csv(OUT / "daily_coverage.csv", index=False)
print(cov.to_string())

# ---------- rules ----------
rw = []
for (s, city), g in allm[allm.city.isin(CITIES)].groupby(["series", "city"]):
    for col in ("rules_primary", "rules_secondary"):
        g2 = g.assign(w=g[col].map(norm))
        for w, h in g2.groupby("w"):
            rw.append({"series": s, "city": city, "field": col, "first_event": h.date.min().date(),
                       "last_event": h.date.max().date(), "n_markets": len(h), "wording_normalised": w})
rw = pd.DataFrame(rw).sort_values(["series", "city", "field", "first_event"])
rw.to_csv(OUT / "rule_wordings.csv", index=False)
print(rw.groupby(["series", "city", "field"]).size().to_string())

# close-time clock (UTC hour) by series: day definition evidence
ct = pd.to_datetime(allm.close_time, format="ISO8601")
allm["close_hhmm_utc"] = ct.dt.strftime("%H:%M")
x = allm[allm.city.isin(["NYC", "PHIL", "EWR", "TTN"])]
cl = x.groupby(["series", x.date.dt.month, "close_hhmm_utc"]).size().rename("n").reset_index()
cl.to_csv(OUT / "close_time_by_month.csv", index=False)

# ---------- NYC base rate ----------
z = nyc[nyc.zero & nyc.date.dt.month.between(5, 9)].assign(src="KXRAINNYC (trace = Yes)")
k = kx[(kx.city == "NYC") & kx.date.dt.month.between(5, 9) & kx.result.isin(["yes", "no"])].assign(src="KXRAIN-NYC (trace = No)")
br = []
for (src, y), g in pd.concat([z, k]).groupby(["src", pd.concat([z, k]).date.dt.year]):
    br.append({"source": src, "year": y, "n_days": g.date.nunique(), "first": g.date.min().date(), "last": g.date.max().date(),
               "n_yes": int((g.result == "yes").sum()), "yes_share": round((g.result == "yes").mean(), 3)})
# station check from the NWS CLI cache (IEM), not Kalshi results
cli = []
for f in sorted(glob.glob(str(RAW / "iem_cli" / "KNYC_*.json"))):
    for r in json.loads(Path(f).read_text())["results"]:
        cli.append({"date": pd.to_datetime(r["valid"]), "precip": r.get("precip")})
cli = pd.DataFrame(cli).drop_duplicates("date")
cli = cli[cli.date.dt.month.between(5, 9)]
def cls(p):
    if p == "T":
        return "trace"
    try:
        return "wet" if float(p) > 0 else "dry"
    except (TypeError, ValueError):
        return "missing"
cli["k"] = cli.precip.map(cls)
for y, g in cli.groupby(cli.date.dt.year):
    n = len(g)
    br.append({"source": "NWS CLI Central Park via IEM (station data, not Kalshi)", "year": y, "n_days": n,
               "first": g.date.min().date(), "last": g.date.max().date(),
               "n_yes": int((g.k == "wet").sum()), "yes_share": round((g.k == "wet").mean(), 3),
               "n_trace": int((g.k == "trace").sum()), "n_missing": int((g.k == "missing").sum()),
               "yes_share_if_trace_counts_yes": round(g.k.isin(["wet", "trace"]).mean(), 3)})
br = pd.DataFrame(br)
br.to_csv(OUT / "base_rate_nyc.csv", index=False)
print(br.to_string())
# agreement between Kalshi results and CLI on days with both
chk = z.merge(cli, on="date", how="inner")
chk["pred"] = chk.k.isin(["wet", "trace"]).map({True: "yes", False: "no"})
print("KXRAINNYC May-Sep vs CLI (trace=yes rule): agree", int((chk.pred == chk.result).sum()), "of", len(chk))
chk2 = k.merge(cli, on="date", how="inner"); chk2["pred"] = (chk2.k == "wet").map({True: "yes", False: "no"})
print("KXRAIN-NYC May-Sep vs CLI (trace=no rule): agree", int((chk2.pred == chk2.result).sum()), "of", len(chk2))
pd.DataFrame([{"test": "KXRAINNYC May-Sep result vs NWS CLI with trace=Yes", "agree": int((chk.pred == chk.result).sum()), "n": len(chk)},
              {"test": "KXRAIN-NYC May-Sep result vs NWS CLI with trace=No", "agree": int((chk2.pred == chk2.result).sum()), "n": len(chk2)}]
             ).to_csv(OUT / "result_vs_cli_check.csv", index=False)

# KXRAIN results vs NWS CLI (IEM cache) for the four cities, all settled events
ST = {"NYC": "KNYC", "PHIL": "KPHL", "EWR": "KEWR", "TTN": "KTTN"}
rows = []
for city, st in ST.items():
    cl = []
    for f in sorted(glob.glob(str(RAW / "iem_cli" / f"{st}_*.json"))):
        for r in json.loads(Path(f).read_text())["results"]:
            cl.append({"date": pd.to_datetime(r["valid"]), "precip": r.get("precip")})
    cl = pd.DataFrame(cl).drop_duplicates("date"); cl["k"] = cl.precip.map(cls)
    g = kx[(kx.city == city) & kx.result.isin(["yes", "no"])].merge(cl, on="date", how="left")
    have = g[g.k.notna()]
    pred = (have.k == "wet").map({True: "yes", False: "no"})
    ms = g[g.date.dt.month.between(5, 9)]
    rows.append({"city": city, "station": st, "n_settled": len(g), "first": g.date.min().date(), "last": g.date.max().date(),
                 "n_with_cli": len(have), "agree_trace_as_no": int((pred == have.result).sum()),
                 "n_cli_trace_days": int((have.k == "trace").sum()),
                 "trace_days_resolved_no": int(((have.k == "trace") & (have.result == "no")).sum()),
                 "n_cli_missing_days": int((have.k == "missing").sum()),
                 "yes_share_all": round((g.result == "yes").mean(), 3),
                 "may_sep_2026_days": len(ms), "may_sep_2026_yes_share": round((ms.result == "yes").mean(), 3)})
kc = pd.DataFrame(rows); kc.to_csv(OUT / "kxrain_result_vs_cli.csv", index=False); print(kc.to_string())

# ---------- liquidity ----------
liq = []
def add(label, g):
    g = g[g.status.isin(["finalized", "settled"])].sort_values("date").tail(30)
    liq.append({"market": label, "n": len(g), "first": g.date.min().date(), "last": g.date.max().date(),
                "volume_median": g.volume.median(), "volume_min": g.volume.min(), "volume_max": g.volume.max(),
                "volume_p25": g.volume.quantile(.25), "volume_p75": g.volume.quantile(.75)})
for city in ["NYC", "PHIL", "EWR", "TTN", "PIT"]:
    add(f"KXRAIN-{city} last 30 settled", kx[kx.city == city])
add("KXRAINNYC last 30 settled (to 2026-07-15)", nyc[nyc.zero])
for y in (2022, 2025, 2026):
    g = nyc[nyc.zero & nyc.date.dt.month.between(5, 9) & (nyc.date.dt.year == y)]
    liq.append({"market": f"KXRAINNYC May-Sep {y} (all days)", "n": len(g), "first": g.date.min().date(), "last": g.date.max().date(),
                "volume_median": g.volume.median(), "volume_min": g.volume.min(), "volume_max": g.volume.max(),
                "volume_p25": g.volume.quantile(.25), "volume_p75": g.volume.quantile(.75)})
for city in ["NYC", "PHIL", "EWR", "TTN"]:
    g = kx[(kx.city == city) & kx.date.dt.month.between(5, 9) & kx.status.eq("finalized")]
    liq.append({"market": f"KXRAIN-{city} May-Sep 2026 (all days)", "n": len(g), "first": g.date.min().date(), "last": g.date.max().date(),
                "volume_median": g.volume.median(), "volume_min": g.volume.min(), "volume_max": g.volume.max(),
                "volume_p25": g.volume.quantile(.25), "volume_p75": g.volume.quantile(.75)})
liq = pd.DataFrame(liq)
liq.to_csv(OUT / "liquidity_last30.csv", index=False)
print(liq.to_string())
act = kx[kx.status.eq("active") & kx.city.isin(["NYC", "PHIL", "EWR", "TTN"])]
oi = act.groupby("city").agg(n_active=("ticker", "size"), oi_min=("oi", "min"), oi_max=("oi", "max"),
                             volume_min=("volume", "min"), volume_max=("volume", "max")).reset_index()
oi.to_csv(OUT / "open_interest_active_snapshot.csv", index=False)
print(oi.to_string())

# ---------- monthly ----------
mo = []
for s in ("KXRAINNYCM", "KXRAINPHILM", "KXRAINEWRM", "KXRAINTTNM"):
    d = load(s)
    per = d.groupby("event_ticker").agg(n=("ticker", "size"), lo=("floor_strike", "min"), hi=("floor_strike", "max"),
                                        vol=("volume", "sum"), close=("close_time", "max")).sort_values("close")
    mo.append({"series": s, "n_events": len(per), "first_event": per.index[0], "last_event": per.index[-1],
               "strikes_per_event_min": int(per.n.min()), "strikes_per_event_max": int(per.n.max()),
               "lowest_strike_in": float(per.lo.min()), "highest_strike_in": float(per.hi.max()),
               "strike_type": "|".join(sorted(set(d.strike_type.dropna()))),
               "median_event_volume": per.vol[per.vol > 0].median()})
mo = pd.DataFrame(mo); mo.to_csv(OUT / "monthly_structure.csv", index=False); print(mo.to_string())

# ---------- prior cache: ask 24 h before close ----------
pc = pd.read_parquet(RAW / "ladder_quotes_prior_repo.parquet")
pc = pc[pc.series_ticker == "KXRAINNYC"].copy()
pc["date"] = pd.to_datetime(pc.event_date)
pm = pc[pc.date.dt.month.between(5, 9)]
rows = []
for y in (2023, 2024, 2025, 2026):
    g = pm[pm.date.dt.year == y]
    if len(g) == 0:
        rows.append({"year": y, "n_days_in_cache": 0}); continue
    two = g[g.ask_24.notna() & g.bid_24.notna()]
    inside = two[(two.ask_24 < 1.0)]
    rows.append({"year": y, "n_days_in_cache": len(g), "first": g.date.min().date(), "last": g.date.max().date(),
                 "share_with_ask_24h": round(g.ask_24.notna().mean(), 3),
                 "share_with_ask_24h_below_1": round((g.ask_24 < 1.0).mean(), 3),
                 "share_with_ask_12h": round(g.ask_12.notna().mean(), 3),
                 "median_spread_24h": round((two.ask_24 - two.bid_24).median(), 3),
                 "median_spread_24h_ask_below_1": round((inside.ask_24 - inside.bid_24).median(), 3),
                 "yes_share": round((g.result == "yes").mean(), 3)})
pcs = pd.DataFrame(rows); pcs.to_csv(OUT / "prior_cache_ask24.csv", index=False); print(pcs.to_string())
