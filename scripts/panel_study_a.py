"""Part 1 Study A: payout mismatch of station hedges across the regional panel (SPEC_v2).

Inputs : data/processed/panel/tmax_panel.parquet, stations.csv, outlines.csv (optional, for map and coast proxy)
Outputs: results/part1/per_location.csv, summary.csv, improve_counts.csv, distance_test.csv,
         distance_regression.csv, mismatch_map.png, study_a_summary.md
Run: python scripts/panel_study_a.py
All numbers are computed from observed NCEI TMAX. Nothing is simulated.
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.panel import hedge as H  # noqa: E402

PAN = ROOT / "data/processed/panel"
OUT = ROOT / "results/part1"
SETS = {"L_pre": H.L_PRE, "L_now": H.L_NOW}
WINS = ["SELECT", "REPORT"]
TEB = "USW00094741"
STATS = ["mean_R", "miss_rate", "false_payout_rate"]


def coast_km(st, outl):
    """Distance (km) from each station to the nearest point of the GSHHS low-resolution ocean shoreline.

    Rough proxy. Shoreline includes Long Island Sound, Delaware Bay and Chesapeake Bay as drawn at low
    resolution. Great Lakes are not counted. Segments are densified to about 1 km before the search.
    """
    pts = []
    for _, g in outl[outl.kind == "coast"].groupby("seg"):
        lon, lat = g.lon.to_numpy(), g.lat.to_numpy()
        for a in range(len(g) - 1):
            n = max(2, int(H.haversine_km(lat[a], lon[a], lat[a + 1], lon[a + 1])) + 1)
            t = np.linspace(0, 1, n)
            pts.append(np.c_[lon[a] + t * (lon[a + 1] - lon[a]), lat[a] + t * (lat[a + 1] - lat[a])])
    p = np.vstack(pts)
    return np.array([H.haversine_km(r.lat, r.lon, p[:, 1], p[:, 0]).min() for r in st.itertuples()])


def ols(y, X, names):
    """Plain OLS with classical standard errors. Returns a table and R^2."""
    X = np.c_[np.ones(len(y)), X]
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ beta
    dof = len(y) - X.shape[1]
    cov = res @ res / dof * np.linalg.inv(X.T @ X)
    se = np.sqrt(np.diag(cov))
    t = beta / se
    p = 2 * stats.t.sf(np.abs(t), dof)
    r2 = 1 - res @ res / ((y - y.mean()) ** 2).sum()
    return pd.DataFrame({"term": ["intercept"] + names, "coef": beta, "se": se, "t": t, "p": p}), r2, len(y)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    st = pd.read_csv(PAN / "stations.csv")
    panel = pd.read_parquet(PAN / "tmax_panel.parquet")
    wide = H.to_wide(panel)
    exp_ids = st[st.is_exposure]["id"].tolist()
    sidx = st.set_index("id")
    not_listed = [i for i in exp_ids if i not in H.L_NOW]
    pops = {"all_exposure": exp_ids, "excl_4_listed": not_listed,
            "excl_4_listed_and_TEB": [i for i in not_listed if i != TEB]}

    # ------------------------------------------------------------ per-location results
    res, yearly = {}, {}
    for name, L in SETS.items():
        r, y = H.mismatch_under_listed_set(L, wide, st, location_ids=exp_ids, windows=WINS, return_yearly=True)
        res[name], yearly[name] = r.assign(listed_set=name), y.assign(listed_set=name)
    long = pd.concat(res.values(), ignore_index=True)
    long.insert(1, "name", long.location_id.map(sidx["name"]))
    long.insert(2, "state", long.location_id.map(sidx["state"]))
    long["hedge_station_name"] = long.hedge_station.map(sidx["name"])
    long = long[["listed_set", "window", "location_id", "name", "state", "in_listed_set", "hedge", "hedge_station",
                 "hedge_station_name", "strike", "dist_km", "fit_R", "fit_n", "n", "n_hot", "n_pay", "fn_days",
                 "fp_days", "R", "FN", "FP", "miss_rate", "false_payout_rate"]]
    long.round(5).to_csv(OUT / "per_location_long.csv", index=False)

    key = ["listed_set", "window", "location_id", "name", "state", "in_listed_set"]
    val = ["hedge_station", "strike", "dist_km", "fit_R", "n", "n_hot", "fn_days", "fp_days", "R", "miss_rate",
           "false_payout_rate"]
    b = long[long.hedge == "baseline"][key + val].rename(columns={v: f"base_{v}" for v in val})
    a = long[long.hedge == "adjusted"][key + val].rename(columns={v: f"adj_{v}" for v in val})
    per = b.merge(a, on=key)
    per["R_change"] = per.adj_R - per.base_R  # negative = adjusted hedge is better
    per["outcome"] = np.where(per.R_change < -1e-12, "improve", np.where(per.R_change > 1e-12, "worsen", "unchanged"))
    # R of holding no contract at all = the location's own hot-day share (every hot day is a miss).
    per["no_hedge_R"] = per.adj_n_hot / per.adj_n
    per["adj_beats_no_hedge"] = per.adj_R < per.no_hedge_R - 1e-12
    per["base_beats_no_hedge"] = per.base_R < per.base_n_hot / per.base_n - 1e-12
    per["hedge_changed"] = (per.base_hedge_station != per.adj_hedge_station) | (per.base_strike != per.adj_strike)
    per.round(5).to_csv(OUT / "per_location.csv", index=False)

    # ------------------------------------------------------------ summary with bootstrap
    rows, crow = [], []
    for w in WINS:
        years = list(range(H.WINDOWS[w][0], H.WINDOWS[w][1] + 1))
        for pop, ids in pops.items():
            arms = {}
            for s in SETS:
                for hk in ("baseline", "adjusted"):
                    y = yearly[s]
                    arms[f"{s}|{hk}"] = y[(y.hedge == hk) & y.year.isin(years) & y.location_id.isin(ids)]
            boot = H.year_block_bootstrap(arms, years=years)
            point = {k: H.aggregate_stats(v.groupby("location_id")[H.COUNT_COLS].sum()) for k, v in arms.items()}
            for k in arms:
                s, hk = k.split("|")
                for stt in STATS:
                    lo, hi = H.percentile_interval(boot[f"{k}:{stt}"])
                    rows.append({"window": w, "population": pop, "n_locations": len(ids), "listed_set": s,
                                 "quantity": hk, "stat": stt, "value": point[k][stt], "ci_lo": lo, "ci_hi": hi})
            diffs = {("L_pre", "adjusted - baseline"): ("L_pre|adjusted", "L_pre|baseline"),
                     ("L_now", "adjusted - baseline"): ("L_now|adjusted", "L_now|baseline"),
                     ("L_now - L_pre", "baseline"): ("L_now|baseline", "L_pre|baseline"),
                     ("L_now - L_pre", "adjusted"): ("L_now|adjusted", "L_pre|adjusted")}
            for (s, q), (k1, k2) in diffs.items():
                for stt in STATS:
                    d = boot[f"{k1}:{stt}"] - boot[f"{k2}:{stt}"]
                    lo, hi = H.percentile_interval(d)
                    rows.append({"window": w, "population": pop, "n_locations": len(ids), "listed_set": s,
                                 "quantity": q, "stat": stt, "value": point[k1][stt] - point[k2][stt],
                                 "ci_lo": lo, "ci_hi": hi})
            for s in SETS:
                p = per[(per.listed_set == s) & (per.window == w) & per.location_id.isin(ids)]
                c = p.outcome.value_counts()
                crow.append({"window": w, "population": pop, "listed_set": s, "n_locations": len(p),
                             "improve": int(c.get("improve", 0)), "unchanged": int(c.get("unchanged", 0)),
                             "worsen": int(c.get("worsen", 0)), "hedge_differs_from_baseline": int(p.hedge_changed.sum()),
                             "adj_beats_no_hedge": int(p.adj_beats_no_hedge.sum()),
                             "base_beats_no_hedge": int(p.base_beats_no_hedge.sum()),
                             "mean_no_hedge_R": p.no_hedge_R.mean(),
                             "median_R_change": p.R_change.median(), "mean_R_change": p.R_change.mean()})
    summ = pd.DataFrame(rows)
    summ.round(5).to_csv(OUT / "summary.csv", index=False)
    counts = pd.DataFrame(crow)
    counts.round(5).to_csv(OUT / "improve_counts.csv", index=False)

    # ------------------------------------------------------------ distance test
    outl = pd.read_csv(PAN / "outlines.csv") if (PAN / "outlines.csv").exists() else None
    geo = st[st.id.isin(exp_ids)].set_index("id")[["lat", "lon", "elev_m"]].copy()
    geo["coast_km"] = coast_km(st[st.id.isin(exp_ids)], outl) if outl is not None else np.nan
    drows, rrows, scat = [], [], {}
    allw = {"SELECT": "SELECT", "REPORT": "REPORT", "2015-2025": (2015, 2025)}
    for s, L in SETS.items():
        ids = [i for i in exp_ids if i not in L]
        for wname, w in allw.items():
            for hk in ("baseline", "adjusted"):
                if hk == "adjusted" and wname == "2015-2025":
                    continue  # adjusted hedge is fitted on 2015-2019; not an out-of-sample window
                recs = []
                for i in ids:
                    hd = H.baseline_hedge(i, L, st) if hk == "baseline" else H.adjusted_hedge(i, L, wide, st)
                    yc = H.yearly_counts(wide, i, hd, w)
                    c = yc.sum()
                    m = H.metrics_from_counts(c)
                    recs.append({"id": i, "dist_km": hd.dist_km, "R": m["R"], "miss_rate": m["miss_rate"],
                                 "false_payout_rate": m["false_payout_rate"], "hot_share": c.n_hot / c.n,
                                 "n_hot": c.n_hot, "hedge_station": hd.station,
                                 "elev_diff_m": abs(geo.at[i, "elev_m"] - sidx.at[hd.station, "elev_m"]),
                                 "coast_km": geo.at[i, "coast_km"], "yc": yc})
                d = pd.DataFrame(recs)
                scat[(s, wname, hk)] = d
                # year-block bootstrap of the Pearson correlation between distance and R
                yrs = sorted(set().union(*[set(r.index) for r in d.yc]))
                draws = H.bootstrap_year_draws(yrs)
                mism = np.array([[(r.fn_days + r.fp_days).reindex(yrs).fillna(0).to_numpy()] for r in d.yc])[:, 0, :]
                nn = np.array([r.n.reindex(yrs).fillna(0).to_numpy() for r in d.yc])
                pos = {y: j for j, y in enumerate(yrs)}
                bc = []
                for dr in draws:
                    j = [pos[y] for y in dr]
                    Rb = mism[:, j].sum(1) / nn[:, j].sum(1)
                    bc.append(np.corrcoef(d.dist_km, Rb)[0, 1])
                lo, hi = H.percentile_interval(bc)
                for yv in ("R", "miss_rate", "false_payout_rate"):
                    ok = d[yv].notna() & ((d.n_hot >= 10) if yv == "miss_rate" else True)
                    pr = stats.pearsonr(d.dist_km[ok], d[yv][ok])
                    sr = stats.spearmanr(d.dist_km[ok], d[yv][ok])
                    drows.append({"listed_set": s, "window": wname, "hedge": hk, "y": yv, "n_locations": int(ok.sum()),
                                  "pearson_r": pr[0], "pearson_p": pr[1], "spearman_rho": sr[0], "spearman_p": sr[1],
                                  "pearson_boot_lo": lo if yv == "R" else np.nan,
                                  "pearson_boot_hi": hi if yv == "R" else np.nan,
                                  "note": "miss_rate: locations with >= 10 hot days only" if yv == "miss_rate" else ""})
                if hk == "baseline" and outl is not None:
                    specs = {"dist_only": ["dist_100km"],
                             "dist_elev_coast": ["dist_100km", "elev_diff_100m", "coast_100km"],
                             "dist_elev_coast_hotshare": ["dist_100km", "elev_diff_100m", "coast_100km", "hot_share"]}
                    X = pd.DataFrame({"dist_100km": d.dist_km / 100, "elev_diff_100m": d.elev_diff_m / 100,
                                      "coast_100km": d.coast_km / 100, "hot_share": d.hot_share})
                    for spec, cols in specs.items():
                        for yv in ("R", "miss_rate"):
                            ok = d[yv].notna() & ((d.n_hot >= 10) if yv == "miss_rate" else True)
                            tab, r2, n = ols(d[yv][ok].to_numpy(), X.loc[ok, cols].to_numpy(), cols)
                            rrows.append(tab.assign(listed_set=s, window=wname, y=yv, model=spec, r2=r2, n_locations=n))
    dist = pd.DataFrame(drows)
    dist.round(5).to_csv(OUT / "distance_test.csv", index=False)
    reg = pd.concat(rrows, ignore_index=True)[["listed_set", "window", "y", "model", "n_locations", "r2", "term",
                                               "coef", "se", "t", "p"]]
    reg.round(6).to_csv(OUT / "distance_regression.csv", index=False)
    geo.round(3).to_csv(OUT / "location_geography.csv")

    # binned view (L_now baseline, REPORT)
    d = scat[("L_now", "REPORT", "baseline")]
    bins = [0, 50, 100, 200, 300, 1000]
    d["bin"] = pd.cut(d.dist_km, bins)
    binned = d.groupby("bin", observed=True).agg(n=("R", "size"), mean_R=("R", "mean"), mean_hot_share=("hot_share", "mean"),
                                                  fn=("yc", lambda s: sum(x.fn_days.sum() for x in s)),
                                                  hot=("n_hot", "sum")).reset_index()
    binned["pooled_miss_rate"] = binned.fn / binned.hot
    binned.round(4).to_csv(OUT / "distance_bins_Lnow_REPORT_baseline.csv", index=False)

    # ------------------------------------------------------------ figures
    make_map(per, st, outl)
    make_scatter(scat)

    # ------------------------------------------------------------ text summary
    write_md(summ, counts, dist, reg, binned, per, st)
    pd.set_option("display.width", 220)
    print(summ[(summ.window == "REPORT") & (summ.population != "all_exposure") & (summ.stat == "mean_R")].to_string(index=False))
    print(counts.to_string(index=False))
    print(dist[(dist.y != "false_payout_rate")].to_string(index=False))
    print(binned.to_string(index=False))


INK, MUTED, SURFACE = "#1f2328", "#6b7280", "#ffffff"


def make_map(per, st, outl):
    sidx = st.set_index("id")
    fig, axes = plt.subplots(1, 2, figsize=(14, 7.2), sharex=True, sharey=True, facecolor=SURFACE)
    vmax = 0.12
    for ax, s in zip(axes, ("L_pre", "L_now")):
        p = per[(per.listed_set == s) & (per.window == "REPORT") & ~per.in_listed_set]
        if outl is not None:
            for kind, col, lw in (("state", "#b8bec6", 0.8), ("lake", "#9aa3ad", 0.8), ("coast", "#7d8791", 0.9)):
                for _, g in outl[outl.kind == kind].groupby("seg"):
                    ax.plot(g.lon, g.lat, color=col, lw=lw, zorder=1)
        sc = ax.scatter(sidx.loc[p.location_id, "lon"], sidx.loc[p.location_id, "lat"], c=p.adj_R, cmap="Blues",
                        vmin=0, vmax=vmax, s=70, edgecolor="#334155", linewidth=0.6, zorder=3)
        L = H.L_PRE if s == "L_pre" else H.L_NOW
        ax.scatter(sidx.loc[L, "lon"], sidx.loc[L, "lat"], marker="*", s=330, color="#d97706", edgecolor=INK,
                   linewidth=0.8, zorder=4, label="Listed station (has a contract)")
        inv = {v: k for k, v in H.LISTED.items()}
        off = {"NYC": (8, 8), "Philadelphia": (-12, -16), "Newark": (-52, 6), "Trenton": (-50, -4)}
        for i in L:
            ax.annotate(inv[i], (sidx.at[i, "lon"], sidx.at[i, "lat"]), xytext=off[inv[i]], textcoords="offset points",
                        fontsize=9.5, color=INK, zorder=5,
                        bbox=dict(boxstyle="round,pad=0.15", fc=SURFACE, ec="none", alpha=0.8))
        ax.set_title(f"{s}: {len(L)} listed stations. Mean mismatch {p.adj_R.mean():.3f} over {len(p)} locations",
                     fontsize=11.5, color=INK, loc="left")
        ax.set_xlim(-81.2, -71.5)
        ax.set_ylim(37.8, 45.3)
        ax.set_aspect(1 / np.cos(np.radians(41.5)))
        ax.set_xlabel("Longitude (deg)", color=MUTED)
        ax.tick_params(colors=MUTED, labelsize=9)
        for sp in ax.spines.values():
            sp.set_color("#d1d5db")
    axes[0].set_ylabel("Latitude (deg)", color=MUTED)
    axes[0].legend(loc="upper left", frameon=True, facecolor=SURFACE, edgecolor="none", framealpha=0.9, fontsize=10)
    cb = fig.colorbar(sc, ax=axes, orientation="horizontal", fraction=0.045, pad=0.09, aspect=50, extend="max")
    cb.set_label("Payout mismatch R of the adjusted hedge, REPORT window 2023-2025 (share of May-Sep days where "
                 "the 90 F event and the payout disagree)", color=INK, fontsize=10)
    cb.ax.tick_params(colors=MUTED, labelsize=9)
    fig.suptitle("Payout mismatch at airport-grade locations without their own contract, by listed set "
                 "(observed NCEI TMAX)", fontsize=13.5, color=INK, x=0.125, ha="left", y=0.965)
    fig.savefig(OUT / "mismatch_map.png", dpi=150, bbox_inches="tight", facecolor=SURFACE)
    plt.close(fig)


def make_scatter(scat):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), facecolor=SURFACE)
    d = scat[("L_now", "REPORT", "baseline")]
    for ax, yv, lab in ((axes[0], "R", "Payout mismatch R"), (axes[1], "miss_rate", "Miss rate (missed hot days / hot days)")):
        ok = d[yv].notna() & ((d.n_hot >= 10) if yv == "miss_rate" else True)
        ax.scatter(d.dist_km[ok], d[yv][ok], s=42, color="#2563eb", edgecolor=SURFACE, linewidth=0.8)
        r = stats.pearsonr(d.dist_km[ok], d[yv][ok])[0]
        ax.set_title(f"{lab}: Pearson r = {r:+.2f}, n = {int(ok.sum())}", fontsize=11, loc="left", color=INK)
        ax.set_xlabel("Distance to nearest listed station (km)", color=MUTED)
        ax.set_ylabel(lab, color=MUTED)
        ax.set_ylim(bottom=0)
        ax.grid(color="#e5e7eb", lw=0.6)
        ax.set_axisbelow(True)
        ax.tick_params(colors=MUTED, labelsize=9)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
    fig.suptitle("Baseline hedge under L_now, REPORT 2023-2025. Right panel: locations with at least 10 hot days",
                 fontsize=11.5, color=INK, x=0.07, ha="left")
    fig.tight_layout()
    fig.savefig(OUT / "distance_scatter.png", dpi=150, facecolor=SURFACE)
    plt.close(fig)


def write_md(summ, counts, dist, reg, binned, per, st):
    def cell(w, pop, s, q, stt):
        r = summ[(summ.window == w) & (summ.population == pop) & (summ.listed_set == s) & (summ.quantity == q)
                 & (summ.stat == stt)].iloc[0]
        return f"{r.value:.4f} [{r.ci_lo:.4f}, {r.ci_hi:.4f}]"
    L = ["# Study A summary (generated by scripts/panel_study_a.py)", "",
         "Observed NCEI TMAX only. May-Sep. Hedges fitted on FIT 2015-2019. Intervals: year-block bootstrap, "
         "1,000 draws, seed 473, 95% percentile.",
         "REPORT and SELECT hold three summers each, so a bootstrap draw can take only 10 distinct year mixes. "
         "Read the intervals as rough.",
         "mean_R = unweighted mean over locations. miss_rate and false_payout_rate are pooled over locations.", ""]
    for pop in ("excl_4_listed", "all_exposure", "excl_4_listed_and_TEB"):
        n = int(summ[summ.population == pop].n_locations.iloc[0])
        for w in ("REPORT", "SELECT"):
            L += [f"## {w}, population {pop} ({n} locations)", "",
                  "| listed set | hedge | mean R | miss rate | false-payout rate |", "|---|---|---|---|---|"]
            for s in ("L_pre", "L_now"):
                for q in ("baseline", "adjusted", "adjusted - baseline"):
                    L.append(f"| {s} | {q} | " + " | ".join(cell(w, pop, s, q, x) for x in STATS) + " |")
            for q in ("baseline", "adjusted"):
                L.append(f"| L_now - L_pre | {q} | " + " | ".join(cell(w, pop, "L_now - L_pre", q, x) for x in STATS) + " |")
            L.append("")
    L += ["## Locations where the adjusted hedge beats, equals or loses to the baseline (by R)", "",
          "| window | population | listed set | n | improve | unchanged | worsen | hedge differs from baseline | "
          "baseline beats no hedge | adjusted beats no hedge | mean no-hedge R |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in counts.itertuples():
        L.append(f"| {r.window} | {r.population} | {r.listed_set} | {r.n_locations} | {r.improve} | {r.unchanged} | "
                 f"{r.worsen} | {r.hedge_differs_from_baseline} | {r.base_beats_no_hedge} | {r.adj_beats_no_hedge} | "
                 f"{r.mean_no_hedge_R:.4f} |")
    L += ["", "No hedge = hold no contract. Its mismatch equals the location's own share of 90 F days.", ""]
    L += ["", "## Distance to the hedge station vs mismatch (locations not in the listed set)", "",
          "| listed set | window | hedge | y | n | Pearson r (p) | Spearman rho (p) | bootstrap 95% for Pearson |",
          "|---|---|---|---|---|---|---|---|"]
    for r in dist[dist.y != "false_payout_rate"].itertuples():
        bt = f"[{r.pearson_boot_lo:+.2f}, {r.pearson_boot_hi:+.2f}]" if r.y == "R" else ""
        L.append(f"| {r.listed_set} | {r.window} | {r.hedge} | {r.y} | {r.n_locations} | {r.pearson_r:+.2f} ({r.pearson_p:.3g}) | "
                 f"{r.spearman_rho:+.2f} ({r.spearman_p:.3g}) | {bt} |")
    L += ["", "p-values treat locations as independent. They are not (neighbours share weather), so p-values are too small.",
          "", "### Distance bins, L_now baseline, REPORT", "",
          "| distance to nearest listed station (km) | n | mean R | mean hot-day share | pooled miss rate |", "|---|---|---|---|---|"]
    for r in binned.itertuples():
        L.append(f"| {r.bin} | {r.n} | {r.mean_R:.4f} | {r.mean_hot_share:.4f} | {r.pooled_miss_rate:.3f} |")
    L += ["", "### OLS, L_now baseline, REPORT (classical standard errors)", "",
          "| y | model | n | R2 | term | coef | se | p |", "|---|---|---|---|---|---|---|---|"]
    for r in reg[(reg.listed_set == "L_now") & (reg.window == "REPORT")].itertuples():
        L.append(f"| {r.y} | {r.model} | {r.n_locations} | {r.r2:.3f} | {r.term} | {r.coef:+.4f} | {r.se:.4f} | {r.p:.3g} |")
    L += ["", "Units: dist per 100 km, elevation difference per 100 m, coast distance per 100 km (GSHHS low-resolution "
          "ocean shoreline, rough proxy), hot_share = the location's own share of 90 F days in the window.", ""]
    (OUT / "study_a_summary.md").write_text("\n".join(L))


if __name__ == "__main__":
    main()
