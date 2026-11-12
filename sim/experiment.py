"""Part 3 experiment: what does a ">= 90F" basket cost in an LMSR bracket market?

EVERYTHING HERE IS A SIMULATION. No orders were placed on any chain or exchange.
Prices come from the LMSR cost rule in sim/lmsr.py (same maths as
contracts/BracketLMSR.sol). Trade sequences are made up and labeled as such.
Only two things are observed data: the station's daily TMAX file (used for the
climatology prior, FIT window 2015-2019, and as settlement outcomes 2020-2025)
and the gas numbers, which come from the local Hardhat EVM (not from Sepolia).

Run:  python -m sim.experiment
Out:  results/part3/  (CSV tables, one PNG figure, summary.md, manifest.json)
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import statistics
from typing import Dict, List, Sequence

from sim import lmsr

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_STATION = os.path.join(ROOT, "data", "raw", "region", "tmax", "USW00014734.csv")
FIT_YEARS = range(2015, 2020)
OUTCOME_YEARS = range(2020, 2026)
SIM = "SIMULATED"


# --------------------------------------------------------------- pricing
def basket_row(prior_name: str, prior: Sequence[float], b: float, size: float,
               bounds: Sequence[int], strike: int) -> Dict[str, object]:
    """Price one >= strike basket of `size` payout units in a fresh market."""
    n = lmsr.n_brackets(bounds)
    uniform = all(abs(p - 1.0 / n) < 1e-12 for p in prior)
    q0 = None if uniform else lmsr.seed_from_prior(prior, b)
    m = lmsr.Market(b, bounds, strike, q0)
    pre = m.price_at_or_above()
    paid = m.buy_basket(size)
    post = m.price_at_or_above()
    avg = paid / size
    return {
        "label": SIM, "prior": prior_name, "b": b, "basket_size": size,
        "pre_trade_price": pre, "cost_units": paid, "avg_price_per_unit": avg,
        "post_trade_price": post,
        "impact_abs": avg - pre, "impact_rel": avg / pre - 1.0,
        "marginal_move_abs": post - pre,
        "sponsor_worst_case_loss": m.funding,
        "uniform_worst_case_b_ln_n": lmsr.worst_case_loss(b, n),
        "extra_subsidy_vs_uniform": m.funding - lmsr.worst_case_loss(b, n),
    }


# ------------------------------------------------------- trade scenarios
def normal_bracket_probs(mean: float, sd: float, bounds: Sequence[int]) -> List[float]:
    """Probability of each bracket if whole-degree TMAX ~ round(Normal(mean, sd))."""
    def cdf(x: float) -> float:
        return 0.5 * (1.0 + math.erf((x - mean) / (sd * math.sqrt(2.0))))
    # integer T < edge  <=>  continuous value < edge - 0.5
    edges = [e - 0.5 for e in bounds]
    cum = [cdf(e) for e in edges]
    probs = [cum[0]] + [b2 - b1 for b1, b2 in zip(cum[:-1], cum[1:])] + [1.0 - cum[-1]]
    return probs


def run_day(scenario: str, b: float, q0, temp: int, prior: Sequence[float], rng: random.Random,
            bounds: Sequence[int], strike: int, hedge_size: float) -> Dict[str, float]:
    """One simulated market day. Returns sponsor P&L and the hedger's basket price."""
    m = lmsr.Market(b, bounds, strike, q0)
    n = m.n
    if scenario == "noise_then_hedger":
        # 20 uninformed traders: random bracket, 1-50 units each.
        for _ in range(20):
            m.buy(rng.randrange(n), rng.randint(1, 50))
    elif scenario == "informed_then_hedger":
        # One trader has a forecast with a 3 F error and moves prices to that belief
        # (95% forecast distribution + 5% prior, so no price is pushed to zero).
        forecast = temp + rng.gauss(0.0, 3.0)
        belief = normal_bracket_probs(forecast, 3.0, bounds)
        belief = [0.95 * x + 0.05 * p for x, p in zip(belief, prior)]
        m.move_to(belief)
    elif scenario != "hedger_only":
        raise ValueError(scenario)
    pre = m.price_at_or_above()
    paid = m.buy_basket(hedge_size)
    return {"pnl": m.sponsor_pnl(temp), "worst": m.worst_pnl(), "hedge_avg_price": paid / hedge_size,
            "hedge_pre_price": pre}


def pnl_rows(priors: Dict[str, Sequence[float]], b_grid: Sequence[float], temps: Sequence[int],
             bounds: Sequence[int], strike: int, seed: int, hedge_size: float) -> List[Dict[str, object]]:
    rows = []
    n = lmsr.n_brackets(bounds)
    for prior_name, prior in priors.items():
        for b in b_grid:
            q0 = None if prior_name == "uniform" else lmsr.seed_from_prior(prior, b)
            bound = lmsr.Market(b, bounds, strike, q0).funding
            for scenario in ("hedger_only", "noise_then_hedger", "informed_then_hedger"):
                rng = random.Random(seed)  # same random draws for every (prior, b)
                days = [run_day(scenario, b, q0, t, prior, rng, bounds, strike, hedge_size) for t in temps]
                pnl = sorted(d["pnl"] for d in days)
                rows.append({
                    "label": SIM, "scenario": scenario, "prior": prior_name, "b": b,
                    "hedger_basket_size": hedge_size, "market_days": len(days),
                    "sponsor_pnl_mean": statistics.fmean(pnl),
                    "sponsor_pnl_p05": pnl[int(0.05 * (len(pnl) - 1))],
                    "sponsor_pnl_min": pnl[0], "sponsor_pnl_max": pnl[-1],
                    "share_days_sponsor_loses": sum(1 for x in pnl if x < 0) / len(pnl),
                    "sponsor_worst_case_bound": -bound,
                    "worst_possible_over_days": min(d["worst"] for d in days),
                    "hedger_avg_price_mean": statistics.fmean(d["hedge_avg_price"] for d in days),
                    "hedger_pre_price_mean": statistics.fmean(d["hedge_pre_price"] for d in days),
                    "n_brackets": n,
                })
    return rows


# ---------------------------------------------------------------- output
def write_csv(path: str, rows: List[Dict[str, object]]) -> None:
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow({k: (f"{v:.6g}" if isinstance(v, float) else v) for k, v in r.items()})


def make_figure(path: str, rows: List[Dict[str, object]], b_grid: Sequence[float], prior_names: Sequence[str]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colors = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]  # fixed order, one per b
    markers = ["o", "s", "^", "D"]
    ink, muted, grid = "#1f1f1e", "#6b6a63", "#e4e3dd"
    fig, axes = plt.subplots(1, len(prior_names), figsize=(5.2 * len(prior_names), 4.4), sharey=True)
    axes = [axes] if len(prior_names) == 1 else list(axes)
    for ax, prior_name in zip(axes, prior_names):
        for i, b in enumerate(b_grid):
            pts = sorted((r["basket_size"], 100 * r["impact_abs"]) for r in rows
                         if r["prior"] == prior_name and r["b"] == b)
            xs, ys = zip(*pts)
            ax.plot(xs, ys, color=colors[i % 4], marker=markers[i % 4], markersize=7, linewidth=2,
                    markeredgecolor="white", markeredgewidth=1, label=f"b = {b:,.0f}")
        pre = next(r["pre_trade_price"] for r in rows if r["prior"] == prior_name and r["b"] == b_grid[-1])
        ax.set_title(f"{prior_name} prior (pre-trade price about {pre:.2f})", fontsize=10, color=ink, loc="left")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xticks(sorted({r["basket_size"] for r in rows}))
        ax.set_xticklabels([f"{int(s):,}" for s in sorted({r["basket_size"] for r in rows})])
        ax.set_xlim(7, 1400)
        ax.set_xlabel("basket size (payout units)", color=muted)
        ax.grid(True, which="major", color=grid, linewidth=0.8)
        ax.minorticks_off()
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color(grid)
        ax.tick_params(colors=muted, labelsize=9)
    axes[0].set_ylabel("price impact: average price paid minus\npre-trade price (cents per $1 of payout)", color=muted)
    from matplotlib.ticker import FuncFormatter
    axes[0].yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, fontsize=9, loc="lower right", ncol=len(b_grid),
               title="LMSR liquidity parameter b (payout units)", title_fontsize=9)
    fig.suptitle("SIMULATED: price impact of a '>= 90F' basket in an LMSR bracket market (n = 12)",
                 fontsize=11, color=ink, x=0.01, ha="left")
    fig.text(0.01, 0.005, "Simulation from the LMSR cost rule, sim/experiment.py. No real orders. Log-log axes.",
             fontsize=8, color=muted)
    fig.tight_layout(rect=(0, 0.09, 1, 0.95))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fmt(x: float, d: int = 4) -> str:
    return f"{x:,.{d}f}"


def write_summary(path: str, ctx: dict) -> None:
    L: List[str] = []
    L.append("# Part 3 experiment summary (SIMULATED)\n")
    L.append("Everything below is a simulation from the LMSR cost rule. No real orders, no real money, no live chain.")
    L.append("Written by `python -m sim.experiment`. Do not edit by hand.\n")
    L.append(f"- Ladder: {', '.join(ctx['labels'])} (n = {len(ctx['labels'])}). Basket = all brackets >= {ctx['strike']}F.")
    L.append("- One payout unit pays 1 if TMAX >= 90F. Prices are per 1 unit of payout (read as $ per $1).")
    L.append(f"- Climatology prior: {ctx['station']}, May-Sep, FIT years 2015-2019, {ctx['fit_days']} days, add-one smoothing.")
    L.append(f"  FIT share of days >= 90F: {fmt(ctx['fit_hot_share'])}. Smoothed prior P(>=90F): {fmt(ctx['prior_hot'])}.\n")
    L.append("## Bracket prior\n")
    L.append("| bracket | FIT days | climatology prior | uniform prior |")
    L.append("|---|---|---|---|")
    for lab, c, p in zip(ctx["labels"], ctx["counts"], ctx["clim"]):
        L.append(f"| {lab} | {c} | {fmt(p)} | {fmt(1 / len(ctx['labels']))} |")
    L.append("\n## Basket pricing (SIMULATED)\n")
    L.append("Impact = average price paid minus pre-trade price.\n")
    L.append("| prior | b | basket | pre-trade price | avg price paid | impact | impact % | post-trade price |")
    L.append("|---|---|---|---|---|---|---|---|")
    for r in ctx["basket"]:
        L.append(f"| {r['prior']} | {r['b']:,.0f} | {r['basket_size']:,.0f} | {fmt(r['pre_trade_price'])} | "
                 f"{fmt(r['avg_price_per_unit'])} | {fmt(r['impact_abs'])} | {100 * r['impact_rel']:.2f}% | {fmt(r['post_trade_price'])} |")
    L.append("\n## Sponsor funding (worst-case loss, in payout units)\n")
    L.append("Uniform start: b ln(n). Seeded start: C(q0) - min(q0), about b ln(1/p_min). Integer seed shares.\n")
    L.append("| b | uniform b ln(12) | climatology start | extra subsidy for the non-uniform prior |")
    L.append("|---|---|---|---|")
    for b in ctx["b_grid"]:
        u = next(r for r in ctx["basket"] if r["prior"] == "uniform" and r["b"] == b)
        c = next(r for r in ctx["basket"] if r["prior"] == "climatology" and r["b"] == b)
        L.append(f"| {b:,.0f} | {fmt(u['sponsor_worst_case_loss'], 1)} | {fmt(c['sponsor_worst_case_loss'], 1)} | "
                 f"{fmt(c['extra_subsidy_vs_uniform'], 1)} |")
    L.append("\n## Realised sponsor P&L under SIMULATED trade sequences\n")
    L.append(f"One market per day. Outcomes: observed TMAX at the station, May-Sep {ctx['outcome_years']} "
             f"({ctx['outcome_days']} days, {fmt(ctx['outcome_hot_share'])} of them >= 90F). Trades are made up:")
    L.append(f"- `hedger_only`: one >= 90F basket of {ctx['hedge_size']:,.0f} units.")
    L.append("- `noise_then_hedger`: 20 uninformed buys (random bracket, 1-50 units), then the basket.")
    L.append("- `informed_then_hedger`: one trader with a forecast (error sd 3F) moves prices to that belief, then the basket.")
    L.append("P&L in payout units per market day. Negative = sponsor loss.\n")
    L.append("| scenario | prior | b | mean P&L | 5th pct | min | share of days with a loss | worst-case bound |")
    L.append("|---|---|---|---|---|---|---|---|")
    for r in ctx["pnl"]:
        L.append(f"| {r['scenario']} | {r['prior']} | {r['b']:,.0f} | {fmt(r['sponsor_pnl_mean'], 1)} | "
                 f"{fmt(r['sponsor_pnl_p05'], 1)} | {fmt(r['sponsor_pnl_min'], 1)} | "
                 f"{100 * r['share_days_sponsor_loses']:.1f}% | {fmt(r['sponsor_worst_case_bound'], 1)} |")
    if ctx.get("gas"):
        g = ctx["gas"]["gas"]
        L.append("\n## Gas (local Hardhat EVM, not Sepolia)\n")
        L.append("From results/part3/gas_report.json, written by `npm test` in contracts/. Median gas per call.\n")
        L.append("| function | median gas | calls measured |")
        L.append("|---|---|---|")
        for k in sorted(g):
            L.append(f"| {k} | {g[k]['median']:,} | {g[k]['calls']} |")
        L.append("\nGas depends mainly on the number of brackets (12 exp calls per quote) and on whether storage slots are written for the first time. It barely changes with the basket size or b (see the repeat-buyer rows, measured at sizes 100 and 1,000).")
    L.append("\n## Limits\n")
    L.append("- No real traders. The LMSR sets a price rule. It does not find a fair probability without informed orders.")
    L.append("- The uniform prior prices >= 90F at 0.50, far above the FIT frequency. A hedger would overpay until someone trades it down, and the contract has no sell function.")
    L.append("- The climatology prior is one station and five summers. The top bracket had 0 FIT days, so its price is set by the smoothing constant.")
    L.append("- Scenario P&L depends on the made-up trade sizes and forecast error. It shows direction, not magnitude.")
    with open(path, "w") as fh:
        fh.write("\n".join(L) + "\n")


def main(argv=None) -> dict:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--station-file", default=DEFAULT_STATION)
    ap.add_argument("--b", type=float, nargs="+", default=[50, 200, 1000, 5000])
    ap.add_argument("--sizes", type=float, nargs="+", default=[10, 100, 1000])
    ap.add_argument("--bounds", type=int, nargs="+", default=lmsr.DEFAULT_BOUNDS)
    ap.add_argument("--strike", type=int, default=lmsr.STRIKE)
    ap.add_argument("--alpha", type=float, default=1.0, help="add-alpha smoothing of the climatology prior")
    ap.add_argument("--hedge-size", type=float, default=100)
    ap.add_argument("--seed", type=int, default=473)
    ap.add_argument("--out", default=os.path.join(ROOT, "results", "part3"))
    a = ap.parse_args(argv)

    lmsr.check_bounds(a.bounds)
    n = lmsr.n_brackets(a.bounds)
    k = lmsr.strike_index(a.bounds, a.strike)
    fit = lmsr.season_tmax(a.station_file, FIT_YEARS)
    if not fit:
        raise SystemExit("no FIT-window data in " + a.station_file)
    counts = lmsr.bracket_counts(fit, a.bounds)
    clim = lmsr.prior_from_counts(counts, a.alpha)
    priors = {"uniform": [1.0 / n] * n, "climatology": clim}
    outcomes = lmsr.season_tmax(a.station_file, OUTCOME_YEARS)

    basket = [basket_row(name, p, b, s, a.bounds, a.strike)
              for name, p in priors.items() for b in a.b for s in a.sizes]
    pnl = pnl_rows(priors, a.b, outcomes, a.bounds, a.strike, a.seed, a.hedge_size)

    os.makedirs(a.out, exist_ok=True)
    write_csv(os.path.join(a.out, "basket_pricing.csv"), basket)
    write_csv(os.path.join(a.out, "sponsor_pnl.csv"), pnl)
    write_csv(os.path.join(a.out, "priors.csv"), [
        {"bracket": lab, "fit_days_2015_2019": c, "climatology_prior": p, "uniform_prior": 1.0 / n}
        for lab, c, p in zip(lmsr.bracket_labels(a.bounds), counts, clim)])
    make_figure(os.path.join(a.out, "price_impact.png"), basket, a.b, list(priors))

    gas_path = os.path.join(a.out, "gas_report.json")
    gas = json.load(open(gas_path)) if os.path.exists(gas_path) else None
    station = os.path.splitext(os.path.basename(a.station_file))[0]
    ctx = {
        "labels": lmsr.bracket_labels(a.bounds), "strike": a.strike, "station": station,
        "fit_days": len(fit), "counts": counts, "clim": clim,
        "fit_hot_share": sum(counts[k:]) / len(fit), "prior_hot": sum(clim[k:]),
        "basket": basket, "pnl": pnl, "b_grid": a.b, "hedge_size": a.hedge_size,
        "outcome_years": f"{OUTCOME_YEARS[0]}-{OUTCOME_YEARS[-1]}", "outcome_days": len(outcomes),
        "outcome_hot_share": sum(1 for t in outcomes if t >= a.strike) / len(outcomes), "gas": gas,
    }
    write_summary(os.path.join(a.out, "summary.md"), ctx)
    with open(os.path.join(a.out, "manifest.json"), "w") as fh:
        json.dump({
            "label": "SIMULATED. LMSR cost rule only. No real orders, no live chain.",
            "script": "python -m sim.experiment", "seed": a.seed,
            "station_file": os.path.relpath(a.station_file, ROOT), "season": "May-Sep",
            "fit_years": [FIT_YEARS[0], FIT_YEARS[-1]], "outcome_years": [OUTCOME_YEARS[0], OUTCOME_YEARS[-1]],
            "fit_days": len(fit), "outcome_days": len(outcomes),
            "bounds": a.bounds, "strike": a.strike, "n_brackets": n, "alpha": a.alpha,
            "b_grid": a.b, "basket_sizes": a.sizes, "hedge_size": a.hedge_size,
            "outputs": ["basket_pricing.csv", "sponsor_pnl.csv", "priors.csv", "price_impact.png", "summary.md"],
            "observed_inputs": ["station TMAX file (NCEI GHCN-Daily)", "gas_report.json (local Hardhat EVM)"],
        }, fh, indent=1)
    print("wrote", os.path.relpath(a.out, ROOT))
    return ctx


if __name__ == "__main__":
    main()
