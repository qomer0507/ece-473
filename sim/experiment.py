"""Rain-count market experiment: what does the REGISTERED stepped hedge cost in a six-bucket LMSR market?

EVERYTHING HERE IS A SIMULATION. No orders were placed on any chain or exchange.
Prices come from the LMSR cost rule in sim/lmsr.py (same maths as
contracts/RainCountLMSR.sol). The "informed trader" is made up. The trading fee is
hypothetical: the contract charges no fee.

Two things are not simulated:
  * the season loss-day counts in data/processed/rain/season_counts_TTN.csv
    (rain workstream; TRAIN seasons 1999-2014 only). If the file is missing the
    script uses a PLACEHOLDER distribution and says so in every output;
  * the gas numbers, measured in the local Hardhat EVM (not on Sepolia) and
    read from results/market/gas_report.json.

Product (docs/PHASE2_PREREG.md, strategy 3):
  * six buckets; the five upper edges are the 1/6 .. 5/6 quantiles of the TRAIN counts;
  * a hedge of size s holds s * h_j shares of bucket j, h_j = max(m_j - d, 0),
    m_j = TRAIN mean count in bucket j, d = deductible;
  * q_j = (n_j + 0.5) / (N + 3), the add-half smoothed TRAIN bucket frequencies;
  * registered MODELLED premium = 1.20 * expected payout = 1.20 * s * sum_j h_j q_j.
The deductible d is chosen by the evaluation workstream. Until it is known this script
runs d = 2, 3 and 4 and labels every row with its d.

Questions, for each liquidity parameter b, hedge size s and deductible d:
  * what does the market charge per 1 unit of expected payout, and how does that
    compare with the registered premium (1.20)?
  * how far does the trade move the price (price impact)?
  * what is the sponsor's worst-case loss, b ln 6?
  * after informed trading: what trading fee (share of trade cost) would cover the
    sponsor's expected loss?
Two starting points: (a) the uniform start (all prices 1/6), and (b) after an informed
trader has moved the prices to the smoothed TRAIN distribution q.

Run:  python -m sim.experiment
Out:  results/market/  (registered_buckets.csv, hedge_pricing.csv, break_even.csv, distribution.csv,
      stepped_hedge_price.png, summary.md, manifest.json)
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
TRAIN_YEARS = range(1999, 2015)  # PHASE2_PREREG: Trenton TRAIN = 1999-2014
LOADING = 0.20                   # PHASE2_PREREG: registered premium = (1 + 0.20) * expected payout
DEFAULT_B = [50, 200, 1000, 5000, 20000]
DEFAULT_SIZES = [10, 100, 1000]
DEFAULT_D = [2, 3, 4]
SIM = "SIMULATED"
PLACEHOLDER = "PLACEHOLDER"
OBSERVED = "OBSERVED"


# ------------------------------------------------- registered product
def registered_product(counts_file: Optional[str], alpha: float = 0.5, force_placeholder: bool = False,
                       edges: Optional[Sequence[int]] = None) -> Dict[str, object]:
    """Edges, bucket means m_j and probabilities q_j of the registered product.

    From the TRAIN-season counts when the file is there. Otherwise a PLACEHOLDER
    (Poisson, mean 5.3, treated the same way) that is labelled as such.
    `edges` overrides the quantile rule (then `edges_rule` says so)."""
    if not force_placeholder and counts_file and os.path.exists(counts_file):
        rows = lmsr.read_season_counts(counts_file, TRAIN_YEARS)
        if rows:
            counts = [r["loss_days"] for r in rows]
            reg = lmsr.registered_edges(counts)
            use = list(edges) if edges else reg["edges"]
            lmsr.check_edges(use)
            bm = lmsr.bucket_means(counts, use)
            return {
                "kind": OBSERVED, "edges": use,
                "edges_rule": "given on the command line" if edges else "registered quantile rule",
                "registered": reg, "means": bm["means"], "means_source": bm["source"], "members": bm["members"],
                "tally": bm["tally"], "probs": lmsr.prior_from_counts(bm["tally"], alpha),
                "counts": counts, "seasons": [r["season"] for r in rows],
                "description": (f"observed loss-day counts, {len(counts)} usable TRAIN seasons "
                                f"{rows[0]['season']}-{rows[-1]['season']} from {os.path.relpath(counts_file, ROOT)}, "
                                f"bucket frequencies with add-{alpha:g} smoothing"),
            }
    pmf = lmsr.placeholder_count_pmf()
    use = list(edges) if edges else list(lmsr.EXAMPLE_EDGES)
    lmsr.check_edges(use)
    probs = lmsr.bucket_probs_from_pmf(pmf, use)
    mass = [0.0] * 6
    for c, p in enumerate(pmf):
        mass[lmsr.count_bucket_of(c, use)] += c * p
    total = math.fsum(pmf)
    return {
        "kind": PLACEHOLDER, "edges": use, "edges_rule": "example edges (placeholder run)", "registered": None,
        "means": [m / (p * total) for m, p in zip(mass, probs)], "means_source": ["placeholder pmf mean"] * 6,
        "members": None, "tally": None, "probs": probs, "counts": None, "seasons": None,
        "description": ("PLACEHOLDER, not data: Poisson distribution with mean 5.3 loss days "
                        "(the preliminary Trenton mean in docs/status/phase0_verdict.md)"),
    }


def count_distribution(counts_file: Optional[str], edges: Sequence[int], alpha: float,
                       force_placeholder: bool = False) -> Dict[str, object]:
    """Bucket probabilities for given edges (kept for callers that fix the edges themselves)."""
    return registered_product(counts_file, alpha, force_placeholder, edges)


# --------------------------------------------------------------- pricing
def hedge_row(state: str, b: float, size: float, probs: Sequence[float], edges: Sequence[int],
              holdings_per_unit: Sequence[float], deductible: Optional[float] = None,
              loading: float = LOADING) -> Dict[str, object]:
    """Price one stepped hedge (size * holdings_per_unit) in a fresh market.

    state = "uniform": the hedger is the first trader (all prices 1/6).
    state = "informed": an informed trader first moves the prices to `probs`.
    "Expected" always means: under `probs` (the smoothed TRAIN distribution)."""
    m = lmsr.CountMarket(b, edges)
    informed_cost = informed_expected = 0.0
    if state == "informed":
        informed_cost = m.move_to(probs)
        informed_expected = lmsr.expected_payout(m.q, probs)
    elif state != "uniform":
        raise ValueError(state)
    vector = [size * x for x in holdings_per_unit]
    pre = m.prices()
    cost = m.buy_vector(vector)
    post = m.prices()
    expected = lmsr.expected_payout(vector, probs)
    marginal_value = lmsr.expected_payout(vector, pre)  # the same hedge at the pre-trade prices
    # Sponsor result if the count follows `probs`: revenue from all buyers minus the expected payout.
    sponsor_expected = m.revenue - lmsr.expected_payout(m.q, probs)
    shortfall = max(0.0, -sponsor_expected)
    return {
        "label": SIM, "state": state, "b": b, "size": size, "deductible_d": deductible,
        "max_payout_units": max(vector),
        "expected_payout_units": expected,
        "cost_units": cost,
        "price_per_1_expected_payout": cost / expected,
        "registered_premium_units": (1.0 + loading) * expected,
        "lmsr_cost_over_registered_premium": cost / ((1.0 + loading) * expected),
        "value_at_pre_trade_prices": marginal_value,
        "impact_rel": cost / marginal_value - 1.0,
        "top_bucket_price_before": pre[-1],
        "top_bucket_price_after": post[-1],
        "sponsor_worst_case_loss_b_ln6": lmsr.worst_case_loss(b, lmsr.N_COUNT_BUCKETS),
        "informed_trader_cost_units": informed_cost,
        "informed_trader_expected_profit_units": informed_expected - informed_cost,
        "sponsor_expected_pnl_units": sponsor_expected,
        "sponsor_worst_pnl_units": m.worst_pnl(),
        # Hypothetical fee (the contract has none), assuming the fee changes nobody's trades:
        "break_even_fee_on_all_trades": shortfall / m.revenue,
        "break_even_fee_on_hedger_only": shortfall / cost,
        "hedger_price_per_1_with_fee_on_hedger": (cost + shortfall) / expected,
    }


def informed_loss_per_b(probs: Sequence[float]) -> float:
    """Sponsor's expected loss to the informed trader, per unit of b: KL(probs || uniform).
    (Loss = b * sum_j p_j ln(6 p_j) when the count really follows `probs`.)"""
    return math.fsum(p * math.log(len(probs) * p) for p in probs)


def self_financing_point(probs: Sequence[float], edges: Sequence[int], holdings_per_unit: Sequence[float],
                         size: float = 100.0) -> Dict[str, float]:
    """The b at which the hedger's price impact exactly pays for the sponsor's expected
    loss to the informed trader (expected sponsor P&L = 0, no fee), found by bisection.
    Only the ratio b / size matters, so the price at this point is the same for every size."""
    def pnl(b: float) -> float:
        return hedge_row("informed", b, size, probs, edges, holdings_per_unit)["sponsor_expected_pnl_units"]
    lo, hi = size * 1e-3, size * 1e4
    if pnl(lo) <= 0 or pnl(hi) >= 0:
        raise ValueError("no sign change")
    for _ in range(200):
        mid = math.sqrt(lo * hi)
        if pnl(mid) > 0:
            lo = mid
        else:
            hi = mid
    r = hedge_row("informed", lo, size, probs, edges, holdings_per_unit)
    return {"b_per_unit_size": lo / size, "price_per_1_expected_payout": r["price_per_1_expected_payout"],
            "sponsor_bound_per_unit_size": lo / size * math.log(6)}


def b_for_price(probs: Sequence[float], edges: Sequence[int], holdings_per_unit: Sequence[float],
                target: float, size: float = 100.0) -> Optional[float]:
    """Smallest b / size at which the informed-start LMSR price per 1 of expected payout is <= target."""
    def price(b: float) -> float:
        return hedge_row("informed", b, size, probs, edges, holdings_per_unit)["price_per_1_expected_payout"]
    lo, hi = size * 1e-3, size * 1e5
    if price(hi) > target:
        return None
    for _ in range(200):
        mid = math.sqrt(lo * hi)
        if price(mid) > target:
            lo = mid
        else:
            hi = mid
    return hi / size


# ---------------------------------------------------------------- output
def write_csv(path: str, rows: List[Dict[str, object]]) -> None:
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow({k: (f"{v:.6g}" if isinstance(v, float) else v) for k, v in r.items()})


def bucket_rows(prod: dict, d_grid: Sequence[float]) -> List[Dict[str, object]]:
    """One row per bucket: the registered product, as written to registered_buckets.csv."""
    labels = lmsr.count_bucket_labels(prod["edges"])
    reg = prod["registered"]
    if reg is None:
        ties = "placeholder run: no train counts"
    elif reg["adjusted"]:
        ties = "TIES: " + "; ".join(f"edge {a['edge_index'] + 1} quantile {a['quantile']} moved up to {a['used']}"
                                    for a in reg["adjusted"])
    else:
        ties = "no ties: five distinct quantiles, six distinct buckets, nothing merged or moved"
    out = []
    lo = 0
    for j, lab in enumerate(labels):
        last = j == len(labels) - 1
        r: Dict[str, object] = {
            "bucket": j, "loss_days": lab, "lowest_count": lo, "upper_edge": "" if last else prod["edges"][j],
            "quantile_level": "" if last else f"{j + 1}/6",
            "quantile_inverted_cdf": "" if last or reg is None else reg["quantiles_inverted_cdf"][j],
            "quantile_linear_interpolation": "" if last or reg is None else reg["quantiles_linear"][j],
            "n_train_seasons": "" if prod["tally"] is None else prod["tally"][j],
            "train_counts_in_bucket": "" if prod["members"] is None else " ".join(str(x) for x in sorted(prod["members"][j])),
            "m_j": prod["means"][j], "m_j_source": prod["means_source"][j], "q_j": prod["probs"][j],
        }
        for d in d_grid:
            r[f"h_j_d{d:g}"] = max(prod["means"][j] - d, 0.0)
        r["distribution"] = prod["kind"]
        r["train_counts_sorted"] = "" if reg is None else " ".join(str(x) for x in reg["sorted_counts"])
        r["ties"] = ties
        out.append(r)
        if not last:
            lo = prod["edges"][j] + 1
    return out


def make_figure(path: str, rows: List[Dict[str, object]], b_grid: Sequence[float], dist_kind: str,
                d_grid: Sequence[float], loading: float = LOADING) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter

    colors = ["#2a78d6", "#eb6834", "#1baf7a"]
    markers = ["o", "s", "^"]
    ink, muted, grid = "#1f1f1e", "#6b6a63", "#e4e3dd"
    titles = {"uniform": "(a) Hedger trades first: uniform start, every price 1/6",
              "informed": "(b) After informed trading: prices = smoothed TRAIN distribution"}
    sizes = sorted({r["size"] for r in rows})
    d_mid = sorted(d_grid)[len(d_grid) // 2]
    prem = 1.0 + loading
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.4), sharey=True)
    for ax, state in zip(axes, ("uniform", "informed")):
        for i, s in enumerate(sizes):
            def series(d):
                pts = sorted((r["b"], r["price_per_1_expected_payout"]) for r in rows
                             if r["state"] == state and r["size"] == s and r["deductible_d"] == d)
                return [p[0] for p in pts], [p[1] for p in pts]
            xs, ys = series(d_mid)
            if len(d_grid) > 1:
                lo = [min(v) for v in zip(*(series(d)[1] for d in d_grid))]
                hi = [max(v) for v in zip(*(series(d)[1] for d in d_grid))]
                ax.fill_between(xs, lo, hi, color=colors[i % 3], alpha=0.16, linewidth=0)
            ax.plot(xs, ys, color=colors[i % 3], marker=markers[i % 3], markersize=7, linewidth=2,
                    markeredgecolor="white", markeredgewidth=1, label=f"hedge size {s:,.0f} x L")
        ax.axhline(1.0, color=ink, linewidth=1.2, linestyle="--", label="fair value 1.00")
        ax.axhline(prem, color=ink, linewidth=1.4, linestyle=":", label=f"registered premium {prem:.2f} (MODELLED)")
        ax.set_title(titles[state], fontsize=10.5, color=ink, loc="left")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xticks(list(b_grid))
        ax.set_xticklabels([f"{b:,.0f}\n({b * math.log(6):,.0f})" for b in b_grid])
        ax.set_xlim(b_grid[0] * 0.55, b_grid[-1] * 1.6)
        ax.set_xlabel("LMSR liquidity parameter b  (in brackets: sponsor's worst-case loss b ln 6), units of L",
                      color=muted, fontsize=9)
        ax.grid(True, which="major", color=grid, linewidth=0.8)
        ax.minorticks_off()
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color(grid)
        ax.tick_params(colors=muted, labelsize=9)
    axes[0].set_ylabel("price paid per 1 unit of expected payout\n(expected payout under the smoothed TRAIN distribution)",
                       color=muted, fontsize=9)
    ymax = max(r["price_per_1_expected_payout"] for r in rows)
    axes[0].set_ylim(0.9, ymax * 1.12)
    axes[0].set_yticks([t for t in (1, 1.2, 1.5, 2, 3, 4, 5, 6, 8) if t <= ymax * 1.12])
    axes[0].yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    handles, labels = axes[0].get_legend_handles_labels()
    band = (f"Line: deductible d = {d_mid:g}. Band: range over d = {', '.join(f'{d:g}' for d in sorted(d_grid))} "
            "(d is not chosen yet).") if len(d_grid) > 1 else f"Deductible d = {d_mid:g}."
    fig.legend(handles, labels, frameon=False, fontsize=9.5, loc="lower left", ncol=len(handles),
               bbox_to_anchor=(0.045, 0.085), columnspacing=1.8, handlelength=2.6)
    fig.suptitle("SIMULATED: what a six-bucket LMSR market charges for the registered stepped rain-count hedge",
                 fontsize=12.5, color=ink, x=0.01, ha="left")
    src = ("Distribution = PLACEHOLDER (not data)." if dist_kind == PLACEHOLDER
           else "Buckets and distribution from OBSERVED Trenton TRAIN counts 1999-2014 (16 seasons); prices are simulated.")
    fig.text(0.01, 0.012,
             "Simulation from the LMSR cost rule (sim/experiment.py). No real orders, no real traders. " + src + "\n"
             + band + " The hedge holds size x max(m_j - d, 0) shares of bucket j. Log-log axes.",
             fontsize=8.5, color=muted, va="bottom")
    fig.tight_layout(rect=(0, 0.14, 1, 0.96))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fmt(x: float, d: int = 4) -> str:
    return f"{x:,.{d}f}"


def pick(rows, state, b, size, d):
    return next(r for r in rows if r["state"] == state and r["b"] == b and r["size"] == size and r["deductible_d"] == d)


def write_summary(path: str, ctx: dict) -> None:
    prod = ctx["prod"]
    rows, b_grid, sizes, d_grid = ctx["rows"], ctx["b_grid"], ctx["sizes"], ctx["d_grid"]
    labels = ctx["labels"]
    prem = 1.0 + ctx["loading"]
    L: List[str] = []
    L.append("# Rain-count market experiment (SIMULATED)\n")
    L.append("Everything below is a simulation from the LMSR cost rule. No real orders, no real money, no live chain, no real traders.")
    L.append("Only the Trenton season counts are observed data. Written by `python -m sim.experiment`. Do not edit by hand.\n")
    if prod["kind"] == PLACEHOLDER:
        L.append("**The count distribution is a PLACEHOLDER, not data.** Every number that depends on it "
                 "(edges here are example edges, bucket means, expected payout, prices per 1 of expected payout) is a placeholder too.\n")
    L.append("## The registered product (docs/PHASE2_PREREG.md, strategy 3)\n")
    if prod["counts"] is not None:
        reg = prod["registered"]
        L.append(f"TRAIN seasons: {prod['seasons'][0]}-{prod['seasons'][-1]} ({len(prod['counts'])} usable, calendar all_days, column loss_days). "
                 f"Counts by season: {', '.join(str(c) for c in prod['counts'])}.")
        L.append(f"Sorted: {', '.join(str(c) for c in reg['sorted_counts'])}.\n")
        L.append("Quantiles 1/6, 2/6, 3/6, 4/6, 5/6 of the counts: "
                 f"{', '.join(str(x) for x in reg['quantiles_inverted_cdf'])} (smallest count with at least that share of seasons at or below it); "
                 f"{', '.join(f'{x:g}' for x in reg['quantiles_linear'])} (linear interpolation, the numpy default).")
        if prod["edges_rule"] != "registered quantile rule":
            L.append(f"**The edges used below were {prod['edges_rule']}: {prod['edges']}. They are NOT the registered edges {reg['edges']}.**")
        elif reg["adjusted"]:
            L.append("**Ties.** Some quantiles were equal. Each tied edge was moved up to the next whole number: "
                     + "; ".join(f"edge {a['edge_index'] + 1}: quantile {a['quantile']}, used {a['used']}" for a in reg["adjusted"]) + ".")
        else:
            L.append(f"**Registered edges: {prod['edges']}.** The five quantiles are all different, so there are six distinct buckets. "
                     "No ties had to be merged and no edge was moved.")
        L.append("Two buckets are one count wide (5 and 6). That is what the quantile rule gives; it was not changed.\n")
    else:
        L.append(f"Edges {prod['edges']}: {prod['edges_rule']}.\n")
    L.append("| bucket | loss days | TRAIN seasons n_j | TRAIN counts in bucket | bucket mean m_j | smoothed probability q_j | "
             + " | ".join(f"holding h_j, d = {d:g}" for d in d_grid) + " |")
    L.append("|---|---|---|---|---|---|" + "---|" * len(d_grid))
    for r in ctx["bucket_rows"]:
        L.append(f"| {r['bucket']} | {r['loss_days']} | {r['n_train_seasons']} | {r['train_counts_in_bucket']} | {fmt(r['m_j'], 4)} | "
                 f"{fmt(r['q_j'], 4)} | " + " | ".join(fmt(r[f'h_j_d{d:g}'], 4) for d in d_grid) + " |")
    L.append("\n- m_j is the TRAIN mean count in the bucket. q_j = (n_j + 0.5) / (N + 3).")
    L.append("- A hedge of size s holds s x h_j shares of bucket j, h_j = max(m_j - d, 0). It pays s x h_j units of L if the season's count lands in bucket j.")
    L.append("- **The deductible d is not known yet.** The evaluation workstream chooses it on TRAIN. Every table below shows d = "
             + ", ".join(f"{d:g}" for d in d_grid) + ".")
    L.append("- On the contract shares are whole numbers. All h_j are multiples of 1/12 here, so a payout unit of L/12 makes every holding whole "
             "(multiply the shares and b by 12). The simulation uses the exact fractions.\n")
    L.append("| d | expected payout per unit of size, sum h_j q_j | registered MODELLED premium (x "
             f"{prem:.2f}) | value at uniform prices, sum h_j / 6 | uniform value / expected payout |")
    L.append("|---|---|---|---|---|")
    for d in d_grid:
        e = ctx["per_d"][d]
        L.append(f"| {d:g} | {fmt(e['expected_unit'])} | {fmt(prem * e['expected_unit'])} | {fmt(e['uniform_unit_value'])} | {fmt(e['uniform_unit_value'] / e['expected_unit'], 3)} |")
    L.append("\n## Set-up of the simulation\n")
    L.append("- (a) Uniform start: the hedger is the first trader; every bucket costs 1/6.")
    L.append("- (b) Informed start: a made-up informed trader first buys until the prices equal q. Then the hedger buys.")
    L.append("- The contract has no sell function, so prices move only when somebody buys.")
    L.append("- One hedger per market. \"Expected\" always means: if the count really follows q.")
    L.append("- One unit = L, the park's loss per loss day (read as $1).\n")

    L.append("## Headline table (SIMULATED): price paid per 1 of expected payout\n")
    L.append(f"1.00 is fair under q. The registered MODELLED premium is {prem:.2f}. Each cell shows d = "
             + " / ".join(f"{d:g}" for d in d_grid) + ".\n")
    L.append("| start | b | sponsor worst-case loss b ln 6 | " + " | ".join(f"size {s:,.0f}" for s in sizes) + " |")
    L.append("|---|---|---|" + "---|" * len(sizes))
    for state in ("uniform", "informed"):
        for b in b_grid:
            cells = [" / ".join(fmt(pick(rows, state, b, s, d)["price_per_1_expected_payout"], 2) for d in d_grid) for s in sizes]
            L.append(f"| {state} | {b:,.0f} | {fmt(b * math.log(6), 1)} | " + " | ".join(cells) + " |")
    L.append("\n## Price impact (SIMULATED)\n")
    L.append("Impact = cost divided by the hedge's value at the pre-trade prices, minus 1. Each cell shows d = "
             + " / ".join(f"{d:g}" for d in d_grid) + ".\n")
    L.append("| start | b | " + " | ".join(f"size {s:,.0f}" for s in sizes) + " |")
    L.append("|---|---|" + "---|" * len(sizes))
    for state in ("uniform", "informed"):
        for b in b_grid:
            cells = [" / ".join(f"{100 * pick(rows, state, b, s, d)['impact_rel']:.1f}%" for d in d_grid) for s in sizes]
            L.append(f"| {state} | {b:,.0f} | " + " | ".join(cells) + " |")

    L.append("\n## LMSR price against the registered premium (SIMULATED against MODELLED)\n")
    L.append(f"LMSR cost divided by the registered premium ({prem:.2f} x expected payout). Below 1.00 the market is cheaper than the "
             "modelled premium; above 1.00 it is dearer. Each cell shows d = " + " / ".join(f"{d:g}" for d in d_grid) + ".\n")
    L.append("| start | b | " + " | ".join(f"size {s:,.0f}" for s in sizes) + " |")
    L.append("|---|---|" + "---|" * len(sizes))
    for state in ("uniform", "informed"):
        for b in b_grid:
            cells = [" / ".join(fmt(pick(rows, state, b, s, d)["lmsr_cost_over_registered_premium"], 2) for d in d_grid) for s in sizes]
            L.append(f"| {state} | {b:,.0f} | " + " | ".join(cells) + " |")
    L.append("\nReading:")
    L.append("- Uniform start: even with no impact the hedge costs sum h_j / 6 instead of sum h_j q_j (ratio in the product table above). "
             "The hedge buys the high buckets, and the uniform start prices them at 1/6 each while q gives the top three 0.13 to 0.18.")
    L.append(f"- Informed start: the price is 1.00 plus impact. It is below the registered {prem:.2f} only when b is large against the hedge.")
    for d in d_grid:
        bb = ctx["break_even"][d]
        if bb["b_per_size_for_registered_premium"] is not None:
            L.append(f"  - d = {d:g}: the LMSR price equals {prem:.2f} at b = {fmt(bb['b_per_size_for_registered_premium'], 2)} x hedge size "
                     f"(sponsor worst-case loss {fmt(bb['b_per_size_for_registered_premium'] * math.log(6), 2)} x hedge size).")

    L.append("\n## Who pays for the sponsor? Break-even fee, scenario (b) (SIMULATED, hypothetical fee)\n")
    kl = ctx["kl"]
    L.append(f"The informed trader buys at uniform prices what is worth more under q. If q is right, the sponsor expects to lose "
             f"b x KL(q || uniform) = **{fmt(kl, 5)} x b** to that trader. With the uniform start this is the cost of finding the price.")
    L.append("The hedger pays more than the expected payout (impact). That excess goes to the sponsor.")
    L.append("Sponsor expected P&L = hedger's excess - informed trader's expected profit. Where it is negative, a fee could cover it.")
    L.append("The contract charges NO fee. The fee below is hypothetical, and it assumes the fee changes nobody's trades.\n")
    L.append("- Fee on all trades = shortfall / (informed trader's cost + hedger's cost).")
    L.append("- Fee on the hedger only = shortfall / hedger's cost. This is the honest one: an informed trader who pays a fee trades less.")
    L.append("- 0.0% means the hedger's impact already covers the sponsor.")
    L.append(f"- With no hedger at all, the fee on the informed trader's own cost would have to be {100 * ctx['fee_cap_all']:.1f}%. "
             "That is the upper limit of the fee on all trades, whatever b is.\n")
    L.append("| b | size | d | informed trader's expected profit | hedger pays above expected payout | sponsor expected P&L | "
             "fee on all trades | fee on hedger only | hedger's price per 1 with that fee | registered premium |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for b in b_grid:
        for s in sizes:
            for d in d_grid:
                r = pick(rows, "informed", b, s, d)
                L.append(f"| {b:,.0f} | {s:,.0f} | {d:g} | {fmt(r['informed_trader_expected_profit_units'], 2)} | "
                         f"{fmt(r['cost_units'] - r['expected_payout_units'], 2)} | {fmt(r['sponsor_expected_pnl_units'], 2)} | "
                         f"{100 * r['break_even_fee_on_all_trades']:.2f}% | {100 * r['break_even_fee_on_hedger_only']:.2f}% | "
                         f"{fmt(r['hedger_price_per_1_with_fee_on_hedger'], 3)} | {prem:.2f} |")
    L.append("\nThe same thing in one line per d. Only b / size matters, so these hold for every hedge size (one hedger per market):\n")
    L.append("| d | expected payout per unit of size | self-financing point: b / size | hedger's price per 1 there, no fee | "
             f"b / size where the LMSR price is {prem:.2f} | fee on the hedger needed there | hedger's price per 1 with that fee |")
    L.append("|---|---|---|---|---|---|---|")
    for d in d_grid:
        bb = ctx["break_even"][d]
        L.append(f"| {d:g} | {fmt(ctx['per_d'][d]['expected_unit'])} | {fmt(bb['self_financing_b_per_size'], 3)} | "
                 f"{fmt(bb['self_financing_price_per_1'], 3)} | {fmt(bb['b_per_size_for_registered_premium'], 3)} | "
                 f"{100 * bb['fee_on_hedger_at_registered_premium']:.2f}% | {fmt(bb['price_with_fee_at_registered_premium'], 3)} |")
    L.append("\nReading:")
    L.append("- Self-financing point: the b at which the hedger's impact exactly pays for the informed trader. Smaller b: the sponsor expects a profit "
             "and the hedger pays more. Larger b: the hedger pays less and the sponsor expects a loss.")
    L.append(f"- At the b where the LMSR price equals the registered {prem:.2f}, the sponsor expects a "
             f"{'profit, so no fee is needed' if all(ctx['break_even'][d]['fee_on_hedger_at_registered_premium'] == 0 for d in d_grid) else 'loss unless the fee in the table is charged'}.")
    L.append("- A deeper market (large b against the hedge) gives the hedger a price near 1.00 and leaves the sponsor a loss of about "
             f"{fmt(kl, 4)} x b. A fee on the hedger of (that loss / hedge cost) would cover it; the table shows when that fee pushes the "
             f"hedger's all-in price above {prem:.2f}.")
    L.append("- With several hedgers in one market the informed trader is paid for once and the fee per hedger falls. That was not simulated.\n")

    L.append("## All rows (SIMULATED)\n")
    L.append("| start | b | size | d | max payout | expected payout | cost | price per 1 | cost / registered premium | impact | "
             "top-bucket price before -> after | sponsor worst P&L after these trades | bound -b ln 6 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        L.append(f"| {r['state']} | {r['b']:,.0f} | {r['size']:,.0f} | {r['deductible_d']:g} | {r['max_payout_units']:,.0f} | "
                 f"{fmt(r['expected_payout_units'], 2)} | {fmt(r['cost_units'], 2)} | {fmt(r['price_per_1_expected_payout'], 3)} | "
                 f"{fmt(r['lmsr_cost_over_registered_premium'], 3)} | {100 * r['impact_rel']:.1f}% | "
                 f"{fmt(r['top_bucket_price_before'], 3)} -> {fmt(r['top_bucket_price_after'], 3)} | "
                 f"{fmt(r['sponsor_worst_pnl_units'], 1)} | {fmt(-r['sponsor_worst_case_loss_b_ln6'], 1)} |")
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
    L.append("- Nobody can sell the price down (buy only). A hedger who trades first pays the uniform prices plus impact.")
    if prod["kind"] == OBSERVED:
        L.append(f"- q rests on {len(prod['counts'])} seasons at one station. \"Fair\" and \"expected\" mean fair under q, not under the true climate.")
        L.append("- The deductible d is not chosen yet; d = " + ", ".join(f"{d:g}" for d in d_grid) + " are shown side by side.")
        L.append("- Some other quantile conventions interpolate to a non-whole number at 2/6 (about 3.7 to 3.8) and 5/6 (8.67 under one rule). "
                 "Rounded to the observed counts they give the same edges, except that one rule could give 9 for the last edge. "
                 "No TRAIN season has 9 loss days, so the TRAIN buckets, m_j and q_j would be the same.")
    else:
        L.append("- The count distribution is a placeholder. Replace it before quoting any price-per-payout number.")
    L.append("- The informed trader is assumed to know q exactly and to move prices all the way. The fee is assumed not to change behaviour.")
    L.append("- The registered premium is MODELLED (expected payout x 1.20). Nobody has offered that price.")
    L.append("- Gas was measured locally. Sepolia gas prices and total fees were not measured.")
    with open(path, "w") as fh:
        fh.write("\n".join(L) + "\n")


def main(argv=None) -> dict:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--counts-file", default=DEFAULT_COUNTS, help="season counts CSV from the rain workstream")
    ap.add_argument("--placeholder", action="store_true", help="ignore the counts file and use the placeholder distribution")
    ap.add_argument("--b", type=float, nargs="+", default=DEFAULT_B)
    ap.add_argument("--sizes", type=float, nargs="+", default=DEFAULT_SIZES, help="hedge sizes in units of L")
    ap.add_argument("--d", type=float, nargs="+", default=DEFAULT_D, help="deductibles to run (not chosen yet: 2 3 4)")
    ap.add_argument("--edges", type=int, nargs="+", default=None, help="override the registered quantile edges (labelled)")
    ap.add_argument("--alpha", type=float, default=0.5, help="add-alpha smoothing of the bucket frequencies (registered: 0.5)")
    ap.add_argument("--loading", type=float, default=LOADING, help="loading of the registered modelled premium")
    ap.add_argument("--out", default=DEFAULT_OUT)
    a = ap.parse_args(argv)

    prod = registered_product(a.counts_file, a.alpha, a.placeholder, a.edges)
    probs, edges = prod["probs"], prod["edges"]
    holdings = {d: lmsr.registered_holdings(prod["means"], d) for d in a.d}
    rows = [hedge_row(state, b, s, probs, edges, holdings[d], d, a.loading)
            for state in ("uniform", "informed") for b in a.b for s in a.sizes for d in a.d]
    for r in rows:
        r["distribution"] = prod["kind"]

    prem = 1.0 + a.loading
    per_d, break_even, be_rows = {}, {}, []
    for d in a.d:
        h = holdings[d]
        per_d[d] = {"expected_unit": lmsr.expected_payout(h, probs), "uniform_unit_value": sum(h) / 6.0}
        sf = self_financing_point(probs, edges, h)
        bp = b_for_price(probs, edges, h, prem)
        at = hedge_row("informed", bp * 100.0, 100.0, probs, edges, h, d, a.loading) if bp else None
        break_even[d] = {
            "self_financing_b_per_size": sf["b_per_unit_size"],
            "self_financing_price_per_1": sf["price_per_1_expected_payout"],
            "b_per_size_for_registered_premium": bp,
            "fee_on_hedger_at_registered_premium": at["break_even_fee_on_hedger_only"] if at else None,
            "price_with_fee_at_registered_premium": at["hedger_price_per_1_with_fee_on_hedger"] if at else None,
        }
        be_rows.append({"label": SIM, "distribution": prod["kind"], "deductible_d": d,
                        "expected_payout_per_unit_size": per_d[d]["expected_unit"],
                        "informed_loss_per_b_KL": informed_loss_per_b(probs), **break_even[d]})

    os.makedirs(a.out, exist_ok=True)
    write_csv(os.path.join(a.out, "hedge_pricing.csv"), rows)
    write_csv(os.path.join(a.out, "break_even.csv"), be_rows)
    labels = lmsr.count_bucket_labels(edges)
    brow = bucket_rows(prod, a.d)
    write_csv(os.path.join(a.out, "registered_buckets.csv"), brow)
    write_csv(os.path.join(a.out, "distribution.csv"), [
        {"bucket": lab, "distribution": prod["kind"],
         "train_seasons_in_bucket": "" if prod["tally"] is None else prod["tally"][j],
         "smoothed_train_probability": probs[j], "uniform_start_price": 1.0 / 6, "bucket_mean_m_j": prod["means"][j]}
        for j, lab in enumerate(labels)])
    make_figure(os.path.join(a.out, "stepped_hedge_price.png"), rows, a.b, prod["kind"], a.d, a.loading)

    gas_path = os.path.join(a.out, "gas_report.json")
    gas = json.load(open(gas_path)) if os.path.exists(gas_path) else None
    ctx = {
        "prod": prod, "dist": prod, "rows": rows, "labels": labels, "edges": list(edges), "bucket_rows": brow,
        "b_grid": a.b, "sizes": a.sizes, "d_grid": a.d, "loading": a.loading, "holdings": holdings,
        "per_d": per_d, "break_even": break_even, "kl": informed_loss_per_b(probs), "gas": gas,
        "fee_cap_all": informed_loss_per_b(probs) / math.log(1.0 / (6.0 * min(probs))),
    }
    write_summary(os.path.join(a.out, "summary.md"), ctx)
    with open(os.path.join(a.out, "manifest.json"), "w") as fh:
        json.dump({
            "label": "SIMULATED. LMSR cost rule only. No real orders, no live chain. The fee is hypothetical.",
            "script": "python -m sim.experiment",
            "written_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M"),
            "distribution": prod["kind"], "distribution_description": prod["description"],
            "train_seasons": prod["seasons"], "train_counts": prod["counts"],
            "edges": list(edges), "edges_rule": prod["edges_rule"],
            "ties_adjusted": None if prod["registered"] is None else prod["registered"]["adjusted"],
            "bucket_means_m_j": prod["means"], "bucket_probabilities_q_j": probs, "alpha": a.alpha,
            "deductibles_run": a.d, "deductible_status": "NOT CHOSEN YET (evaluation workstream chooses d on TRAIN)",
            "holdings_per_unit_size": {f"{d:g}": holdings[d] for d in a.d},
            "loading": a.loading, "b_grid": a.b, "sizes": a.sizes,
            "informed_loss_per_b_KL": informed_loss_per_b(probs),
            "break_even": {f"{d:g}": break_even[d] for d in a.d},
            "outputs": ["registered_buckets.csv", "hedge_pricing.csv", "break_even.csv", "distribution.csv",
                        "stepped_hedge_price.png", "summary.md"],
            "not_simulated": ["season counts (if distribution is OBSERVED)", "gas_report.json (local Hardhat EVM, not Sepolia)"],
        }, fh, indent=1)
    print("wrote", os.path.relpath(a.out, ROOT), "| distribution:", prod["kind"], "| edges:", list(edges))
    return ctx


if __name__ == "__main__":
    main()
