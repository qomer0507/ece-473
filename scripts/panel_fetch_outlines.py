"""State borders and coastline for the map and the coastal-distance proxy.

Source: PyPI package basemap-data (GSHHS coastline and GMT political boundaries, low resolution).
github.com raw files and www2.census.gov were refused by the network proxy on 2026-11-11, PyPI is allowed.
The wheel is downloaded to a temporary folder and only its binary .dat files are read. Nothing is installed.

Output: data/processed/panel/outlines.csv  (kind in {state, coast, lake}, seg, lon, lat)
Run: python scripts/panel_fetch_outlines.py
"""
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/processed/panel/outlines.csv"
BOX = (-82.0, -70.5, 36.5, 46.0)  # lon0, lon1, lat0, lat1


def read(z, name, kind, keep):
    meta = z.read(f"mpl_toolkits/basemap_data/{name}meta_l.dat").decode().splitlines()
    data = z.read(f"mpl_toolkits/basemap_data/{name}_l.dat")
    rows = []
    for j, line in enumerate(meta):
        f = line.split()
        typ, area, npts, south, north, off, nbytes = int(f[0]), float(f[1]), int(f[2]), float(f[3]), float(f[4]), int(f[5]), int(f[6])
        if north < BOX[2] or south > BOX[3] or not keep(typ, area):
            continue
        xy = np.frombuffer(data[off:off + nbytes], dtype="<f4").reshape(-1, 2).astype(float)
        lon = np.where(xy[:, 0] > 180, xy[:, 0] - 360, xy[:, 0])
        inside = (lon >= BOX[0]) & (lon <= BOX[1]) & (xy[:, 1] >= BOX[2]) & (xy[:, 1] <= BOX[3])
        if not inside.any():
            continue
        # split into runs of consecutive in-box points so lines are not drawn across the box
        run = np.cumsum(np.r_[True, inside[1:] != inside[:-1]])
        for r in np.unique(run[inside]):
            m = run == r
            if m.sum() >= 2:
                rows.append(pd.DataFrame({"kind": kind, "seg": f"{kind}{j}_{r}", "lon": lon[m].round(4), "lat": xy[m, 1].round(4)}))
    return rows


def main():
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run([sys.executable, "-m", "pip", "download", "--no-deps", "-q", "-d", tmp, "basemap-data"], check=True)
        whl = next(Path(tmp).glob("basemap_data-*.whl"))
        print("source:", whl.name)
        with zipfile.ZipFile(whl) as z:
            rows = read(z, "states", "state", lambda t, a: True)
            rows += read(z, "gshhs", "coast", lambda t, a: t == 1)            # ocean shoreline
            rows += read(z, "gshhs", "lake", lambda t, a: t == 2 and a > 5000)  # Great Lakes
    d = pd.concat(rows, ignore_index=True)
    d.to_csv(OUT, index=False)
    print(d.groupby("kind").agg(points=("lon", "size"), segments=("seg", "nunique")))


if __name__ == "__main__":
    main()
