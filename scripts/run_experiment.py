#!/usr/bin/env python
"""Run the Strategy A vs B comparison.

Real run (needs Qasim's aligned data):
    python scripts/run_experiment.py
Synthetic pipeline test (clearly labeled, NOT results):
    python scripts/run_experiment.py --synthetic

Outputs (real):      results/tables/comparison_*.csv, results/figures/loading_sweep.png
Outputs (synthetic): results/synthetic/...  (every file name starts with SYNTHETIC_)
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import backtest as bt  # noqa: E402
from src import local_residual as lr  # noqa: E402

DATA = ROOT / "data" / "processed" / "aligned_daily.csv"

# Categorical slots 1-8 (validated reference palette, light mode).
SERIES_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]


def synthetic_frame(seed: int = 0) -> pd.DataFrame:
    """Made-up temperatures for pipeline testing only. Not weather data."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2015-05-01", "2025-09-30", freq="D")
    dates = dates[dates.month.isin(bt.SEASON_MONTHS)]
    doy = dates.dayofyear.to_numpy()
    rows = []
    for city, ref, local, bias, sd in (("SYN_A", "SYN_REF_A", "SYN_LOC_A", 1.0, 2.5),
                                       ("SYN_B", "SYN_REF_B", "SYN_LOC_B", -0.5, 3.5)):
        ref_t = 82 + 8 * np.sin((doy - 120) / 153 * np.pi) + rng.normal(0, 6, doy.size)
        loc_t = ref_t + bias + rng.normal(0, sd, doy.size)
        miss = rng.random(doy.size) < 0.01
        loc_t = np.where(miss, np.nan, loc_t)
        rows.append(pd.DataFrame({
            "date": dates.strftime("%Y-%m-%d"), "city": city, "local_station_id": local,
            "ref_station_id": ref, "local_tmax_f": np.round(loc_t), "ref_tmax_f": np.round(ref_t),
            "data_quality": np.where(miss, "SYNTHETIC_MISSING", "SYNTHETIC")}))
    return pd.concat(rows, ignore_index=True)


def plot_sweep(sweep: pd.DataFrame, out: Path, threshold: float, split: str, label: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    s = sweep[(sweep["threshold_f"] == threshold) & (sweep["split"] == split)]
    objs = ["risk_neutral", "mean_variance", "mean_cvar"]
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8), constrained_layout=True)
    pairs = list(s.groupby(bt.PAIR_KEYS).groups.keys())
    for ax, o in zip(axes, objs):
        so = s[s["objective"] == o]
        for i, pair in enumerate(pairs):
            g = so[(so[bt.PAIR_KEYS] == pd.Series(pair, index=bt.PAIR_KEYS)).all(axis=1)]
            if g.empty:
                continue
            ax.plot(g["loading"] * 100, g["delta_B_minus_A"], lw=2,
                    color=SERIES_COLORS[i % len(SERIES_COLORS)],
                    label=f"{pair[0]}: {pair[1]} vs {pair[2]}")
        ax.axhline(0, color="#52514e", lw=1)
        ax.set_title(o.replace("_", " "), fontsize=10, color="#0b0b0b")
        ax.set_xlabel("residual loading L (%)", color="#52514e")
        ax.grid(axis="y", color="#e5e4e0", lw=0.8)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        ax.tick_params(colors="#52514e")
    axes[0].set_ylabel("objective B minus A ($/day)\n< 0 means B preferred", color="#52514e")
    handles, labels = axes[0].get_legend_handles_labels()
    if handles:
        fig.legend(handles, labels, loc="lower center", ncol=min(4, len(labels)),
                   frameon=False, bbox_to_anchor=(0.5, -0.12), fontsize=8)
    fig.suptitle(f"{label}Residual loading sweep, k={threshold:g}°F, {split} split "
                 f"(premiums ASSUMED)", fontsize=11)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="#fcfcfb")
    plt.close(fig)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, default=DATA)
    ap.add_argument("--synthetic", action="store_true",
                    help="use made-up temperatures; writes only to results/synthetic/")
    ap.add_argument("--station-markup", type=float, default=bt.DEFAULT_STATION_MARKUP,
                    help="ASSUMED station premium markup over expected payout (default 0.20)")
    ap.add_argument("--notional", type=float, default=bt.DEFAULT_NOTIONAL)
    ap.add_argument("--thresholds", type=float, nargs="+", default=list(bt.DEFAULT_THRESHOLDS))
    ap.add_argument("--mv-a", type=float, default=1.0, help="mean-variance risk aversion (ASSUMED)")
    ap.add_argument("--cvar-gamma", type=float, default=0.25, help="CVaR weight (ASSUMED)")
    ap.add_argument("--cvar-alpha", type=float, default=0.95, help="CVaR level (ASSUMED)")
    ap.add_argument("--plot-threshold", type=float, default=90.0)
    args = ap.parse_args(argv)

    if args.synthetic:
        df = synthetic_frame()
        tables, figs, prefix, label = ROOT / "results/synthetic", ROOT / "results/synthetic", "SYNTHETIC_", "SYNTHETIC DEMO - "
        source = "synthetic_frame(seed=0) - made-up temperatures, NOT weather data"
    else:
        if not args.data.exists():
            print(f"ERROR: {args.data} not found.\n"
                  "The comparison needs real aligned station data from the Qasim workstream "
                  "(src/load_weather.py / scripts/pull_*.py).\n"
                  "No results were written. For a pipeline test only, run with --synthetic.",
                  file=sys.stderr)
            return 2
        df = pd.read_csv(args.data)
        tables, figs, prefix, label = ROOT / "results/tables", ROOT / "results/figures", "", ""
        source = str(args.data.relative_to(ROOT)) if args.data.is_relative_to(ROOT) else str(args.data)

    out = bt.run_backtest(df, thresholds=args.thresholds, notional=args.notional,
                          station_markup=args.station_markup, mv_a=args.mv_a,
                          cvar_gamma=args.cvar_gamma, cvar_alpha=args.cvar_alpha)
    tables.mkdir(parents=True, exist_ok=True)
    for name, t in out.items():
        t.to_csv(tables / f"{prefix}comparison_{name}.csv", index=False)
    fig_name = f"{prefix}loading_sweep.png"
    if not out["loading_sweep"].empty:
        plot_sweep(out["loading_sweep"], figs / fig_name, args.plot_threshold, "test", label)

    manifest = {
        "run_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "input": source, "synthetic": args.synthetic,
        "input_md5": (None if args.synthetic else
                      __import__("hashlib").md5(args.data.read_bytes()).hexdigest()),
        "station_payout_source": lr.STATION_PAYOUT_SOURCE,
        "station_markup_ASSUMED": args.station_markup, "notional": args.notional,
        "thresholds_f": args.thresholds, "train_years": bt.TRAIN_YEARS, "test_years": bt.TEST_YEARS,
        "objective_params_ASSUMED": {"mv_a": args.mv_a, "cvar_gamma": args.cvar_gamma,
                                     "cvar_alpha": args.cvar_alpha},
        "rows_in": int(len(df)),
        "rows_used": int(out["row_accounting"]["rows"].sum() - out["row_accounting"]["missing_rows"].sum()),
        "rows_missing_dropped": int(out["row_accounting"]["missing_rows"].sum()),
    }
    (tables / f"{prefix}run_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))
    print(f"Wrote tables to {tables} and figure to {figs / fig_name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
