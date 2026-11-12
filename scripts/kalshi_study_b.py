"""Study B driver: coverage, cost of $1 of station heat-day protection, liquidity snapshot.

Reads the cached pull (data/raw/kalshi/). Writes AGGREGATES ONLY to results/studyB/.
The per-day working table goes to data/raw/kalshi/derived/ (git-ignored) because it
is derived row by row from Kalshi quotes.

All costs are top-of-book estimates from hourly candles. They show the best ask,
not its size. An ask does not prove that a hedge-sized order would fill.

Usage: python scripts/kalshi_study_b.py [--k 90]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.kalshi.client import RAW, REPO  # noqa: E402
from src.kalshi.data import load_candles, load_events, load_iem_cli_high  # noqa: E402
from src.kalshi.study_b import (SERIES, Quote, hedge_day, quote_at, replication_error,  # noqa: E402
                                year_block_bootstrap)

OUT = REPO / "results" / "studyB"
PRIOR = RAW / "ladder_quotes_prior_repo.parquet"
NOTE = ("OBSERVED Kalshi quotes. Top-of-book estimate: yes_ask (or 1 - yes_bid for NO legs) from the last hourly "
        "candle at or before close-24h, at most 6 h stale, plus taker fee ceil-to-cent(0.07*C*P*(1-P)). "
        "An ask does not prove a hedge-sized fill.")


def load_prior_quotes() -> dict[str, Quote]:
    """Prior-repo cache (NYC 2023-01-01..2026-06-30): ask_24 / bid_24 per market. Staleness unknown -> age_s = -1."""
    if not PRIOR.exists():
        return {}
    df = pd.read_parquet(PRIOR)
    df = df[df["series_ticker"] == "KXHIGHNY"]
    out = {}
    for t, a, b in zip(df["market_ticker"], df["ask_24"], df["bid_24"]):
        if pd.isna(a) and pd.isna(b):
            continue
        ac = None if pd.isna(a) else int(round(a * 100))
        bc = None if pd.isna(b) else int(round(b * 100))
        out[t] = Quote(ac if ac is not None and 1 <= ac <= 99 else None,
                       bc if bc is not None and 1 <= bc <= 99 else None, -1)
    return out


def build_daily(city: str, k: int, prior: dict[str, Quote], use_prior: bool) -> pd.DataFrame:
    cli = load_iem_cli_high(city)
    rows = []
    for e in load_events(city):
        quotes, src = {}, "fresh"
        pulled = True
        for b in e.brackets:
            c = load_candles(e.series, b.ticker)
            if c is None:
                pulled = False
                break
            quotes[b.ticker] = quote_at(c, e.close_ts)
        if not pulled:
            if use_prior and all(b.ticker in prior for b in e.brackets):
                quotes, src, pulled = {b.ticker: prior[b.ticker] for b in e.brackets}, "prior_cache", True
            else:
                quotes, src = {}, "not_pulled"
        t = e.settle_value if e.settle_value is not None else (int(cli[e.date]) if e.date in cli.index else None)
        row = {"city": city, "date": e.date, "year": e.date.year, "summer": 5 <= e.date.month <= 9,
               "n_markets": len(e.brackets), "quote_source": src, "t_settle": t,
               "hot": None if t is None else int(t >= k)}
        for label, contracts, allow_no in (("c100", 100, True), ("c1", 1, True), ("yesonly_c100", 100, False)):
            h = hedge_day(e.brackets, quotes, k, contracts=contracts, allow_no=allow_no)
            if label == "c100":
                row.update(status=h.status, k_achieved=h.k_achieved, strike_gap=h.strike_gap,
                           rep_error=None if (t is None or h.k_achieved is None) else replication_error(t, k, h.k_achieved))
                if h.priced:
                    legs = h.priced.rep.tickers
                    any_yes = any(e.results[x] == "yes" for x in legs)
                    row.update(side=h.priced.rep.side, n_legs=len(legs),
                               payout=int(any_yes) if h.priced.rep.side == "yes" else int(not any_yes),
                               fee=h.priced.fee_per_dollar,
                               max_age_h=max(quotes[x].age_s for x in legs) / 3600)
            row[f"cost_{label}"] = h.priced.cost_per_dollar if h.priced else np.nan
        # ladder-level liquidity at decision time
        qs = [q for q in quotes.values() if q is not None]
        row["n_fresh"] = len(qs)
        row["n_ask"] = sum(q.ask_c is not None for q in qs)
        row["n_two_sided"] = sum(q.ask_c is not None and q.bid_c is not None for q in qs)
        sp = [q.ask_c - q.bid_c for q in qs if q.ask_c is not None and q.bid_c is not None]
        row["mean_spread_c"] = float(np.mean(sp)) if sp else np.nan
        row["max_spread_c"] = float(np.max(sp)) if sp else np.nan
        full = len(qs) == len(e.brackets) and all(q.ask_c is not None for q in qs) and len(e.brackets) >= 6
        row["sum_asks"] = sum(q.ask_c for q in qs) / 100 if full else np.nan
        row["sum_bids"] = (sum((q.bid_c or 0) for q in qs) / 100) if full else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def coverage(d: pd.DataFrame) -> pd.DataFrame:
    out = []
    for season, sub in (("May-Sep", d[d["summer"]]), ("all months", d)):
        for (city, year), g in sub.groupby(["city", "year"]):
            p = g[g["quote_source"] != "not_pulled"]
            ex = g[g["status"] == "exact"]
            exp = p[p["status"] == "exact"]
            hot = g[g["hot"] == 1]
            hotp = p[p["hot"] == 1]
            out.append({
                "city": city, "year": year, "season": season, "market_days": len(g),
                "days_with_quotes_pulled": len(p),
                "share_days_any_fresh_ask": _share((p["n_ask"] > 0).sum(), len(p)),
                "share_days_full_ladder_ask": _share((p["n_ask"] == p["n_markets"]).sum(), len(p)),
                "days_exact_boundary": len(ex),
                "share_days_exact_boundary": _share(len(ex), len(g)),
                "share_exact_days_priced": _share(exp["cost_c100"].notna().sum(), len(exp)),
                "share_days_exact_and_priced": _share(exp["cost_c100"].notna().sum(), len(p)),
                "hot_days": len(hot),
                "hot_days_exact_boundary": int((hot["status"] == "exact").sum()),
                "share_hot_days_exact_and_priced": _share(
                    ((hotp["status"] == "exact") & hotp["cost_c100"].notna()).sum(), len(hotp)),
                "quote_sources": "; ".join(f"{a}: {b}" for a, b in g["quote_source"].value_counts().items()),
            })
    return pd.DataFrame(out)


def _share(a, b):
    return round(float(a) / b, 4) if b else np.nan


def cost_row(g: pd.DataFrame, label: dict) -> dict:
    """g: exact-boundary, priced days."""
    def per_paid(years, col="cost_c100"):
        x = pd.concat([g[g["year"] == y] for y in years])
        return x[col].sum() / x["payout"].sum() if x["payout"].sum() > 0 else np.nan

    def mean_of(col):
        return lambda years: pd.concat([g[g["year"] == y] for y in years])[col].mean()

    r = dict(label)
    r["years"] = ", ".join(str(y) for y in sorted(g["year"].unique()))
    r["days_priced"] = len(g)
    if len(g) == 0:
        return r
    yrs = list(g["year"].unique())
    for name, f in (("mean_cost_per_$1_protection", mean_of("cost_c100")),
                    ("mean_realised_payout_per_$1", mean_of("payout")),
                    ("cost_per_$1_paid_out", per_paid)):
        r[name] = round(float(f(yrs)), 4)
        lo, hi = year_block_bootstrap(yrs, f)
        r[name + "_ci_lo"], r[name + "_ci_hi"] = round(lo, 4), round(hi, 4)
    r["mean_cost_1_contract_rounding"] = round(g["cost_c1"].mean(), 4)
    yo = g["cost_yesonly_c100"]
    r["mean_cost_yes_legs_only"] = round(yo.mean(), 4)
    r["days_yes_only_priced"] = int(yo.notna().sum())
    r["mean_fee_per_$1"] = round(g["fee"].mean(), 4)
    r["median_cost"] = round(g["cost_c100"].median(), 4)
    r["share_no_leg_route"] = round((g["side"] == "no").mean(), 4)
    r["mean_legs"] = round(g["n_legs"].mean(), 2)
    r["payout_days"] = int(g["payout"].sum())
    r["bootstrap"] = "year blocks, 1000 draws, seed 473" if len(yrs) >= 2 else "not possible (one year)"
    r["note"] = NOTE
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=90)
    ap.add_argument("--no-prior", action="store_true", help="never fall back to the prior-repo quote cache")
    a = ap.parse_args()
    k = a.k
    prior = load_prior_quotes()
    d = pd.concat([build_daily(c, k, prior, not a.no_prior) for c in SERIES], ignore_index=True)
    (RAW / "derived").mkdir(parents=True, exist_ok=True)
    d.to_csv(RAW / "derived" / f"studyB_daily_k{k}.csv", index=False)
    OUT.mkdir(parents=True, exist_ok=True)
    sfx = "" if k == 90 else f"_k{k}"

    cov = coverage(d)
    cov.insert(3, "strike_k", k)
    cov.to_csv(OUT / f"quote_coverage_by_city_year{sfx}.csv", index=False)

    # ---- cost tables: exact boundary, priced --------------------------------
    pr = d[(d["status"] == "exact") & d["cost_c100"].notna()]
    S = pr["summer"]
    specs = [
        ("NYC", "May-Sep 2023-2025 (SPEC window)", (pr.city == "NYC") & S & pr.year.between(2023, 2025)),
        ("NYC", "May-Sep 2022 (before SPEC window)", (pr.city == "NYC") & S & (pr.year == 2022)),
        ("NYC", "Aug-Sep 2021 (before SPEC window, 1-2 thresholds per day)", (pr.city == "NYC") & S & (pr.year == 2021)),
        ("Philadelphia", "May-Sep 2025-2026", (pr.city == "Philadelphia") & S),
        ("Philadelphia", "all months from 2024-11-20", pr.city == "Philadelphia"),
        ("Newark", "2026-08-26 to 2026-11-10", pr.city == "Newark"),
        ("Trenton", "2026-08-26 to 2026-11-10", pr.city == "Trenton"),
    ]
    rows = [cost_row(pr[m], {"city": c, "window": w, "strike_k": k}) for c, w, m in specs]
    for c in ("NYC", "Philadelphia"):
        for y, g in pr[(pr.city == c) & S].groupby("year"):
            rows.append(cost_row(g, {"city": c, "window": f"May-Sep {y}", "strike_k": k}))
    pd.DataFrame(rows).to_csv(OUT / f"cost_of_protection{sfx}.csv", index=False)

    # ---- strike basis: how far is the nearest achievable threshold -----------
    rows = []
    for (city, summer), g in d.groupby(["city", "summer"]):
        g2 = g[g["status"] != "no_ladder"]
        gap = g2["strike_gap"].astype(float)
        re_ = g2["rep_error"].dropna().astype(int)
        hot = g2[g2["hot"] == 1]
        rows.append({
            "city": city, "season": "May-Sep" if summer else "Oct-Apr", "strike_k": k, "market_days": len(g2),
            "share_exact": _share((gap == 0).sum(), len(g2)),
            "share_within_1F": _share((gap.abs() <= 1).sum(), len(g2)),
            "share_nearest_below_k": _share((gap < 0).sum(), len(g2)),
            "share_nearest_above_k": _share((gap > 0).sum(), len(g2)),
            "median_gap_F": float(gap.median()) if len(gap) else np.nan,
            "replication_error_days": int((re_ != 0).sum()),
            "over_payment_days": int((re_ == 1).sum()), "shortfall_days": int((re_ == -1).sum()),
            "replication_error_rate": _share((re_ != 0).sum(), len(re_)),
            "hot_days": len(hot), "hot_days_exact": int((hot["strike_gap"] == 0).sum()),
            "hot_days_within_1F": int((hot["strike_gap"].astype(float).abs() <= 1).sum()),
        })
    pd.DataFrame(rows).to_csv(OUT / f"strike_basis{sfx}.csv", index=False)

    # ---- liquidity snapshot (decision-time quotes), same dates for all cities -
    from datetime import date
    rows = []
    win = d[(d["date"] >= date(2026, 8, 26)) & (d["quote_source"] == "fresh")]
    for label, w in (("2026-08-26 to 2026-11-10", win),
                     ("2026-08-26 to 2026-09-30", win[win["date"] <= date(2026, 9, 30)])):
        for city, g in w.groupby("city"):
            nm = g["n_markets"].sum()
            rows.append({
                "city": city, "window": label, "market_days": len(g), "markets": int(nm),
                "share_markets_fresh_candle": _share(g["n_fresh"].sum(), nm),
                "share_markets_with_ask": _share(g["n_ask"].sum(), nm),
                "share_markets_two_sided": _share(g["n_two_sided"].sum(), nm),
                "mean_bid_ask_spread_cents": round(float(np.average(g["mean_spread_c"].dropna(),
                                                   weights=g.loc[g["mean_spread_c"].notna(), "n_two_sided"])), 2)
                if g["mean_spread_c"].notna().any() else np.nan,
                "median_of_daily_mean_spread_cents": round(g["mean_spread_c"].median(), 2),
                "median_of_daily_max_spread_cents": round(g["max_spread_c"].median(), 2),
                "days_full_ladder_asks": int(g["sum_asks"].notna().sum()),
                "mean_sum_of_asks_$": round(g["sum_asks"].mean(), 4),
                "mean_sum_of_bids_$": round(g["sum_bids"].mean(), 4),
                "note": "Quotes 24 h before close, hourly candle close, at most 6 h stale. Prices only, no depth.",
            })
    pd.DataFrame(rows).to_csv(OUT / "liquidity_snapshot.csv", index=False)

    pd.set_option("display.width", 250, "display.max_columns", 40, "display.max_colwidth", 40)
    print(cov[cov.season == "May-Sep"].drop(columns=["quote_sources"]).to_string())
    print(pd.read_csv(OUT / f"cost_of_protection{sfx}.csv").drop(columns=["note"]).T.to_string())
    print(pd.read_csv(OUT / f"strike_basis{sfx}.csv").T.to_string())
    print(pd.read_csv(OUT / "liquidity_snapshot.csv").drop(columns=["note"]).T.to_string())


if __name__ == "__main__":
    main()
