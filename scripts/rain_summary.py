"""Summary table and figure for the rain workstream (SPEC_v3 Phase 1, deliverable 6). Observed station data only.

    python scripts/rain_summary.py

Reads   data/processed/rain/season_counts_cases_<SID>.csv, season_counts_<SID>.csv
Writes  results/rain/summary_by_case.csv        per station x calendar x threshold x window, usable seasons only
        results/rain/summary_main.md            the main case and the reference check, as a readable table
        results/rain/loss_vs_kalshi_days.png    Trenton, per season: Kalshi-pay days and loss days
No hedge evaluation here (Phase 2).
"""
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "processed", "rain")
OUT = os.path.join(ROOT, "results", "rain")
STATIONS = ("TTN", "PHL", "ABE")
REPORT_FROM = 2015  # SPEC: train to 2014, report 2015-2026


def summarise(x, label):
    """x: season rows of one case (usable seasons only)."""
    paid, loss = x["kalshi_pay_days"].sum(), x["loss_days"].sum()
    r = dict(
        seasons_set=label, n_seasons=len(x), first_season=int(x["season"].min()), last_season=int(x["season"].max()),
        days_per_season=round(x["days"].mean(), 1), usable_days=int(x["usable_days"].sum()), days_unusable=int(x["days_unusable"].sum()),
        loss_days_mean=round(x["loss_days"].mean(), 2), loss_days_min=int(x["loss_days"].min()), loss_days_max=int(x["loss_days"].max()),
        kalshi_pay_days_mean=round(x["kalshi_pay_days"].mean(), 2), kalshi_pay_days_min=int(x["kalshi_pay_days"].min()),
        kalshi_pay_days_max=int(x["kalshi_pay_days"].max()),
        share_kalshi_pay_days_not_loss=round(x["paid_not_loss"].sum() / paid, 4) if paid else None,
        share_loss_days_kalshi_pays=round(x["loss_and_paid"].sum() / loss, 4) if loss else None,
        loss_not_paid_days=int(x["loss_not_paid"].sum()),
        usable_days_climate_day_incomplete=int(x["usable_days_climate_day_incomplete"].sum()),
    )
    if "ref_ghcn_pay_days" in x:
        g = x["ref_ghcn_pay_days"].sum()
        r.update(
            ref_ghcn_pay_days_mean=round(x["ref_ghcn_pay_days"].mean(), 2),
            ref_share_ghcn_pay_days_not_loss=round(x["ref_ghcn_paid_not_loss"].sum() / g, 4) if g else None,
            ref_share_loss_days_ghcn_pays=round(x["ref_loss_and_ghcn_paid"].sum() / loss, 4) if loss else None,
            ref_usable_days_ghcn_missing=int(x["ref_usable_days_ghcn_missing"].sum()),
        )
    return r


def build_summary():
    rows = []
    for sid in STATIONS:
        c = pd.read_csv(os.path.join(DATA, f"season_counts_cases_{sid}.csv"))
        c = c[c["season_usable"]]
        for (variant, thr, win), x in c.groupby(["calendar", "threshold_in", "window"]):
            main = variant == "all_days" and thr == 0.25 and win == "10:00-18:00"
            sets = [("all usable seasons", x)]
            if main:
                sets += [("train (to 2014)", x[x.season < REPORT_FROM]), (f"report ({REPORT_FROM}-2026)", x[x.season >= REPORT_FROM]),
                         ("1999-2026 (Trenton's seasons)", x[x.season >= 1999])]
            for label, y in sets:
                r = dict(station=sid, case="SPEC main" if main else "sensitivity", calendar=variant, threshold_in=thr, window=win)
                r.update(summarise(y, label))
                rows.append(r)
    return pd.DataFrame(rows)


def write_markdown(S):
    m = S[(S.case == "SPEC main")]
    lines = [
        "# Rain workstream: loss days vs Kalshi-pay days (observed station data)",
        "",
        "Main case per SPEC_v3: every day from the Friday before Memorial Day through Labor Day; loss day = at least",
        "0.25 inch between 10:00 and 18:00 local clock time; Kalshi pays when the climate-day total is at least 0.01 inch.",
        "Usable seasons only; unusable days are dropped and counted. Shares are pooled over seasons.",
        "",
        "| Station | Seasons | N | Loss days per season: mean (min-max) | Kalshi-pay days per season: mean (min-max) | Kalshi-pay days that are not loss days | Loss days Kalshi pays on | Days dropped |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in m.itertuples():
        lines.append(
            f"| {r.station} | {r.seasons_set}, {r.first_season}-{r.last_season} | {r.n_seasons} | {r.loss_days_mean:.2f} ({r.loss_days_min}-{r.loss_days_max}) | "
            f"{r.kalshi_pay_days_mean:.2f} ({r.kalshi_pay_days_min}-{r.kalshi_pay_days_max}) | {100 * r.share_kalshi_pay_days_not_loss:.1f}% | "
            f"{100 * r.share_loss_days_kalshi_pays:.1f}% | {r.days_unusable} of {r.usable_days + r.days_unusable} |"
        )
    lines += [
        "",
        "Reference check (not the SPEC flag): the same rule applied to the GHCN-Daily total instead of the hourly sum.",
        "",
        "| Station | Seasons | Kalshi-pay days per season, hourly rule | Same, GHCN-Daily total | Pay days not loss days, GHCN | Loss days paid, GHCN | Usable days without a GHCN value |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in m[m.seasons_set == "all usable seasons"].itertuples():
        lines.append(
            f"| {r.station} | {r.first_season}-{r.last_season} | {r.kalshi_pay_days_mean:.2f} | {r.ref_ghcn_pay_days_mean:.2f} | "
            f"{100 * r.ref_share_ghcn_pay_days_not_loss:.1f}% | {100 * r.ref_share_loss_days_ghcn_pays:.1f}% | {r.ref_usable_days_ghcn_missing} |"
        )
    lines += ["", "Sensitivity cases (all usable seasons): see summary_by_case.csv. Extract:", "",
              "| Station | Calendar | Threshold | Window | Loss days: mean (min-max) | Kalshi-pay days: mean | Pay days not loss days | Loss days paid |",
              "|---|---|---|---|---|---|---|---|"]
    s = S[S.seasons_set == "all usable seasons"]
    for r in s.itertuples():
        lines.append(
            f"| {r.station} | {r.calendar} | {r.threshold_in:.2f} | {r.window} | {r.loss_days_mean:.2f} ({r.loss_days_min}-{r.loss_days_max}) | "
            f"{r.kalshi_pay_days_mean:.2f} | {100 * r.share_kalshi_pay_days_not_loss:.1f}% | "
            + (f"{100 * r.share_loss_days_kalshi_pays:.1f}% |" if pd.notna(r.share_loss_days_kalshi_pays) else "n/a |")
        )
    with open(os.path.join(OUT, "summary_main.md"), "w") as fh:
        fh.write("\n".join(lines) + "\n")


def figure(S):
    c = pd.read_csv(os.path.join(DATA, "season_counts_TTN.csv"))
    c = c[(c.calendar == "all_days") & c.season_usable].sort_values("season")
    r = S[(S.station == "TTN") & (S.case == "SPEC main") & (S.seasons_set == "all usable seasons")].iloc[0]
    blue, orange, ink, muted = "#3b6ea5", "#d1603d", "#1f2933", "#5b6770"
    fig, ax = plt.subplots(figsize=(11, 5.6), dpi=150)
    x = c.season.to_numpy()
    ax.bar(x, c.kalshi_pay_days, width=0.78, color=blue, label="Kalshi-pay days (climate-day total at least 0.01 in)")
    ax.bar(x, c.loss_days, width=0.42, color=orange, label="Loss days (at least 0.25 in between 10:00 and 18:00)")
    for xi, k, l in zip(x, c.kalshi_pay_days, c.loss_days):
        ax.text(xi, k + 0.8, str(k), ha="center", va="bottom", fontsize=8, color=blue)
        ax.text(xi, l + 0.8, str(l), ha="center", va="bottom", fontsize=8, color="white" if l + 4 < k else orange, fontweight="bold")
    ax.hlines(r.kalshi_pay_days_mean, x.min() - 0.6, x.max() + 0.6, color=blue, lw=1, ls="--")
    ax.hlines(r.loss_days_mean, x.min() - 0.6, x.max() + 0.6, color=orange, lw=1, ls="--")
    ax.text(x.max() + 0.75, r.kalshi_pay_days_mean, f"mean {r.kalshi_pay_days_mean:.1f}", color=blue, va="center", fontsize=9)
    ax.text(x.max() + 0.75, r.loss_days_mean, f"mean {r.loss_days_mean:.1f}", color=orange, va="center", fontsize=9)
    ax.set_xlim(x.min() - 0.8, x.max() + 3.2)
    ax.set_ylim(0, c.kalshi_pay_days.max() + 14)
    ax.set_xticks(x)
    ax.set_xticklabels([str(v) for v in x], rotation=60, fontsize=8)
    ax.set_ylabel("Days per season", color=ink)
    ax.set_xlabel("Season (Friday before Memorial Day through Labor Day, 102 or 109 days)", color=ink)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="y", color="#e3e6ea", lw=0.6)
    ax.set_axisbelow(True)
    ax.legend(loc="upper left", frameon=False, fontsize=9, ncol=1)
    fig.suptitle(
        f"Trenton: the daily rain contract pays on about {r.kalshi_pay_days_mean / r.loss_days_mean:.0f} times as many days as a park loses\n"
        f"{100 * r.share_kalshi_pay_days_not_loss:.0f}% of Kalshi-pay days are not loss days; Kalshi pays on {100 * r.share_loss_days_kalshi_pays:.0f}% of loss days",
        x=0.07, ha="left", fontsize=12.5, color=ink, fontweight="bold",
    )
    fig.text(
        0.07, 0.012,
        f"Observed station data: Trenton-Mercer (TTN) hourly rain, {r.n_seasons} usable seasons {r.first_season}-{r.last_season}; "
        f"{r.days_unusable} days with incomplete opening hours dropped.\n"
        "Kalshi-pay days use the hourly sum. In 2002-2013 it counts 56 days whose hourly sum is 0.01 in (mostly one early-morning reading) where the NWS daily report "
        "has no measurable rain (docs/status/phase1_rain.md).",
        fontsize=8, color=muted, ha="left", va="bottom",
    )
    fig.text(0.98, 0.955, "OBSERVED STATION DATA", ha="right", va="center", fontsize=8.5, color=muted, fontweight="bold")
    fig.subplots_adjust(left=0.07, right=0.98, top=0.86, bottom=0.2)
    fig.savefig(os.path.join(OUT, "loss_vs_kalshi_days.png"))
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    S = build_summary()
    S.to_csv(os.path.join(OUT, "summary_by_case.csv"), index=False)
    write_markdown(S)
    figure(S)
    pd.set_option("display.width", 260); pd.set_option("display.max_columns", 40)
    cols = ["station", "seasons_set", "n_seasons", "loss_days_mean", "loss_days_min", "loss_days_max", "kalshi_pay_days_mean",
            "kalshi_pay_days_min", "kalshi_pay_days_max", "share_kalshi_pay_days_not_loss", "share_loss_days_kalshi_pays",
            "ref_ghcn_pay_days_mean", "ref_share_ghcn_pay_days_not_loss", "ref_share_loss_days_ghcn_pays", "ref_usable_days_ghcn_missing"]
    print(S[S.case == "SPEC main"][cols].to_string(index=False))
