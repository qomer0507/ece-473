"""Rain-count market experiment: what does a stepped hedge cost in a six-bucket LMSR market?

EVERYTHING HERE IS A SIMULATION. No orders were placed on any chain or exchange.
Prices come from the LMSR cost rule in sim/lmsr.py (same maths as
contracts/RainCountLMSR.sol). The "informed trader" is made up.

Two things are not simulated:
  * the season loss-day counts, if data/processed/rain/season_counts_TTN.csv
    exists (rain workstream; training seasons only). If the file is missing the
    script uses a PLACEHOLDER distribution and says so in every output;
  * the gas numbers, measured in the local Hardhat EVM (not on Sepolia) and
    read from results/market/gas_report.json.

Question. A park buys a stepped hedge: s shares of bucket 3, 2s of bucket 4,
3s of bucket 5 (it pays s, 2s or 3s payout units when the season has many loss
days). For each liquidity parameter b and each size s:
  * what does the market charge, per 1 unit of expected payout?
  * how far does the trade move the price (price impact)?
  * what is the sponsor's worst-case loss, b ln 6?
Two starting points: the uniform start (all prices 1/6), and after an informed
trader has moved the prices to the climatology distribution of the count.

Run:  python -m sim.experiment
Out:  results/market/  (hedge_pricing.csv, distribution.csv, stepped_hedge_price.png,
      summary.md, manifest.json)
The earlier temperature experiment is sim/experiment_temperature.py.
"""
from __future__ import annotations

import argparse
import csv
import datetime
import json
import math
import os
from typing import Dict, List, Optional, Sequence

from sim import lmsr

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_COUNTS = os.path.join(ROOT, "data", "processed", "rain", "season_counts_TTN.csv")
DEFAULT_OUT = os.path.join(ROOT, "results", "market")
TRAIN_YEARS = range(1998, 2015)  # SPEC_v3: train on seasons 1998-2014
SIM = "SIMULATED"
PLACEHOLDER = "PLACEHOLDER"
OBSERVED = "OBSERVED"


# ---------------------------------------------------------- distribution
def count_distribution(counts_file: Optional[str], edges: Sequence[int], alpha: float,
                       force_placeholder: bool = False) -> Dict[str, object]:
    """Bucket probabilities of the season count ("climatology").

    Uses the training-season counts from the rain workstream when the file is there.
    Otherwise a placeholder (Poisson, mean 5.3) that is labelled as such."""
    if not force_placeholder and counts_file and os.path.exists(counts_file):
        rows = lmsr.read_season_counts(counts_file, TRAIN_YEARS)
        if rows:
            counts = [r["loss_days"] for r in rows]
            tally = [0] * lmsr.N_COUNT_BUCKETS
            for c in counts:
                tally[lmsr.count_bucket_of(c, edges)] += 1
            return {
                "kind": OBSERVED,
                "probs": lmsr.bucket_probs_from_counts(counts, edges, alpha),
                "tally": tally,
                "counts": counts,
                "seasons": [r["season"] for r in rows],
                "description": (f"observed loss-day counts, {len(counts)} usable training seasons "
                                f"{rows[0]['season']}-{rows[-1]['season']} from {os.path.relpath(counts_file, ROOT)}, "
                                f"bucket frequencies with add-{alpha:g} smoothing"),
            }
    pmf = lmsr.placeholder_count_pmf()
    return {
        "kind": PLACEHOLDER,
        "probs": lmsr.bucket_probs_from_pmf(pmf, edges),
        "tally": None, "counts": None, "seasons": None,
        "description": ("PLACEHOLDER, not data: Poisson distribution with mean 5.3 loss days "
                        "(the preliminary Trenton mean in docs/status/phase0_verdict.md)"),
    }


# --------------------------------------------------------------- pricing
def hedge_row(state: str, b: float, size: float, probs: Sequence[float], edges: Sequence[int],
              start_bucket: int) -> Dict[str, object]:
    """Price one stepped hedge of `size` in a fresh market.

    state = "uniform": the hedger is the first trader (all prices 1/6).
    state = "informed": an informed trader first moves the prices to `probs`."""
    m = lmsr.CountMarket(b, edges)
    informed_cost = 0.0
    if state == "informed":
        informed_cost = m.move_to(probs)
    elif state != "uniform":
        raise ValueError(state)
    vector = [size * x for x in lmsr.stepped_vector(start_bucket)]
    pre = m.prices()
    cost = m.buy_vector(vector)
    post = m.prices()
    expected = lmsr.expected_payout(vector, probs)      # under the climatology distribution
    marginal_value = lmsr.expected_payout(vector, pre)  # the same hedge at the pre-trade prices
    # Sponsor result if the count follows `probs`: revenue from all buyers minus the expected payout.
    sponsor_expected = m.revenue - lmsr.expected_payout(m.q, probs)
    return {
        "label": SIM, "state": state, "b": b, "size": size,
        "max_payout_units": max(vector),
        "expected_payout_units": expected,
        "cost_units": cost,
        "price_per_1_expected_payout": cost / expected,
        "value_at_pre_trade_prices": marginal_value,
        "impact_rel": cost / marginal_value - 1.0,
        "top_bucket_price_before": pre[-1],
        "top_bucket_price_after": post[-1],
        "sponsor_worst_case_loss_b_ln6": lmsr.worst_case_loss(b, lmsr.N_COUNT_BUCKETS),
        "informed_trader_cost_units": informed_cost,
        "sponsor_expected_pnl_units": sponsor_expected,
        "sponsor_worst_pnl_units": m.worst_pnl(),
    }


# ---------------------------------------------------------------- output
def write_csv(path: str, rows: List[Dict[str, object]]) -> None:
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow({k: (f"{v:.6g}" if isinstance(v, float) else v) for k, v in r.items()})


def make_figure(path: str, rows: List[Dict[str, object]], b_grid: Sequence[float], dist_kind: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter

    colors = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#8a5cd6", "#c2417f"]
    markers = ["o", "s", "^", "D", "v", "P"]
    ink, muted, grid = "#1f1f1e", "#6b6a63", "#e4e3dd"
    titles = {"uniform": "Hedger trades first (uniform start, every price 1/6)",
              "informed": "After informed trading (prices = climatology)"}
    sizes = sorted({r["size"] for r in rows})
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.8), sharey=True)
    for ax, state in zip(axes, ("uniform", "informed")):
        for i, b in enumerate(b_grid):
            pts = sorted((r["size"], r["price_per_1_expected_payout"]) for r in rows
                         if r["state"] == state and r["b"] == b)
            xs, ys = zip(*pts)
            ax.plot(xs, ys, color=colors[i % 6], marker=markers[i % 6], markersize=7, linewidth=2,
                    markeredgecolor="white", markeredgewidth=1, label=f"b = {b:,.0f}")
        ax.axhline(1.0, color=ink, linewidth=1, linestyle="--")
        ax.text(sizes[-1] * 1.3, 0.975, "fair value = 1.00", fontsize=8, color=ink, va="top", ha="right")
        ax.set_title(titles[state], fontsize=10, color=ink, loc="left")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xticks(sizes)
        ax.set_xticklabels([f"{int(s):,}" for s in sizes])
        ax.set_xlim(sizes[0] * 0.7, sizes[-1] * 1.4)
        ax.set_xlabel("hedge size s (pays s, 2s, 3s payout units in the top three buckets)", color=muted, fontsize=9)
        ax.grid(True, which="major", color=grid, linewidth=0.8)
        ax.minorticks_off()
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color(grid)
        ax.tick_params(colors=muted, labelsize=9)
    axes[0].set_ylabel("price paid per 1 unit of expected payout\n(1.00 = fair under the climatology distribution)",
                       color=muted, fontsize=9)
    axes[0].set_ylim(0.88, 6.5)
    axes[0].set_yticks([1, 1.5, 2, 3, 4, 6])
    axes[0].yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, fontsize=9, loc="lower right", ncol=len(b_grid),
               title="LMSR liquidity parameter b (payout units); sponsor's worst-case loss = b ln 6",
               title_fontsize=9)
    fig.suptitle("SIMULATED: price of a stepped rain-count hedge in a six-bucket LMSR market",
                 fontsize=12, color=ink, x=0.01, ha="left")
    src = ("Climatology = PLACEHOLDER distribution (not data)." if dist_kind == PLACEHOLDER
           else "Climatology = observed training-season counts at Trenton (example bucket edges).")
    fig.text(0.01, 0.012, "Simulation from the LMSR cost rule, sim/experiment.py. No real orders.\n" + src + " Log-log axes.",
             fontsize=8, color=muted, va="bottom")
    fig.tight_layout(rect=(0, 0.12, 1, 0.95))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fmt(x: float, d: int = 4) -> str:
    return f"{x:,.{d}f}"


def write_summary(path: str, ctx: dict) -> None:
    d = ctx["dist"]
    L: List[str] = []
    L.append("# Rain-count market experiment (SIMULATED)\n")
    L.append("Everything below is a simulation from the LMSR cost rule. No real orders, no real money, no live chain.")
    L.append("Written by `python -m sim.experiment`. Do not edit by hand.\n")
    if d["kind"] == PLACEHOLDER:
        L.append("**The count distribution is a PLACEHOLDER, not data.** Every number that depends on it "
                 "(expected payout, price per 1 of expected payout, the informed start) changes when real counts are used.\n")
    L.append(f"- Buckets (loss days in the season): {', '.join(ctx['labels'])}. Edges {ctx['edges']} are "
             f"{'EXAMPLE edges, not the final ones' if ctx['example_edges'] else 'as given on the command line'}.")
    L.append(f"- Stepped hedge of size s: {ctx['step_text']}. One payout unit = 1 (read as $1).")
    L.append(f"- Count distribution (\"climatology\"): {d['description']}.")
    L.append("- Uniform start: the hedger is the first trader; every bucket costs 1/6.")
    L.append("- Informed start: a made-up informed trader first buys until the prices equal the climatology distribution.")
    L.append("- The contract has no sell function, so prices move only when somebody buys.\n")
    L.append("## Count distribution\n")
    if d["counts"] is not None:
        L.append(f"Training seasons used: {d['seasons'][0]}-{d['seasons'][-1]} ({len(d['counts'])} usable). "
                 f"Loss-day counts: {', '.join(str(c) for c in d['counts'])}.\n")
    L.append("| bucket | seasons in bucket | climatology probability | uniform start price |")
    L.append("|---|---|---|---|")
    for j, lab in enumerate(ctx["labels"]):
        t = "n/a (placeholder)" if d["tally"] is None else str(d["tally"][j])
        L.append(f"| {lab} | {t} | {fmt(d['probs'][j])} | {fmt(1 / 6)} |")
    L.append(f"\nExpected payout of a size-1 hedge under this distribution: {fmt(ctx['expected_unit'])} units. "
             f"Its cost at the uniform prices, before any impact: {fmt(ctx['uniform_unit_value'])} units.\n")
    L.append("## Hedge pricing (SIMULATED)\n")
    L.append("Price per 1 = cost divided by expected payout (1.00 is fair under the distribution above). "
             "Impact = cost divided by the hedge's value at the pre-trade prices, minus 1.\n")
    L.append("| start | b | size s | max payout | expected payout | cost | price per 1 of expected payout | impact | "
             "top-bucket price before -> after | sponsor worst-case loss b ln 6 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in ctx["rows"]:
        L.append(f"| {r['state']} | {r['b']:,.0f} | {r['size']:,.0f} | {r['max_payout_units']:,.0f} | "
                 f"{fmt(r['expected_payout_units'], 2)} | {fmt(r['cost_units'], 2)} | {fmt(r['price_per_1_expected_payout'], 3)} | "
                 f"{100 * r['impact_rel']:.1f}% | {fmt(r['top_bucket_price_before'], 3)} -> {fmt(r['top_bucket_price_after'], 3)} | "
                 f"{fmt(r['sponsor_worst_case_loss_b_ln6'], 1)} |")
    L.append("\n## Sponsor (SIMULATED)\n")
    L.append("Worst-case loss is b ln 6 whatever happens (tested on the contract). Expected P&L assumes the count follows "
             "the distribution above. In the informed start it includes what the informed trader paid and is expected to win.\n")
    L.append("| start | b | size s | informed trader paid | sponsor expected P&L | sponsor worst P&L after these trades | bound -b ln 6 |")
    L.append("|---|---|---|---|---|---|---|")
    for r in ctx["rows"]:
        L.append(f"| {r['state']} | {r['b']:,.0f} | {r['size']:,.0f} | {fmt(r['informed_trader_cost_units'], 1)} | "
                 f"{fmt(r['sponsor_expected_pnl_units'], 1)} | {fmt(r['sponsor_worst_pnl_units'], 1)} | "
                 f"{fmt(-r['sponsor_worst_case_loss_b_ln6'], 1)} |")
    if ctx.get("gas"):
        g = ctx["gas"]["gas"]
        L.append("\n## Gas (local Hardhat EVM, NOT Sepolia)\n")
        L.append("From results/market/gas_report.json, written by `npm test` in contracts/ (test/15_rain_gas.test.js). "
                 "Gas does not depend on b and barely on the hedge size; it depends on whether storage slots are written for the first time.\n")
        L.append("| function | calls measured | min | median | max |")
        L.append("|---|---|---|---|---|")
        for k in sorted(g):
            L.append(f"| {k} | {g[k]['calls']} | {g[k]['min']:,} | {g[k]['median']:,} | {g[k]['max']:,} |")
    else:
        L.append("\n## Gas\n\nresults/market/gas_report.json not found. Run `npm test` in contracts/ first.")
    L.append("\n## Limits\n")
    L.append("- No real traders. The LMSR is a pricing rule. It finds a fair price only if informed traders show up.")
    L.append("- At the uniform start the top three buckets cost 1/6 each, whatever the climate. A hedger who trades first "
             "pays that price plus impact. Nobody can sell the price down (buy only).")
    if d["kind"] == OBSERVED:
        L.append(f"- The distribution rests on {len(d['counts'])} seasons at one station. A bucket with 0 seasons gets its "
                 "probability from the smoothing constant alone.")
        L.append("- The bucket edges are example edges. The rain workstream chooses the final edges on the training seasons.")
        L.append("- The counts file belongs to the rain workstream and may still change. Re-run this script after it does.")
    else:
        L.append("- The count distribution is a placeholder. Replace it before quoting any price-per-payout number.")
    L.append("- The informed trader is assumed to know the climatology exactly and to move prices all the way.")
    L.append("- Gas was measured locally. Sepolia gas prices and total fees were not measured.")
    with open(path, "w") as fh:
        fh.write("\n".join(L) + "\n")


def main(argv=None) -> dict:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--counts-file", default=DEFAULT_COUNTS, help="season counts CSV from the rain workstream")
    ap.add_argument("--placeholder", action="store_true", help="ignore the counts file and use the placeholder distribution")
    ap.add_argument("--b", type=float, nargs="+", default=[50, 200, 1000, 5000])
    ap.add_argument("--sizes", type=float, nargs="+", default=[10, 100, 1000])
    ap.add_argument("--edges", type=int, nargs="+", default=lmsr.EXAMPLE_EDGES)
    ap.add_argument("--start-bucket", type=int, default=3, help="first bucket that pays (3 = top three buckets)")
    ap.add_argument("--alpha", type=float, default=0.5, help="add-alpha smoothing of the bucket frequencies")
    ap.add_argument("--out", default=DEFAULT_OUT)
    a = ap.parse_args(argv)

    lmsr.check_edges(a.edges)
    dist = count_distribution(a.counts_file, a.edges, a.alpha, a.placeholder)
    probs = dist["probs"]
    rows = [hedge_row(state, b, s, probs, a.edges, a.start_bucket)
            for state in ("uniform", "informed") for b in a.b for s in a.sizes]

    os.makedirs(a.out, exist_ok=True)
    for r in rows:
        r["distribution"] = dist["kind"]
    write_csv(os.path.join(a.out, "hedge_pricing.csv"), rows)
    labels = lmsr.count_bucket_labels(a.edges)
    step = lmsr.stepped_vector(a.start_bucket)
    write_csv(os.path.join(a.out, "distribution.csv"), [
        {"bucket": lab, "distribution": dist["kind"],
         "train_seasons_in_bucket": "" if dist["tally"] is None else dist["tally"][j],
         "climatology_probability": probs[j], "uniform_start_price": 1.0 / 6, "stepped_hedge_shares_per_size": step[j]}
        for j, lab in enumerate(labels)])
    make_figure(os.path.join(a.out, "stepped_hedge_price.png"), rows, a.b, dist["kind"])

    gas_path = os.path.join(a.out, "gas_report.json")
    gas = json.load(open(gas_path)) if os.path.exists(gas_path) else None
    ctx = {
        "dist": dist, "rows": rows, "labels": labels, "edges": list(a.edges),
        "example_edges": list(a.edges) == lmsr.EXAMPLE_EDGES, "b_grid": a.b, "sizes": a.sizes,
        "step_text": ", ".join(f"{k}s shares of bucket {labels[j]}" for j, k in enumerate(step) if k),
        "expected_unit": lmsr.expected_payout(step, probs),
        "uniform_unit_value": sum(step) / 6.0,
        "gas": gas,
    }
    write_summary(os.path.join(a.out, "summary.md"), ctx)
    with open(os.path.join(a.out, "manifest.json"), "w") as fh:
        json.dump({
            "label": "SIMULATED. LMSR cost rule only. No real orders, no live chain.",
            "script": "python -m sim.experiment",
            "written_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M"),
            "distribution": dist["kind"], "distribution_description": dist["description"],
            "train_seasons": dist["seasons"], "train_counts": dist["counts"],
            "edges": list(a.edges), "edges_are_example": ctx["example_edges"],
            "bucket_probabilities": probs, "alpha": a.alpha,
            "stepped_hedge_shares_per_size": step, "b_grid": a.b, "sizes": a.sizes,
            "outputs": ["hedge_pricing.csv", "distribution.csv", "stepped_hedge_price.png", "summary.md"],
            "not_simulated": ["season counts (if distribution is OBSERVED)", "gas_report.json (local Hardhat EVM, not Sepolia)"],
        }, fh, indent=1)
    print("wrote", os.path.relpath(a.out, ROOT), "| distribution:", dist["kind"])
    return ctx


if __name__ == "__main__":
    main()
