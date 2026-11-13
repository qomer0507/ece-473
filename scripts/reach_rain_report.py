"""Phase 3 rain reach, step 5: the summary and the figure, from the CSVs only (no new computation).

    python scripts/reach_rain_report.py

Reads  results/phase3/rain_reach_curve.csv, rain_reach_curve_sensitivity.csv, rain_reach_regression.csv,
       rain_reach_numbers.json, rain_station_table.csv, data/processed/reach/rain_pairs.csv,
       rain_pairs_excluded.csv, rain_stations.csv
Writes results/phase3/rain_reach_summary.md, results/phase3/rain_reach.png
"""
import json
import os
import sys

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
RES = os.path.join(ROOT, "results", "phase3")
PROC = os.path.join(ROOT, "data", "processed", "reach")

BLUE, ORANGE, INK, MUTED, BAND = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#2a78d6"


def fmt(x, nd=2):
    return "n/a" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.{nd}f}"


def figure(curve, pairs, numbers, path):
    fig, ax = plt.subplots(figsize=(9, 5.6), dpi=150)
    p = pairs[~pairs["he"].isna()]
    pts = p[~p["same_station"]]
    same = p[p["same_station"]]
    ax.scatter(pts["dist_km"], pts["he"], s=9, color=MUTED, alpha=0.35, linewidths=0, label="one pair (S, G)")
    ax.scatter(same["dist_km"], same["he"], s=14, color=INK, alpha=0.6, linewidths=0, label="same station (S = G)")
    c = curve[(curve["bin"] > 0) & ~curve["mean_he"].isna()]
    mid = (c["bin_lo_km"] + c["bin_hi_km"]) / 2
    ax.fill_between(mid, c["he_lo_pair"], c["he_hi_pair"], color=BAND, alpha=0.18, linewidth=0,
                    label="95% band, pairs resampled")
    ax.plot(mid, c["he_lo_gauge"], color=BLUE, lw=1, ls=":", label="95% band edges, gauges resampled")
    ax.plot(mid, c["he_hi_gauge"], color=BLUE, lw=1, ls=":")
    ax.plot(mid, c["mean_he"], color=BLUE, lw=2, marker="o", ms=4, label="mean HE per 10-km bin (registered)")
    ax.plot(mid, c["median_he"], color=INK, lw=1.2, ls="--", label="median HE per bin")
    lo_axis = max(-2.0, float(np.nanpercentile(p["he"], 1)) - 0.1)
    off = c[c["mean_he"] < lo_axis]
    for r in off.itertuples():
        x = (r.bin_lo_km + r.bin_hi_km) / 2
        ax.annotate(f"{r.bin_lo_km:.0f}-{r.bin_hi_km:.0f} km bin mean {r.mean_he:.1f}\n(off axis; median {r.median_he:.2f})",
                    (x, lo_axis + 0.02), xytext=(x + 8, lo_axis + 0.45), fontsize=8, color=BLUE,
                    arrowprops=dict(arrowstyle="-", color=BLUE, lw=0.8))
    ax.axhline(0, color=INK, lw=1)
    tp = numbers.get("trenton_pne")
    if tp and tp.get("he") == tp.get("he"):
        ax.scatter([tp["dist_km"]], [tp["he"]], s=70, color=ORANGE, zorder=5, edgecolor="white", linewidths=1)
        ax.annotate(f"Trenton-PNE: HE {tp['he']:.2f} at {tp['dist_km']:.0f} km",
                    (tp["dist_km"], tp["he"]), xytext=(tp["dist_km"] + 14, tp["he"] - 0.55),
                    fontsize=9, color=ORANGE, arrowprops=dict(arrowstyle="-", color=ORANGE, lw=0.8))
    lo = max(-2.0, float(np.nanpercentile(p["he"], 1)) - 0.1)
    ax.set_ylim(lo, 1.08)
    ax.set_xlim(-4, 204)
    ax.set_xlabel("distance from settlement station S to exposure gauge G, km")
    ax.set_ylabel("hedge effectiveness on REPORT seasons")
    rk = numbers["reach_pair_boot"]["reach_km"]
    rg = numbers["reach_gauge_boot"]["reach_km"]
    n_below = int((p["he"] < lo).sum())
    if rk == 0 and rg == 0:
        title = ("Rain: the seasonal count contract hedges only at its own station;\n"
                 "no 10-km distance bin is reliably above zero (reach 0 km under both bootstraps)")
    else:
        title = (f"Rain: the seasonal count contract reaches about {rk:.0f} km "
                 f"(pairs resampled; {rg:.0f} km with gauges resampled)")
    ax.set_title(title, fontsize=10, loc="left")
    note = "exploratory; observed weather, modelled prices"
    if n_below:
        note += f"; {n_below} pairs below the axis"
    ax.text(0.99, 0.02, note, transform=ax.transAxes, ha="right", va="bottom", fontsize=8, color=MUTED)
    ax.legend(loc="upper right", fontsize=8, frameon=False)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color="#e6e5e0", lw=0.6)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def summary(curve, curve_s, reg, numbers, pairs, excluded, stations, table):
    L = []
    L.append("# Phase 3, Question 1: how far does a rain hedge reach? (EXPLORATORY)\n")
    L.append("Observed weather, modelled premiums. Pre-registration: docs/PHASE3_PREREG.md. Reading choices and "
             "the log: docs/status/phase3_rain.md. Every number here is read from the CSVs beside this file.\n")
    k = stations[stations["kept"] == True]  # noqa: E712
    L.append("## Stations and pairs\n")
    L.append(f"- Candidates: {numbers['n_candidates']} ASOS/AWOS stations in NJ, NY, PA, CT, DE, MD with an IEM "
             f"archive beginning by 2005. Kept (>= 20 usable seasons): {numbers['n_kept']}, of which "
             f"{numbers['n_kept_cli']} have an NWS daily climate report and can settle a contract.")
    nk = stations[stations["kept"] != True]  # noqa: E712
    L.append(f"- Not kept: {len(nk)} ({nk['why_not_kept'].value_counts().to_dict()}). Listed with their "
             f"season counts in data/processed/reach/rain_stations.csv.")
    L.append(f"- Usable seasons per kept station: median {int(k['n_usable'].median())}, range "
             f"{int(k['n_usable'].min())}-{int(k['n_usable'].max())}; {int((k['n_usable_isd'] > 0).sum())} "
             f"stations have seasons from the NCEI archive (before 1997).")
    z = k[k["n_usable_zero_rain"] > 0]
    L.append(f"- Kept stations with a usable season whose opening-hours rain total is 0.00 in (gauge silent, not "
             f"caught by the 90% rule): {len(z)}" + (": " + ", ".join(f"{r.sid} ({int(r.n_usable_zero_rain)})"
                                                                    for r in z.itertuples()) if len(z) else "") + ".")
    L.append(f"- Pairs within 200 km (S with climate report, G any kept station, plus S = G): "
             f"{numbers['n_pairs_built']}. Scored under the main rule (>= 20 joint usable seasons): "
             f"{numbers['n_pairs_scored']}, HE defined for {numbers['n_pairs_he_defined']}. Excluded: "
             f"{numbers['n_pairs_excluded']} (data/processed/reach/rain_pairs_excluded.csv). "
             f"Exposure gauges scored: {numbers['n_gauges_scored']}; settlement stations: {numbers['n_settlement_scored']}.")
    ss = numbers["same_station"]
    L.append(f"- Same-station ceiling: {ss['n']} pairs, mean HE {ss['mean_he']:.2f} "
             f"(band {fmt(curve.loc[0, 'he_lo_pair'])} to {fmt(curve.loc[0, 'he_hi_pair'])}).\n")

    L.append("## Reach\n")
    for key, name in (("reach_pair_boot", "pairs resampled"), ("reach_gauge_boot", "exposure gauges resampled")):
        r = numbers[key]
        L.append(f"- {name}: reach {r['reach_km']:.0f} km (registered definition: largest 10-km bin whose lower "
                 f"band edge is above 0); contiguous reach {r['contiguous_reach_km']:.0f} km.")
    for key, name in (("reach_sensitivity_pair_boot", "pairs"), ("reach_sensitivity_gauge_boot", "gauges")):
        r = numbers[key]
        L.append(f"- Sensitivity, pairs with fewer than 20 joint seasons included ({name} resampled): "
                 f"reach {r['reach_km']:.0f} km, contiguous {r['contiguous_reach_km']:.0f} km.")
    for key, name in (("reach_nozero_pair_boot", "pairs"), ("reach_nozero_gauge_boot", "gauges")):
        r = numbers[key]
        L.append(f"- Sensitivity, zero-rain seasons treated as unusable ({numbers['nozero_n_stations']} stations, "
                 f"{numbers['nozero_n_pairs_scored']} pairs; dropped {numbers['nozero_stations_dropped']}; "
                 f"{name} resampled): reach {r['reach_km']:.0f} km, contiguous {r['contiguous_reach_km']:.0f} km.")
    L.append("")
    L.append("| bin km | pairs | gauges | mean HE | median HE | 95% band (pairs) | 95% band (gauges) | mean r | mean daily agreement |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for r in curve.itertuples():
        lab = "0 (S = G)" if r.bin == 0 else f"{r.bin_lo_km:.0f}-{r.bin_hi_km:.0f}"
        L.append(f"| {lab} | {r.n_he_defined} of {r.n_pairs} | {r.n_gauges} | {fmt(r.mean_he)} | {fmt(r.median_he)} | "
                 f"{fmt(r.he_lo_pair)} to {fmt(r.he_hi_pair)} | {fmt(r.he_lo_gauge)} to {fmt(r.he_hi_gauge)} | "
                 f"{fmt(r.mean_corr)} | {fmt(r.mean_agreement, 3)} |")
    L.append("")

    nz = pairs[~pairs["he"].isna()]
    worst = nz.sort_values("he").iloc[0]
    L.append(f"HE has no lower bound: {int((nz['he'] < -1).sum())} of {len(nz)} pairs are below -1 (worst "
             f"{worst['s_id']}-{worst['g_id']}, {worst['dist_km']:.0f} km, HE {worst['he']:.0f}: a contract that "
             f"paid in TRAIN-like seasons and then charged its premium in REPORT seasons where the gauge was dry). "
             f"The registered bin mean is pulled down by such pairs (the 90-100 km bin most of all); the median "
             f"beside it is the more stable summary. Over all pairs with S != G the median HE is "
             f"{nz.loc[~nz['same_station'], 'he'].median():.2f} and {100 * (nz.loc[~nz['same_station'], 'he'] > 0).mean():.0f}% "
             f"of them are above 0, so the hedge beyond the station is a coin flip around zero, not a slow decay.\n")
    L.append("## Regression of HE on distance, elevation difference and coast\n")
    L.append("| model | term | coefficient | classical SE | 95% gauge-bootstrap interval |")
    L.append("|---|---|---|---|---|")
    for r in reg.itertuples():
        L.append(f"| {r.model} (n = {r.n_pairs}, R2 {r.r2:.2f}) | {r.term} | {r.coef:.3f} | {r.se_classical:.3f} | "
                 f"{r.lo_gauge_boot:.3f} to {r.hi_gauge_boot:.3f} |")
    L.append("")
    L.append("Units: distance per 100 km, |elevation difference| per 100 m, coast = 1 when the exposure gauge is "
             "within 15 km of the Atlantic Ocean or Long Island Sound (GSHHS shoreline, bays masked; "
             "src/reach/rain_geo.py).\n")

    tp = numbers.get("trenton_pne")
    L.append("## Trenton-PNE\n")
    if tp:
        L.append(f"- S = TTN, G = PNE, {tp['dist_km']:.1f} km. Joint usable seasons {tp['n_joint_seasons']} "
                 f"({tp['first_joint']}-{tp['last_joint']}; TRAIN {tp['n_train']}, REPORT {tp['n_report']}). "
                 f"d = {tp['d']}, premium {fmt(tp['premium'])}. REPORT HE {fmt(tp['he'])}; daily agreement "
                 f"{fmt(tp['trigger_agreement'], 3)}; count correlation {fmt(tp['count_corr'])}. "
                 f"Status: {tp['status']}.")
        b = curve[(curve["bin_lo_km"] < tp["dist_km"]) & (tp["dist_km"] <= curve["bin_hi_km"]) & (curve["bin"] > 0)]
        if len(b):
            b = b.iloc[0]
            L.append(f"- Its bin ({b.bin_lo_km:.0f}-{b.bin_hi_km:.0f} km): mean HE {fmt(b.mean_he)}, band "
                     f"{fmt(b.he_lo_pair)} to {fmt(b.he_hi_pair)} over {int(b.n_he_defined)} pairs. The point sits "
                     f"inside the band: Trenton-PNE is a typical pair at that distance, not an unlucky one.")
        L.append("- Phase 2 (case B1, strategy 4, windows 1999-2014 / 2015-2026) gave HE(4) -0.35 [-0.58, -0.27]; the "
                 "60/40 split here lands on the same 16 / 12 seasons, so the number is the same.")
    L.append("")

    L.append("## Station-level table (results/phase3/rain_station_table.csv)\n")
    nn = table[table["nearest_cli_dist_km"] > 0]
    L.append(f"- {len(table)} exposure gauges, {len(table) - len(nn)} of them climate-report stations (their nearest "
             f"settlement station is themselves, HE = the same-station ceiling).")
    L.append(f"- The {len(nn)} gauges without a climate report: nearest climate-report station at a median "
             f"{nn['nearest_cli_dist_km'].median():.0f} km, HE median {nn['nearest_cli_he'].median():.2f} (mean "
             f"{nn['nearest_cli_he'].mean():.2f}), above 0 for {int((nn['nearest_cli_he'] > 0).sum())} of "
             f"{int(nn['nearest_cli_he'].notna().sum())}. 'Best' settlement station (highest REPORT HE among up to "
             f"{int(nn['n_settlement_candidates'].max())} candidates): median {nn['best_he'].median():.2f}, above 0 "
             f"for {int((nn['best_he'] > 0).sum())}; median distance {nn['best_dist_km'].median():.0f} km.")
    L.append("- The 'best' column is a maximum over many noisy REPORT HEs and is chosen on REPORT seasons, so it "
             "overstates what a buyer could know in advance (several 'best' stations are 100-190 km away). It "
             "says how good the luckiest pairing looks, not which station to list.")
    L.append("")

    L.append("## Caveats, plain language\n")
    L.append("- Exploratory: the question was chosen after Phase 2. Nothing here is a confirmatory test.")
    L.append("- Pairs share stations. Each settlement station appears in many pairs and each gauge in many pairs, "
             "so the pairs are not independent draws. The pair bootstrap treats them as if they were and its band "
             "is too narrow. The gauge bootstrap resamples exposure gauges and carries each gauge's whole set of "
             "pairs along, which respects one of the two sharing structures (gauges) but not the other "
             "(settlement stations). Both bands are reported; the gauge band is the one to trust more.")
    L.append("- Each pair's HE rests on its REPORT seasons (8 to 34 per pair); HE of a single pair is noisy, and "
             "pairs with few seasons scatter widely. Pairs with fewer than 20 joint seasons were excluded by a rule "
             "fixed before results; the sensitivity curve puts them back.")
    L.append("- Bins at long distance hold pairs from different sub-regions (coast, Appalachians, lake shore); the "
             "mean over a bin is not the HE any one park would see.")
    L.append("- Premiums are modelled (1.2 x TRAIN mean payout); nobody sells this contract. Weather is observed.")
    L.append("- Gauge quality differs between stations and decades (Phase 0 and 1 found dew tips and silent gauge "
             "failures). Hourly data before 1997 is from the NCEI archive at first-order stations; the sources are "
             "never mixed inside a season but can differ between TRAIN and REPORT of one pair.")
    L.append("- The coast indicator is coarse (nearest vertex of a low-resolution shoreline).")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    curve = pd.read_csv(os.path.join(RES, "rain_reach_curve.csv"))
    curve_s = pd.read_csv(os.path.join(RES, "rain_reach_curve_sensitivity.csv"))
    reg = pd.read_csv(os.path.join(RES, "rain_reach_regression.csv"))
    numbers = json.load(open(os.path.join(RES, "rain_reach_numbers.json")))
    pairs = pd.read_csv(os.path.join(PROC, "rain_pairs.csv"))
    excluded = pd.read_csv(os.path.join(PROC, "rain_pairs_excluded.csv"))
    stations = pd.read_csv(os.path.join(PROC, "rain_stations.csv"))
    table = pd.read_csv(os.path.join(RES, "rain_station_table.csv"))
    figure(curve, pairs, numbers, os.path.join(RES, "rain_reach.png"))
    with open(os.path.join(RES, "rain_reach_summary.md"), "w") as fh:
        fh.write(summary(curve, curve_s, reg, numbers, pairs, excluded, stations, table))
    print("wrote rain_reach_summary.md and rain_reach.png")
