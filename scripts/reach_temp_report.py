"""Figures and summary for the temperature reach (Phase 3, Question 1). Reads CSVs only; no new computation.

    python scripts/reach_temp_report.py

Reads   results/phase3/temp_reach_curve*.csv, temp_reach_numbers*.csv, temp_regression*.csv, temp_listing.csv
        data/processed/reach/temp_pairs*.csv, data/processed/panel/outlines.csv
Writes  results/phase3/temp_reach.png           registered mean curve with both bands; labelled median and sensitivity
        results/phase3/temp_listing_map.png     exposure gauges coloured by HE from their nearest CLI station
        results/phase3/temp_reach_summary.md
EXPLORATORY. Observed weather, modelled premiums.
"""
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "results", "phase3")
REACH = os.path.join(ROOT, "data", "processed", "reach")

BLUE, ORANGE, GRAY, INK, MUTED = "#2a78d6", "#eb6834", "#9a9a94", "#0b0b0b", "#52514e"
NOTE = "Exploratory. Observed weather, modelled prices."


def xpos(curve: pd.DataFrame) -> np.ndarray:
    """Plot position of a bin: 0 for the same-station bin, the bin midpoint otherwise."""
    return np.where(curve["bin"] == 0, 0.0, (curve["lo_km"] + curve["hi_km"]) / 2)


def style(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color="#e6e6e2", lw=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors=MUTED, labelsize=9)


def reach_text(numbers: pd.DataFrame) -> str:
    parts = []
    for r in numbers.itertuples():
        v = "none" if np.isnan(r.reach_km) else f"{r.reach_km:.0f} km"
        parts.append(f"{v} ({r.scheme} bootstrap)")
    return "reach: " + ", ".join(parts)


def curve_figure(curve, numbers, sens, sens_numbers, path):
    fig, axes = plt.subplots(2, 1, figsize=(9, 8.2), sharex=True, gridspec_kw={"height_ratios": [1.15, 1]})
    for ax, c, num, title, ylim in (
        (axes[0], curve, numbers, "Registered rule: d from {0..8}", (-26, 3)),
        (axes[1], sens, sens_numbers, "Labelled sensitivity, NOT registered: d from {0..40}", (-13, 2)),
    ):
        x = xpos(c)
        ax.axhline(0, color=INK, lw=1)
        ax.fill_between(x, c["lo_pair"], c["hi_pair"], color=BLUE, alpha=0.16, lw=0, label="95% band, pairs resampled")
        ax.plot(x, c["lo_gauge"], color=BLUE, lw=1, ls=(0, (3, 2)), label="95% band, gauges resampled")
        ax.plot(x, c["hi_gauge"], color=BLUE, lw=1, ls=(0, (3, 2)))
        ax.plot(x, c["mean_he"], color=BLUE, lw=2, marker="o", ms=4, label="bin mean HE (registered statistic)")
        ax.plot(x, c["median_he"], color=GRAY, lw=1.5, marker="s", ms=3.5, label="bin median HE (labelled extra)")
        clipped = c[c["lo_pair"] < ylim[0]]
        for _, r in clipped.iterrows():
            ax.annotate(f"{r['lo_pair']:.0f}", (xpos(pd.DataFrame([r]))[0], ylim[0] + 0.6), ha="center",
                        fontsize=7, color=MUTED)
        ax.set_ylim(*ylim)
        ax.set_ylabel("hedge effectiveness (REPORT)", color=MUTED, fontsize=9)
        ax.set_title(f"{title}  |  {reach_text(num)}", fontsize=10, loc="left", color=INK)
        style(ax)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", fontsize=8, frameon=False, ncol=2, bbox_to_anchor=(0.5, 0.035))
    axes[1].set_xlabel("distance from exposure gauge to settlement station, km (10 km bins; 0 = same station)",
                       color=MUTED, fontsize=9)
    axes[1].set_xticks(range(0, 201, 20))
    fig.suptitle("Temperature: the seasonal hot-day contract does not reach past zero at any distance,\n"
                 "not even at the settlement station itself", fontsize=12, x=0.01, ha="left", color=INK)
    fig.text(0.01, 0.005, f"{NOTE} 992 pairs, 84 exposure gauges, 40 settlement stations, TRAIN 2015-2020, "
             "REPORT 2021-2025.\nBand edges below the axis are printed as numbers.", fontsize=7.5, color=MUTED)
    fig.tight_layout(rect=(0, 0.075, 1, 0.94))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def listing_map(listing, outlines, path):
    fig, ax = plt.subplots(figsize=(9, 7.6))
    for seg, g in outlines.groupby("seg"):
        ax.plot(g["lon"], g["lat"], color="#c9c9c3", lw=0.7, zorder=1)
    cmap = LinearSegmentedColormap.from_list("div", [ORANGE, "#d9d9d4", BLUE])
    norm = TwoSlopeNorm(vmin=-1.0, vcenter=0.0, vmax=1.0)
    ok = listing[listing["he"].notna()]
    nan = listing[listing["he"].isna()]
    sc = ax.scatter(ok["lon"], ok["lat"], c=ok["he"].clip(-1, 1), cmap=cmap, norm=norm, s=70, edgecolor="white",
                    lw=0.8, zorder=3)
    ax.scatter(nan["lon"], nan["lat"], facecolor="white", edgecolor=INK, s=70, lw=0.8, zorder=3, label="HE undefined")
    cl = listing[listing["has_cli"]]
    ax.scatter(cl["lon"], cl["lat"], marker="o", facecolor="none", edgecolor=INK, s=170, lw=1.1, zorder=4,
               label="has a climate report (settlement station)")
    cb = fig.colorbar(sc, ax=ax, shrink=0.6, pad=0.02)
    cb.set_label("HE from the nearest settlement station (clipped to [-1, 1])", fontsize=9, color=MUTED)
    cb.ax.tick_params(labelsize=8, colors=MUTED)
    ax.set_xlim(listing["lon"].min() - 0.8, listing["lon"].max() + 0.8)
    ax.set_ylim(listing["lat"].min() - 0.5, listing["lat"].max() + 0.5)
    ax.set_aspect(1 / np.cos(np.radians(41)))
    ax.set_xlabel("longitude", color=MUTED, fontsize=9)
    ax.set_ylabel("latitude", color=MUTED, fontsize=9)
    ax.legend(loc="lower right", fontsize=8, frameon=False)
    style(ax)
    ax.grid(False)
    n_pos = int((ok["he"] > 0).sum())
    ax.set_title("Temperature hedge from the nearest settlement station: blue helps, orange hurts\n"
                 f"({n_pos} of {len(listing)} exposure gauges have HE above 0; registered d rule; REPORT 2021-2025)",
                 fontsize=11, loc="left", color=INK)
    fig.text(0.01, 0.01, NOTE + " Circle rings mark the 40 stations with a climate report (their own HE is shown).",
             fontsize=7.5, color=MUTED)
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fmt(x, nd=2):
    return "undefined" if x != x else f"{x:.{nd}f}"


def summary(curve, numbers, reg, sens, sens_numbers, sens_reg, pairs, spairs, listing, info, path):
    L = []
    L.append("# Temperature reach (Phase 3, Question 1) - EXPLORATORY\n")
    L.append("Observed weather (TMAX panel, 84 exposure stations, 2015-2025). Modelled premiums (1.2 x TRAIN mean payout). "
             "Rules: docs/PHASE3_PREREG.md and the reading choices in docs/status/phase3_temp.md.\n")
    L.append("## Pairs")
    sc = info["status_counts"]
    L.append(f"- {info['n_pairs']} ordered pairs (settlement station S with a climate report, exposure gauge G, "
             f"<= 200 km), including the 40 same-station pairs. 40 settlement stations, 84 gauges.")
    L.append(f"- Every pair has 11 usable seasons: TRAIN 2015-2020 (6), REPORT 2021-2025 (5). 0 pairs fail the usable rule.")
    L.append(f"- HE defined for {sc.get('ok', 0)} pairs; undefined for {sc.get('he_undefined', 0)} "
             "(no REPORT season above the TRAIN reference; listed in data/processed/reach/temp_pairs.csv with status he_undefined).")
    dd = pairs["d"].value_counts().sort_index()
    L.append(f"- TRAIN-chosen deductible d: {', '.join(f'd={int(k)}: {v}' for k, v in dd.items())}. "
             f"d = 8 is the grid maximum and is chosen for {int(dd.get(8, 0))} of {len(pairs)} pairs.")
    L.append(f"- HE over pairs: median {pairs['he'].median():.2f}, mean {pairs['he'].mean():.2f}, min {pairs['he'].min():.0f}, "
             f"max {pairs['he'].max():.2f}; {int((pairs['he'] > 0).sum())} pairs above 0. "
             f"Same-station pairs: median {pairs[pairs.same_station]['he'].median():.2f}, "
             f"{int((pairs[pairs.same_station]['he'] > 0).sum())} of 40 above 0.")
    L.append(f"- Daily trigger agreement: median {pairs['agreement'].median():.3f} over pairs; same station 1.0. "
             f"Seasonal count correlation: median {pairs['count_corr'].median():.2f}.\n")

    L.append("## Reach (registered definition: the largest 10 km bin whose lower 95% band edge is above 0)")
    for r in numbers.itertuples():
        L.append(f"- {r.scheme} bootstrap: reach = {'NONE' if np.isnan(r.reach_km) else f'{r.reach_km:.0f} km'}; "
                 f"{r.n_bins_above} of {r.n_bins_with_band} bins have a lower edge above 0.")
    c0 = curve.iloc[0]
    L.append(f"- Same-station bin: mean HE {c0['mean_he']:.2f}, median {c0['median_he']:.2f}, "
             f"pair band [{c0['lo_pair']:.2f}, {c0['hi_pair']:.2f}], gauge band [{c0['lo_gauge']:.2f}, {c0['hi_gauge']:.2f}].")
    L.append("- So the temperature reach cannot be resolved: no bin, including the settlement station itself, "
             "has a lower band edge above zero. In plain words, the registered contract did not hedge the 2021-2025 "
             "hot-day counts even where the exposure sits on the settlement station.\n")
    L.append("### Curve table (registered)")
    L.append("| bin | pairs with HE | mean HE | median HE | pair band | gauge band |")
    L.append("|---|---|---|---|---|---|")
    for r in curve.itertuples():
        L.append(f"| {r.label} | {r.n_he} | {fmt(r.mean_he)} | {fmt(r.median_he)} | [{fmt(r.lo_pair)}, {fmt(r.hi_pair)}] "
                 f"| [{fmt(r.lo_gauge)}, {fmt(r.hi_gauge)}] |")
    L.append("")
    L.append("## Why the same-station hedge fails (read from the pair table, not a new rule)")
    L.append("- For a same-station pair the net cost is C - max(C - d, 0) + premium. With d = 8 and TRAIN mean counts of "
             "20-40 hot days, the contract pays nearly every season, the premium is 20-40 loss-days, and net cost sits at "
             "a constant 8 + premium = reference + 0.2 x (reference - 8), which is ABOVE the reference every season. "
             "The hedged semi-variance is then the square of the loading; it beats the unhedged semi-variance only when "
             "REPORT seasons are far hotter than TRAIN. 2021-2025 was not far hotter than 2015-2020 at most stations.")
    L.append("- HE is unbounded below. A pair whose REPORT seasons barely exceed the reference has a tiny unhedged "
             f"semi-variance and an HE like {pairs['he'].min():.0f}. Bin means are dragged by such pairs; the medians are "
             "shown as a labelled extra and are also at or below zero beyond the same-station bin.")
    L.append("- The d grid {0..8} was written for rain counts (Phase 2) and carried into the temperature rule by the "
             "pre-registration ('same d and premium rule'). It is run as registered.\n")

    L.append("## Labelled sensitivity (NOT registered): d grid widened to {0..40}")
    s0 = sens.iloc[0]
    for r in sens_numbers.itertuples():
        L.append(f"- {r.scheme} bootstrap: reach = {'NONE' if np.isnan(r.reach_km) else f'{r.reach_km:.0f} km'}; "
                 f"{r.n_bins_above} bins above 0.")
    L.append(f"- Same-station bin: mean {s0['mean_he']:.2f}, median {s0['median_he']:.2f}, pair band "
             f"[{s0['lo_pair']:.2f}, {s0['hi_pair']:.2f}], gauge band [{s0['lo_gauge']:.2f}, {s0['hi_gauge']:.2f}]. "
             f"{int((spairs[spairs.same_station]['he'] > 0).sum())} of 40 same-station pairs above 0; "
             f"d chosen: median {spairs['d'].median():.0f}, {int((spairs['d'] == 40).sum())} pairs at the new grid maximum.")
    L.append(f"- Over all pairs: median HE {spairs['he'].median():.2f}, {int((spairs['he'] > 0).sum())} of "
             f"{int(spairs['he'].notna().sum())} above 0. The wider grid lifts the same-station bin but no bin's band "
             "clears zero. Reach is unresolved under this reading too.\n")

    L.append("## Regression of HE on distance, elevation difference and coast (registered)")
    L.append("OLS, pairs with defined HE. Classical SE treats pairs as independent, which is false (pairs share gauges); "
             "read the gauge-bootstrap interval. coast = 1 if the exposure gauge is within 25 km of the shoreline.")
    for sample in ("all_pairs", "excluding_same_station"):
        t = reg[reg["sample"] == sample]
        L.append(f"\n{sample} (n = {int(t['n_pairs'].iloc[0])}, {int(t['n_gauges'].iloc[0])} gauges, R2 = {t['r2'].iloc[0]:.3f})\n")
        L.append("| term | coef | classical SE | gauge 95% |")
        L.append("|---|---|---|---|")
        for r in t.itertuples():
            L.append(f"| {r.term} | {r.coef:.3f} | {r.se_classical:.3f} | [{r.lo_gauge:.3f}, {r.hi_gauge:.3f}] |")
    t = reg[reg["sample"] == "all_pairs"].set_index("term")
    L.append(f"\n- Distance: {t.loc['dist_100km', 'coef']:.2f} HE per 100 km, gauge interval "
             f"[{t.loc['dist_100km', 'lo_gauge']:.2f}, {t.loc['dist_100km', 'hi_gauge']:.2f}]: spans zero. Elevation difference: "
             f"{t.loc['abs_elev_diff_100m', 'coef']:.2f} per 100 m [{t.loc['abs_elev_diff_100m', 'lo_gauge']:.2f}, "
             f"{t.loc['abs_elev_diff_100m', 'hi_gauge']:.2f}]: spans zero. Coast: {t.loc['coast', 'coef']:.2f} "
             f"[{t.loc['coast', 'lo_gauge']:.2f}, {t.loc['coast', 'hi_gauge']:.2f}]: below zero under the gauge bootstrap. "
             "R2 is 0.04; the regression explains almost nothing of HE because HE's spread is dominated by its lower tail.")
    ts = sens_reg[sens_reg["sample"] == "all_pairs"].set_index("term")
    L.append(f"- Sensitivity grid: distance {ts.loc['dist_100km', 'coef']:.2f} [{ts.loc['dist_100km', 'lo_gauge']:.2f}, "
             f"{ts.loc['dist_100km', 'hi_gauge']:.2f}], elevation {ts.loc['abs_elev_diff_100m', 'coef']:.2f} "
             f"[{ts.loc['abs_elev_diff_100m', 'lo_gauge']:.2f}, {ts.loc['abs_elev_diff_100m', 'hi_gauge']:.2f}], coast "
             f"{ts.loc['coast', 'coef']:.2f} [{ts.loc['coast', 'lo_gauge']:.2f}, {ts.loc['coast', 'hi_gauge']:.2f}]. "
             "The coast effect does not survive the wider grid.\n")

    L.append("## Listing map (results/phase3/temp_listing_map.png)")
    ok = listing[listing["he"].notna()]
    L.append(f"- Each exposure gauge coloured by the HE of the pair (nearest settlement station, gauge). "
             f"{int((ok['he'] > 0).sum())} of {len(listing)} gauges above 0; {int(listing['he'].isna().sum())} undefined. "
             f"Nearest-station distance: median {listing['dist_km'].median():.0f} km, max {listing['dist_km'].max():.0f} km.")
    by_state = listing.groupby("state")["he"].agg(["median", lambda x: (x > 0).mean(), "size"])
    by_state.columns = ["median_he", "share_above_0", "n"]
    L.append("- By state: " + "; ".join(f"{s}: median HE {r.median_he:.2f}, {r.share_above_0:.0%} above 0 (n={int(r.n)})"
                                        for s, r in by_state.iterrows()) + ".")
    L.append("- Poorly served areas: Maryland and the Delmarva shore (0 of 8 above 0), coastal Connecticut (1 of 8), "
             "and the hot corridor of south-eastern Pennsylvania and central New Jersey show orange; upstate New York and "
             "the northern tier show blue, but there the counts are small (often d = 0 on a station with one or two hot "
             "days a season), so a blue dot there says little about a hedge anyone would buy.")
    L.append("")
    L.append("## Caveats")
    L.append("- Five REPORT seasons per pair. HE on five seasons is a rough number; the bands reflect pair and gauge "
             "sampling, not season sampling.")
    L.append("- Every pair shares the same 11 seasons, so the bins are not independent of one another: one hot or mild "
             "summer moves the whole curve. The pre-registered bootstrap resamples pairs (and, here, gauges), not seasons.")
    L.append("- The gauge bootstrap and the pair bootstrap give almost the same bands, because the dominant spread is "
             "between pairs within the same bin, not between gauges.")
    L.append("- 41 pairs with undefined HE are left out of the curve; they are mostly far pairs where the gauge's "
             "REPORT counts never exceeded its TRAIN mean.")
    L.append("- Coast indicator uses a low-resolution shoreline and ignores the Great Lakes (Phase 1).")
    L.append("- Teterboro 2023-2025 is suspect (docs/status/qasim.md); it is in the panel as SPEC says.")
    L.append("- Nothing was dropped after seeing results. The d-grid sensitivity and the median curve were added after "
             "seeing the registered result and are labelled as such everywhere.")
    with open(path, "w") as f:
        f.write("\n".join(L) + "\n")


def main() -> None:
    curve = pd.read_csv(os.path.join(OUT, "temp_reach_curve.csv"))
    numbers = pd.read_csv(os.path.join(OUT, "temp_reach_numbers.csv"))
    reg = pd.read_csv(os.path.join(OUT, "temp_regression.csv"))
    sens = pd.read_csv(os.path.join(OUT, "temp_reach_curve_sens_dgrid40.csv"))
    sens_numbers = pd.read_csv(os.path.join(OUT, "temp_reach_numbers_sens_dgrid40.csv"))
    sens_reg = pd.read_csv(os.path.join(OUT, "temp_regression_sens_dgrid40.csv"))
    pairs = pd.read_csv(os.path.join(REACH, "temp_pairs.csv"))
    spairs = pd.read_csv(os.path.join(REACH, "temp_pairs_sens_dgrid40.csv"))
    listing = pd.read_csv(os.path.join(OUT, "temp_listing.csv"))
    outlines = pd.read_csv(os.path.join(ROOT, "data", "processed", "panel", "outlines.csv"))
    with open(os.path.join(OUT, "temp_run_info.json")) as f:
        info = json.load(f)
    curve_figure(curve, numbers, sens, sens_numbers, os.path.join(OUT, "temp_reach.png"))
    listing_map(listing, outlines, os.path.join(OUT, "temp_listing_map.png"))
    summary(curve, numbers, reg, sens, sens_numbers, sens_reg, pairs, spairs, listing, info,
            os.path.join(OUT, "temp_reach_summary.md"))
    print("written: temp_reach.png, temp_listing_map.png, temp_reach_summary.md")


if __name__ == "__main__":
    main()
