"""Combined rain and temperature reach curves (Phase 3, Question 1). Reads CSVs only; no new computation.

    python scripts/reach_combined.py

Reads   data/processed/reach/rain_pairs.csv, results/phase3/rain_reach_curve.csv      (rain workstream)
        data/processed/reach/temp_pairs.csv, results/phase3/temp_reach_curve.csv      (this workstream)
Writes  results/phase3/combined_reach.png
        results/phase3/combined_summary.md
If the rain files are missing the script writes temperature-only outputs that say so, and runs fully once they
exist. Reach is recomputed from each curve with the registered definition (largest 10 km bin whose lower 95%
band edge is above 0), so both hazards are judged by one rule. Column names of the two curve files differ a
little; `normalise` maps both to one layout. EXPLORATORY. Observed weather, modelled prices.
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from src.reach_temp.curve import reach_km  # noqa: E402

OUT = os.path.join(ROOT, "results", "phase3")
REACH = os.path.join(ROOT, "data", "processed", "reach")
BLUE, ORANGE, INK, MUTED = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e"
NOTE = "exploratory; observed weather, modelled prices"

ALIASES = {"lo_km": ("lo_km", "bin_lo_km"), "hi_km": ("hi_km", "bin_hi_km"), "n_he": ("n_he", "n_he_defined"),
           "lo_pair": ("lo_pair", "he_lo_pair"), "hi_pair": ("hi_pair", "he_hi_pair"),
           "lo_gauge": ("lo_gauge", "he_lo_gauge"), "hi_gauge": ("hi_gauge", "he_hi_gauge"),
           "mean_he": ("mean_he",), "median_he": ("median_he",), "n_pairs": ("n_pairs",), "bin": ("bin",)}


def normalise(curve: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame()
    for k, names in ALIASES.items():
        hit = [n for n in names if n in curve.columns]
        if not hit:
            if k == "median_he":
                out[k] = np.nan
                continue
            raise KeyError(f"curve file has none of {names}")
        out[k] = curve[hit[0]].to_numpy()
    return out.sort_values("bin").reset_index(drop=True)


def load(hazard: str):
    pairs_path = os.path.join(REACH, f"{hazard}_pairs.csv")
    curve_path = os.path.join(OUT, f"{hazard}_reach_curve.csv")
    if not (os.path.exists(pairs_path) and os.path.exists(curve_path)):
        return None, None
    return pd.read_csv(pairs_path), normalise(pd.read_csv(curve_path))


def xpos(c: pd.DataFrame) -> np.ndarray:
    return np.where(c["bin"] == 0, 0.0, (c["lo_km"] + c["hi_km"]) / 2)


def reach_str(r: dict) -> str:
    return "none" if np.isnan(r["reach_km"]) else f"{r['reach_km']:.0f} km"


def reaches(curve: pd.DataFrame) -> dict:
    return {s: reach_km(curve, f"lo_{s}") for s in ("pair", "gauge")}


def verdict(rain_r, temp_r) -> tuple[str, str]:
    """(status, sentence) for the pre-registered hypothesis: rain reach shorter than temperature reach."""
    if rain_r is None:
        return "unresolved", "The rain curve is not available yet, so the hypothesis cannot be tested."
    rr = rain_r["pair"]["reach_km"]
    tr = temp_r["pair"]["reach_km"]
    rg = rain_r["gauge"]["reach_km"]
    tg = temp_r["gauge"]["reach_km"]
    both_none = np.isnan(rr) and np.isnan(tr)
    if both_none:
        return "unresolved", ("Neither hazard has a bin whose lower band edge is above zero, so neither reach is "
                              "resolved and the hypothesis cannot be tested with these pairs.")
    rr0, tr0 = (0.0 if np.isnan(rr) else rr), (0.0 if np.isnan(tr) else tr)
    rg0, tg0 = (0.0 if np.isnan(rg) else rg), (0.0 if np.isnan(tg) else tg)
    if rr0 < tr0 and rg0 < tg0:
        return "supported", "Rain reach is shorter than temperature reach under both bootstrap schemes."
    if rr0 > tr0 and rg0 > tg0:
        return "not supported", "Rain reach is longer than temperature reach under both bootstrap schemes."
    if rr0 == tr0 and rg0 == tg0:
        return "not supported", "The two reaches are equal."
    return "unresolved", "The two bootstrap schemes disagree on the order of the reaches."


def separate(rain_c, temp_c) -> dict:
    """Do the curves separate? A bin separates when one hazard's pair band lies wholly above the other's."""
    m = rain_c.merge(temp_c.drop(columns=["lo_km", "hi_km"]), on="bin", suffixes=("_rain", "_temp"))
    rain_above = (m["lo_pair_rain"] > m["hi_pair_temp"])
    temp_above = (m["lo_pair_temp"] > m["hi_pair_rain"])
    return {"n_bins_compared": int((m["lo_pair_rain"].notna() & m["lo_pair_temp"].notna()).sum()),
            "n_rain_above": int(rain_above.sum()), "n_temp_above": int(temp_above.sum()),
            "rain_above_bins": m.loc[rain_above, "hi_km"].astype(int).tolist(),
            "temp_above_bins": m.loc[temp_above, "hi_km"].astype(int).tolist()}


def figure(rain_c, temp_c, rain_r, temp_r, rain_pairs, temp_pairs, path, status):
    ymin, ymax = -3.0, 1.1
    fig, ax = plt.subplots(figsize=(10, 6.6))
    ax.axhline(0, color=INK, lw=1)
    series = [("temperature", temp_c, temp_r, BLUE, temp_pairs)]
    if rain_c is not None:
        series.insert(0, ("rain", rain_c, rain_r, ORANGE, rain_pairs))
    clip = lambda v: np.clip(np.asarray(v, dtype=float), ymin, ymax)  # noqa: E731
    for name, c, r, col, pr in series:
        x = xpos(c)
        ax.fill_between(x, clip(c["lo_pair"]), clip(c["hi_pair"]), color=col, alpha=0.15, lw=0)
        ax.plot(x, clip(c["lo_gauge"]), color=col, lw=0.9, ls=(0, (3, 2)))
        ax.plot(x, clip(c["hi_gauge"]), color=col, lw=0.9, ls=(0, (3, 2)))
        n = int(pr["he"].notna().sum()) if pr is not None else 0
        mean = c["mean_he"].to_numpy(dtype=float)
        inside = mean >= ymin
        ax.plot(x, np.where(inside, mean, np.nan), color=col, lw=2, marker="o", ms=4,
                label=f"{name}: bin mean HE ({n} pairs with HE); reach {reach_str(r['pair'])} (pairs resampled), "
                      f"{reach_str(r['gauge'])} (gauges resampled)")
        below = ~inside & ~np.isnan(mean)
        ax.scatter(x[below], np.full(below.sum(), ymin + 0.06), marker="v", color=col, s=28, zorder=4)
        for xi, m in zip(x[below], mean[below]):
            ax.annotate(f"{m:.0f}", (xi, ymin + 0.14), ha="center", fontsize=7, color=col)
        ax.plot(x, clip(c["median_he"]), color=col, lw=1, alpha=0.6, marker="s", ms=3,
                label=f"{name}: bin median HE (labelled extra, not the registered statistic)")
        rk = r["pair"]["reach_km"]
        if not np.isnan(rk):
            ax.axvline(rk, color=col, lw=1, ls=":")
            ax.text(rk + 1.5, ymax - 0.02, f"{name} reach {rk:.0f} km", color=col, fontsize=8, va="top")
    # Trenton-PNE point on the rain curve, if the rain pair file carries it
    if rain_pairs is not None and "s_id" in rain_pairs.columns:
        hit = rain_pairs[rain_pairs["s_id"].astype(str).str.contains("TTN|14792") &
                         rain_pairs["g_id"].astype(str).str.contains("PNE")]
        if len(hit) == 1 and hit["he"].notna().item():
            ax.scatter(hit["dist_km"], clip(hit["he"]), color=ORANGE, edgecolor=INK, s=60, zorder=5)
            ax.annotate(f"Trenton-PNE (Phase 2), HE {hit['he'].item():.2f}", (hit["dist_km"].item(), clip(hit["he"])[0]),
                        xytext=(6, 6), textcoords="offset points", fontsize=8, color=INK)
    ax.set_ylim(ymin, ymax)
    ax.set_xlabel("distance from exposure gauge to settlement station, km (10 km bins; 0 = same station)",
                  color=MUTED, fontsize=9)
    ax.set_ylabel("hedge effectiveness on REPORT seasons (axis cut at -3)", color=MUTED, fontsize=9)
    ax.set_xticks(range(0, 201, 20))
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.grid(axis="y", color="#e6e6e2", lw=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors=MUTED, labelsize=9)
    handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", fontsize=7.5, frameon=False, ncol=1, bbox_to_anchor=(0.5, 0.045))
    if rain_c is None:
        title = ("Temperature curve only: the rain curve is not available yet.\n"
                 "The temperature hedge never clears zero with confidence at any distance")
    elif status == "unresolved":
        title = ("Neither the rain nor the temperature hedge reaches past zero with confidence at any distance,\n"
                 "so the curves do not separate and the hypothesis (rain reach shorter) is unresolved")
    elif status == "supported":
        title = "Rain reach is shorter than temperature reach (pre-registered hypothesis supported)"
    else:
        title = "Rain reach is not shorter than temperature reach (pre-registered hypothesis not supported)"
    ax.set_title(title, fontsize=11, loc="left", color=INK)
    fig.text(0.01, 0.005, f"Note: {NOTE}. Shaded: 95% band, pairs resampled. Dashed: 95% band, gauges resampled. "
             "2,000 draws, seed 473.\nBin means below -3 are drawn as triangles on the axis floor with their value.",
             fontsize=7.5, color=MUTED)
    fig.tight_layout(rect=(0, 0.14, 1, 1))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def summary(rain_c, temp_c, rain_r, temp_r, rain_pairs, temp_pairs, status, sentence, sep, path):
    L = ["# Combined reach: rain and temperature (Phase 3, Question 1) - EXPLORATORY\n",
         f"Note: {NOTE}. Reach = the largest 10 km bin whose lower 95% band edge is above 0 (registered definition), "
         "recomputed here from each curve file with one rule.\n"]
    L.append("## Reach side by side")
    L.append("| hazard | pairs | pairs with HE | reach, pairs resampled | reach, gauges resampled | same-station bin mean HE [pair band] |")
    L.append("|---|---|---|---|---|---|")
    for name, c, r, pr in (("rain", rain_c, rain_r, rain_pairs), ("temperature", temp_c, temp_r, temp_pairs)):
        if c is None:
            L.append(f"| {name} | not available yet | | | | |")
            continue
        c0 = c.iloc[0]
        L.append(f"| {name} | {len(pr)} | {int(pr['he'].notna().sum())} | {reach_str(r['pair'])} | {reach_str(r['gauge'])} "
                 f"| {c0['mean_he']:.2f} [{c0['lo_pair']:.2f}, {c0['hi_pair']:.2f}] |")
    L.append("")
    L.append("## Do the curves separate?")
    if sep is None:
        L.append("- Not testable yet: the rain curve file is missing. Rerun `python scripts/reach_combined.py` once "
                 "data/processed/reach/rain_pairs.csv and results/phase3/rain_reach_curve.csv exist.")
    else:
        L.append(f"- Bins where both hazards have a band: {sep['n_bins_compared']}. Bins where the rain band lies wholly "
                 f"above the temperature band: {sep['n_rain_above']} {sep['rain_above_bins']}. Bins where the temperature "
                 f"band lies wholly above the rain band: {sep['n_temp_above']} {sep['temp_above_bins']}.")
        if sep["n_rain_above"] == 0 and sep["n_temp_above"] == 0:
            L.append("- The two curves do not separate: in no bin does one hazard's band sit above the other's.")
        else:
            L.append("- The curves separate in the bins listed; elsewhere the bands overlap.")
    L.append("")
    L.append(f"## Pre-registered hypothesis: rain reach is shorter than temperature reach - **{status.upper()}**")
    L.append(f"- {sentence}")
    if temp_c is not None:
        L.append("- Temperature: no bin, including the same-station bin, has a lower band edge above 0 under either "
                 "bootstrap (results/phase3/temp_reach_summary.md explains why: the registered d grid {0..8} is far "
                 "below the 20-40 hot days a season at the warm stations).")
    L.append("")
    L.append("## Caveats")
    L.append("- Rain and temperature pairs have different histories (rain pairs use up to several decades of seasons, "
             "temperature pairs 11 seasons, 5 of them REPORT), so a band width is not comparable across hazards.")
    L.append("- HE is unbounded below; bin means are pulled by pairs whose REPORT seasons barely exceed the TRAIN "
             "reference. Medians are shown as a labelled extra.")
    L.append("- The bands resample pairs or gauges, not seasons; all pairs of a hazard share seasons.")
    with open(path, "w") as f:
        f.write("\n".join(L) + "\n")


def main() -> None:
    rain_pairs, rain_c = load("rain")
    temp_pairs, temp_c = load("temp")
    if temp_c is None:
        raise SystemExit("temperature outputs missing: run scripts/reach_temp_run.py first")
    temp_r = reaches(temp_c)
    rain_r = reaches(rain_c) if rain_c is not None else None
    status, sentence = verdict(rain_r, temp_r)
    sep = separate(rain_c, temp_c) if rain_c is not None else None
    figure(rain_c, temp_c, rain_r, temp_r, rain_pairs, temp_pairs, os.path.join(OUT, "combined_reach.png"), status)
    summary(rain_c, temp_c, rain_r, temp_r, rain_pairs, temp_pairs, status, sentence, sep,
            os.path.join(OUT, "combined_summary.md"))
    print("rain available:", rain_c is not None, "| hypothesis:", status, "|", sentence)


if __name__ == "__main__":
    main()
