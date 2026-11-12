"""Geographic basis-risk statistics for local-vs-reference daily TMAX pairs.

Only rows with data_quality == "ok" enter any statistic. Missing days are counted, not filled.
Heat day at threshold k: TMAX >= k (degF), as in docs/SPEC.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
THRESHOLDS = (85, 90, 95)


def trigger_mismatch(local: np.ndarray, ref: np.ndarray, k: float) -> dict:
    """Counts and rates of trigger agreement at threshold k. Inputs must have no NaN."""
    local, ref = np.asarray(local, float), np.asarray(ref, float)
    if np.isnan(local).any() or np.isnan(ref).any():
        raise ValueError("trigger_mismatch expects complete pairs; filter on data_quality first")
    L, R = local >= k, ref >= k
    n = len(L)
    both, l_only, r_only = int((L & R).sum()), int((L & ~R).sum()), int((~L & R).sum())
    out = dict(k=k, n_days=n, heat_days_ref=int(R.sum()), heat_days_local=int(L.sum()),
               both_heat=both, local_heat_ref_not=l_only, ref_heat_local_not=r_only,
               neither=n - both - l_only - r_only)
    out["p_local_heat_ref_not"] = l_only / n if n else np.nan   # under-hedge day (A pays 0, target pays)
    out["p_ref_heat_local_not"] = r_only / n if n else np.nan   # over-hedge day (A pays, target 0)
    out["mismatch_rate"] = (l_only + r_only) / n if n else np.nan
    # conditional rates: share of local heat days the station contract misses, and vice versa
    out["miss_rate_given_local_heat"] = l_only / L.sum() if L.sum() else np.nan
    out["false_rate_given_ref_heat"] = r_only / R.sum() if R.sum() else np.nan
    return out


def temp_diff_stats(local: np.ndarray, ref: np.ndarray) -> dict:
    d = np.asarray(local, float) - np.asarray(ref, float)
    return dict(mean_diff_f=float(np.mean(d)), sd_diff_f=float(np.std(d, ddof=1)),
                mae_f=float(np.mean(np.abs(d))), p05_diff_f=float(np.percentile(d, 5)),
                p95_diff_f=float(np.percentile(d, 95)),
                corr=float(np.corrcoef(local, ref)[0, 1]))


def pair_table(aligned: pd.DataFrame, thresholds=THRESHOLDS) -> pd.DataFrame:
    rows = []
    for (city, lid, rid), g in aligned.groupby(["city", "local_station_id", "ref_station_id"], sort=False):
        ok = g[g["data_quality"] == "ok"]
        base = dict(city=city, local_station_id=lid, ref_station_id=rid, days_in_window=len(g),
                    days_ok=len(ok), coverage_pct=100.0 * len(ok) / len(g) if len(g) else np.nan,
                    first_date=g["date"].min(), last_date=g["date"].max())
        base.update(temp_diff_stats(ok["local_tmax_f"], ok["ref_tmax_f"]))
        for k in thresholds:
            r = dict(base)
            r.update(trigger_mismatch(ok["local_tmax_f"].to_numpy(), ok["ref_tmax_f"].to_numpy(), k))
            rows.append(r)
    return pd.DataFrame(rows)


def scatter_figure(aligned: pd.DataFrame, path: Path, k: float = 90) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    pairs = list(aligned.groupby(["city", "local_station_id", "ref_station_id"], sort=False))
    ncol = 4
    nrow = int(np.ceil(len(pairs) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(3.2 * ncol, 3.2 * nrow), squeeze=False)
    for ax, ((city, lid, rid), g) in zip(axes.flat, pairs):
        ok = g[g["data_quality"] == "ok"]
        x, y = ok["ref_tmax_f"], ok["local_tmax_f"]
        mis = (x >= k) != (y >= k)
        ax.scatter(x[~mis], y[~mis], s=3, alpha=0.25, color="#4a6fa5", label="agree")
        ax.scatter(x[mis], y[mis], s=5, alpha=0.6, color="#d1495b", label=f"mismatch at {k}F")
        lo, hi = 50, 105
        ax.plot([lo, hi], [lo, hi], color="0.4", lw=0.8)
        ax.axvline(k, color="0.6", lw=0.6, ls="--")
        ax.axhline(k, color="0.6", lw=0.6, ls="--")
        ax.set_xlim(lo, hi); ax.set_ylim(lo, hi)
        ax.set_title(f"{city}: {lid} vs {rid}", fontsize=7.5)
        ax.set_xlabel("reference TMAX (F)", fontsize=7)
        ax.set_ylabel("local TMAX (F)", fontsize=7)
        ax.tick_params(labelsize=6)
    for ax in list(axes.flat)[len(pairs):]:
        ax.axis("off")
    axes.flat[0].legend(fontsize=6, loc="upper left", markerscale=3)
    fig.suptitle("Daily TMAX, May-Sep 2015-2025, GHCN-Daily (local vs reference station)", fontsize=9)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    from src.load_weather import load_aligned
    a = load_aligned()
    t = pair_table(a)
    st = pd.read_csv(ROOT / "data" / "manifests" / "stations.csv")
    t = t.merge(st[["station_id", "name", "distance_km"]].rename(
        columns={"station_id": "local_station_id", "name": "local_name"}), on="local_station_id", how="left")
    cols = ["city", "local_station_id", "local_name", "ref_station_id", "distance_km", "k",
            "first_date", "last_date", "days_in_window", "days_ok", "coverage_pct",
            "heat_days_ref", "heat_days_local", "both_heat", "local_heat_ref_not", "ref_heat_local_not",
            "p_local_heat_ref_not", "p_ref_heat_local_not", "mismatch_rate",
            "miss_rate_given_local_heat", "false_rate_given_ref_heat",
            "mean_diff_f", "sd_diff_f", "mae_f", "p05_diff_f", "p95_diff_f", "corr"]
    t = t[cols]
    out = ROOT / "results" / "tables" / "basis_risk_prelim.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    t.round(4).to_csv(out, index=False)
    scatter_figure(a, ROOT / "results" / "figures" / "local_vs_ref_scatter.png")
    pd.set_option("display.width", 250)
    print(t[["city", "local_station_id", "distance_km", "k", "coverage_pct", "heat_days_ref", "heat_days_local",
             "p_local_heat_ref_not", "p_ref_heat_local_not", "mean_diff_f", "corr"]].round(3).to_string(index=False))
