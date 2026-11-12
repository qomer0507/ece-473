"""Phase 3, Question 1, temperature part: pairs, HE per pair, reach curve, regression. EXPLORATORY.

    python scripts/reach_temp_run.py

Reads   data/processed/panel/stations.csv, tmax_panel.parquet        OBSERVED TMAX panel (84 exposure stations)
        results/part1/location_geography.csv                         coast_km per exposure station (Phase 1)
Writes  data/processed/reach/temp_pairs.csv          one row per (S, G) pair: distance, counts, d, premium, HE, ...
        data/processed/reach/temp_pair_seasons.csv   per pair and season: joint days, C_S, C_G, window
        results/phase3/temp_reach_curve.csv          10 km bins, mean HE, 95% bands (pair and gauge bootstrap)
        results/phase3/temp_reach_numbers.csv        reach under both schemes
        results/phase3/temp_regression.csv           OLS coefficients (all pairs; and without same-station pairs)
        results/phase3/temp_listing.csv              per exposure gauge: nearest CLI station and its HE
        *_sens_dgrid40.csv                           LABELLED SENSITIVITY (not registered): d grid widened to {0..40}
Rules: docs/PHASE3_PREREG.md and the reading choices in docs/status/phase3_temp.md. Nothing is dropped after
seeing results; pairs that fail the usable rule or have undefined HE stay in temp_pairs.csv with a status.
"""
import json
import os
import sys
import time

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.panel.hedge import to_wide, haversine_km  # noqa: E402
from src.reach_temp import pairs as rp  # noqa: E402
from src.reach_temp import contract as rc  # noqa: E402
from src.reach_temp import curve as rcv  # noqa: E402
from src.reach_temp import regress as rr  # noqa: E402

PANEL = os.path.join(ROOT, "data", "processed", "panel")
REACH = os.path.join(ROOT, "data", "processed", "reach")
OUT = os.path.join(ROOT, "results", "phase3")


SENS_D_GRID = tuple(range(0, 41))   # labelled sensitivity only


def main() -> None:
    t0 = time.time()
    os.makedirs(REACH, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    stations = pd.read_csv(os.path.join(PANEL, "stations.csv"))
    geo = pd.read_csv(os.path.join(ROOT, "results", "part1", "location_geography.csv")).set_index("id")
    wide = to_wide(pd.read_parquet(os.path.join(PANEL, "tmax_panel.parquet")))
    run(stations, geo, wide, rc.D_GRID, "", t0)
    run(stations, geo, wide, SENS_D_GRID, "_sens_dgrid40", t0)


def run(stations, geo, wide, d_grid, suffix, t0) -> None:
    """One full pass. suffix '' is the registered run; anything else is a labelled sensitivity."""
    pairs = rp.build_pairs(stations)
    print(f"[{suffix or 'registered'}] pairs: {len(pairs)} ({int(pairs['same_station'].sum())} same-station)")

    rows, seas_rows = [], []
    for pr in pairs.itertuples():
        seasons = rp.pair_seasons(wide, pr.s_id, pr.g_id)
        res = rc.evaluate_pair(seasons, d_grid=d_grid)
        res["agreement"] = rp.trigger_agreement(seasons)
        res["count_corr"] = rp.count_correlation(seasons)
        res["n_seasons_in_panel"] = int(len(seasons))
        rows.append(res)
        s = seasons.copy()
        s.insert(0, "g_id", pr.g_id)
        s.insert(0, "s_id", pr.s_id)
        s["window"] = np.where(~s["usable"], "unusable",
                               np.where(s["season"] <= (res["train_last"] if res["n_train"] else -1), "TRAIN",
                                        np.where(s["season"] >= (res["report_first"] if res["n_report"] else 1e9),
                                                 "REPORT", "unused")))
        seas_rows.append(s)
    pairs = pd.concat([pairs, pd.DataFrame(rows)], axis=1)
    pairs["coast_km_g"] = pairs["g_id"].map(geo["coast_km"])
    pairs["coast_g"] = (pairs["coast_km_g"] <= rr.COAST_KM).astype(int)
    pairs["d_grid"] = f"{min(d_grid)}..{max(d_grid)}"
    pairs.to_csv(os.path.join(REACH, f"temp_pairs{suffix}.csv"), index=False)
    if not suffix:
        pd.concat(seas_rows, ignore_index=True).to_csv(os.path.join(REACH, "temp_pair_seasons.csv"), index=False)
    print(pairs["status"].value_counts().to_dict(), f"{time.time() - t0:.0f} s")

    curve = rcv.curve_table(pairs)
    curve.to_csv(os.path.join(OUT, f"temp_reach_curve{suffix}.csv"), index=False)
    reach = []
    for scheme in ("pair", "gauge"):
        r = rcv.reach_km(curve, f"lo_{scheme}")
        r["scheme"] = scheme
        reach.append(r)
    reach = pd.DataFrame(reach)
    reach.to_csv(os.path.join(OUT, f"temp_reach_numbers{suffix}.csv"), index=False)
    print(reach.to_string(index=False))

    tabs = []
    for name, sub in (("all_pairs", pairs), ("excluding_same_station", pairs[~pairs["same_station"]])):
        tab, info = rr.ols_table(sub)
        tab.insert(0, "sample", name)
        for k, v in info.items():
            tab[k] = v
        tabs.append(tab)
    pd.concat(tabs, ignore_index=True).to_csv(os.path.join(OUT, f"temp_regression{suffix}.csv"), index=False)

    # listing map input: nearest CLI station of every exposure gauge, and the HE of that pair
    exp = stations[stations["is_exposure"].astype(bool)].set_index("id")
    cli = exp[exp["has_cli"].astype(bool)]
    lst = []
    key = pairs.set_index(["s_id", "g_id"])
    for g in exp.itertuples():
        d = haversine_km(g.lat, g.lon, cli["lat"].to_numpy(), cli["lon"].to_numpy())
        j = int(np.argmin(d))
        s_id = cli.index[j]
        row = key.loc[(s_id, g.Index)] if (s_id, g.Index) in key.index else None
        lst.append({"g_id": g.Index, "name": g.name, "state": g.state, "lat": g.lat, "lon": g.lon,
                    "has_cli": bool(g.has_cli), "nearest_cli": s_id, "dist_km": float(d[j]),
                    "he": float(row["he"]) if row is not None else np.nan,
                    "status": row["status"] if row is not None else "no_pair"})
    pd.DataFrame(lst).to_csv(os.path.join(OUT, f"temp_listing{suffix}.csv"), index=False)
    with open(os.path.join(OUT, f"temp_run_info{suffix}.json"), "w") as f:
        json.dump({"n_pairs": int(len(pairs)), "status_counts": pairs["status"].value_counts().to_dict(),
                   "seconds": round(time.time() - t0, 1)}, f, indent=1)
    print(f"done in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
