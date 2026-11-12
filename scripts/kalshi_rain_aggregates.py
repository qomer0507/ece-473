"""Phase 1 Kalshi rain: aggregates, price-model fit and calibration figure (no network).

Reads data/raw/kalshi/rain/quote_table.csv (raw, git-ignored) and station history (GHCN-Daily,
data/raw/rain/ncei_daily, read-only). Writes AGGREGATES ONLY to data/processed/kalshi_rain/:
  pull_coverage.csv        markets in scope / pulled / empty, by series, city, year
  quotes_by_city_year.csv  per decision time: usable quotes, mean ask, bid, result, spread, fee  (observed)
  calibration.csv          mid price bins vs realised frequency, with counts                      (observed)
  sharpness.csv            Brier score of observed prices vs climatology and persistence
  strategy_24h.csv         cost of buying one contract every day at the 24-hour time               (observed)
  climatology.csv          station rain frequency by month, 1998-2024 (station data, not Kalshi)
  model_eval.csv           modelled vs observed premium, payout, pattern; held-out tests
  price_model.json         fitted parameters (MODELLED prices)
and results/kalshi_rain/calibration.png.
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from src.kalshi.client import RAW  # noqa: E402
from src.kalshi.rain_price_model import MODELS, fit_model, modelled_ask  # noqa: E402
from src.kalshi.rain_quotes import DECISION_HOURS, GHCN, brier, calibration_table, taker_fee  # noqa: E402

OUT = REPO / "data" / "processed" / "kalshi_rain"
FIG = REPO / "results" / "kalshi_rain"
CLIM_YEARS = (1998, 2024)   # before the market years used for fitting; Trenton daily data start 1998
DAILY = REPO / "data" / "raw" / "rain" / "ncei_daily"


# ---------------------------------------------------------------- station history
def ghcn_daily(city: str) -> pd.DataFrame:
    fs = [f for f in sorted(glob.glob(str(DAILY / f"{GHCN[city]}_*.csv"))) if "PRCP" in open(f).readline()]
    d = pd.concat([pd.read_csv(f, dtype=str) for f in fs], ignore_index=True)
    d["prcp"] = pd.to_numeric(d.PRCP, errors="coerce")
    d = d.dropna(subset=["prcp"]).drop_duplicates("DATE")
    d["date"] = pd.to_datetime(d.DATE)
    d["trace"] = d.PRCP_ATTRIBUTES.fillna("").str.startswith("T")
    d["wet"] = (d.prcp > 0).astype(int)                       # measurable: trace = No (current rule)
    d["wet_or_trace"] = ((d.prcp > 0) | d.trace).astype(int)  # old NYC rule: trace = Yes
    return d[["date", "prcp", "wet", "wet_or_trace"]].set_index("date")


def climatology() -> tuple[pd.DataFrame, dict, dict]:
    """Monthly May-Sep frequency per city and rule, lag-1 persistence k, and daily indicators."""
    rows, ks, daily = [], {}, {}
    for city in GHCN:
        d = ghcn_daily(city)
        daily[city] = d
        h = d[(d.index.year >= CLIM_YEARS[0]) & (d.index.year <= CLIM_YEARS[1]) & (d.index.month >= 5) & (d.index.month <= 9)]
        for col, rule in (("wet", "trace_no"), ("wet_or_trace", "trace_yes")):
            for mth, g in h.groupby(h.index.month):
                rows.append({"city": city, "rule": rule, "month": mth, "years": f"{CLIM_YEARS[0]}-{CLIM_YEARS[1]}",
                             "n_days": len(g), "rain_share": round(g[col].mean(), 4)})
            # persistence: P(rain | rain yesterday) - P(rain | dry yesterday), consecutive days only
            x = pd.DataFrame({"y": d[col], "p": d[col].shift(1), "gap": d.index.to_series().diff().dt.days}).loc[h.index]
            x = x[x.gap == 1]
            ks[(city, rule)] = float(x.y[x.p == 1].mean() - x.y[x.p == 0].mean())
    return pd.DataFrame(rows), ks, daily


# ---------------------------------------------------------------- helpers
def group_label(r) -> str:
    return f"{r.city} {r.year} ({r.series})"


def fee1(p):      # one contract per order, rounded up to the cent
    return taker_fee(float(p), 1)


def fee100(p):    # per contract in a 100-contract order
    return taker_fee(float(p), 100) / 100.0


def quotes_table(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    groups = [(k, g) for k, g in df.groupby(["series", "city", "year"], sort=False)]
    nyc26 = df[(df.city == "NYC") & (df.year == 2026) & ~((df.series == "KXRAINNYC") & (df.date >= "2026-07-15"))]
    groups.append((("both series", "NYC", 2026), nyc26))
    for (series, city, year), g in groups:
        for h in DECISION_HOURS:
            p = g[g.pulled]
            b = p[p[f"buyable_{h}"] == True]      # noqa: E712
            t = p[p[f"two_sided_{h}"] == True]    # noqa: E712
            fresh = p[(p[f"has_quote_{h}"] == True) & (p[f"stale_{h}"] == False)]  # noqa: E712
            r = {"label": "observed", "series": series, "city": city, "year": year, "hours_before_close": h,
                 "markets": len(g), "pulled": len(p), "no_quote_yet": int((p[f"has_quote_{h}"] == False).sum()),  # noqa: E712
                 "stale_quote": int((p[f"stale_{h}"] == True).sum()), "fresh_quote": len(fresh),  # noqa: E712
                 "ask_is_1": int(fresh[f"ask_is_1_{h}"].sum()), "bid_is_0": int(fresh[f"bid_is_0_{h}"].sum()),
                 "buyable_ask_below_1": len(b), "two_sided_usable": len(t),
                 "two_sided_share_of_markets": round(len(t) / len(g), 3) if len(g) else None,
                 "yes_share_all_markets": round(g.result.mean(), 3)}
            if len(b):
                r.update(mean_ask_buyable=round(b[f"ask_{h}"].mean(), 4), yes_share_buyable=round(b.result.mean(), 3))
            if len(t):
                a = t[f"ask_{h}"]
                r.update(mean_ask=round(a.mean(), 4), mean_bid=round(t[f"bid_{h}"].mean(), 4),
                         mean_mid=round(t[f"mid_{h}"].mean(), 4), yes_share=round(t.result.mean(), 3),
                         mean_spread=round(t[f"spread_{h}"].mean(), 4), median_spread=round(t[f"spread_{h}"].median(), 4),
                         mean_taker_fee_1_contract=round(a.map(fee1).mean(), 4),
                         mean_taker_fee_per_contract_100_lot=round(a.map(fee100).mean(), 4),
                         mean_fee_unrounded=round((0.07 * a * (1 - a)).mean(), 4))
            rows.append(r)
    return pd.DataFrame(rows)


def calib(df: pd.DataFrame) -> pd.DataFrame:
    sets = {"all markets": df, "NYC 2025": df[(df.city == "NYC") & (df.year == 2025)],
            "NYC 2026": df[(df.city == "NYC") & (df.year == 2026)],
            "Philadelphia+Trenton+Newark 2026": df[df.city.isin(["PHIL", "TTN", "EWR"])],
            "NYC 2021-2022": df[(df.city == "NYC") & (df.year <= 2022)]}
    rows = []
    for name, g in sets.items():
        for h in DECISION_HOURS:
            t = g[g[f"two_sided_{h}"] == True]  # noqa: E712
            for price in ("mid", "ask"):
                for b in calibration_table(t[f"{price}_{h}"].tolist(), t.result.tolist()):
                    n = b["n"]
                    r = {"label": "observed", "set": name, "hours_before_close": h, "price": price,
                         "bin_lo": b["lo"], "bin_hi": b["hi"], "n": n,
                         "mean_price": round(b["mean_price"], 4) if n else None,
                         "yes_share": round(b["yes_share"], 4) if n else None}
                    if n:
                        k = b["yes_share"] * n; z = 1.96
                        c = (k + z * z / 2) / (n + z * z); w = z * np.sqrt(k * (n - k) / n + z * z / 4) / (n + z * z)
                        r.update(yes_share_lo95=round(c - w, 4), yes_share_hi95=round(c + w, 4))
                    rows.append(r)
    return pd.DataFrame(rows)


def strategy(df: pd.DataFrame, h: int = 24) -> pd.DataFrame:
    rows = []
    groups = [(k, g) for k, g in df.groupby(["series", "city", "year"], sort=False)]
    nyc26 = df[(df.city == "NYC") & (df.year == 2026) & ~((df.series == "KXRAINNYC") & (df.date >= "2026-07-15"))]
    groups.append((("both series", "NYC", 2026), nyc26))
    ov = df[(df.series == "KXRAIN") & (df.date >= "2026-08-27")]
    groups.append((("KXRAIN", "four cities, 2026-08-27 to 09-30", 2026), ov))
    for (series, city, year), g in groups:
        p = g[g.pulled]
        b = p[p[f"buyable_{h}"] == True]  # noqa: E712
        if not len(p):
            continue
        prem = b[f"ask_{h}"].sum(); fee = b[f"ask_{h}"].map(fee1).sum(); pay = b.result.sum()
        f100 = b[f"ask_{h}"].map(fee100).sum()
        skipped = p[p[f"buyable_{h}"] != True]  # noqa: E712
        rows.append({"label": "observed", "series": series, "city": city, "year": year, "decision_hours_before_close": h,
                     "first_day": g.date.min(), "last_day": g.date.max(), "market_days": len(g), "pulled": len(p),
                     "days_bought": len(b), "days_no_buyable_ask": len(skipped),
                     "rain_days_missed_no_ask": int(skipped.result.sum()),
                     "total_premium": round(prem, 2), "total_fees_1_contract_orders": round(fee, 2),
                     "total_payout": int(pay), "net": round(pay - prem - fee, 2),
                     "premium_per_1_payout": round(prem / pay, 3) if pay else None,
                     "premium_plus_fee_per_1_payout": round((prem + fee) / pay, 3) if pay else None,
                     "net_per_contract": round((pay - prem - fee) / len(b), 4) if len(b) else None,
                     "total_fees_100_lot_per_contract": round(f100, 2),
                     "net_100_lot_per_contract": round(pay - prem - f100, 2)})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- price model
def priced_mask(df: pd.DataFrame, h: int = 24) -> pd.Series:
    """Days with a real price: a fresh quote with ask < 1.00, or ask = 1.00 with a positive bid.

    Ask = 1.00 with a positive bid means buyers are bidding and nobody sells: protection costs the
    full $1 (in 2026 the bid was 0.98-0.99 on every such day and all resolved Yes). An empty book
    (bid 0, ask 1), a stale quote and no quote are not prices and are left out.
    """
    fresh = (df[f"has_quote_{h}"] == True) & (df[f"stale_{h}"] == False)  # noqa: E712
    return fresh & ((df[f"ask_is_1_{h}"] == False) | (df[f"bid_is_0_{h}"] == False))  # noqa: E712


def model_frame(df: pd.DataFrame, clim: pd.DataFrame, daily: dict, ks: dict, mask=None) -> pd.DataFrame:
    """Days of 2025-2026 with p_clim, rain_yesterday (under the contract's own rule) and k."""
    mask = priced_mask(df) if mask is None else mask
    d = df[mask & df.year.isin([2025, 2026])].copy()
    d["rule"] = np.where(d.trace_counts, "trace_yes", "trace_no")
    d["month"] = pd.to_datetime(d.date).dt.month
    d = d.merge(clim[["city", "rule", "month", "rain_share"]].rename(columns={"rain_share": "p_clim"}),
                on=["city", "rule", "month"], how="left")
    ry, kk = [], []
    for r in d.itertuples():
        col = "wet_or_trace" if r.rule == "trace_yes" else "wet"
        prev = pd.Timestamp(r.date) - pd.Timedelta(days=1)
        s = daily[r.city][col]
        ry.append(int(s.loc[prev]) if prev in s.index else None)
        kk.append(ks[(r.city, r.rule)])
    d["rain_yesterday"] = ry; d["k"] = kk
    d["ask"] = d.ask_24; d["y"] = d.result
    d["set"] = np.where(d.year == 2025, "A: NYC 2025",
                        np.where(d.series == "KXRAINNYC", "B: NYC 2026 to Jul 15", "C: four cities Jul 15-Sep 30 2026"))
    return d


def predict(d: pd.DataFrame, model: str, par: dict) -> np.ndarray:
    out = []
    for r in d.itertuples():
        p = dict(par)
        if model == "persist":
            p["k"] = r.k
        out.append(modelled_ask(r.p_clim, model, p, rain_today=int(r.y),
                                rain_yesterday=None if pd.isna(r.rain_yesterday) else int(r.rain_yesterday)))
    return np.array(out)


def fit(d: pd.DataFrame, model: str) -> dict:
    if model == "persist":
        # k differs by city and rule (station persistence), so fit a on the residual directly
        return {"a": float((d.ask - (d.p_clim + d.k * (d.rain_yesterday - d.p_clim))).mean())}
    return fit_model(model, d.ask.tolist(), d.p_clim.tolist(), d.y.tolist())


def evaluate(d: pd.DataFrame, pred: np.ndarray) -> dict:
    a = d.ask.values; y = d.y.values
    fo = np.array([fee1(x) for x in a]); fm = np.array([fee1(x) for x in pred])
    r = {"n_days": len(d), "obs_mean_ask": a.mean(), "mod_mean_ask": pred.mean(),
         "err_mean_ask": pred.mean() - a.mean(),
         "obs_mean_cost_ask_plus_fee": (a + fo).mean(), "mod_mean_cost_ask_plus_fee": (pred + fm).mean(),
         "err_mean_cost": (pred + fm).mean() - (a + fo).mean(),
         "payout_per_contract": y.mean(),
         "obs_premium_per_1_payout": a.sum() / y.sum() if y.sum() else np.nan,
         "mod_premium_per_1_payout": pred.sum() / y.sum() if y.sum() else np.nan,
         "obs_net_per_contract": (y - a - fo).mean(), "mod_net_per_contract": (y - pred - fm).mean(),
         "obs_mean_ask_rain_days": a[y == 1].mean() if (y == 1).any() else np.nan,
         "mod_mean_ask_rain_days": pred[y == 1].mean() if (y == 1).any() else np.nan,
         "obs_mean_ask_dry_days": a[y == 0].mean() if (y == 0).any() else np.nan,
         "mod_mean_ask_dry_days": pred[y == 0].mean() if (y == 0).any() else np.nan,
         "daily_rmse_ask": float(np.sqrt(((pred - a) ** 2).mean())),
         "daily_mae_ask": float(np.abs(pred - a).mean())}
    # net gain kept on a rain day relative to a dry day: 1 - (ask on rain days - ask on dry days)
    r["obs_rain_minus_dry_net"] = 1 - (r["obs_mean_ask_rain_days"] - r["obs_mean_ask_dry_days"])
    r["mod_rain_minus_dry_net"] = 1 - (r["mod_mean_ask_rain_days"] - r["mod_mean_ask_dry_days"])
    return {k: (round(float(v), 4) if isinstance(v, (float, np.floating)) else v) for k, v in r.items()}


def boot_se(d: pd.DataFrame, model: str, draws: int = 1000, seed: int = 473) -> dict:
    """Standard error of the parameters: bootstrap over calendar dates (cities share a day's weather)."""
    rng = np.random.default_rng(seed)
    dates = d.date.unique()
    groups = {k: g for k, g in d.groupby("date")}
    out = []
    for _ in range(draws):
        pick = rng.choice(dates, size=len(dates), replace=True)
        out.append(fit(pd.concat([groups[x] for x in pick]), model))
    return {k: float(np.std([o[k] for o in out])) for k in out[0]}


def retention_by_month(d: pd.DataFrame, final: dict) -> pd.DataFrame:
    """How much of a wet month's extra payout the buyer keeps after paying the asks.

    Per city, series and month: X = sum(result - p_clim) (rain days above climatology),
    Y = sum(result - ask) (payout minus premium). Slope of Y on X across the city-months.
    Climatology pricing gives slope 1 by construction; a market with forecast skill gives less.
    """
    rows = []
    preds = {"observed asks": d.ask.values, **{f"modelled, {m}": predict(d, m, final[m]) for m in MODELS}}
    key = d.series + "|" + d.city + "|" + d.date.str[:7]
    for name, a in preds.items():
        g = pd.DataFrame({"key": key.values, "x": (d.y - d.p_clim).values, "y": d.y.values - a}).groupby("key").sum()
        slope = float(np.polyfit(g.x, g.y, 1)[0]); corr = float(np.corrcoef(g.x, g.y)[0, 1])
        rows.append({"label": "observed" if name.startswith("observed") else "modelled", "prices": name,
                     "city_months": len(g), "days": len(d), "slope_net_on_excess_rain_days": round(slope, 3),
                     "correlation": round(corr, 3), "sd_monthly_net": round(float(g.y.std()), 3)})
    return pd.DataFrame(rows)


def model_work(df, clim, daily, ks, mask=None):
    d = model_frame(df, clim, daily, ks, mask)
    d = d.dropna(subset=["p_clim", "rain_yesterday"])
    sets = sorted(d.set.unique())
    rows, fits = [], {}
    designs = [(f"hold out {s}", [x for x in sets if x != s], [s]) for s in sets]
    designs.append(("hold out Philadelphia+Trenton+Newark (fit on all NYC)", None, None))
    for name, tr_sets, te_sets in designs:
        if tr_sets is None:
            tr, te = d[d.city == "NYC"], d[d.city != "NYC"]
        else:
            tr, te = d[d.set.isin(tr_sets)], d[d.set.isin(te_sets)]
        if not len(tr) or not len(te):
            continue
        for m in MODELS:
            par = fit(tr, m)
            fits[(name, m)] = par
            for part, x in (("train", tr), ("test (held out)", te)):
                rows.append({"label": "modelled vs observed", "design": name, "model": m, "part": part,
                             **{f"par_{k}": round(v, 4) for k, v in par.items()}, **evaluate(x, predict(x, m, par))})
            if te_sets and te_sets[0].startswith("C"):
                for city, x in te.groupby("city"):
                    rows.append({"label": "modelled vs observed", "design": name, "model": m,
                                 "part": f"test (held out), {city} only",
                                 **{f"par_{k}": round(v, 4) for k, v in par.items()}, **evaluate(x, predict(x, m, par))})
    ev = pd.DataFrame(rows)
    final = {m: fit(d, m) for m in MODELS}
    resid = {m: float(np.std(d.ask.values - predict(d, m, final[m]))) for m in MODELS}
    return d, ev, fits, final, resid


def sharpness(df, clim, daily, ks) -> pd.DataFrame:
    rows = []
    d0 = model_frame(df, clim, daily, ks, mask=pd.Series(True, index=df.index)).dropna(subset=["p_clim", "rain_yesterday"])
    d0["p_persist"] = d0.p_clim + d0.k * (d0.rain_yesterday - d0.p_clim)
    sets = {"all 2025-2026": d0, **{s: g for s, g in d0.groupby("set")},
            "Philadelphia+Trenton+Newark 2026": d0[d0.city != "NYC"]}
    for name, g in sets.items():
        for h in DECISION_HOURS:
            t = g[g[f"two_sided_{h}"] == True]  # noqa: E712
            if len(t) < 5:
                continue
            y = t.y.tolist(); yb = float(np.mean(y))
            bc = brier(t.p_clim.tolist(), y)
            r = {"label": "observed prices vs station climatology", "set": name, "hours_before_close": h, "n_days": len(t),
                 "yes_share": round(yb, 3),
                 "brier_observed_mid": round(brier(t[f"mid_{h}"].tolist(), y), 4),
                 "brier_observed_ask": round(brier(t[f"ask_{h}"].tolist(), y), 4),
                 "brier_climatology_month": round(bc, 4),
                 "brier_persistence": round(brier(t.p_persist.tolist(), y), 4),
                 "brier_sample_base_rate": round(yb * (1 - yb), 4),
                 "mean_mid_rain_days": round(t.loc[t.y == 1, f"mid_{h}"].mean(), 3),
                 "mean_mid_dry_days": round(t.loc[t.y == 0, f"mid_{h}"].mean(), 3)}
            r["skill_score_mid_vs_climatology"] = round(1 - r["brier_observed_mid"] / bc, 3)
            r["skill_score_persistence_vs_climatology"] = round(1 - r["brier_persistence"] / bc, 3)
            rows.append(r)
    return pd.DataFrame(rows)


def figure(cal: pd.DataFrame) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    c = cal[(cal.set == "all markets") & (cal.price == "mid") & (cal.hours_before_close == 24) & (cal.n > 0)]
    fig, (ax, bx) = plt.subplots(2, 1, figsize=(7.0, 8.4), dpi=150, sharex=True,
                                 gridspec_kw={"height_ratios": [4.2, 1], "hspace": 0.08})
    ax.plot([0, 1], [0, 1], color="#888888", lw=1, ls="--", label="perfect calibration")
    lo = (c.yes_share - c.yes_share_lo95).clip(lower=0); hi = (c.yes_share_hi95 - c.yes_share).clip(lower=0)
    ax.errorbar(c.mean_price, c.yes_share, yerr=[lo, hi], fmt="o-", color="#1f5fa8", ms=7, lw=1.6, capsize=3,
                label="observed Kalshi prices, 10-cent bins (95% interval)")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.set_xticks(np.arange(0, 1.01, 0.1)); ax.set_yticks(np.arange(0, 1.01, 0.1))
    ax.grid(color="#dddddd", lw=0.6)
    ax.set_ylabel("Share of markets that resolved Yes (rain)", fontsize=10)
    ax.set_title("Observed Kalshi prices: daily rain markets, May-Sep\n"
                 "NYC 2021-22 and 2025-26; Philadelphia, Trenton, Newark 2026", fontsize=11)
    ax.legend(loc="upper left", fontsize=9, frameon=False)
    mid = (c.bin_lo + c.bin_hi) / 2
    bx.bar(mid, c.n, width=0.085, color="#9db8d9", edgecolor="#1f5fa8", lw=0.6)
    for x, n in zip(mid, c.n):
        bx.annotate(str(int(n)), (x, n), textcoords="offset points", xytext=(0, 3), ha="center", fontsize=9)
    bx.set_ylim(0, c.n.max() * 1.3)
    bx.set_ylabel("Market days", fontsize=10)
    bx.set_xlabel(f"Mid price 24 hours before close (dollars); {int(c.n.sum())} market days with a two-sided quote", fontsize=10)
    bx.grid(axis="y", color="#dddddd", lw=0.6); bx.set_axisbelow(True)
    fig.subplots_adjust(left=0.11, right=0.97, top=0.93, bottom=0.07)
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / "calibration.png")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(RAW / "rain" / "quote_table.csv")
    cov = df.groupby(["series", "city", "year"], sort=False).agg(
        markets=("ticker", "size"), pulled=("pulled", "sum"),
        pulled_but_no_candles=("n_candles", lambda x: int((x == 0).sum())),
        first_day=("date", "min"), last_day=("date", "max"),
        median_candles=("n_candles", "median")).reset_index()
    cov["not_pulled"] = cov.markets - cov.pulled
    cov.to_csv(OUT / "pull_coverage.csv", index=False)
    print(cov.to_string())
    df = df[df.pulled]
    q = quotes_table(df); q.to_csv(OUT / "quotes_by_city_year.csv", index=False)
    cal = calib(df); cal.to_csv(OUT / "calibration.csv", index=False)
    st = strategy(df); st.to_csv(OUT / "strategy_24h.csv", index=False)
    clim, ks, daily = climatology()
    clim.to_csv(OUT / "climatology.csv", index=False)
    sh = sharpness(df, clim, daily, ks); sh.to_csv(OUT / "sharpness.csv", index=False)
    # main fit: days on which a contract could be bought (ask < 1.00). Sensitivity: also the days with
    # ask = 1.00 and a positive bid, kept at 1.00 ("priced days").
    dp, evp, fitsp, finalp, residp = model_work(df, clim, daily, ks)
    d, ev, fits, final, resid = model_work(df, clim, daily, ks, mask=(df.buyable_24 == True))  # noqa: E712
    db, finalb = d, final
    evp.insert(1, "sample", "sensitivity: priced days (ask < 1.00, or ask = 1.00 with a bid)")
    ev.insert(1, "sample", "main: buyable days (ask < 1.00)")
    ev = pd.concat([ev, evp], ignore_index=True)
    ev.to_csv(OUT / "model_eval.csv", index=False)
    ret = pd.concat([retention_by_month(d, final).assign(sample="main: buyable days"),
                     retention_by_month(dp, finalp).assign(sample="sensitivity: priced days")], ignore_index=True)
    ret.to_csv(OUT / "retention_by_month.csv", index=False)
    se = {m: boot_se(d, m) for m in MODELS}
    no_offer_tab = {}
    for sname, g in dp.groupby("set"):
        one = g.ask >= 1 - 1e-9
        no_offer_tab[sname] = {"priced_days": int(len(g)), "ask_1.00_days": int(one.sum()),
                               "ask_1.00_days_that_rained": int(g.y[one].sum()), "rain_days": int(g.y.sum()),
                               "u_share_of_rain_days_with_no_offer": round(float(g.y[one].sum() / g.y.sum()), 4)}
    g26 = dp[dp.year == 2026]
    u_c = no_offer_tab["C: four cities Jul 15-Sep 30 2026"]["u_share_of_rain_days_with_no_offer"]
    u_2026 = round(float(g26.y[g26.ask >= 1 - 1e-9].sum() / g26.y.sum()), 4)
    per_set = {sname: {m: {k: round(v, 4) for k, v in fit(g, m).items()} for m in MODELS} for sname, g in d.groupby("set")}
    per_set["Philadelphia+Trenton+Newark 2026"] = {m: {k: round(v, 4) for k, v in fit(d[d.city != "NYC"], m).items()} for m in MODELS}
    a_net = {m: round(float((d.ask - d.y).mean()), 4) for m in ("skill",)}
    primary = "hold out C: four cities Jul 15-Sep 30 2026"
    js = {
        "label": "MODELLED price parameters, fitted on observed Kalshi asks 24 hours before close",
        "recommended": "skill",
        "formula": {"clim": "ask = clamp(p + a)", "persist": "ask = clamp(p + k*(rain_yesterday - p) + a)",
                    "skill": "ask = clamp(p + s*(rain_today - p) + a)",
                    "clamp": "round to cent, keep in [0.01, 0.99]",
                    "fee": "round_up_to_cent(0.07 * C * ask * (1 - ask)) per order"},
        "p": "climatological share of days with a Yes outcome in that calendar month at the station (caller supplies it from training seasons)",
        "fit_sample": "days of 2025-2026 with a fresh quote 24 h before close and ask < 1.00 (a contract could be bought)",
        "fit_days": int(len(d)), "fit_sets": {s: int(n) for s, n in d.set.value_counts().sort_index().items()},
        "no_offer_days": no_offer_tab,
        "u_note": "u = share of rain days on which the ask was 1.00 with a positive bid (no seller). Default u is set C, the current KXRAIN series; all of 2026 gives " + str(u_2026) + "; the thin 2025 market was much worse.",
        "models": {m: {**{k: round(v, 4) for k, v in final[m].items()}, "resid_sd": round(resid[m], 4)} for m in MODELS},
        "param_se_bootstrap_by_date": {m: {k: round(v, 4) for k, v in se[m].items()} for m in MODELS},
        "a_net_matched": {"skill": a_net["skill"], "note": "mean(observed ask - result) on the fit days; use as a in a sensitivity run (keeps s)"},
        "models_fitted_on_each_set_alone": per_set,
        "sensitivity_models_fitted_on_priced_days_incl_ask_1.00": {m: {k: round(v, 4) for k, v in finalp[m].items()} for m in MODELS},
        "models_fitted_without_held_out_set_C": {m: {k: round(v, 4) for k, v in fits[(primary, m)].items()} for m in MODELS
                                                 if (primary, m) in fits},
        "persistence_k_by_city_rule": {f"{c}|{r}": round(v, 4) for (c, r), v in ks.items()},
        "persistence_k_note": "P(rain | rain yesterday) - P(rain | dry yesterday), May-Sep 1998-2024, station data. For 'persist' pass k for the station; default below is Trenton, trace = No.",
        "climatology_used_for_fit": "data/processed/kalshi_rain/climatology.csv (GHCN-Daily 1998-2024, by month)",
        "decision_time": "24 hours before close",
    }
    js["models"]["persist"]["k"] = round(ks[("TTN", "trace_no")], 4)
    for m in MODELS:
        js["models"][m]["u"] = u_c
    (OUT / "price_model.json").write_text(json.dumps(js, indent=1))
    figure(cal)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
    print(q[q.hours_before_close == 24].drop(columns=["label"]).to_string())
    print(st.drop(columns=["label"]).to_string())
    print(sh.drop(columns=["label"]).to_string())
    print(ev.drop(columns=["label"]).to_string())
    print(ret.to_string())
    print(json.dumps(js["models"], indent=1)); print(ks)
    print(cal[(cal.set == "all markets") & (cal.price == "mid") & (cal.hours_before_close == 24)].to_string())


if __name__ == "__main__":
    main()
