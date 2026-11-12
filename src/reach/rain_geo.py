"""Distance and the coast indicator for the rain pairs.

Coast indicator (reading choice, fixed before any pair result): a station is "coastal" when it lies within
COAST_KM = 15 km of the Atlantic Ocean or Long Island Sound shoreline. The shoreline is the GSHHS low-resolution
ocean shoreline already cached by the panel workstream (data/processed/panel/outlines.csv, kind == "coast";
source basemap-data, see scripts/panel_fetch_outlines.py). GSHHS treats Chesapeake Bay, Delaware Bay and the
tidal Hudson as ocean shoreline, so those are removed by a geographic mask before the distance is taken:
  keep shoreline points with lon >= -75.10 (east of the Delaware and Maryland ocean beaches; this drops the
  whole Chesapeake Bay and the Delaware side of Delaware Bay), and then drop the New Jersey side of Delaware
  Bay (lat 38.90..39.90 and lon < -74.85). Raritan Bay, New York Harbor and Long Island Sound stay in.
The distance is the haversine distance to the nearest kept shoreline vertex (low-resolution polyline, vertices
a few km apart), so the indicator is coarse; the continuous coast_km is kept in the station table as well.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..panel.hedge import haversine_km

COAST_KM = 15.0
LON_MIN = -75.10
DELAWARE_BAY_NJ = (38.90, 39.90, -74.85)   # lat0, lat1, lon below which points are Delaware Bay


def atlantic_shoreline(outlines: pd.DataFrame) -> pd.DataFrame:
    """Shoreline vertices (lon, lat) of the Atlantic Ocean and Long Island Sound, per the mask above."""
    c = outlines[outlines["kind"] == "coast"]
    keep = c["lon"] >= LON_MIN
    lat0, lat1, lon_bay = DELAWARE_BAY_NJ
    keep &= ~((c["lat"] >= lat0) & (c["lat"] <= lat1) & (c["lon"] < lon_bay))
    return c.loc[keep, ["lon", "lat"]].reset_index(drop=True)


def coast_distance_km(lat, lon, shore: pd.DataFrame) -> np.ndarray:
    """Distance from each (lat, lon) to the nearest kept shoreline vertex, km."""
    lat = np.atleast_1d(np.asarray(lat, dtype=float))
    lon = np.atleast_1d(np.asarray(lon, dtype=float))
    slat = shore["lat"].to_numpy(dtype=float)
    slon = shore["lon"].to_numpy(dtype=float)
    out = np.empty(len(lat))
    for i in range(len(lat)):
        out[i] = float(haversine_km(lat[i], lon[i], slat, slon).min())
    return out


def coast_flag(coast_km, threshold: float = COAST_KM) -> np.ndarray:
    return np.asarray(coast_km, dtype=float) <= threshold
