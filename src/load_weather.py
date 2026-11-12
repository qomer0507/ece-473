"""Load daily station TMAX and align local stations with their reference station.

Rules:
- One row per (date, city, local station, reference station) for every calendar day in the window.
- Missing values stay missing (NaN). No imputation. Each row carries a data_quality flag:
  ok, missing_local, missing_ref, missing_both.
- Dates are GHCN-D observation days (local standard time day for these first-order stations), stored
  as ISO strings. No time-zone shift is applied.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_CACHE = ROOT / "data" / "raw" / "ghcnd_tmax_from_ceraunic_cache.csv"
RAW_NCEI = ROOT / "data" / "raw" / "ghcnd_tmax_ncei.csv"
STATIONS = ROOT / "data" / "manifests" / "stations.csv"
ALIGNED = ROOT / "data" / "processed" / "aligned_daily.csv"

SEASON_MONTHS = (5, 6, 7, 8, 9)
START, END = "2015-05-01", "2025-09-30"
ALIGNED_COLS = ["date", "city", "local_station_id", "ref_station_id",
                "local_tmax_f", "ref_tmax_f", "data_quality"]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def load_raw(path: Path | None = None) -> pd.DataFrame:
    """Long table: date (str), station_id, tmax_f (float). Prefers a direct NCEI pull if present.

    Values with a non-blank GHCN quality flag are set to NaN (not dropped silently: the day then
    shows up as missing in the aligned table).
    """
    if path is None:
        path = RAW_NCEI if RAW_NCEI.exists() else RAW_CACHE
    df = pd.read_csv(path, dtype={"date": str, "station_id": str})
    df["tmax_f"] = df["tmax_f"].astype(float)
    if "qflag" in df.columns:
        bad = df["qflag"].fillna("").astype(str).str.strip() != ""
        df.loc[bad, "tmax_f"] = np.nan
    dup = df.duplicated(["date", "station_id"], keep=False)
    if dup.any():
        raise ValueError(f"duplicate (date, station_id) rows: {int(dup.sum())}")
    return df[["date", "station_id", "tmax_f"]]


def season_dates(start: str = START, end: str = END, months=SEASON_MONTHS) -> pd.DatetimeIndex:
    d = pd.date_range(start, end, freq="D")
    return d[d.month.isin(months)]


def quality_flag(local: pd.Series, ref: pd.Series) -> pd.Series:
    lm, rm = local.isna(), ref.isna()
    q = np.select([lm & rm, lm, rm], ["missing_both", "missing_local", "missing_ref"], default="ok")
    return pd.Series(q, index=local.index)


def align_pair(raw: pd.DataFrame, city: str, local_id: str, ref_id: str,
               dates: pd.DatetimeIndex) -> pd.DataFrame:
    """Left-join both stations onto the full date grid; flag gaps, never fill them."""
    ds = pd.Index(dates.strftime("%Y-%m-%d"), name="date")
    wide = raw[raw["station_id"].isin([local_id, ref_id])].pivot(
        index="date", columns="station_id", values="tmax_f")
    loc = wide[local_id].reindex(ds) if local_id in wide else pd.Series(np.nan, index=ds)
    ref = wide[ref_id].reindex(ds) if ref_id in wide else pd.Series(np.nan, index=ds)
    out = pd.DataFrame({"date": ds, "city": city, "local_station_id": local_id,
                        "ref_station_id": ref_id, "local_tmax_f": loc.to_numpy(),
                        "ref_tmax_f": ref.to_numpy()})
    out["data_quality"] = quality_flag(out["local_tmax_f"], out["ref_tmax_f"]).to_numpy()
    return out[ALIGNED_COLS]


def load_stations(path: Path = STATIONS) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"station_id": str, "reference_id": str})


def build_aligned(raw: pd.DataFrame | None = None, stations: pd.DataFrame | None = None,
                  start: str = START, end: str = END) -> pd.DataFrame:
    raw = load_raw() if raw is None else raw
    st = load_stations() if stations is None else stations
    dates = season_dates(start, end)
    parts = [align_pair(raw, r.city, r.station_id, r.reference_id, dates)
             for r in st[st["role"] == "local"].itertuples()]
    return pd.concat(parts, ignore_index=True)


def load_aligned(path: Path = ALIGNED) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"date": str, "local_station_id": str, "ref_station_id": str})


if __name__ == "__main__":
    a = build_aligned()
    ALIGNED.parent.mkdir(parents=True, exist_ok=True)
    a.to_csv(ALIGNED, index=False)
    print(f"wrote {ALIGNED} rows={len(a)}")
    print(a.groupby(["city", "local_station_id"])["data_quality"].value_counts().unstack(fill_value=0))
