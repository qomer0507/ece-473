"""Build data/processed/panel/tmax_panel.parquet: long (date, id, tmax_f).

Stations: exposure locations plus listed stations (from data/processed/panel/stations.csv).
Days: May 1 to Sep 30, 2015-2025. Only observed values. Missing days are absent rows. No imputation.
Readings above 111 F (all-time record of the six states) are dropped and listed in dropped_values.csv.

Run: python scripts/panel_build_panel.py   (after scripts/panel_build_stations.py)
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.panel.hedge import season_mask  # noqa: E402

RAW = ROOT / "data/raw/region/tmax"
OUT = ROOT / "data/processed/panel"
MAX_PLAUSIBLE_F = 111


def main():
    st = pd.read_csv(OUT / "stations.csv")
    keep = st[st["is_exposure"].astype(bool) | st["is_listed"].notna()]["id"]
    parts = []
    for sid in keep:
        d = pd.read_csv(RAW / f"{sid}.csv", parse_dates=["DATE"])
        d = d[season_mask(d["DATE"]) & d["TMAX"].notna()
              & (d["DATE"].dt.year >= 2015) & (d["DATE"].dt.year <= 2025)]
        parts.append(pd.DataFrame({"date": d["DATE"].values, "id": sid, "tmax_f": d["TMAX"].astype(float).values}))
    p = pd.concat(parts, ignore_index=True).sort_values(["id", "date"]).reset_index(drop=True)
    assert not p.duplicated(["date", "id"]).any()
    # Plausibility screen (not in SPEC, documented in docs/status/qasim.md): a reading above the all-time
    # record high of any of the six states (111 F, Pennsylvania) is treated as a failed observation and
    # left out, the same as a missing day. Nothing is substituted. Dropped rows are listed in a file.
    bad = p[p["tmax_f"] > MAX_PLAUSIBLE_F]
    bad.to_csv(OUT / "dropped_values.csv", index=False)
    p = p[p["tmax_f"] <= MAX_PLAUSIBLE_F].reset_index(drop=True)
    print(f"dropped as implausible (> {MAX_PLAUSIBLE_F} F): {len(bad)}")
    print(bad.to_string(index=False))
    p.to_parquet(OUT / "tmax_panel.parquet", index=False)
    frac_int = (p["tmax_f"] == p["tmax_f"].round()).mean()
    print(f"rows {len(p)}  stations {p['id'].nunique()}  dates {p['date'].min().date()}..{p['date'].max().date()}")
    print(f"possible station-days {p['id'].nunique() * 153 * 11}  present share {len(p) / (p['id'].nunique() * 153 * 11):.4f}")
    print(f"whole-degree share {frac_int:.4f}  min {p.tmax_f.min()}  max {p.tmax_f.max()}")


if __name__ == "__main__":
    main()
