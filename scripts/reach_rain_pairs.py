"""Phase 3 rain reach, step 4: pairs, HE, the reach curve, the regression and the station-level table.

    python scripts/reach_rain_pairs.py

Reads  data/processed/reach/rain_stations.csv, data/processed/reach/rain_daily/daily_<SID>.parquet
Writes data/processed/reach/rain_pairs.csv            one row per (S, G) pair within 200 km, plus S = G
       data/processed/reach/rain_pairs_excluded.csv   pairs that fail the usable rule, with the reason
       results/phase3/rain_reach_curve.csv            10-km bins: n, mean HE, bands (pair and gauge bootstrap), mean r
       results/phase3/rain_reach_regression.csv       OLS of HE on distance, elevation difference, coast
       results/phase3/rain_reach_numbers.json         reach in km under both schemes, Trenton-PNE, counts
       results/phase3/rain_station_table.csv          per exposure gauge: best settlement station, nearest CLI station
       results/phase3/rain_reach_curve_sensitivity.csv  curve with the pairs of < 20 joint seasons included
Observed weather, modelled premiums. EXPLORATORY (docs/PHASE3_PREREG.md).
"""
import json
import os
import sys
import time

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.reach import rain_curve as rc  # noqa: E402
from src.reach import rain_pairs as rp  # noqa: E402

PROC = os.path.join(ROOT, "data", "processed", "reach")
DAILY = os.path.join(PROC, "rain_daily")
RES = os.path.join(ROOT, "results", "phase3")
FIRST, LAST = 1941, 2026


def log(msg: str) -> None:
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def station_table(scored: pd.DataFrame, stations: pd.DataFrame) -> pd.DataFrame:
    """Per exposure gauge G: the settlement station with the highest REPORT HE, and the nearest CLI station."""
    rows = []
    cli = stations[(stations["kept"] == True) & (stations["has_cli"] == True)]  # noqa: E712
    for g, grp in scored.groupby("g_id"):
        ok = grp[~grp["he"].isna()]
        best = ok.sort_values(["he", "dist_km"], ascending=[False, True]).iloc[0] if len(ok) else None
        near = grp.sort_values("dist_km").iloc[0]      # S = G when G has a climate report (distance 0)
        rows.append(dict(
            g_id=g, g_name=stations.set_index("sid").loc[g, "name"], g_has_cli=bool(near["same_station"]) or
            g in set(cli["sid"]), n_settlement_candidates=int(len(grp)), n_he_defined=int(len(ok)),
            best_s_id=best["s_id"] if best is not None else None,
            best_dist_km=round(float(best["dist_km"]), 1) if best is not None else np.nan,
            best_he=float(best["he"]) if best is not None else np.nan,
            best_corr=float(best["count_corr"]) if best is not None else np.nan,
            nearest_cli_s_id=near["s_id"], nearest_cli_dist_km=round(float(near["dist_km"]), 1),
            nearest_cli_he=float(near["he"]), nearest_cli_corr=float(near["count_corr"]),
            nearest_cli_n_joint=int(near["n_joint_seasons"]),
        ))
    return pd.DataFrame(rows).sort_values("g_id").reset_index(drop=True)


if __name__ == "__main__":
    os.makedirs(RES, exist_ok=True)
    st = pd.read_csv(os.path.join(PROC, "rain_stations.csv"), dtype={"sid": str, "cli_id": str})
    kept = st[st["kept"] == True]  # noqa: E712
    daily = {sid: pd.read_parquet(os.path.join(DAILY, f"daily_{sid}.parquet")) for sid in kept["sid"]}
    m = rp.build_day_matrix(daily, FIRST, LAST)
    pairs = rp.build_pairs(st)
    log(f"{len(kept)} kept stations, {int(kept['has_cli'].sum())} with a climate report, {len(pairs)} pairs "
        f"(incl. {int(pairs['same_station'].sum())} same-station)")
    allp = rp.evaluate_all(pairs, m)
    allp.to_csv(os.path.join(PROC, "rain_pairs_all.csv"), index=False)
    scored = allp[allp["status"] == "ok"].reset_index(drop=True)
    excluded = allp[allp["status"] != "ok"]
    scored.to_csv(os.path.join(PROC, "rain_pairs.csv"), index=False)
    excluded.to_csv(os.path.join(PROC, "rain_pairs_excluded.csv"), index=False)
    log(f"scored {len(scored)} pairs ({int(scored['he_defined'].sum())} with a defined HE); "
        f"excluded {len(excluded)}: {excluded['status'].value_counts().to_dict()}")

    curve = rc.curve_table(scored)
    curve.to_csv(os.path.join(RES, "rain_reach_curve.csv"), index=False)

    # Labelled sensitivity (reading choice 15): seasons whose opening-hours rain total is 0.00 in are treated as
    # unusable (silent gauge); stations are re-kept at >= 20 seasons; pairs rebuilt and rescored.
    sc = pd.read_csv(os.path.join(PROC, "rain_season_counts.csv"), dtype={"station": str})
    zero = sc[sc["season_usable"] & (sc["open_hours_rain_in"].fillna(0) <= 0)]
    m2 = rp.build_day_matrix(daily, FIRST, LAST)
    for r in zero.itertuples():
        if r.station in m2.ids:
            m2.season_ok[m2.row(r.station), int(r.season) - FIRST] = False
    st2 = st.copy()
    st2["n_usable_nozero"] = st2["n_usable"].fillna(0) - st2["n_usable_zero_rain"].fillna(0)
    st2["kept"] = (st2["kept"] == True) & (st2["n_usable_nozero"] >= 20)  # noqa: E712
    pairs2 = rp.build_pairs(st2)
    allp2 = rp.evaluate_all(pairs2, m2)
    scored2 = allp2[allp2["status"] == "ok"].reset_index(drop=True)
    scored2.to_csv(os.path.join(PROC, "rain_pairs_sens_nozero.csv"), index=False)
    curve2 = rc.curve_table(scored2)
    curve2.to_csv(os.path.join(RES, "rain_reach_curve_sens_nozero.csv"), index=False)
    log(f"no-zero-rain sensitivity: {int(st2['kept'].sum())} stations, {len(scored2)} pairs scored")
    sens = allp[allp["status"].isin(["ok", "few_joint_seasons"])].reset_index(drop=True)
    curve_s = rc.curve_table(sens)
    curve_s.to_csv(os.path.join(RES, "rain_reach_curve_sensitivity.csv"), index=False)

    reg = pd.concat([
        rc.regression(scored, label="all_pairs"),
        rc.regression(scored[~scored["same_station"]], label="without_same_station"),
    ], ignore_index=True)
    reg.to_csv(os.path.join(RES, "rain_reach_regression.csv"), index=False)

    tp = scored[(scored["s_id"] == "TTN") & (scored["g_id"] == "PNE")]
    tp_all = allp[(allp["s_id"] == "TTN") & (allp["g_id"] == "PNE")]
    numbers = {
        "n_candidates": int(len(st)), "n_kept": int(len(kept)), "n_kept_cli": int(kept["has_cli"].sum()),
        "n_pairs_built": int(len(pairs)), "n_pairs_scored": int(len(scored)),
        "n_pairs_he_defined": int(scored["he_defined"].sum()),
        "n_pairs_excluded": excluded["status"].value_counts().to_dict(),
        "n_gauges_scored": int(scored["g_id"].nunique()), "n_settlement_scored": int(scored["s_id"].nunique()),
        "reach_pair_boot": rc.reach_km(curve, "he_lo_pair"), "reach_gauge_boot": rc.reach_km(curve, "he_lo_gauge"),
        "reach_sensitivity_pair_boot": rc.reach_km(curve_s, "he_lo_pair"),
        "reach_sensitivity_gauge_boot": rc.reach_km(curve_s, "he_lo_gauge"),
        "reach_nozero_pair_boot": rc.reach_km(curve2, "he_lo_pair"),
        "reach_nozero_gauge_boot": rc.reach_km(curve2, "he_lo_gauge"),
        "nozero_n_stations": int(st2["kept"].sum()), "nozero_n_pairs_scored": int(len(scored2)),
        "nozero_stations_dropped": sorted(set(kept["sid"]) - set(st2.loc[st2["kept"], "sid"])),
        "trenton_pne": (tp_all.iloc[0].to_dict() if len(tp_all) else None),
        "trenton_pne_scored": bool(len(tp)),
        "same_station": {"n": int(scored["same_station"].sum()),
                         "mean_he": float(scored.loc[scored["same_station"], "he"].mean())},
    }
    with open(os.path.join(RES, "rain_reach_numbers.json"), "w") as fh:
        json.dump(numbers, fh, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    station_table(scored, st).to_csv(os.path.join(RES, "rain_station_table.csv"), index=False)
    log(f"reach (pair bootstrap) {numbers['reach_pair_boot']}, (gauge bootstrap) {numbers['reach_gauge_boot']}")
    log("done")
