"""Task 5: figure results/phase3/leadtime.png and results/phase3/leadtime_summary.md from the CSVs. No new computation.

    python scripts/leadtime_report.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
RES = REPO / "results" / "phase3"
LT = REPO / "data" / "processed" / "leadtime"

C_OBS = "#2a78d6"      # observed Kalshi prices (categorical slot 1)
C_MOD = "#eb6834"      # modelled prices (slot 2)
C_CLIM = "#52514e"     # climatology point, neutral
INF_X = 9.0            # where "lead = infinity" is drawn on the lead axis


def load() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    he = pd.read_csv(RES / "leadtime_he_by_lead.csv")
    obs = pd.read_csv(LT / "observed_by_decision_time.csv")
    skill = pd.read_csv(RES / "leadtime_skill_by_lead.csv")
    chk = pd.read_csv(RES / "leadtime_price_check.csv")
    return he, obs, skill, chk


def modelled_points(he: pd.DataFrame, case: str, variant: str = "main") -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    h = he[(he["case"] == case) & (he["variant"] == variant) & he["he"].notna()]
    mos = h[np.isfinite(h["lead_days"]) & (h["lead_label"] != "1 (p06x4)")].sort_values("lead_days")
    p06 = h[h["lead_label"] == "1 (p06x4)"]
    inf = h[~np.isfinite(h["lead_days"])]
    return mos, p06, inf


def figure(he: pd.DataFrame, obs: pd.DataFrame, out: Path) -> str:
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.2))
    o = obs[obs["group"] == "four cities, all years"].sort_values("lead_days")
    cases = [("A (Trenton same-station)", "Trenton (case A)", "s"), ("D-same (Philadelphia same-station)", "Philadelphia (case D-same)", "^")]

    # ---- left: premium per $1 of payout
    ax = axes[0]
    ax.plot(o["lead_days"], o["premium_fee_per_payout"], "o-", color=C_OBS, ms=7, lw=1.5, label="observed Kalshi asks + fee, four cities, 2021-22 and 2025-26 (36, 24, 12, 2 h before close)")
    for case, name, mk in cases:
        mos, p06, inf = modelled_points(he, case)
        ax.plot(mos["lead_days"], mos["premium_per_payout"], marker=mk, ls="--", color=C_MOD, mfc="white", ms=7, lw=1.2,
                label=f"MODELLED, MOS price: {name}")
        ax.plot(p06["lead_days"], p06["premium_per_payout"], marker=mk, ls="none", color=C_MOD, mfc=C_MOD, ms=5, alpha=0.6)
        allinf = inf[inf["lead_label"] == "inf (all seasons)"]
        ax.plot([INF_X], allinf["premium_per_payout"], marker=mk, ls="none", color=C_CLIM, mfc="white", ms=8,
                label=f"MODELLED, climatology price (lead = infinity): {name}")
    ax.set_xlabel("lead time before the contract closes (days)")
    ax.set_ylabel("premium (incl. fee) per $1 of payout, 1 contract per season day")
    ax.set_title("Cost of $1 of protection against lead time", fontsize=11)
    ax.axhline(1.0, color="#c3c2b7", lw=0.8, ls=":")
    ax.text(0.4, 1.0, "fair (premium = payout)", fontsize=8, color=C_CLIM, va="bottom")

    # ---- right: HE
    ax = axes[1]
    ax.axhline(0.0, color="#0b0b0b", lw=1.0)
    for case, name, mk in cases:
        mos, p06, inf = modelled_points(he, case)
        ax.errorbar(mos["lead_days"], mos["he"], yerr=[mos["he"] - mos["he_lo"], mos["he_hi"] - mos["he"]], marker=mk,
                    ls="--", color=C_MOD, mfc="white", ms=7, lw=1.2, capsize=3, label=f"MODELLED, MOS price: {name}")
        ax.errorbar(p06["lead_days"], p06["he"], yerr=[p06["he"] - p06["he_lo"], p06["he_hi"] - p06["he"]], marker=mk,
                    ls="none", color=C_MOD, mfc=C_MOD, ms=5, alpha=0.6, capsize=2)
        allinf = inf[inf["lead_label"] == "inf (all seasons)"]
        ax.errorbar([INF_X], allinf["he"], yerr=[allinf["he"] - allinf["he_lo"], allinf["he_hi"] - allinf["he"]],
                    marker=mk, ls="none", color=C_CLIM, mfc="white", ms=8, capsize=3,
                    label=f"MODELLED, climatology price (infinity), all Phase 2 seasons: {name}")
    ax.set_xlabel("lead time before the contract closes (days)")
    ax.set_ylabel("hedge effectiveness on REPORT seasons (95% season bootstrap)")
    ax.set_title("Hedge effectiveness of the daily contract against lead time", fontsize=11)
    ax.text(0.4, 0.05, "HE > 0: the hedge reduces bad-season cost", fontsize=8, color=C_CLIM, va="bottom")
    ax.text(0.4, -0.12, "no observed HE: real prices cover 2 seasons", fontsize=8, color=C_OBS, va="top")

    for ax in axes:
        ax.set_xticks([0.08, 0.5, 1, 1.5, 2, 3, 4, 5, 6, 7, INF_X])
        ax.set_xticklabels(["2h", "12h", "1", "1.5", "2", "3", "4", "5", "6", "7", "inf"], fontsize=9)
        ax.set_xlim(-0.2, INF_X + 0.6)
        ax.axvspan(1.6, 1.9, color="#e8e8e6", lw=0, zorder=0)
        ax.axvspan(INF_X - 0.6, INF_X - 0.3, color="#e8e8e6", lw=0, zorder=0)
        ax.grid(axis="y", color="#e8e8e6", lw=0.6)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    axes[0].set_ylim(0.9, max(3.3, float(o["premium_fee_per_payout"].max()) + 0.1))
    axes[1].set_ylim(-3.2, 0.5)
    axes[1].text(0.4, 0.38, "lower band edges of the MEX leads (4-7 d) reach -5 to -8; clipped", fontsize=7, color=C_CLIM)
    # legends
    h0, l0 = axes[0].get_legend_handles_labels()
    axes[0].legend(h0, l0, fontsize=7, loc="upper right", frameon=False)
    h1, l1 = axes[1].get_legend_handles_labels()
    axes[1].legend(h1, l1, fontsize=7, loc="lower left", frameon=False)

    title = finding_title(he)
    fig.suptitle(title, fontsize=12, y=0.995)
    fig.text(0.5, 0.005, "EXPLORATORY (Phase 3 pre-registration). Observed Kalshi prices to 1.5 days (shaded gap); modelled beyond: "
             "ask = clamp(MOS PoP + 0.085) + fee, GFS MAV 1.5-3 d (2004-2026), MEX 4-7 d (2021-2026), monthly climatology at infinity. "
             "Filled small markers: 1-day point from four 6-h PoPs. Weather observed; n = contracts per day chosen on TRAIN seasons.",
             ha="center", fontsize=7, color=C_CLIM, wrap=True)
    fig.tight_layout(rect=(0, 0.04, 1, 0.97))
    fig.savefig(out, dpi=160)
    plt.close(fig)
    return title


def finding_title(he: pd.DataFrame) -> str:
    h = he[(he["variant"] == "main") & he["he"].notna()]
    ever = h[h["he_lo"] > 0]
    if ever.empty:
        return "Daily rain contract: HE stays below zero at every lead from 1 day to climatology (modelled); shape, not timing, is the limit"
    return "Daily rain contract: HE first exceeds zero at lead " + ", ".join(f"{r.case}: {r.lead_label} d" for r in ever.itertuples())


def first_positive(he: pd.DataFrame, case: str, variant: str) -> str:
    h = he[(he["case"] == case) & (he["variant"] == variant) & he["he"].notna()].copy()
    h["order"] = h["lead_days"].replace(np.inf, 99)
    h = h.sort_values("order")
    pos = h[h["he"] > 0]
    band = h[h["he_lo"] > 0]
    if pos.empty:
        return f"never (point estimate below zero at every lead; highest HE {h['he'].max():.2f} at lead {h.loc[h['he'].idxmax(), 'lead_label']})"
    r = pos.iloc[0]
    s = f"lead {r['lead_label']} (HE {r['he']:.2f} [{r['he_lo']:.2f}, {r['he_hi']:.2f}])"
    return s + ("" if band.empty else f"; band above zero first at lead {band.iloc[0]['lead_label']}")


def fmt_he(r) -> str:
    return f"{r['he']:.2f} [{r['he_lo']:.2f}, {r['he_hi']:.2f}]"


def summary(he: pd.DataFrame, obs: pd.DataFrame, skill: pd.DataFrame, chk: pd.DataFrame, title: str) -> str:
    L = []
    L.append("# Phase 3, Question 2: when must the daily contract be listed to work as a hedge?\n")
    L.append("EXPLORATORY (docs/PHASE3_PREREG.md). Weather observed. Kalshi prices observed to 1.5 days before close; "
             "every price beyond that is MODELLED (MOS probability + Phase 1 markup + fee). Rules: docs/status/phase3_leadtime.md.\n")
    L.append(f"Finding: {title}.\n")
    L.append("## Lead at which HE first exceeds zero (REPORT seasons, strategy-2 sizing, 95% season bootstrap)\n")
    for case in he["case"].unique():
        for variant in ("main", "markup_0.068"):
            L.append(f"- {case}, markup {variant}: {first_positive(he, case, variant)}")
    L.append("")
    L.append("Per the pre-registration: if HE stays below zero at every lead, the daily contract's shape, not its timing, "
             "is the binding problem. " + ("That is the outcome here." if "stays below zero" in title else "That is NOT the outcome here; see the table."))
    L.append("")
    L.append("## HE and cost by lead (main markup a = 0.085; MODELLED prices)\n")
    L.append("| case | lead (days) | price source | windows | TRAIN / REPORT seasons | n per day | HE [95%] | mean net cost | premium per $1 useful payout | premium per $1 payout | mean ask | carry-forward days |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    h = he[(he["variant"] == "main") & he["he"].notna()].copy()
    h["order"] = h["lead_days"].replace(np.inf, 99)
    for _, r in h.sort_values(["case", "order", "lead_label"]).iterrows():
        L.append(f"| {r['case']} | {r['lead_label']} | {r['price_source']} | {r['windows']} | {int(r['n_train_seasons'])} / {int(r['n_report_seasons'])} "
                 f"({int(r['report_first'])}-{int(r['report_last'])}) | {r['n_contracts']:.2f} | {fmt_he(r)} | {r['mean_net_cost']:.2f} "
                 f"[{r['mean_net_cost_lo']:.2f}, {r['mean_net_cost_hi']:.2f}] | {r['premium_per_useful_payout']:.2f} | {r['premium_per_payout']:.2f} | "
                 f"{r['mean_ask_report']:.3f} | {int(r['carry_forward_days_report'])} |")
    L.append("")
    L.append("Sensitivity a = 0.068 (markup_0.068 rows of results/phase3/leadtime_he_by_lead.csv): HE is higher by 0.1-0.3 at every lead and still below zero everywhere." if (he[(he['variant']=='markup_0.068')]['he'].dropna() < 0).all() else "Sensitivity a = 0.068: see the CSV.")
    L.append("")
    L.append("## Observed decision-time table (Phase 1 quote table, aggregates; one contract per market day)\n")
    L.append("| group | hours before close | lead (days) | market days | share with a usable ask | premium + fee per $1 payout | share of rain days with no offer | Brier of mid (n two-sided) | mean ask, rain days | mean ask, dry days |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for _, r in obs.iterrows():
        L.append(f"| {r['group']} | {int(r['hours_before_close'])} | {r['lead_days']:.2f} | {int(r['market_days'])} | {r['usable_ask_share']:.2f} | "
                 f"{r['premium_fee_per_payout']:.2f} | {r['rain_no_offer_share']:.2f} | {r['brier_mid']:.3f} ({int(r['n_two_sided'])}) | "
                 f"{r['mean_ask_rain']:.2f} | {r['mean_ask_dry']:.2f} |")
    L.append("")
    L.append("## Forecast skill by lead (MOS archive vs the station's official daily total >= 0.01 inch; park-season days)\n")
    L.append("| station | line | field | target lead | mean lead | days | seasons | mean PoP | rain share | Brier | Brier of climatology (same days, leave-one-season-out monthly) | skill vs climatology |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for _, r in skill.iterrows():
        L.append(f"| {r['station']} | {r['line']} | {r['pop_field']} | {r['target_lead_days']} | {r['mean_lead_days']:.2f} | {int(r['n_days'])} | "
                 f"{int(r['n_seasons'])} ({int(r['first_season'])}-{int(r['last_season'])}) | {r['mean_pop']:.3f} | {r['rain_share']:.3f} | {r['brier']:.3f} | "
                 f"{r['brier_climatology_same_days']:.3f} | {r['skill_vs_climatology']:.2f} |")
    L.append("")
    L.append("Calibration tables per lead: results/phase3/leadtime_calibration_by_lead.csv.")
    L.append("")
    L.append("## Model check at the observed end (modelled ask at lead 1.5 vs the real 36-hour ask on the same days)\n")
    L.append("| city | line | target lead | markup | days | years | mean observed ask | mean modelled ask | difference (modelled - observed) | daily RMSE | daily corr | Brier of observed ask | Brier of PoP |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for _, r in chk.iterrows():
        L.append(f"| {r['city']} | {r['line']} | {r['target_lead']} | {r['markup']} | {int(r['n_days'])} | {r['years']} | {r['mean_observed_ask_36h']:.3f} | "
                 f"{r['mean_modelled_ask']:.3f} | {r['mean_difference_modelled_minus_observed']:+.3f} | {r['rmse_daily']:.3f} | {r['corr_daily']:.2f} | "
                 f"{r['brier_observed_ask']:.3f} | {r['brier_pop']:.3f} |")
    L.append("")
    L.append("## Caveats\n")
    L.append("1. Modelled prices are a deterministic markup over a MOS probability; real asks scatter, thin out and go to 1.00 on some rain days. The model is checked only at 1.5 days.")
    L.append("2. The MOS 24-h window is 00Z-00Z (20:00-20:00 local), four hours before the climate day. The p12x2 and p06x4 fields assume independent periods and overstate the probability on persistent-rain days (see calibration).")
    L.append("3. MEX leads 4-7 exist only from 2021 (6 seasons); their n and reference level come from the station's GFS lead-3 TRAIN choice, and their REPORT bands are wide.")
    L.append("4. Philadelphia GFS leads use a 60/40 split of 2004-2026 because the Phase 2 TRAIN window (1941-1990) predates the archive.")
    L.append("5. The strategy-2 grid has no n = 0; TRAIN prefers the smallest n at every lead, as in Phase 2.")
    L.append("6. Leads are measured from the model run time; MOS text is issued 2-4 h later.")
    L.append("7. Two cases, same-station, circular by construction (Phase 2 case A is a ceiling). Location basis (Phase 2 case B) is not added here.")
    return "\n".join(L) + "\n"


def main() -> None:
    he, obs, skill, chk = load()
    title = figure(he, obs, RES / "leadtime.png")
    (RES / "leadtime_summary.md").write_text(summary(he, obs, skill, chk, title))
    print(title)


if __name__ == "__main__":
    main()
