"""Build data/manifests/stations.csv: station ids, coordinates, roles, and distance to reference.

Coordinates are the LATITUDE/LONGITUDE columns that NCEI returned with includeStationLocation=1
(saved verbatim in data/raw/ncei_spotcheck/). Distances are great-circle (haversine, R = 6371.0088 km).
Names are from the NCEI GHCN-D station list (ghcnd-stations.txt).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.load_weather import haversine_km  # noqa: E402

SPOT = "https://www.ncei.noaa.gov/access/services/data/v1?dataset=daily-summaries&dataTypes=TMAX&format=csv&includeStationLocation=1&stations="
# id: (name, lat, lon, elev_m, spot-check file the coordinates came from)
META = {
    "USW00094728": ("NY CITY CENTRAL PARK", 40.77898, -73.96925, 42.7, "set2"),
    "USW00014732": ("NY LAGUARDIA AP", 40.77945, -73.88027, 3.0, "set1"),
    "USW00094789": ("NY JFK INTL AP", 40.63915, -73.7639, 2.7, "set1"),
    "USW00014734": ("NEWARK LIBERTY INTL AP", 40.68275, -74.16927, 1.9, "set2"),
    "USW00094741": ("TETERBORO AP", 40.85898, -74.05616, 0.8, "2025"),
    "USW00014792": ("TRENTON MERCER CO AP", 40.27681, -74.81587, 57.9, "set2"),
    "USW00094732": ("PHILADELPHIA NE AP", 40.07892, -75.01336, 32.9, "set1"),
    "USW00054786": ("DOYLESTOWN AP", 40.33015, -75.12284, 120.5, "set2"),
    "USW00054785": ("SOMERVILLE CENTRAL JERSEY RGNL AP", 40.62406, -74.66898, 30.1, "set1"),
}
FILES = {"set1": "ncei_20190720_20190721_set1_tenthsC.csv", "set2": "ncei_20190720_20190721_set2_tenthsC.csv",
         "2025": "ncei_20250728_20250729_tenthsC.csv"}
PAIRS = [  # (city, reference, [local candidates])
    ("NYC", "USW00094728", ["USW00014732", "USW00094741", "USW00014734", "USW00094789"]),
    ("Trenton", "USW00014792", ["USW00054786", "USW00094732", "USW00054785"]),
]


def build() -> pd.DataFrame:
    rows = []
    for city, ref, locs in PAIRS:
        for sid, role in [(ref, "reference")] + [(x, "local") for x in locs]:
            name, lat, lon, elev, f = META[sid]
            rlat, rlon = META[ref][1], META[ref][2]
            rows.append(dict(station_id=sid, name=name, lat=lat, lon=lon, elev_m=elev, city=city,
                             role=role, reference_id=ref,
                             distance_km=round(haversine_km(lat, lon, rlat, rlon), 2),
                             coord_source=f"data/raw/ncei_spotcheck/{FILES[f]}",
                             source_url=f"https://www.ncei.noaa.gov/pub/data/ghcn/daily/by_station/{sid}.csv.gz"))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = build()
    out = ROOT / "data" / "manifests" / "stations.csv"
    df.to_csv(out, index=False)
    print(df[["city", "station_id", "name", "role", "distance_km"]].to_string(index=False))
