"""Phase 0 rain probe: park coordinates and haversine distances to nearby ASOS / climate-report stations.

Park coordinates: English Wikipedia infobox coordinates (pages named in the source column), read 2026-11-12.
Station coordinates: IEM network metadata (data/raw/rain/iem_meta/*_ASOS.geojson).
has_cli: from data/processed/panel/stations.csv, joined on the GHCN id IEM lists for the ASOS site (GHCNH_ID).
Distance: src/panel/hedge.py haversine_km.
Outputs: data/processed/rain_probe/parks.csv, park_station_distances.csv
"""
import json, os, sys
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from src.panel.hedge import haversine_km  # noqa: E402

OUT = os.path.join(ROOT, "data", "processed", "rain_probe")
PARKS = [
    ("sesame_place", "Sesame Place Philadelphia", "Langhorne (Middletown Twp), PA", 40.18500, -74.87194,
     "https://en.wikipedia.org/wiki/Sesame_Place_Philadelphia"),
    ("great_adventure", "Six Flags Great Adventure", "Jackson, NJ", 40.13750, -74.44000,
     "https://en.wikipedia.org/wiki/Six_Flags_Great_Adventure"),
    ("dorney_park", "Dorney Park & Wildwater Kingdom", "Dorneyville (Allentown), PA", 40.5779417, -75.5315278,
     "https://en.wikipedia.org/wiki/Dorney_Park_%26_Wildwater_Kingdom"),
    ("luna_park", "Luna Park (Coney Island)", "Brooklyn, NY", 40.573972, -73.978479,
     "https://en.wikipedia.org/wiki/Luna_Park_(Coney_Island,_2010)"),
]
INTEREST = ["TTN", "PHL", "PNE", "ABE", "EWR", "NYC", "JFK", "LGA", "WRI", "NEL", "BLM", "DYL"]

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    parks = pd.DataFrame(PARKS, columns=["park_id", "name", "place", "lat", "lon", "coord_source"])
    parks.to_csv(os.path.join(OUT, "parks.csv"), index=False)
    st = pd.read_csv(os.path.join(ROOT, "data", "processed", "panel", "stations.csv"), dtype={"cli_id": str})
    st = st.set_index("id")
    rows = []
    for net in ("NJ_ASOS", "PA_ASOS", "NY_ASOS"):
        for f in json.load(open(os.path.join(ROOT, "data", "raw", "rain", "iem_meta", f"{net}.geojson")))["features"]:
            p = f["properties"]
            lon, lat = f["geometry"]["coordinates"]
            gid = (p.get("attributes") or {}).get("GHCNH_ID")
            rows.append(dict(asos_id=p["sid"], station_name=p["sname"], network=net, st_lat=lat, st_lon=lon,
                             ghcn_id=gid, iem_archive_begin=p.get("archive_begin"), iem_archive_end=p.get("archive_end"),
                             is_awos=(p.get("attributes") or {}).get("IS_AWOS") == "1"))
    S = pd.DataFrame(rows)
    out = []
    for _, pk in parks.iterrows():
        d = S.copy()
        d["distance_km"] = haversine_km(pk.lat, pk.lon, d.st_lat.values, d.st_lon.values).round(1)
        d = d[(d.distance_km <= 45) | d.asos_id.isin(INTEREST)]
        d.insert(0, "park_id", pk.park_id)
        out.append(d)
    D = pd.concat(out, ignore_index=True)
    D["in_stations_csv"] = D.ghcn_id.isin(st.index)
    D["has_cli"] = D.ghcn_id.map(st.has_cli).map({True: "True", False: "False"}).fillna("not in stations.csv")
    D["cli_id"] = D.ghcn_id.map(st.cli_id).fillna("")
    D["station_of_interest"] = D.asos_id.isin(INTEREST)
    D["rank_for_park"] = D.groupby("park_id").distance_km.rank(method="first").astype(int)
    D = D.sort_values(["park_id", "distance_km"])
    D.to_csv(os.path.join(OUT, "park_station_distances.csv"), index=False)
    pd.set_option("display.width", 250)
    print(D[D.distance_km <= 60][["park_id", "asos_id", "station_name", "distance_km", "has_cli", "cli_id",
                                   "iem_archive_begin", "iem_archive_end", "is_awos"]].to_string(index=False))
