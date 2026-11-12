"""Phase 3 rain reach, step 1: the candidate station list.

    python scripts/reach_rain_stations.py

Reads  data/raw/rain/reach/meta/<ST>_ASOS.geojson   (IEM network metadata, cached; NJ NY PA copied from Phase 0)
       data/processed/panel/stations.csv             (has_cli, cli_id; mapped by ICAO id K<sid>)
       data/raw/rain/ncei_global_hourly_probe/isd-history.csv (USAF/WBAN ids for the NCEI pre-1997 pull)
Writes data/processed/reach/rain_stations_candidates.csv

Rule: every station in the six ASOS networks whose IEM archive begins on or before 2005-12-31.
"""
import json
import os

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
META = os.path.join(ROOT, "data", "raw", "rain", "reach", "meta")
OUT = os.path.join(ROOT, "data", "processed", "reach")
STATES = ("NJ", "NY", "PA", "CT", "DE", "MD")
CUTOFF = "2005-12-31"


def load_networks() -> pd.DataFrame:
    rows = []
    for st in STATES:
        d = json.load(open(os.path.join(META, f"{st}_ASOS.geojson")))
        for f in d["features"]:
            p = f["properties"]
            lon, lat = f["geometry"]["coordinates"]
            rows.append(dict(sid=p["sid"], name=p.get("sname"), state=p.get("state"), network=p.get("network"),
                             lat=lat, lon=lon, elev_m=p.get("elevation"), archive_begin=p.get("archive_begin"),
                             archive_end=p.get("archive_end"), ncdc81=p.get("ncdc81"), ncei91=p.get("ncei91"),
                             ghcnh_id=(p.get("attributes") or {}).get("GHCNH_ID"),
                             has_phour=(p.get("attributes") or {}).get("HAS_PHOUR")))
    return pd.DataFrame(rows)


def isd_ids(wban: str, hist: pd.DataFrame) -> str:
    """All USAF+WBAN ids in isd-history for this WBAN, comma separated (NCEI v1 API station ids)."""
    h = hist[hist["WBAN"] == wban]
    return ",".join(sorted(set(h["USAF"] + h["WBAN"])))


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    st = load_networks()
    st = st[st["archive_begin"].notna() & (st["archive_begin"] <= CUTOFF)].copy()
    panel = pd.read_csv(os.path.join(ROOT, "data", "processed", "panel", "stations.csv"))
    cli = panel[panel["has_cli"] == True][["cli_id", "id", "name"]].rename(  # noqa: E712
        columns={"id": "panel_ghcn_id", "name": "panel_name"})
    cli["sid"] = cli["cli_id"].str[1:]
    st = st.merge(cli, on="sid", how="left")
    st["has_cli"] = st["cli_id"].notna()
    hist = pd.read_csv(os.path.join(ROOT, "data", "raw", "rain", "ncei_global_hourly_probe", "isd-history.csv"),
                       dtype=str)
    wban = st["ghcnh_id"].fillna(st["ncdc81"]).fillna("").str.extract(r"USW000(\d{5})")[0]
    st["wban"] = wban
    st["isd_ids"] = [isd_ids(w, hist) if isinstance(w, str) else "" for w in wban]
    st = st.sort_values(["archive_begin", "sid"]).reset_index(drop=True)
    st.to_csv(os.path.join(OUT, "rain_stations_candidates.csv"), index=False)
    print(len(st), "candidate stations;", int(st["has_cli"].sum()), "with a climate report")
    print(st.groupby("state").size().to_dict())
    print(st[["sid", "state", "archive_begin", "has_cli", "isd_ids"]].to_string())
