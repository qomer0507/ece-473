"""Build the audited station table data/processed/panel/stations.csv (SPEC_v2).

Inputs : data/raw/region/stations_region.csv, data/raw/region/tmax/{ID}.csv
         IEM NWSCLI network list (cached in data/processed/panel/iem_cache/)
Outputs: data/processed/panel/stations.csv
         data/processed/panel/cli_mapping.csv  (one row per IEM CLI site in the six states)

Run: python scripts/panel_build_stations.py [--refresh]
"""
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.panel.hedge import LISTED, WINDOWS, haversine_km, season_mask  # noqa: E402

RAW = ROOT / "data/raw/region"
OUT = ROOT / "data/processed/panel"
CACHE = OUT / "iem_cache"
STATES = ["NY", "NJ", "PA", "CT", "DE", "MD"]
CLI_URL = "https://mesonet.agron.iastate.edu/geojson/network/NWSCLI.geojson"
CLI_YEAR_URL = "https://mesonet.agron.iastate.edu/json/cli.py?station={sid}&year={year}"
MATCH_KM = 2.0
CLI_CHECK_YEAR = 2025


def fetch(url, path, refresh=False):
    """Download url to path with curl unless cached. Returns the text."""
    if refresh or not path.exists() or path.stat().st_size == 0:
        for attempt in range(4):  # transient connection resets happen; same URL, short pause
            r = subprocess.run(["curl", "-sS", "-f", "-m", "90", "-o", str(path), url])
            if r.returncode == 0:
                break
            time.sleep(3 * (attempt + 1))
        else:
            path.unlink(missing_ok=True)
            raise RuntimeError(f"download failed: {url}")
        time.sleep(0.3)
    return path.read_text()


def coverage(ids):
    rows = []
    for sid in ids:
        d = pd.read_csv(RAW / "tmax" / f"{sid}.csv", parse_dates=["DATE"])
        d = d[season_mask(d["DATE"]) & d["TMAX"].notna()]
        yr = d["DATE"].dt.year
        row = {"id": sid, "season_days": int(((yr >= 2015) & (yr <= 2025)).sum())}
        row["cov_all"] = row["season_days"] / (153 * 11)
        for w, (a, b) in WINDOWS.items():
            n = int(((yr >= a) & (yr <= b)).sum())
            row[f"cov_{w.lower()}"] = n / (153 * (b - a + 1))
        rows.append(row)
    return pd.DataFrame(rows)


def main(refresh=False):
    CACHE.mkdir(parents=True, exist_ok=True)
    st = pd.read_csv(RAW / "stations_region.csv")
    st = st.merge(coverage(st["id"]), on="id")
    st["network"] = st["id"].str[:3]
    st["is_exposure"] = (
        (st["network"] == "USW") & (st["cov_all"] >= 0.90)
        & (st["cov_fit"] >= 0.80) & (st["cov_select"] >= 0.80) & (st["cov_report"] >= 0.80)
    )
    inv = {v: k for k, v in LISTED.items()}
    st["is_listed"] = st["id"].map(inv).fillna("")

    # --- CLI sites: IEM NWSCLI network, matched to our stations by coordinates ---
    gj = json.loads(fetch(CLI_URL, CACHE / "NWSCLI.geojson", refresh))
    rows = []
    for f in gj["features"]:
        p = f["properties"]
        if p["state"] not in STATES:
            continue
        lon, lat = f["geometry"]["coordinates"]
        d = haversine_km(lat, lon, st["lat"].values, st["lon"].values)
        order = np.argsort(d)
        near = st.iloc[order[0]]
        within = st.iloc[order][d[order] <= MATCH_KM]
        txt = fetch(CLI_YEAR_URL.format(sid=f["id"], year=CLI_CHECK_YEAR),
                    CACHE / f"cli_{f['id']}_{CLI_CHECK_YEAR}.json", refresh)
        res = json.loads(txt)["results"]
        n_season = sum(1 for r in res if "05-01" <= r["valid"][5:] <= "09-30")
        matched = d[order[0]] <= MATCH_KM
        iem_ids = {p.get("ncdc81"), p.get("ncei91")}
        # Rule: nearest station within 2 km. If several stations are within 2 km and exactly one of them
        # is the GHCN id IEM itself lists for the site (ncei91, else ncdc81), take that one instead.
        pick, rule = near, "nearest"
        if matched and len(within) > 1 and near["id"] not in iem_ids:
            for key in ("ncei91", "ncdc81"):
                hit = within[within["id"] == p.get(key)]
                if len(hit) == 1:
                    pick, rule = hit.iloc[0], f"iem_{key}_within_2km"
                    break
        rows.append({
            "cli_id": f["id"], "cli_name": p["sname"], "state": p["state"], "cli_lat": lat, "cli_lon": lon,
            "iem_ncdc81": p.get("ncdc81"), "iem_ncei91": p.get("ncei91"),
            "nearest_id": near["id"], "nearest_name": near["name"], "nearest_km": round(float(d[order[0]]), 3),
            "n_within_2km": len(within), "ids_within_2km": ";".join(within["id"]),
            "matched_id": pick["id"] if matched else "", "match_rule": rule if matched else "",
            "matched_km": round(float(haversine_km(lat, lon, pick["lat"], pick["lon"])), 3) if matched else np.nan,
            "agrees_with_iem_id": bool(matched and pick["id"] in iem_ids),
            f"cli_season_days_{CLI_CHECK_YEAR}": n_season,
            "ambiguous": bool((not matched) or len(within) > 1 or near["id"] not in iem_ids),
        })
    cm = pd.DataFrame(rows).sort_values("cli_id")
    cm.to_csv(OUT / "cli_mapping.csv", index=False)

    ok = cm[(cm["matched_id"] != "") & (cm[f"cli_season_days_{CLI_CHECK_YEAR}"] > 0)]
    m = dict(zip(ok["matched_id"], ok["cli_id"]))
    st["cli_id"] = st["id"].map(m).fillna("")
    st["has_cli"] = st["cli_id"] != ""
    st["is_candidate"] = st["is_exposure"] & st["has_cli"] & (st["is_listed"] == "")
    st["station_inferred"] = st["id"] == LISTED["Philadelphia"]
    cols = ["id", "name", "state", "lat", "lon", "elev_m", "network", "season_days", "cov_all", "cov_fit",
            "cov_select", "cov_report", "is_exposure", "is_listed", "has_cli", "cli_id", "is_candidate",
            "station_inferred"]
    st = st[cols].sort_values("id")
    for c in ["cov_all", "cov_fit", "cov_select", "cov_report"]:
        st[c] = st[c].round(4)
    st.to_csv(OUT / "stations.csv", index=False)

    print(f"stations: {len(st)}  USW: {(st.network == 'USW').sum()}  exposure: {st.is_exposure.sum()}")
    print(f"CLI sites in six states: {len(cm)}  matched <= {MATCH_KM} km: {(cm.matched_id != '').sum()}  "
          f"ambiguous: {cm.ambiguous.sum()}")
    print(f"has_cli: {st.has_cli.sum()}  exposure & has_cli: {(st.is_exposure & st.has_cli).sum()}  "
          f"candidates: {st.is_candidate.sum()}")
    print("listed:\n", st[st.is_listed != ""][["id", "name", "is_listed", "cov_all", "cov_fit", "cov_select",
                                               "cov_report", "is_exposure", "has_cli", "cli_id"]].to_string(index=False))
    print("ambiguous / unmatched CLI sites:\n", cm[cm.ambiguous].to_string(index=False))


if __name__ == "__main__":
    main(refresh="--refresh" in sys.argv)
