"""Tasks 3 and 4: modelled price by lead and HE by lead for the Trenton (A) and Philadelphia (D-same) cases.

    python scripts/leadtime_he.py

Reads  data/processed/rain/daily_{TTN,PHL}.parquet (observed), data/processed/leadtime/mos_pop_{TTN,PHL}.parquet
       (MOS PoP by lead), data/processed/kalshi_rain/price_model.json (a, u), the raw quote table (for the
       observed-end check; aggregates only are written).
Writes results/phase3/leadtime_he_by_lead.csv, results/phase3/leadtime_price_check.csv,
       data/processed/leadtime/season_cost_by_lead.csv.
Windows and rules: docs/status/phase3_leadtime.md, reading choices 5-6 (fixed before this script was run).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.hedge_eval.cases import PHILADELPHIA_WINDOWS, TRENTON_WINDOWS  # noqa: E402
from src.hedge_eval.data import joint_daily, load_daily, season_aggregates, split_windows  # noqa: E402
from src.hedge_eval.strategies import monthly_p  # noqa: E402
from src.leadtime.hedge_by_lead import (A_SENS, available_seasons, evaluate_lead, modelled_ask,  # noqa: E402
                                        pop_with_carry_forward, split_60_40)

REPO = Path(__file__).resolve().parents[1]
RAIN = REPO / "data" / "processed" / "rain"
LT = REPO / "data" / "processed" / "leadtime"
RES = REPO / "results" / "phase3"
QUOTES = REPO / "data" / "raw" / "kalshi" / "rain" / "quote_table.csv"
PRICE_JSON = REPO / "data" / "processed" / "kalshi_rain" / "price_model.json"

CASES = {
    "A (Trenton same-station)": ("TTN", TRENTON_WINDOWS, "worst3"),
    "D-same (Philadelphia same-station)": ("PHL", PHILADELPHIA_WINDOWS, "worst10pct"),
}
# modelled leads: (lead label, line in mos_pop parquet, target lead, family)
MOS_LEADS = [
    ("1 (p06x4)", "GFS-p06x4", 1.0, "GFS"),
    ("1.5", "GFS", 1.5, "GFS"),
    ("2", "GFS", 2.0, "GFS"),
    ("3", "GFS", 3.0, "GFS"),
    ("4", "MEX", 4.0, "MEX"),
    ("5", "MEX", 5.0, "MEX"),
    ("6", "MEX", 6.0, "MEX"),
    ("7", "MEX", 7.0, "MEX"),
]
MARKUPS = {"main": None, "markup_0.068": A_SENS}


def pop_map(mos: pd.DataFrame, line: str, lead: float) -> dict:
    g = mos[(mos["line"] == line) & (np.isclose(mos["target_lead"], lead))]
    return dict(zip(pd.DatetimeIndex(g["date"]), g["pop_used"].astype(float)))


def result_row(case, st, lead_label, lead_days, family, variant, a, r, windows_note, n_source) -> dict:
    m, iv = r.metrics, r.intervals
    return {
        "case": case, "station": st, "lead_label": lead_label, "lead_days": lead_days, "price_source": family,
        "variant": variant, "markup_a": a, "windows": windows_note, "n_source": n_source,
        "n_contracts": r.n, "train_he_in_sample": r.train_he, "n_train_seasons": len(r.train_seasons),
        "n_report_seasons": len(r.report_seasons),
        "report_first": min(r.report_seasons), "report_last": max(r.report_seasons), "reference": r.reference,
        "he": m["he"], "he_lo": iv["he"][0], "he_hi": iv["he"][1], "he_n_boot_valid": iv["he"][2],
        "mean_net_cost": m["mean_net_cost"], "mean_net_cost_lo": iv["mean_net_cost"][0],
        "mean_net_cost_hi": iv["mean_net_cost"][1], "mean_payout": m["mean_payout"], "mean_premium": m["mean_premium"],
        "premium_per_useful_payout": m["premium_per_useful_payout"],
        "premium_per_useful_payout_lo": iv["premium_per_useful_payout"][0],
        "premium_per_useful_payout_hi": iv["premium_per_useful_payout"][1],
        "premium_per_payout": m["premium_per_payout"], "mean_ask_report": r.mean_ask_report,
        "carry_forward_days_train": r.carry_forward_days_train, "carry_forward_days_report": r.carry_forward_days_report,
        "worst_reduction": m["worst_reduction"], "share_seasons_reduced": m["share_seasons_reduced"],
        "label": "MODELLED price, observed weather; exploratory",
    }


def main() -> None:
    price = json.loads(PRICE_JSON.read_text())
    a_main = float(price["models"]["skill"]["a"])
    u = float(price["models"]["skill"]["u"])
    rows, season_rows = [], []
    for case, (st, windows, worst_rule) in CASES.items():
        daily = load_daily(str(RAIN), st)
        joint = joint_daily(daily, daily)
        mos = pd.read_parquet(LT / f"mos_pop_{st}.parquet")
        for variant, a_override in MARKUPS.items():
            a = a_main if a_override is None else a_override
            # ---- lead = infinity on all Phase 2 seasons (Phase 2 windows)
            tr, rp = split_windows(joint, windows[0], windows[1])
            p_month = monthly_p(tr)
            clim_tr = np.array([p_month.get(int(mm), p_month[0]) for mm in tr["month"]])
            clim_rp = np.array([p_month.get(int(mm), p_month[0]) for mm in rp["month"]])
            r = evaluate_lead(tr, rp, clim_tr, clim_rp, np.ones(len(tr), bool), np.ones(len(rp), bool), a, worst_rule,
                              "inf", u)
            rows.append(result_row(case, st, "inf (all seasons)", np.inf, "climatology (TRAIN monthly)", variant, a, r,
                                   f"Phase 2 windows {windows[0][0]}-{windows[0][1]} / {windows[1][0]}-{windows[1][1]}",
                                   "TRAIN"))
            # ---- MOS leads
            fam_state: dict[str, dict] = {}
            for lead_label, line, lead, family in MOS_LEADS:
                pm = pop_map(mos, line, lead)
                pop_all, used_all = pop_with_carry_forward(joint, pm, p_month)
                avail = available_seasons(joint, used_all)
                if not avail:
                    rows.append({"case": case, "station": st, "lead_label": lead_label, "lead_days": lead,
                                 "price_source": family, "variant": variant, "markup_a": a,
                                 "windows": "no available season", "label": "not available"})
                    continue
                j = joint[joint["season"].isin(avail)].reset_index(drop=True)
                # windows for this family
                if family == "GFS":
                    tr_s = [s for s in avail if windows[0][0] <= s <= windows[0][1]]
                    rp_s = [s for s in avail if windows[1][0] <= s <= windows[1][1]]
                    note = "Phase 2 windows restricted to MOS seasons"
                    if len(tr_s) < 5:
                        tr_s, rp_s = split_60_40(avail)
                        note = "60/40 split of MOS seasons (Phase 2 TRAIN window has no MOS season)"
                    n_fixed = reference_fixed = None
                    n_source = "TRAIN at this lead"
                else:  # MEX: no TRAIN window; n and reference from the station's GFS lead-3 TRAIN
                    g3 = fam_state.get("GFS")
                    if g3 is None:
                        raise RuntimeError("GFS lead 3 must run before the MEX leads")
                    tr_s, rp_s = [], avail
                    note = f"all MOS seasons are REPORT; n and reference from GFS lead 3 ({g3['note']})"
                    n_fixed, reference_fixed = g3["n"], g3["reference"]
                    n_source = "GFS lead-3 TRAIN (same station)"
                tr_d = j[j["season"].isin(tr_s)].reset_index(drop=True)
                rp_d = j[j["season"].isin(rp_s)].reset_index(drop=True)
                p_month_lead = monthly_p(tr_d) if len(tr_d) else fam_state["GFS"]["p_month"]
                pop_tr, used_tr = pop_with_carry_forward(tr_d, pm, p_month_lead)
                pop_rp, used_rp = pop_with_carry_forward(rp_d, pm, p_month_lead)
                r = evaluate_lead(tr_d, rp_d, pop_tr, pop_rp, used_tr, used_rp, a, worst_rule, lead_label, u,
                                  n_fixed=n_fixed, reference_fixed=reference_fixed)
                rows.append(result_row(case, st, lead_label, lead, family, variant, a, r, note, n_source))
                if family == "GFS" and lead == 3.0:
                    fam_state["GFS"] = {"n": r.n, "reference": r.reference, "note": note, "tr_s": tr_s, "rp_s": rp_s,
                                        "p_month": p_month_lead}
                # climatology price on the same windows (comparable infinity point)
                if lead in (3.0, 7.0):
                    ctr = np.array([p_month_lead.get(int(mm), p_month_lead[0]) for mm in tr_d["month"]])
                    crp = np.array([p_month_lead.get(int(mm), p_month_lead[0]) for mm in rp_d["month"]])
                    rc = evaluate_lead(tr_d, rp_d, ctr, crp, np.ones(len(tr_d), bool), np.ones(len(rp_d), bool), a,
                                       worst_rule, "inf", u, n_fixed=n_fixed if family == "MEX" else None,
                                       reference_fixed=reference_fixed if family == "MEX" else None)
                    rows.append(result_row(case, st, f"inf (same seasons as {family} leads)", np.inf,
                                           "climatology (TRAIN monthly)", variant, a, rc, note,
                                           n_source if family == "MEX" else "TRAIN at lead inf on these seasons"))
                # per-season detail (main variant only)
                if variant == "main":
                    from src.leadtime.hedge_by_lead import season_unit_table
                    for wname, dd, pp in (("TRAIN", tr_d, pop_tr), ("REPORT", rp_d, pop_rp)):
                        if not len(dd):
                            continue
                        ut = season_unit_table(dd, pp, a, u)
                        ag = season_aggregates(dd)
                        ut = ut.merge(ag, on="season")
                        ut.insert(0, "window", wname); ut.insert(0, "lead_label", lead_label); ut.insert(0, "case", case)
                        ut["n_contracts"] = r.n
                        season_rows.append(ut)
    out = pd.DataFrame(rows)
    RES.mkdir(parents=True, exist_ok=True)
    out.to_csv(RES / "leadtime_he_by_lead.csv", index=False, float_format="%.4f")
    pd.concat(season_rows, ignore_index=True).to_csv(LT / "season_cost_by_lead.csv", index=False, float_format="%.4f")
    cols = ["case", "lead_label", "variant", "n_contracts", "n_train_seasons", "n_report_seasons", "he", "he_lo",
            "he_hi", "mean_net_cost", "premium_per_useful_payout", "premium_per_payout", "mean_ask_report",
            "carry_forward_days_report", "windows"]
    print(out[cols].to_string(index=False))
    price_check(a_main, u)


def price_check(a_main: float, u: float) -> None:
    """Observed-end check: modelled ask at lead 1.5 (GFS 18Z run of D-1) vs the real 36-hour ask, 2025-2026.
    Only aggregates are written."""
    q = pd.read_csv(QUOTES)
    q["date"] = pd.to_datetime(q["date"])
    rows = []
    for st, city in (("TTN", "TTN"), ("PHL", "PHIL")):
        mos = pd.read_parquet(LT / f"mos_pop_{st}.parquet")
        for line, lead in (("GFS", 1.5), ("GFS-p06x4", 1.0), ("GFS-p06x4", 1.5), ("MEX", 1.5), ("MEX-p12x2", 1.5), ("NBS", 1.5)):
            pm = pop_map(mos, line, lead)
            if not pm:
                continue
            qq = q[(q["city"] == city) & (q["series"] == "KXRAIN") & q["buyable_36"].fillna(False).astype(bool)]
            qq = qq[qq["date"].isin(list(pm.keys()))]
            if qq.empty:
                continue
            for a_label, a in (("main", a_main), ("markup_0.068", A_SENS)):
                mod = np.array([modelled_ask(pm[d], a) for d in qq["date"]])
                obs = qq["ask_36"].astype(float).to_numpy()
                res = qq["result"].astype(int).to_numpy()
                rows.append({"station": st, "line": line, "target_lead": lead, "markup": a_label, "a": a,
                             "n_days": len(qq), "mean_observed_ask_36h": obs.mean(), "mean_modelled_ask": mod.mean(),
                             "mean_difference_modelled_minus_observed": mod.mean() - obs.mean(),
                             "rmse_daily": float(np.sqrt(np.mean((mod - obs) ** 2))),
                             "corr_daily": float(np.corrcoef(mod, obs)[0, 1]) if len(qq) > 2 else np.nan,
                             "mean_observed_ask_rain": obs[res == 1].mean() if (res == 1).any() else np.nan,
                             "mean_modelled_ask_rain": mod[res == 1].mean() if (res == 1).any() else np.nan,
                             "mean_observed_ask_dry": obs[res == 0].mean() if (res == 0).any() else np.nan,
                             "mean_modelled_ask_dry": mod[res == 0].mean() if (res == 0).any() else np.nan,
                             "mean_pop": float(np.mean([pm[d] for d in qq["date"]])), "rain_share": res.mean(),
                             "label": "observed ask vs MODELLED ask on the same days (2026 KXRAIN)"})
    t = pd.DataFrame(rows)
    t.to_csv(RES / "leadtime_price_check.csv", index=False, float_format="%.4f")
    print(t[["station", "line", "target_lead", "markup", "n_days", "mean_observed_ask_36h", "mean_modelled_ask",
             "mean_difference_modelled_minus_observed", "rmse_daily", "corr_daily"]].to_string(index=False))


if __name__ == "__main__":
    main()
