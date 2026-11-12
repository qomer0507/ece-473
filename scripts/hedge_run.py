"""Run every registered Phase 2 case (docs/PHASE2_PREREG.md) and the labelled sensitivities.

    python scripts/hedge_run.py

Reads   data/processed/rain/daily_{TTN,PHL,ABE,PNE,DYL}.parquet      OBSERVED station rain
        data/processed/kalshi_rain/price_model.json                   MODELLED Kalshi price parameters (Phase 1)
        data/processed/rain/parks.csv, data/processed/rain_probe/park_station_distances.csv   coordinates
Writes  results/phase2/metrics_tidy.csv        case x variant x strategy x window x metric, value and 95% interval
        results/phase2/train_params.csv        TRAIN-chosen parameters per case and variant
        results/phase2/season_net_cost.csv     per season: observed counts, payout, premium, net cost per strategy
        results/phase2/standin_distances.csv   stand-in gauge distances
        data/processed/hedge/season_aggregates.csv   D_park, C_S, K_S and joint usable days per case and season
Variants: main (loading 0.20, fitted markup); loading_0.10; loading_0.30; markup_0.068; edges_linear_floor.
"""
import json
import math
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.hedge_eval import cases as hc  # noqa: E402
from src.hedge_eval import data as hd  # noqa: E402
from src.kalshi.rain_price_model import load_params  # noqa: E402

RAIN = os.path.join(ROOT, "data", "processed", "rain")
PROBE = os.path.join(ROOT, "data", "processed", "rain_probe")
HEDGE = os.path.join(ROOT, "data", "processed", "hedge")
OUT = os.path.join(ROOT, "results", "phase2")
STATIONS = ("TTN", "PHL", "ABE", "PNE", "DYL")
MARKUP_SENSITIVITY = 0.068
INPUTS = {True: "observed weather only", False: "observed weather, modelled prices"}


def variants(price: dict) -> list[tuple[str, dict, float, str]]:
    """(name, price parameters, loading, edge method) for the main run and each registered sensitivity."""
    low = dict(price, a=MARKUP_SENSITIVITY)
    return [("main", price, 0.20, "inverse_cdf"), ("loading_0.10", price, 0.10, "inverse_cdf"),
            ("loading_0.30", price, 0.30, "inverse_cdf"), ("markup_0.068", low, 0.20, "inverse_cdf"),
            ("edges_linear_floor", price, 0.20, "linear_floor")]


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    """Great-circle distance in km (Earth radius 6371.0088 km)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371.0088 * math.asin(math.sqrt(a))


def distances() -> pd.DataFrame:
    """Distance from each stand-in gauge to Sesame Place and to the settlement stations."""
    st = pd.read_csv(os.path.join(PROBE, "park_station_distances.csv")).drop_duplicates("asos_id").set_index("asos_id")
    park = pd.read_csv(os.path.join(RAIN, "parks.csv")).set_index("park_id").loc["sesame_place"]
    rows = []
    for sid in ("PNE", "DYL", "TTN"):
        lat, lon = float(st.loc[sid, "st_lat"]), float(st.loc[sid, "st_lon"])
        r = {"gauge": sid, "name": st.loc[sid, "station_name"], "lat": lat, "lon": lon,
             "km_to_sesame_place": round(haversine_km(lat, lon, float(park["lat"]), float(park["lon"])), 1)}
        for other in ("TTN", "PHL"):
            r[f"km_to_{other}"] = round(haversine_km(lat, lon, float(st.loc[other, "st_lat"]),
                                                     float(st.loc[other, "st_lon"])), 1)
        rows.append(r)
    out = pd.DataFrame(rows)
    out["note"] = "coordinates observed (station metadata); the stand-in gauge is not the park"
    return out


def params_row(case, variant, p) -> dict:
    fmt = lambda xs, k=3: json.dumps([round(float(x), k) for x in xs])  # noqa: E731
    return {
        "case": case.case_id, "registered": case.registered, "variant": variant, "settlement": case.settlement,
        "park_gauge": case.park, "train_window": f"{case.train[0]}-{case.train[1]}",
        "report_window": f"{case.report[0]}-{case.report[1]}", "n_train_seasons": len(p.train_seasons),
        "train_reference_mean_D_park": round(p.reference, 4), "loading": p.loading, "markup_a": p.price_params["a"],
        "n_strategy2": p.n2, "n_strategy5": p.n5, "edges": json.dumps(p.edges), "edges_raw_quantiles": json.dumps(p.edges_raw),
        "edges_repaired": p.edges != p.edges_raw, "edge_method": p.edge_method, "m_j": fmt(p.m), "train_bucket_counts_n_j": json.dumps(p.n_j),
        "q_j": fmt(p.q, 4), "d_strategy3": p.d3, "h_j": fmt(p.h), "premium_strategy3": round(p.premium3, 4),
        "d_strategy4": p.d4, "premium_strategy4": round(p.premium4, 4),
        "p_month": json.dumps({str(k): round(v, 4) for k, v in sorted(p.p_month.items()) if k != 0}),
        "train_HE_in_sample": json.dumps({k: round(v, 4) for k, v in p.train_he.items() if k in case.strategies}),
        "train_seasons": json.dumps(p.train_seasons),
        "label": "edges, m_j, n_j, d, n, p_month from OBSERVED TRAIN weather; premiums MODELLED",
    }


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(HEDGE, exist_ok=True)
    price = {k: float(v) for k, v in load_params()["models"]["skill"].items() if k in ("a", "s", "u")}
    daily = {s: hd.load_daily(RAIN, s) for s in STATIONS}
    metrics, params, seasons, aggs = [], [], [], []
    for case in hc.registered_cases() + hc.sensitivity_cases():
        for name, pp, loading, method in variants(price):
            res = hc.run_case(case, daily, pp, loading, method)
            m = res["metrics"].copy()
            m.insert(0, "variant", name)
            m.insert(0, "registered", case.registered)
            m.insert(0, "case", case.case_id)
            m["strategy_label"] = m["strategy"].map(hc.STRATEGY_LABEL).fillna("difference in HE: " + m["strategy"])
            m["inputs"] = [INPUTS[s == "0"] for s in m["strategy"]]
            m["interval"] = "95% percentile, 2000 season draws, seed 473 (REPORT only; TRAIN is in-sample)"
            metrics.append(m)
            params.append(params_row(case, name, res["params"]))
            s = res["seasons"].copy()
            s.insert(0, "variant", name)
            s.insert(0, "case", case.case_id)
            s["inputs"] = "n_days, D_park, C_S, K_S observed; payout from observed counts; premium and net_cost MODELLED"
            seasons.append(s)
            if name == "main":
                a = s[s["strategy"] == "0"][["case", "window", "season", "n_days", "D_park", "C_S", "K_S"]].copy()
                a["label"] = "observed"
                aggs.append(a)
        print("done", case.case_id, flush=True)
    pd.concat(metrics, ignore_index=True).to_csv(os.path.join(OUT, "metrics_tidy.csv"), index=False)
    pd.DataFrame(params).to_csv(os.path.join(OUT, "train_params.csv"), index=False)
    pd.concat(seasons, ignore_index=True).round(6).to_csv(os.path.join(OUT, "season_net_cost.csv"), index=False)
    pd.concat(aggs, ignore_index=True).to_csv(os.path.join(HEDGE, "season_aggregates.csv"), index=False)
    distances().to_csv(os.path.join(OUT, "standin_distances.csv"), index=False)
    print("written to", OUT)
