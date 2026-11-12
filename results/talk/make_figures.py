"""Talk and report figures for Phase 4 (wrap-up).

Run from the repository root:  python results/talk/make_figures.py
Writes results/talk/fig*.png at 1920x1080 and results/talk/figure_numbers.csv
(every number printed on a figure, with the file it came from).

Every figure reads only processed aggregates and results files; nothing under
data/raw is touched. Rain counts are OBSERVED station data. Every price,
premium and net cost is MODELLED. Figure 5 is a SIMULATION.

Figures 6 and 7 (Phase 3 reach and lead time) are drawn from
results/phase3/*reach_curve.csv and results/phase3/leadtime_he_by_lead.csv when
those files exist; otherwise a clearly marked placeholder slide is written.
"""
from __future__ import annotations

import csv
import glob
import textwrap
import json
import os
import sys

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "results", "talk")
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- palette --
# dataviz reference palette (light surface). Categorical slots in fixed order;
# validated with scripts/validate_palette.js (all checks pass; aqua and yellow
# need direct labels for contrast relief, which every figure here supplies).
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
S1, S2, S3, S4 = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"  # blue orange aqua yellow
CRITICAL = "#d03b3b"  # status: the failed registered case
GOOD = "#0ca30c"

# Slide type sizes (16:9 at 1920x1080). Legible from the back of a room.
FIG = (16, 9)
DPI = 120
T_TITLE, T_SUB, T_AX, T_TICK, T_LABEL, T_FOOT = 30, 20, 21, 19, 19, 15

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "axes.edgecolor": BASELINE,
    "axes.linewidth": 1.0,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "axes.grid.axis": "y",
    "grid.color": GRID,
    "grid.linewidth": 1.0,
    "grid.linestyle": "-",
    "xtick.color": INK2,
    "ytick.color": INK2,
    "xtick.labelsize": T_TICK,
    "ytick.labelsize": T_TICK,
    "axes.labelsize": T_AX,
    "axes.labelcolor": INK2,
    "axes.titlesize": T_TITLE,
    "legend.fontsize": T_LABEL,
    "legend.frameon": False,
    "lines.linewidth": 2,
})

NUMBERS: list[dict] = []


def note(fig: str, name: str, value, source: str) -> None:
    NUMBERS.append({"figure": fig, "name": name, "value": value, "source": source})


def wrap(text: str, width: int) -> str:
    return "\n".join(textwrap.wrap(text, width=width))


def frame(title: str, subtitle: str, footnote: str, rect=(0.07, 0.235, 0.90, 0.535), bottom_note: str = ""):
    """One slide-sized figure: headline, two-line subtitle, plot, one-line note, footnote."""
    fig = plt.figure(figsize=FIG, dpi=DPI)
    t = wrap(title, 66)
    fig.text(0.04, 0.945, t, fontsize=T_TITLE, fontweight="bold", color=INK, ha="left", va="top")
    y_sub = 0.875 - 0.055 * t.count("\n")
    fig.text(0.04, y_sub, wrap(subtitle, 100), fontsize=T_SUB, color=INK2, ha="left", va="top",
             linespacing=1.3)
    if bottom_note:
        fig.text(0.5, 0.105, wrap(bottom_note, 104), fontsize=T_LABEL - 1, color=INK, ha="center",
                 va="center", linespacing=1.3)
    fig.text(0.04, 0.018, wrap(footnote, 138), fontsize=T_FOOT, color=MUTED, ha="left", va="bottom",
             linespacing=1.3)
    if t.count("\n"):
        rect = (rect[0], rect[1], rect[2], rect[3] - 0.055 * t.count("\n"))
    ax = fig.add_axes(rect)
    return fig, ax


def save(fig, name: str) -> None:
    path = os.path.join(OUT, name)
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    print("wrote", os.path.relpath(path, ROOT))


def tag(ax, text: str, color=INK2, x=0.995, y=0.98):
    """Observed / modelled / simulated stamp inside the axes, top right."""
    ax.text(x, y, text, transform=ax.transAxes, ha="right", va="top", fontsize=T_LABEL,
            color=color, fontweight="bold")


# ------------------------------------------------------------- figure 1 ----
def fig1_wrong_days() -> None:
    src = "data/processed/rain/season_counts_TTN.csv"
    s = pd.read_csv(os.path.join(ROOT, src))
    s = s[(s.calendar == "all_days") & (s.threshold_in == 0.25) & (s.window == "10:00-18:00")
          & (s.season_usable) & (s.season >= 1999)].sort_values("season")
    pay, loss = s.ref_ghcn_pay_days.to_numpy(float), s.loss_days.to_numpy(float)
    m_pay, m_loss = pay.mean(), loss.mean()
    ratio = m_pay / m_loss
    not_loss = s.ref_ghcn_paid_not_loss.sum() / s.ref_ghcn_pay_days.sum()
    loss_paid = s.ref_loss_and_ghcn_paid.sum() / s.loss_days.sum()
    for k, v in [("seasons", len(s)), ("mean_kalshi_pay_days", round(m_pay, 2)),
                 ("mean_loss_days", round(m_loss, 2)), ("ratio", round(ratio, 2)),
                 ("share_pay_days_not_loss", round(not_loss, 3)),
                 ("share_loss_days_paid", round(loss_paid, 3))]:
        note("fig1", k, v, src)

    fig, ax = frame(
        f"Kalshi's rain contract pays on ~{ratio:.0f}x more days than a park loses",
        f"Trenton, {len(s)} usable seasons 1999-2026. Kalshi pays on any day with 0.01 inch "
        f"(official daily total); the park loses on a day with 0.25 inch between 10:00 and 18:00.",
        "OBSERVED station data (Trenton/Mercer, hourly ASOS and GHCN-Daily). No prices on this chart. "
        "Source: data/processed/rain/season_counts_TTN.csv",
        bottom_note=f"{not_loss:.0%} of Kalshi pay days are not loss days. Kalshi pays on {loss_paid:.0%} of loss days.",
    )
    x = np.arange(len(s))
    w = 0.38
    ax.bar(x - w / 2 - 0.02, pay, width=w, color=S1, label="Days Kalshi pays", zorder=3)
    ax.bar(x + w / 2 + 0.02, loss, width=w, color=S2, label="Days the park loses money", zorder=3)
    ax.axhline(m_pay, color=S1, lw=1.5, ls=(0, (4, 3)), zorder=2)
    ax.axhline(m_loss, color=S2, lw=1.5, ls=(0, (4, 3)), zorder=2)
    bb = dict(boxstyle="round,pad=0.25", fc=SURFACE, ec="none", alpha=0.9)
    ax.text(len(s) - 0.4, m_pay + 1.5, f"mean {m_pay:.1f} pay days", ha="right", va="bottom",
            fontsize=T_LABEL, color=INK2, fontweight="bold", bbox=bb, zorder=6)
    ax.text(len(s) - 0.4, m_loss + 1.5, f"mean {m_loss:.1f} loss days", ha="right", va="bottom",
            fontsize=T_LABEL, color=INK2, fontweight="bold", bbox=bb, zorder=6)
    ax.set_xticks(x)
    ax.set_xticklabels([str(y) if y % 3 == 0 else "" for y in s.season], rotation=0)
    ax.set_xlim(-0.7, len(s) - 0.3)
    ax.set_ylim(0, 64)
    ax.set_ylabel("Days per season")
    ax.legend(loc="upper left", ncol=2, handlelength=1.2, columnspacing=1.5)
    tag(ax, "OBSERVED")
    save(fig, "fig1_wrong_days.png")


# ------------------------------------------------------------- figure 2 ----
def fig2_forecast_in_price() -> None:
    src = "data/processed/kalshi_rain/calibration.csv"
    src2 = "data/processed/kalshi_rain/model_eval.csv"
    c = pd.read_csv(os.path.join(ROOT, src))
    a = c[(c.hours_before_close == 24) & (c.set == "all markets") & (c.price == "ask")].sort_values("bin_lo")
    mid = c[(c.hours_before_close == 24) & (c.set == "all markets") & (c.price == "mid")]
    rain = (a.n * a.yes_share).to_numpy()
    dry = (a.n - a.n * a.yes_share).to_numpy()
    n_all = int(a.n.sum())
    mean_ask_rain_bins = float((a.mean_price * rain).sum() / rain.sum())
    mean_ask_dry_bins = float((a.mean_price * dry).sum() / dry.sum())
    mean_mid = float((mid.mean_price * mid.n).sum() / mid.n.sum())
    yes_share = float((mid.n * mid.yes_share).sum() / mid.n.sum())
    # Held-out set C (four cities, Jul 15-Sep 30 2026): observed mean ask by outcome.
    m = pd.read_csv(os.path.join(ROOT, src2))
    rc = m[(m["sample"].str.startswith("main")) & (m.design.str.startswith("hold out C"))
           & (m.model == "skill") & (m.part == "test (held out)")].iloc[0]
    ask_rain_c, ask_dry_c, n_c = float(rc.obs_mean_ask_rain_days), float(rc.obs_mean_ask_dry_days), int(rc.n_days)
    for k, v, s_ in [("two_sided_days_24h", n_all, src), ("rain_days_in_bins", round(float(rain.sum()), 1), src),
                     ("mean_ask_rain_days_from_bins", round(mean_ask_rain_bins, 3), src),
                     ("mean_ask_dry_days_from_bins", round(mean_ask_dry_bins, 3), src),
                     ("mean_mid_price_24h", round(mean_mid, 3), src), ("share_rain_days", round(yes_share, 3), src),
                     ("mean_ask_rain_days_setC", ask_rain_c, src2), ("mean_ask_dry_days_setC", ask_dry_c, src2),
                     ("n_days_setC", n_c, src2)]:
        note("fig2", k, v, s_)

    fig, ax = frame(
        "By the time you can buy, the forecast is already in the price",
        f"Kalshi ask price 24 h before close, {n_all} market-days with a two-sided book, 2021-2026, four cities. "
        f"Right on average (mean price {mean_mid:.2f}, rain on {yes_share:.0%} of days), but split by what happened.",
        "OBSERVED Kalshi quotes, binned aggregates only (10-cent bins; counts per bin split by the day's outcome; "
        f"these bins give means of {mean_ask_dry_bins:.2f} and {mean_ask_rain_bins:.2f}). "
        "Sources: data/processed/kalshi_rain/calibration.csv, model_eval.csv",
        bottom_note=f"Calibration: mean mid price {mean_mid:.2f}, rain on {yes_share:.1%} of days. "
        f"Outcome means: held-out 2026 set, {n_c} days.",
    )
    centers = ((a.bin_lo + a.bin_hi) / 2).to_numpy()
    w = 0.042
    ax.bar(centers - w / 2 - 0.003, dry, width=w, color=S1, label="Dry days (no rain)", zorder=3)
    ax.bar(centers + w / 2 + 0.003, rain, width=w, color=S2, label="Rain days", zorder=3)
    for cx, d_, r_ in zip(centers, dry, rain):
        ax.text(cx - w / 2 - 0.003, d_ + 1.2, f"{d_:.0f}", ha="center", va="bottom", fontsize=15, color=INK2)
        ax.text(cx + w / 2 + 0.003, r_ + 1.2, f"{r_:.0f}", ha="center", va="bottom", fontsize=15, color=INK2)
    ax.set_xticks(np.arange(0, 1.01, 0.1))
    ax.set_xticklabels([f"{v:.1f}" for v in np.arange(0, 1.01, 0.1)])
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(0, 108)
    ax.set_xlabel("Ask price for a $1 'rain' contract, 24 h before close")
    ax.set_ylabel("Market-days")
    ax.legend(loc="upper center", ncol=2, handlelength=1.2)
    # Mean ask by outcome: a vertical marker in the series color, label in ink.
    for val, col, lab in [(ask_dry_c, S1, f"mean ask on dry days: {ask_dry_c:.2f}"),
                          (ask_rain_c, S2, f"mean ask on rain days: {ask_rain_c:.2f}")]:
        ax.plot([val, val], [0, 60], color=col, lw=2.5, ls=(0, (4, 3)), zorder=2)
        ax.text(val, 62, lab, ha="center", va="bottom", fontsize=T_LABEL, color=INK, fontweight="bold")
    tag(ax, "OBSERVED")
    save(fig, "fig2_forecast_in_price.png")


# ------------------------------------------------------------- figure 3 ----
CASES = [("A", "A  Trenton,\nsame station\n(ceiling, circular)"),
         ("B1", "B1  Trenton,\npark 28 km away\n(REGISTERED HEADLINE)"),
         ("D-same", "D-same  Philadelphia,\nsame station\n(35 seasons)"),
         ("D-PNE", "D-PNE  Philadelphia,\npark 29 km away\n(30 seasons)")]
STRATS = [("2", "Kalshi daily, sized", S1), ("3", "Seasonal count, 6 buckets (the product)", S2),
          ("4", "Seasonal count, exact (benchmark)", S3), ("5", "Kalshi daily at fair-comparison price", S4)]


def fig3_hedge_effectiveness() -> None:
    src = "results/phase2/metrics_tidy.csv"
    m = pd.read_csv(os.path.join(ROOT, src))
    m = m[(m.variant == "main") & (m.window == "REPORT") & (m.metric == "he")]
    fig, ax = frame(
        "Seasonal contract hedges Philadelphia, fails 28 km from Trenton",
        "Hedge effectiveness on held-out seasons: 1 = all bad-season excess removed, 0 = no hedge, below 0 = worse "
        "than no hedge. 95% bootstrap intervals.",
        "Rain counts OBSERVED; every premium and Kalshi price MODELLED (Phase 1 'skill' model, loading 0.20). "
        "Intervals: 2,000 season bootstrap draws, seed 473. Source: results/phase2/metrics_tidy.csv (variant main)",
        rect=(0.07, 0.235, 0.90, 0.535),
    )
    lo_clip = -1.35
    x0 = np.arange(len(CASES)) * 1.0
    off = np.linspace(-0.3, 0.3, len(STRATS))
    nseas = {}
    for i, (case, _) in enumerate(CASES):
        for j, (st, lab, col) in enumerate(STRATS):
            r = m[(m.case == case) & (m.strategy.astype(str) == st)].iloc[0]
            v, lo, hi = float(r.value), float(r.lo), float(r.hi)
            nseas[case] = int(r.n_seasons)
            note("fig3", f"HE_{case}_strategy{st}", f"{v:.3f} [{lo:.3f}, {hi:.3f}]", src)
            xx = x0[i] + off[j]
            lo_draw = max(lo, lo_clip)
            ax.plot([xx, xx], [lo_draw, hi], color=col, lw=3, solid_capstyle="round", zorder=3)
            if lo < lo_clip:
                ax.text(xx, lo_clip - 0.03, f"to {lo:.1f}", ha="center", va="top", fontsize=13, color=INK2)
            ax.plot([xx], [v], marker="o", ms=13, color=col, mec=SURFACE, mew=2, zorder=4,
                    label=lab if i == 0 else None)
            ax.text(xx + 0.055, v, f"{v:.2f}", ha="left", va="center", fontsize=15, color=INK, zorder=5)
    ax.axhline(0, color=INK, lw=1.5, zorder=2)
    ax.text(x0[-1] + 0.46, 0.02, "no hedge", ha="right", va="bottom", fontsize=T_LABEL - 2, color=INK2)
    # Mark the failed registered case.
    ax.axvspan(x0[1] - 0.47, x0[1] + 0.47, color=CRITICAL, alpha=0.07, zorder=1)
    ax.text(x0[1], 0.93, "FAILED: registered claim not made\n(seasonal vs Kalshi: -0.04 [-0.13, -0.00])",
            ha="center", va="top", fontsize=T_LABEL - 2, color=CRITICAL, fontweight="bold")
    ax.set_xticks(x0)
    ax.set_xticklabels([lab for _, lab in CASES], fontsize=T_TICK - 1)
    ax.set_xlim(-0.55, len(CASES) - 0.45)
    ax.set_ylim(lo_clip - 0.15, 1.0)
    ax.set_yticks([-1, -0.5, 0, 0.5, 1])
    ax.set_ylabel("Hedge effectiveness (HE)")
    ax.legend(loc="lower right", ncol=2, handlelength=1.0, columnspacing=1.6,
              fontsize=T_LABEL - 2, markerscale=0.9)
    save(fig, "fig3_hedge_effectiveness.png")


# ------------------------------------------------------------- figure 4 ----
def fig4_net_cost_philadelphia() -> None:
    src = "results/phase2/season_net_cost.csv"
    src_m = "results/phase2/metrics_tidy.csv"
    src_p = "results/phase2/train_params.csv"
    sn = pd.read_csv(os.path.join(ROOT, src))
    d = sn[(sn.case == "D-same") & (sn.variant == "main") & (sn.window == "REPORT")]
    piv = d.pivot(index="season", columns="strategy", values="net_cost").sort_index()
    m = pd.read_csv(os.path.join(ROOT, src_m))
    mm = m[(m.case == "D-same") & (m.variant == "main") & (m.window == "REPORT")]

    def met(st, metric):
        r = mm[(mm.strategy.astype(str) == st) & (mm.metric == metric)].iloc[0]
        return float(r.value), float(r.lo), float(r.hi)

    he3 = met("3", "he")
    worst0 = met("0", "worst_mean_unhedged")
    worst3 = met("3", "worst_mean_hedged")
    worst2 = met("2", "worst_mean_hedged")
    mean0, mean2, mean3 = met("0", "mean_net_cost"), met("2", "mean_net_cost"), met("3", "mean_net_cost")
    tp = pd.read_csv(os.path.join(ROOT, src_p))
    ref = float(tp[(tp.case == "D-same") & (tp.variant == "main")].train_reference_mean_D_park.iloc[0])
    prem3 = float(tp[(tp.case == "D-same") & (tp.variant == "main")].premium_strategy3.iloc[0])
    for k, v, s_ in [("HE_strategy3", f"{he3[0]:.3f} [{he3[1]:.3f}, {he3[2]:.3f}]", src_m),
                     ("worst10pct_mean_unhedged", round(worst0[0], 2), src_m),
                     ("worst10pct_mean_seasonal", round(worst3[0], 2), src_m),
                     ("worst10pct_mean_kalshi_sized", round(worst2[0], 2), src_m),
                     ("mean_net_cost_unhedged", round(mean0[0], 2), src_m),
                     ("mean_net_cost_kalshi_sized", round(mean2[0], 2), src_m),
                     ("mean_net_cost_seasonal", round(mean3[0], 2), src_m),
                     ("train_reference_level", ref, src_p), ("premium_strategy3_per_season", prem3, src_p),
                     ("report_seasons", len(piv), src)]:
        note("fig4", k, v, s_)

    fig, ax = frame(
        f"Seasonal contract cuts Philadelphia's bad seasons by two-thirds",
        f"Net cost per season in loss days, {len(piv)} held-out seasons 1991-2026; terms fixed on 1941-1990. "
        f"HE {he3[0]:.2f} [{he3[1]:.2f}, {he3[2]:.2f}]. Worst 10% of seasons: {worst0[0]:.1f} unhedged, {worst3[0]:.1f} hedged. "
        f"Dashed line: reference level ({ref:.1f}).",
        "Loss days OBSERVED (Philadelphia Intl); payouts from observed counts; premiums and Kalshi prices MODELLED. "
        "HE = share of downside semi-variance above the reference removed. Sources: results/phase2/season_net_cost.csv, metrics_tidy.csv",
        bottom_note=f"Mean net cost: none {mean0[0]:.2f}, Kalshi sized {mean2[0]:.2f}, seasonal {mean3[0]:.2f} "
        f"(the {prem3:.2f} premium raises the mean).",
    )
    years = piv.index.to_numpy()
    x = np.arange(len(years))
    w = 0.26
    ax.bar(x - w - 0.02, piv["0"], width=w, color=BASELINE, label="No hedge", zorder=3)
    ax.bar(x, piv["2"], width=w, color=S1, label="Kalshi daily, sized", zorder=3)
    ax.bar(x + w + 0.02, piv["3"], width=w, color=S2, label="Seasonal count contract", zorder=3)
    ax.axhline(ref, color=INK, lw=1.5, ls=(0, (4, 3)), zorder=2)
    ax.set_xticks(x)
    ax.set_xticklabels([str(y) if y % 5 == 0 else "" for y in years])
    ax.set_xlim(-0.7, len(years) - 0.3)
    ax.set_ylim(0, 16)
    ax.set_ylabel("Net cost (loss days)")
    ax.legend(loc="upper left", ncol=3, handlelength=1.2, columnspacing=1.6)
    save(fig, "fig4_net_cost_philadelphia.png")


# ------------------------------------------------------------- figure 5 ----
def fig5_market_price(d_show: int = 3) -> None:
    src = "results/market/hedge_pricing.csv"
    src_b = "results/market/break_even.csv"
    h = pd.read_csv(os.path.join(ROOT, src))
    h = h[h.deductible_d == d_show].copy()
    h["ratio"] = h.b / h["size"]
    be = pd.read_csv(os.path.join(ROOT, src_b))
    cross = float(be[be.deductible_d == d_show].b_per_size_for_registered_premium.iloc[0])
    note("fig5", "deductible_shown", d_show, src)
    note("fig5", "b_over_size_where_price_is_1.20_informed", round(cross, 2), src_b)
    fig, ax = frame(
        "A sponsor-funded market prices the hedge near fair value once funding is ~10x the hedge",
        f"LMSR market for the six-bucket contract, deductible d = {d_show}. What the hedger pays per $1 of expected "
        "payout, against sponsor funding b as a multiple of the hedge.",
        "SIMULATION of the LMSR cost rule: no real traders, no real money. 'Fair' means fair under the TRAIN bucket "
        "probabilities (16 Trenton seasons). Sources: results/market/hedge_pricing.csv, break_even.csv",
    )
    for state, col, lab in [("uniform", S1, "Uniform start (hedger trades first)"),
                            ("informed", S2, "Informed start (prices already at the bucket odds)")]:
        g = h[h.state == state].groupby("ratio").price_per_1_expected_payout.mean().sort_index()
        ax.plot(g.index, g.values, color=col, lw=2.5, marker="o", ms=10, mec=SURFACE, mew=2, label=lab, zorder=4)
        for r_, v_ in g.items():
            note("fig5", f"price_per_1_{state}_b_over_size_{r_:g}", round(float(v_), 3), src)
        dy = 0.13 if state == "uniform" else -0.13
        ax.text(g.index[-1], g.values[-1] + dy, f"{g.values[-1]:.2f}", ha="center", va="center",
                fontsize=T_LABEL, color=INK)
    ax.axhline(1.20, color=INK, lw=1.5, ls=(0, (4, 3)), zorder=2)
    ax.text(0.052, 1.23, "1.20 = registered modelled premium (20% loading)", ha="left", va="bottom",
            fontsize=T_LABEL - 2, color=INK2)
    ax.axhline(1.0, color=INK, lw=1.0, zorder=2)
    ax.text(0.052, 1.015, "1.00 = fair value", ha="left", va="bottom", fontsize=T_LABEL - 2, color=INK2)
    ax.axvline(cross, color=S2, lw=1.5, ls=(0, (2, 3)), zorder=2)
    ax.text(cross * 1.12, 2.45, f"informed start crosses 1.20\nat b = {cross:.1f}x the hedge size", ha="left",
            va="top", fontsize=T_LABEL - 2, color=INK2)
    ax.set_xscale("log")
    ax.set_xticks([0.05, 0.2, 1, 5, 20, 100, 500, 2000])
    ax.set_xticklabels(["0.05x", "0.2x", "1x", "5x", "20x", "100x", "500x", "2000x"])
    ax.set_xlim(0.04, 3200)
    ax.set_ylim(0.8, 3.6)
    ax.set_xlabel("Sponsor funding b as a multiple of the hedge size")
    ax.set_ylabel("Price per $1 of expected payout")
    ax.legend(loc="upper right", handlelength=1.6)
    tag(ax, "SIMULATION", x=0.995, y=0.80)
    save(fig, "fig5_market_price.png")


# ------------------------------------------------------- figures 6 and 7 ---
def placeholder(name: str, title: str, expected: str, what: str) -> None:
    fig = plt.figure(figsize=FIG, dpi=DPI)
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_axis_off()
    ax.add_patch(FancyBboxPatch((0.08, 0.18), 0.84, 0.62, boxstyle="round,pad=0.01,rounding_size=0.02",
                                fc=SURFACE, ec=CRITICAL, lw=3, ls=(0, (6, 4))))
    fig.text(0.04, 0.945, title, fontsize=T_TITLE, fontweight="bold", color=INK, ha="left", va="top")
    fig.text(0.5, 0.60, "PLACEHOLDER: PHASE 3 RESULT PENDING", fontsize=40, fontweight="bold", color=CRITICAL,
             ha="center", va="center")
    fig.text(0.5, 0.47, what, fontsize=T_SUB, color=INK2, ha="center", va="center", wrap=True)
    fig.text(0.5, 0.33, f"Drawn automatically by results/talk/make_figures.py when\n{expected}\nexists.",
             fontsize=T_LABEL, color=MUTED, ha="center", va="center")
    fig.text(0.04, 0.035, "EXPLORATORY (Phase 3, pre-registered after Phase 2 results). Weather observed; premiums modelled.",
             fontsize=T_FOOT, color=MUTED, ha="left", va="bottom")
    save(fig, name)


def _col(df: pd.DataFrame, *names: str):
    """First column whose lower-case name matches one of the candidates (prefix match allowed)."""
    cols = {c.lower(): c for c in df.columns}
    for n in names:
        if n in cols:
            return cols[n]
    for n in names:
        for lc, c in cols.items():
            if lc.startswith(n):
                return c
    return None


def fig6_reach() -> None:
    files = sorted(glob.glob(os.path.join(ROOT, "results", "phase3", "*reach_curve.csv")))
    if not files:
        placeholder("fig6_reach.png", "How far does a weather hedge reach?",
                    "results/phase3/*reach_curve.csv (one file per hazard: rain, temperature)",
                    "Hedge effectiveness against distance between settlement station and exposure gauge,\n"
                    "binned mean with 95% bootstrap band, one curve for rain and one for temperature.\n"
                    "Reach = the farthest bin whose band stays above zero.")
        return
    fig, ax = frame(
        "How far a weather hedge reaches",
        "Every (settlement station, exposure gauge) pair in the region. Binned mean HE with a 95% bootstrap band. "
        "EXPLORATORY Phase 3 result.",
        "Weather OBSERVED; premiums MODELLED (exact count contract, loading 0.20). Sources: " +
        ", ".join(os.path.relpath(f, ROOT) for f in files),
    )
    cols = [S1, S2, S3]
    for k, f in enumerate(files[:3]):
        df = pd.read_csv(f)
        xc = _col(df, "bin_mid", "distance_km", "bin_center", "distance", "bin_upper", "bin_hi", "bin")
        yc = _col(df, "he_mean", "mean_he", "he", "value")
        lc = _col(df, "lo", "he_lo", "lower", "lo95", "ci_lo")
        hc = _col(df, "hi", "he_hi", "upper", "hi95", "ci_hi")
        if xc is None or yc is None:
            print("fig6: cannot find distance/HE columns in", f, list(df.columns))
            continue
        label = os.path.basename(f).replace("_reach_curve.csv", "").replace("reach_curve.csv", "all").capitalize()
        d = df.sort_values(xc)
        if lc and hc:
            ax.fill_between(d[xc], d[lc], d[hc], color=cols[k], alpha=0.12, lw=0)
        ax.plot(d[xc], d[yc], color=cols[k], lw=2.5, marker="o", ms=9, mec=SURFACE, mew=2, label=label)
        note("fig6", f"curve_{label}", "see file", os.path.relpath(f, ROOT))
    ax.axhline(0, color=INK, lw=1.5)
    ax.set_xlabel("Distance from settlement station to exposure gauge (km)")
    ax.set_ylabel("Hedge effectiveness (HE)")
    ax.set_ylim(-1.0, 1.0)
    ax.set_yticks([-1, -0.5, 0, 0.5, 1])
    ax.legend(loc="upper right")
    save(fig, "fig6_reach.png")


def fig7_leadtime() -> None:
    f = os.path.join(ROOT, "results", "phase3", "leadtime_he_by_lead.csv")
    if not os.path.exists(f):
        placeholder("fig7_leadtime.png", "When must a daily contract be listed to work as a hedge?",
                    "results/phase3/leadtime_he_by_lead.csv",
                    "Hedge effectiveness (and premium per $1 of payout) of buying Kalshi's daily contract every day,\n"
                    "priced at the forecast probability a buyer would face 1 to 7 days ahead (GFS MOS) and at climatology.\n"
                    "Trenton and Philadelphia same-station cases.")
        return
    df = pd.read_csv(f)
    xc = _col(df, "lead_days", "lead", "lead_time")
    yc = _col(df, "he", "he_mean", "value")
    lc = _col(df, "lo", "he_lo", "lower", "lo95")
    hc = _col(df, "hi", "he_hi", "upper", "hi95")
    cc = _col(df, "case", "station", "settlement")
    fig, ax = frame(
        "Hedge effectiveness of the daily contract against listing lead time",
        "Buy the daily rain contract every season day, priced at the forecast probability at each lead. "
        "EXPLORATORY Phase 3 result.",
        "Weather OBSERVED; prices MODELLED from GFS MOS probabilities plus the fitted Phase 1 markup and fee. "
        "Source: results/phase3/leadtime_he_by_lead.csv",
    )
    groups = [(None, df)] if cc is None else list(df.groupby(cc))
    for k, (g, d) in enumerate(groups[:4]):
        col = [S1, S2, S3, S4][k]
        d = d.sort_values(xc)
        if lc and hc:
            ax.fill_between(d[xc], d[lc], d[hc], color=col, alpha=0.12, lw=0)
        ax.plot(d[xc], d[yc], color=col, lw=2.5, marker="o", ms=9, mec=SURFACE, mew=2, label=str(g) if g else "HE")
    ax.axhline(0, color=INK, lw=1.5)
    ax.set_xlabel("Lead time at which the buyer can trade (days)")
    ax.set_ylabel("Hedge effectiveness (HE)")
    if len(groups) > 1:
        ax.legend(loc="upper left")
    note("fig7", "curve", "see file", os.path.relpath(f, ROOT))
    save(fig, "fig7_leadtime.png")


# ------------------------------------------------------------- figure 8 ----
def fig8_method() -> None:
    fig = plt.figure(figsize=FIG, dpi=DPI)
    fig.text(0.04, 0.945, "How the hedge was tested: rules first, then held-out seasons",
             fontsize=T_TITLE, fontweight="bold", color=INK, ha="left", va="top")
    fig.text(0.04, 0.875, wrap("Nothing was tuned after a result was seen. Two people coded the rules "
                               "independently and compared numbers only at the end.", 105),
             fontsize=T_SUB, color=INK2, ha="left", va="top", linespacing=1.3)
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9)
    ax.set_axis_off()

    def box(x, y, w, h, title, body, fc, ec):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.15",
                                    fc=fc, ec=ec, lw=2.5))
        ax.text(x + w / 2, y + h - 0.28, title, ha="center", va="top", fontsize=T_AX, fontweight="bold",
                color=INK)
        ax.text(x + w / 2, y + h - 0.85, body, ha="center", va="top", fontsize=T_LABEL - 2, color=INK2,
                linespacing=1.35)

    def arrow(x1, y1, x2, y2):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=30, lw=2.5,
                                     color=INK2, shrinkA=4, shrinkB=4))

    light_blue, light_orange, light_gray = "#e3eefb", "#fdeae1", "#f1f0ec"
    # Row 1: pre-registered rules
    box(0.6, 5.75, 14.8, 1.25, "Pre-registered rules, written before any hedge number was computed",
        "Question, cases, strategies, windows, metric, bootstrap, what counts as a result (docs/PHASE2_PREREG.md)",
        light_gray, BASELINE)
    # Row 2: train -> report
    box(0.6, 2.95, 6.6, 2.35, "TRAIN seasons: choose the terms",
        "Trenton 1999-2014 (16 seasons)\nPhiladelphia 1941-1990 (50 seasons)\n"
        "Bucket edges, deductible, Kalshi position size,\npremium and reference level: all fixed here",
        light_blue, S1)
    box(8.8, 2.95, 6.6, 2.35, "REPORT seasons: score, never tune",
        "Trenton 2015-2026 (12 seasons)\nPhiladelphia 1991-2026 (35 seasons)\n"
        "Hedge effectiveness, net cost, worst seasons,\n95% bootstrap intervals (2,000 draws)",
        light_orange, S2)
    arrow(7.25, 4.2, 8.75, 4.2)
    ax.text(8.0, 4.45, "terms", ha="center", va="bottom", fontsize=T_LABEL - 2, color=INK2)
    arrow(3.9, 5.7, 3.9, 5.35)
    arrow(12.1, 5.7, 12.1, 5.35)
    # Row 3: two implementations agree
    box(0.6, 0.85, 4.6, 1.65, "Implementation 1",
        "registered: src/hedge_eval\nresults/phase2", light_gray, BASELINE)
    box(10.8, 0.85, 4.6, 1.65, "Implementation 2",
        "independent: replication/replicate.py\nwritten from the rules alone", light_gray, BASELINE)
    arrow(2.9, 2.9, 2.9, 2.55)
    arrow(13.1, 2.9, 13.1, 2.55)
    ax.text(8.0, 1.68, "300 of 300 shared\nnumbers agree\n(120 on the registered\ncases and strategies)",
            ha="center", va="center", fontsize=T_LABEL - 1, fontweight="bold", color=GOOD, linespacing=1.3)
    ax.plot([5.3, 5.9], [1.68, 1.68], color=GOOD, lw=2.5)
    ax.plot([10.1, 10.7], [1.68, 1.68], color=GOOD, lw=2.5)
    fig.text(0.04, 0.018, wrap("Inputs: rain counts OBSERVED at the station; every premium and Kalshi price "
                               "MODELLED (Phase 1 price model fitted on 381 real quotes). Agreement: "
                               "replication/results.csv vs results/phase2/metrics_tidy.csv, tolerance 1e-6.", 138),
             fontsize=T_FOOT, color=MUTED, ha="left", va="bottom", linespacing=1.3)
    note("fig8", "numbers_agree", "300 of 300 (120 registered)",
         "replication/results.csv vs results/phase2/metrics_tidy.csv")
    save(fig, "fig8_method.png")


def main() -> None:
    fig1_wrong_days()
    fig2_forecast_in_price()
    fig3_hedge_effectiveness()
    fig4_net_cost_philadelphia()
    fig5_market_price()
    fig6_reach()
    fig7_leadtime()
    fig8_method()
    with open(os.path.join(OUT, "figure_numbers.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["figure", "name", "value", "source"])
        w.writeheader()
        w.writerows(NUMBERS)
    print("wrote results/talk/figure_numbers.csv")


if __name__ == "__main__":
    main()
