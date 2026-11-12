"""Figures and summary for Phase 2, built only from the CSVs written by scripts/hedge_run.py.

    python scripts/hedge_report.py

Writes  results/phase2/fig_b1_net_cost_by_season.png   net cost per REPORT season, case B1, strategies 0, 2, 3
        results/phase2/fig_hedge_effectiveness.png     HE with 95% intervals, strategies 1-5, cases A, B1, D
        results/phase2/headline_table.csv              HE and intervals, strategies 1-5 and HE(3)-HE(2), main cases
        results/phase2/summary.md                      findings in the pre-registration's terms
Weather is OBSERVED; prices and premiums are MODELLED. No number is computed here that is not in the CSVs.
"""
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "results", "phase2")
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
COLORS = {"0": "#2a78d6", "2": "#eb6834", "3": "#1baf7a"}
HE_COLORS = {"1": "#2a78d6", "2": "#eb6834", "3": "#1baf7a", "4": "#eda100", "5": "#e87ba4"}
HE_MARKERS = {"1": "v", "2": "s", "3": "o", "4": "D", "5": "^"}
NAMES = {"0": "No hedge", "1": "1 Kalshi daily, 1 per day", "2": "2 Kalshi daily, sized", "3": "3 Seasonal, six buckets",
         "4": "4 Seasonal, exact (benchmark)", "5": "5 Kalshi daily, fair-comparison price"}
NOTE = "Observed weather, modelled prices."


def load():
    m = pd.read_csv(os.path.join(OUT, "metrics_tidy.csv"), dtype={"strategy": str})
    p = pd.read_csv(os.path.join(OUT, "train_params.csv"))
    s = pd.read_csv(os.path.join(OUT, "season_net_cost.csv"), dtype={"strategy": str})
    d = pd.read_csv(os.path.join(OUT, "standin_distances.csv"))
    return m, p, s, d


def get(m, case, strategy, metric="he", window="REPORT", variant="main"):
    """(value, lo, hi) of one cell of the tidy table."""
    r = m[(m.case == case) & (m.variant == variant) & (m.strategy == strategy) & (m.metric == metric) & (m.window == window)]
    if len(r) != 1:
        raise KeyError((case, strategy, metric, window, variant, len(r)))
    r = r.iloc[0]
    return float(r.value), float(r.lo), float(r.hi)


def cell(m, case, strategy, metric="he", window="REPORT", variant="main", nd=2):
    """'value [lo, hi]' (REPORT) or 'value' (TRAIN)."""
    try:
        v, lo, hi = get(m, case, strategy, metric, window, variant)
    except KeyError:
        return "n/a"
    if np.isnan(v):
        return "undefined"
    if window == "TRAIN" or np.isnan(lo):
        return f"{v:.{nd}f}"
    return f"{v:.{nd}f} [{lo:.{nd}f}, {hi:.{nd}f}]"


def style(ax):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(INK2)
    ax.tick_params(colors=INK2, labelsize=10)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def figure_net_cost(m, p, s):
    x = s[(s.case == "B1") & (s.variant == "main") & (s.window == "REPORT")]
    w = x.pivot(index="season", columns="strategy", values="net_cost")
    ref = float(p[(p.case == "B1") & (p.variant == "main")].train_reference_mean_D_park.iloc[0])
    lower = int(((w["2"] < w["0"]) | (w["3"] < w["0"])).sum())
    fig, ax = plt.subplots(figsize=(11, 5.8), facecolor=SURFACE)
    style(ax)
    pos = np.arange(len(w))
    for i, k in enumerate(("0", "2", "3")):
        ax.bar(pos + (i - 1) * 0.27, w[k], width=0.24, color=COLORS[k], label=NAMES[k], edgecolor=SURFACE, linewidth=1)
    ax.axhline(ref, color=INK2, linewidth=1.2, linestyle="--")
    ax.text(-0.45, ref + 0.15, f"TRAIN mean, no hedge ({ref:.2f})", color=INK2, fontsize=9, ha="left")
    ax.set_xticks(pos)
    ax.set_xticklabels(w.index.astype(int))
    ax.set_ylabel("Net cost per season (loss days, L = 1)", color=INK, fontsize=11)
    ax.set_xlabel("REPORT season", color=INK, fontsize=11)
    ax.legend(frameon=False, fontsize=10, loc="upper left", ncol=3)
    ax.set_ylim(0, max(w[["0", "2", "3"]].max()) * 1.18)
    title = (f"Settled at Trenton, a hedge lowered the stand-in park's cost in {lower} of {len(w)} seasons"
             if lower else f"Settled at Trenton, neither hedge lowered the stand-in park's cost in any of {len(w)} seasons")
    fig.suptitle(title, x=0.06, ha="left", fontsize=14, color=INK, fontweight="bold")
    ax.set_title("Case B1: contracts settle at Trenton (TTN); park loss measured at Philadelphia NE gauge (PNE, 27.7 km "
                 "away; not the park).\nThe seasonal contract paid nothing in these seasons; both hedges only added "
                 "their premium.", loc="left", fontsize=10, color=INK2)
    fig.text(0.06, 0.012, NOTE + " Net cost = loss days - payout + premium. Parameters chosen on 1999-2014 only.",
             fontsize=9, color=INK2)
    fig.tight_layout(rect=(0.03, 0.04, 1, 0.94))
    path = os.path.join(OUT, "fig_b1_net_cost_by_season.png")
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)
    return path


def figure_he(m):
    cases = [("A", "A: Trenton,\nsame station (ceiling)"), ("B1", "B1: Trenton -> PNE\nstand-in (headline)"),
             ("D-same", "D: Philadelphia,\nsame station"), ("D-PNE", "D: Philadelphia -> PNE\nstand-in")]
    floor = -1.6
    fig, ax = plt.subplots(figsize=(11.5, 6.4), facecolor=SURFACE)
    style(ax)
    for ci, (cid, _) in enumerate(cases):
        for si, k in enumerate(("1", "2", "3", "4", "5")):
            v, lo, hi = get(m, cid, k)
            xpos = ci + (si - 2) * 0.16
            if v < floor:
                ax.plot([xpos], [floor + 0.08], marker=HE_MARKERS[k], color=HE_COLORS[k], markersize=9, linestyle="none",
                        markeredgecolor=SURFACE)
                ax.annotate(f"{v:.0f}\n(off scale)", (xpos, floor + 0.16), ha="center", va="bottom", fontsize=8.5, color=INK2)
                continue
            ax.plot([xpos, xpos], [max(lo, floor), hi], color=HE_COLORS[k], linewidth=2, solid_capstyle="round")
            ax.plot([xpos], [v], marker=HE_MARKERS[k], color=HE_COLORS[k], markersize=9, linestyle="none",
                    markeredgecolor=SURFACE, markeredgewidth=1.5)
            if k == "3":
                ax.annotate(f"{v:.2f}", (xpos, hi + 0.05), ha="center", va="bottom", fontsize=9.5, color=INK, fontweight="bold")
    ax.axhline(0, color=INK2, linewidth=1.2)
    ax.text(3.48, 0.03, "0 = no better than no hedge", fontsize=9, color=INK2, ha="right", va="bottom")
    ax.set_xticks(range(len(cases)))
    ax.set_xticklabels([c[1] for c in cases], fontsize=10.5, color=INK)
    ax.set_xlim(-0.5, 3.5)
    ax.set_ylim(floor, 1.25)
    ax.set_ylabel("Hedge effectiveness on REPORT seasons (1 = perfect)", color=INK, fontsize=11)
    handles = [plt.Line2D([], [], marker=HE_MARKERS[k], color=HE_COLORS[k], linestyle="none", markersize=9, label=NAMES[k])
               for k in ("1", "2", "3", "4", "5")]
    fig.legend(handles=handles, frameon=False, fontsize=9.5, loc="lower center", bbox_to_anchor=(0.5, 0.045), ncol=3)
    fig.suptitle("The seasonal contract hedges in the Philadelphia cases, is uncertain at Trenton itself,\n"
                 "and fails for a park gauge 28 km from Trenton", x=0.05, ha="left", fontsize=13.5, color=INK,
                 fontweight="bold")
    ax.set_title("Markers: point estimate. Bars: 95% interval, 2,000 bootstrap draws of whole seasons (12 seasons for "
                 "A and B1, 35 and 30 for D).\nThe Kalshi daily contract is below zero in every case. Number shown: "
                 "strategy 3.", loc="left", fontsize=10, color=INK2)
    fig.text(0.05, 0.012, NOTE + " Reference level fixed at the TRAIN mean. PNE is a stand-in gauge, not the park.",
             fontsize=9, color=INK2)
    fig.tight_layout(rect=(0.03, 0.13, 1, 0.92))
    path = os.path.join(OUT, "fig_hedge_effectiveness.png")
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)
    return path


def md_table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def summary(m, p, s, d):
    main_cases = ["A", "B1", "B2", "D-same", "D-PNE"]
    hl = []
    for c in main_cases:
        n = int(m[(m.case == c) & (m.variant == "main") & (m.window == "REPORT")].n_seasons.iloc[0])
        hl.append([c, n] + [cell(m, c, k) for k in ("1", "2", "3", "4", "5", "3_minus_2")])
    head = ["Case", "REPORT seasons", "HE 1", "HE 2", "HE 3", "HE 4", "HE 5", "HE(3) - HE(2)"]
    pd.DataFrame(hl, columns=head).assign(label="observed weather, modelled prices; value [95% interval]").to_csv(
        os.path.join(OUT, "headline_table.csv"), index=False)

    d32 = get(m, "B1", "3_minus_2")
    dD = get(m, "D-PNE", "3_minus_2")
    he3_b1, he3_b2 = get(m, "B1", "3"), get(m, "B2", "3")
    excl = (d32[1] > 0) or (d32[2] < 0)
    claim = excl and d32[0] > 0 and dD[0] > 0
    b1 = p[(p.case == "B1") & (p.variant == "main")].iloc[0]
    x = s[(s.case == "B1") & (s.variant == "main") & (s.window == "REPORT")]
    pay3 = x[x.strategy == "3"]
    dist = d.set_index("gauge")

    L = []
    A = L.append
    A("# Phase 2 results: seasonal rain-count contract versus Kalshi's daily rain contract\n")
    A("Pre-registration: docs/PHASE2_PREREG.md. Nothing was tuned after results were seen. Reading choices made before "
      "the first run are listed in docs/status/phase2_eval.md.\n")
    A("**Labels.** Rain counts (D_park, C_S, K_S) are OBSERVED station data. Every price and premium is MODELLED. "
      "Units: one loss day costs 1 (L = 1). HE = hedge effectiveness against the fixed TRAIN mean. "
      "Brackets are 95% intervals from 2,000 bootstrap draws of whole REPORT seasons (seed 473).\n")
    A("## The registered verdict\n")
    A(f"1. **The claim \"the seasonal contract beats Kalshi's\" is {'made' if claim else 'NOT made'}.** "
      f"In B1 on REPORT seasons HE(3) - HE(2) = {cell(m, 'B1', '3_minus_2', nd=3)}. "
      + ("The interval excludes zero, but on the negative side: the seasonal contract did slightly worse than the sized Kalshi position. "
         if excl and d32[0] < 0 else ("The interval includes zero. " if not excl else ""))
      + f"In case D with the stand-in the difference is {cell(m, 'D-PNE', '3_minus_2')}, the opposite sign. The two conditions are not both met.")
    A(f"2. **HE(3) is not above zero in case B.** B1: {cell(m, 'B1', '3')}. B2: {cell(m, 'B2', '3')}. "
      f"In the pre-registration's words: the product does not hedge a park 11-30 km away, and location basis is the finding. "
      f"Here the stand-in gauges are {dist.loc['PNE', 'km_to_TTN']} km (PNE) and {dist.loc['DYL', 'km_to_TTN']} km (DYL) from Trenton.")
    A(f"3. **Strategy 5 (shape versus timing and markup).** In B1 no contract shape helps: HE(5) = {cell(m, 'B1', '5')}, also below zero. "
      f"Where the seasonal contract does work (D with stand-in), the gap HE(3) - HE(2) = {cell(m, 'D-PNE', '3_minus_2')} splits into "
      f"{cell(m, 'D-PNE', '3_minus_5')} from contract shape (HE(3) - HE(5)) and {cell(m, 'D-PNE', '5_minus_2')} from timing and markup (HE(5) - HE(2)).\n")
    A("In B1 both hedges are close to empty positions. The TRAIN rule chose the smallest allowed Kalshi size (n = 0.05) and the "
      "largest allowed deductible (d = 8), because no choice gave a positive TRAIN hedge effectiveness. "
      f"The seasonal contract then paid in {int((pay3.payout > 0).sum())} of {len(pay3)} REPORT seasons. "
      "The B1 difference compares two premium drags. It does not show that Kalshi's contract hedges the park.\n")

    A("## Headline table (REPORT seasons; observed weather, modelled prices)\n")
    A(md_table(head, hl) + "\n")
    A("Strategies: 1 Kalshi daily, one contract per day. 2 Kalshi daily, sized n. 3 seasonal, six buckets (the product). "
      "4 seasonal, exact payout (benchmark). 5 Kalshi daily at the fair-comparison price, sized n. "
      "A is circular by construction (a ceiling). The stand-in gauge is not the park.\n")

    A("## TRAIN-chosen parameters, headline case B1 (TRAIN 1999-2014, 16 seasons)\n")
    A(md_table(["Parameter", "Value", "Label"], [
        ["Reference level (TRAIN mean of D_park)", f"{b1.train_reference_mean_D_park:.3f}", "observed"],
        ["n, strategy 2", b1.n_strategy2, "chosen on TRAIN; smallest value in the grid"],
        ["n, strategy 5", b1.n_strategy5, "chosen on TRAIN; smallest value in the grid"],
        ["Bucket upper edges e1..e5", b1.edges, "observed TRAIN counts; no repair needed"],
        ["m_j", b1.m_j, "observed"], ["TRAIN seasons per bucket", b1.train_bucket_counts_n_j, "observed"],
        ["q_j (add-half)", b1.q_j, "modelled"],
        ["d, strategy 3", b1.d_strategy3, "chosen on TRAIN; largest value in the grid"],
        ["h_j", b1.h_j, "holding"], ["Premium, strategy 3 (loading 0.20)", f"{b1.premium_strategy3:.4f} per season", "modelled"],
        ["d and premium, strategy 4", f"{b1.d_strategy4}; {b1.premium_strategy4:.4f}", "modelled"],
        ["Monthly p (May..Sep)", b1.p_month, "observed TRAIN frequency"],
        ["TRAIN HE, in-sample", b1.train_HE_in_sample, "in-sample"]]) + "\n")
    A("All cases and variants: results/phase2/train_params.csv.\n")

    A("## Case B1 in money terms (REPORT 2015-2026, 12 seasons; observed weather, modelled prices)\n")
    rows = []
    for k in ("0", "2", "3", "4", "5"):
        tp, pu = get(m, "B1", k, "total_premium")[0], get(m, "B1", k, "premium_per_useful_payout")
        useful = float(np.minimum(x[x.strategy == k].payout, x[x.strategy == k].D_park).sum())
        ratio = "no hedge" if k == "0" else (f"undefined (premium {tp:.2f}, useful payout 0)" if useful == 0 else cell(m, "B1", k, "premium_per_useful_payout"))
        rows.append([NAMES[k], cell(m, "B1", k, "mean_net_cost"), cell(m, "B1", k, "mean_premium"), cell(m, "B1", k, "mean_payout"),
                     ratio, cell(m, "B1", k, "worst_mean_hedged"), cell(m, "B1", k, "sd_net_cost"), cell(m, "B1", k, "share_seasons_reduced")])
    A(md_table(["Strategy", "Mean net cost", "Mean premium", "Mean payout", "Premium per $1 useful payout",
                "Mean cost, worst 3 seasons", "SD of net cost", "Share of seasons with lower cost"], rows) + "\n")
    A("Per-season values: results/phase2/season_net_cost.csv. Figure: results/phase2/fig_b1_net_cost_by_season.png.\n")

    A("## Shape versus timing and markup (strategy 5; REPORT seasons)\n")
    A(md_table(["Case", "HE(3) - HE(2), total gap", "HE(3) - HE(5), contract shape", "HE(5) - HE(2), timing and markup",
                "HE(3) - HE(4), cost of bucketing"],
               [[c] + [cell(m, c, k) for k in ("3_minus_2", "3_minus_5", "5_minus_2", "3_minus_4")] for c in main_cases]) + "\n")
    A("Removing the market's forecast information, spread and fees lifts the Kalshi position by about 0.2 to 0.4 in every case, "
      "but it stays below zero everywhere. Away from B, most of the gap is contract shape.\n")

    A("## Misspecification (case C; REPORT seasons; contract stays at 0.25 inch, 10:00-18:00, all days)\n")
    crow = []
    text = {"c1": ">= 0.10 inch", "c2": ">= 0.50 inch", "c3": "10:00-20:00", "c4": "10:00-16:00", "c5": "weekends and holidays only"}
    for key in ("c1", "c2", "c3", "c4", "c5"):
        for where in ("TTN", "B1"):
            c = f"C-{key}-{where}"
            crow.append([c, text[key], "Trenton same station" if where == "TTN" else "B1 stand-in (PNE)",
                         cell(m, c, "3", window="TRAIN"), cell(m, c, "2"), cell(m, c, "3"), cell(m, c, "3_minus_2")])
    A(md_table(["Case", "Park's true loss day", "Where", "HE 3 on TRAIN (in-sample)", "HE 2", "HE 3", "HE(3) - HE(2)"], crow) + "\n")
    npos = sum(get(m, f"C-{k}-{w}", "3")[0] > 0 for k in text for w in ("TTN", "B1"))
    A(f"HE(3) is above zero in {npos} of 10 misspecification runs on REPORT seasons. At Trenton itself the in-sample values are high "
      "(0.63 to 0.75 for c1-c4) and the REPORT values are not. With 12 REPORT seasons the intervals are very wide. "
      "The weekend-only park (c5) is hurt badly by an all-days contract: it pays a premium for rain on days it does not lose money.\n")

    A("## Case E, Allentown same station (no Kalshi market; strategies 0, 3, 4)\n")
    A(md_table(["Run", "TRAIN / REPORT seasons", "HE 3", "HE 4", "Mean net cost: none / 3", "Premium per $1 useful payout, 3"],
               [[c, f"{int(p[(p.case == c) & (p.variant == 'main')].n_train_seasons.iloc[0])} / "
                    f"{int(m[(m.case == c) & (m.variant == 'main') & (m.window == 'REPORT')].n_seasons.iloc[0])}",
                 cell(m, c, "3"), cell(m, c, "4"), cell(m, c, "0", "mean_net_cost") + " / " + cell(m, c, "3", "mean_net_cost"),
                 cell(m, c, "3", "premium_per_useful_payout")] for c in ("E", "E-trenton-windows")]) + "\n")
    A("The pre-registration names no window for E. E uses the Philadelphia windows (TRAIN 1948-1990, REPORT 1991-2026). "
      "E-trenton-windows is a sensitivity, not a registered case. E is same-station, so it is a ceiling like A.\n")

    A("## Registered sensitivities (REPORT seasons)\n")
    vr = []
    for c in ("A", "B1", "B2", "D-same", "D-PNE"):
        for v in ("main", "loading_0.10", "loading_0.30", "markup_0.068", "edges_linear_floor"):
            pr = p[(p.case == c) & (p.variant == v)].iloc[0]
            vr.append([c, v, pr.n_strategy2, pr.edges, pr.d_strategy3, cell(m, c, "2", variant=v), cell(m, c, "3", variant=v),
                       cell(m, c, "3_minus_2", variant=v)])
    A(md_table(["Case", "Variant", "n (2)", "Edges", "d (3)", "HE 2", "HE 3", "HE(3) - HE(2)"], vr) + "\n")
    A("loading_0.10 and loading_0.30 change strategies 3, 4, 5. markup_0.068 changes strategies 1 and 2. "
      "edges_linear_floor is the alternative reading of the quantile rule (not registered wording; shown because the rule was ambiguous). "
      f"Under it the B1 difference is {cell(m, 'B1', '3_minus_2', variant='edges_linear_floor')}: the sign flips and the interval includes zero. "
      "HE(3) in B1 is below zero in every variant. Philadelphia without the doubtful seasons 1941-47: "
      f"HE(3) = {cell(m, 'D-same-ex4147', '3')}, HE(3) - HE(2) = {cell(m, 'D-same-ex4147', '3_minus_2')}.\n")

    A("## Stand-in gauges (observed coordinates)\n")
    A(md_table(["Gauge", "km to Sesame Place", "km to Trenton (TTN)", "km to Philadelphia Intl (PHL)"],
               [[f"{g} ({dist.loc[g, 'name']})", dist.loc[g, "km_to_sesame_place"], dist.loc[g, "km_to_TTN"], dist.loc[g, "km_to_PHL"]]
                for g in ("PNE", "DYL", "TTN")]) + "\n")
    A("The stand-in is not the park. Sesame Place is 11.3 km from Trenton; the stand-ins are 27 to 28 km from Trenton. "
      "Usable seasons: PNE 36 (1974, 1977-79, 1987-88, 1997-2026); DYL 26 (2000-2024, 2026). "
      "File: results/phase2/standin_distances.csv.\n")

    agg = pd.read_csv(os.path.join(ROOT, "data", "processed", "hedge", "season_aggregates.csv"))
    def corr(c, w):
        y = agg[(agg.case == c) & (agg.window == w)]
        return float(np.corrcoef(y.D_park, y.C_S)[0, 1])
    A("## Things a sceptical reader should know\n")
    A(f"1. **Small sample.** Trenton cases have 12 REPORT seasons (B2 has 11) and 16 TRAIN seasons (B2 15). "
      f"The ceiling case A has HE(3) = {cell(m, 'A', '3')}: the interval runs from clearly harmful to very good. "
      f"Only the Philadelphia and Allentown cases (30 to 35 REPORT seasons) have strategy 3 intervals that stay above zero.")
    A(f"2. **B1 compares two near-empty hedges.** n = 0.05 is the bottom of the registered grid (zero was not allowed) and d = 8 is the top. "
      f"On TRAIN the best seasonal contract had HE = {json.loads(b1.train_HE_in_sample)['3']:.2f}, so the product failed for this gauge even in-sample. "
      f"The seasonal contract paid nothing in 2015-2026, so its premium per $1 of useful payout is undefined (premium paid {get(m, 'B1', '3', 'total_premium')[0]:.2f}, payout 0). "
      f"The B1 difference of {d32[0]:.3f} is the difference between two small premiums, measured against a fixed reference.")
    A(f"3. **Why the stand-in fails.** Season counts at Trenton and at PNE correlate {corr('B1', 'TRAIN'):.2f} on TRAIN and {corr('B1', 'REPORT'):.2f} on REPORT "
      f"(Doylestown: {corr('B2', 'TRAIN'):.2f} and {corr('B2', 'REPORT'):.2f}). That is too weak for a count contract with a 20% loading to pay for itself. "
      f"Also, PNE had more loss days in REPORT (mean {get(m, 'B1', '0', 'mean_net_cost')[0]:.2f}) than in TRAIN ({b1.train_reference_mean_D_park:.2f}); "
      "with the reference fixed at the TRAIN mean, any premium is punished harder in REPORT.")
    A("4. **What the stand-in does and does not prove.** It shows that rain counts 27-28 km apart differ enough to defeat this contract. "
      "It does not measure the park: Sesame Place is 11.3 km from Trenton, closer than either stand-in, and no gauge at the park was available. "
      "The true basis for the park is probably smaller than in B1 and B2, but it is unmeasured. The result is a warning, not a measurement of the park's hedge.")
    A(f"5. **Case D with the stand-in rests on 6 TRAIN seasons.** PNE has only 1974, 1977-79 and 1987-88 before 1991. Edges from six seasons needed the tie repair "
      f"(raw quantiles {p[(p.case == 'D-PNE') & (p.variant == 'main')].edges_raw_quantiles.iloc[0]} became {p[(p.case == 'D-PNE') & (p.variant == 'main')].edges.iloc[0]}). "
      f"HE(3) = {cell(m, 'D-PNE', '3')}. A non-registered sensitivity that takes the buckets from all 50 Philadelphia TRAIN seasons (and so picks d = "
      f"{int(p[(p.case == 'D-PNE-phl-buckets') & (p.variant == 'main')].d_strategy3.iloc[0])}) gives HE(3) = {cell(m, 'D-PNE-phl-buckets', '3')} "
      f"and HE(3) - HE(2) = {cell(m, 'D-PNE-phl-buckets', '3_minus_2')}. The positive D stand-in result is fragile. It depends on the deductible, which six seasons chose. "
      f"Its premium was also set from those six seasons ({get(m, 'D-PNE', '3', 'mean_premium')[0]:.2f} a season) and came out below the mean REPORT payout "
      f"({get(m, 'D-PNE', '3', 'mean_payout')[0]:.2f}), so part of its score is a premium that turned out too low.")
    A(f"6. **Timing and markup versus shape.** Pricing Kalshi's contract like the seasonal one (strategy 5) recovers {cell(m, 'B1', '5_minus_2')} of HE in B1, "
      f"{cell(m, 'A', '5_minus_2')} in A and {cell(m, 'D-PNE', '5_minus_2')} in D with stand-in. The rest of the gap is shape: a daily 0.01-inch contract pays on about 35 days "
      "a season of which about 5 are loss days. Even at a fair-comparison price it is below zero in every case.")
    A(f"7. **Kalshi daily is never a hedge here.** One contract per day (strategy 1) costs about {get(m, 'B1', '1', 'mean_premium')[0]:.0f} a season in modelled premium against about "
      f"{get(m, 'B1', '0', 'mean_net_cost')[0]:.1f} loss days; HE is -20 or worse. The TRAIN rule always shrinks it to the smallest size. "
      "The Kalshi price is modelled from 381 real quotes in 2025-2026, not observed for these seasons; the model probably still overstates Kalshi's seasonal protection (docs/status/phase1_kalshi.md, limit 3).")
    A(f"8. **Misspecification.** The conclusion that the seasonal contract helps does not survive it on Trenton REPORT seasons: HE(3) is above zero in {npos} of 10 runs. "
      "The conclusion that the Kalshi daily contract does not help survives everywhere: HE(2) is below zero in all 10 runs. "
      "HE(3) - HE(2) is positive at Trenton same-station for c1-c4 but every interval includes zero.")
    A("9. **The metric is harsh on premiums by design.** The reference is the TRAIN mean of unhedged cost. A hedge with a steady premium must pay out in bad seasons to score above zero. "
      "Mean net cost is higher under every hedge in every Trenton case, as expected with a positive loading.")
    A("10. **Bootstrap limits.** Seasons are resampled as independent. Some draws have no season above the reference; those draws are dropped and counted (column n_boot_valid). "
      "TRAIN-window numbers are in-sample and have no interval.\n")
    A("## Files\n")
    A("- metrics_tidy.csv: every case x variant x strategy x window x metric with its interval.\n- train_params.csv: TRAIN-chosen parameters per case and variant.\n"
      "- season_net_cost.csv: per-season counts, payout, premium, net cost.\n- headline_table.csv, standin_distances.csv.\n"
      "- fig_b1_net_cost_by_season.png, fig_hedge_effectiveness.png.\n\n## Deviations from the pre-registration\n\n"
      "None forced. Additions that are not registered and are labelled as such: runs E-trenton-windows and D-PNE-phl-buckets; variant edges_linear_floor; "
      "strategy 5n; the differences HE(3) - HE(5), HE(5) - HE(2), HE(3) - HE(4).")
    with open(os.path.join(OUT, "summary.md"), "w") as f:
        f.write("\n".join(L) + "\n")


if __name__ == "__main__":
    m, p, s, d = load()
    print(figure_net_cost(m, p, s))
    print(figure_he(m))
    summary(m, p, s, d)
    print(os.path.join(OUT, "summary.md"))
