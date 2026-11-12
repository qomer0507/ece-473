"""Reduce raw hourly precipitation pulls to the Phase 0 hourly format (one row per UTC hour label).

The rules are copied from scripts/p0_rain_analyze.py (Phase 0; see docs/status/phase0_rain.md) so that the
reach stations are coded exactly like the 12 Phase 0 stations in data/processed/rain_probe/:

IEM METAR (asos.py, p01i + raw METAR, 1990 on)
  - the routine report closest to the station's usual reporting minute (within 3 minutes) labels the hour;
    the label is the start of the hour the report covers (report at HH:53 -> label (HH-1):00 + ... see _label)
  - the hour is PRESENT when that report is not PNO (rain gauge not operating) and either carries a p01i
    value, or comes from an automated AO2 station and is not an IEM backfill row (IEM_DS3505 / IEM_GHCNH);
    a present hour without a P-group means 0.00
  - the value is the maximum p01i over the reports in the hour; trace (T) is 0.0 with trace = True
NCEI ISD (global-hourly, AA1..AA4, before 2006)
  - the first AA group with period 01 (one hour), a value that is not 9999 and a quality flag not 3 or 7
  - value in tenths of a millimetre -> inches; condition code 2 = trace; only closing reports are kept

Output columns match rain_probe: hour_label_utc (index), source, ldate, lhour, lst_date, present, precip_in,
trace, pno. May-September rows only (local month).
"""
from __future__ import annotations

import glob
import gzip
import os

import numpy as np
import pandas as pd

TZ = "America/New_York"
SOURCES = ("IEM_METAR", "NCEI_ISD")
OUT_COLUMNS = ["source", "ldate", "lhour", "lst_date", "present", "precip_in", "trace", "pno"]


def _label(df: pd.DataFrame) -> pd.DataFrame:
    """df has t (naive UTC Timestamp). Adds the hour label of each report and the closing-report flag."""
    df["y"] = df["t"].dt.year
    df["minute"] = df["t"].dt.minute
    rm = df.groupby("y")["minute"].agg(lambda s: s.value_counts().index[0])
    df["rm"] = df["y"].map(rm)
    gap = (df["rm"] - df["minute"]) % 60
    df["closing"] = gap <= 3
    df["label"] = (df["t"] + pd.to_timedelta(gap, unit="m") - pd.Timedelta(minutes=30)).dt.floor("h")
    return df


def reduce_iem(path: str) -> pd.DataFrame | None:
    """One row per hour label from an IEM asos.py pull (columns station, valid, p01i, metar)."""
    if not os.path.exists(path):
        return None
    d = pd.read_csv(path, dtype=str, usecols=[1, 2, 3], names=["t", "p", "metar"], header=0, on_bad_lines="skip")
    if d.empty:
        return None
    d["t"] = pd.to_datetime(d["t"], errors="coerce")
    d = d.dropna(subset=["t"]).drop_duplicates(subset=["t", "metar"])
    if d.empty:
        return None
    m = d["metar"].fillna("")
    d["ao2"] = m.str.contains(r"\bAO2", regex=True)
    d["pno"] = m.str.contains(r"\bPNO\b", regex=True)
    d["isd"] = m.str.contains("IEM_DS3505|IEM_GHCNH", regex=True)
    d["hasval"] = d["p"] != "M"
    d["trace"] = d["p"] == "T"
    d["val"] = pd.to_numeric(d["p"], errors="coerce").fillna(0.0)
    d = _label(d)
    d["ok"] = d["closing"] & ~d["pno"] & (d["hasval"] | (d["ao2"] & ~d["isd"]))
    d["pno_close"] = d["closing"] & d["pno"]
    g = d.groupby("label").agg(present=("ok", "max"), precip_in=("val", "max"), trace=("trace", "max"),
                               pno=("pno_close", "max"), closing=("closing", "max"))
    g["source"] = "IEM_METAR"
    return g


def reduce_isd(paths: list[str]) -> pd.DataFrame | None:
    """One row per hour label from NCEI global-hourly pulls (DATE, AA1..AA4)."""
    paths = [p for p in paths if os.path.exists(p) and os.path.getsize(p) > 0]
    if not paths:
        return None
    frames = []
    for p in paths:
        try:
            frames.append(pd.read_csv(p, dtype=str))
        except (pd.errors.EmptyDataError, gzip.BadGzipFile, OSError):
            continue
    frames = [f for f in frames if not f.empty and "DATE" in f.columns]
    if not frames:
        return None
    d = pd.concat(frames, ignore_index=True)
    d["t"] = pd.to_datetime(d["DATE"], errors="coerce")
    d = d.dropna(subset=["t"])
    val = pd.Series(np.nan, index=d.index)
    tr = pd.Series(False, index=d.index)
    for c in ("AA1", "AA2", "AA3", "AA4"):
        if c not in d:
            continue
        s = d[c].fillna("").str.split(",", expand=True)
        if s.shape[1] < 4:
            continue
        good = (s[0] == "01") & (s[1] != "9999") & ~s[3].isin(["3", "7"]) & (s[1].str.len() == 4)
        v = pd.to_numeric(s[1], errors="coerce") / 10.0 / 25.4
        val = val.where(~(good & val.isna()), v)
        tr = tr | (good & (s[2] == "2"))
    d["val"], d["trace"] = val, tr
    d = d[d["val"].notna()].copy()
    if d.empty:
        return None
    d = _label(d)
    d = d[d["closing"]]
    g = d.groupby("label").agg(precip_in=("val", "max"), trace=("trace", "max"))
    g["present"], g["pno"], g["closing"], g["source"] = True, False, True, "NCEI_ISD"
    return g


def add_local(g: pd.DataFrame) -> pd.DataFrame:
    """Local clock date and hour (America/New_York), local-standard-time date, season, local month."""
    g = g.copy()
    loc = g.index.tz_localize("UTC").tz_convert(TZ)
    g["ldate"] = loc.strftime("%Y-%m-%d")
    g["lhour"] = loc.hour
    lst = g.index - pd.Timedelta(hours=5)
    g["lst_date"] = lst.strftime("%Y-%m-%d")
    g["season"] = loc.year
    g["lmonth"] = loc.month
    return g


def maysep(g: pd.DataFrame) -> pd.DataFrame:
    """Rows of local months May..September, in the rain_probe column order."""
    k = g[(g["lmonth"] >= 5) & (g["lmonth"] <= 9)]
    return k[OUT_COLUMNS]


def write_station(sid: str, iem_path: str, isd_paths: list[str], out_dir: str) -> dict:
    """Reduce both sources for one station and write hourly_maysep_<SID>_<SOURCE>.csv.gz. Returns row counts."""
    os.makedirs(out_dir, exist_ok=True)
    counts = {}
    for name, g in (("IEM_METAR", reduce_iem(iem_path)), ("NCEI_ISD", reduce_isd(isd_paths))):
        if g is None or g.empty:
            counts[name] = 0
            continue
        k = maysep(add_local(g))
        k.to_csv(os.path.join(out_dir, f"hourly_maysep_{sid}_{name}.csv.gz"), index_label="hour_label_utc")
        counts[name] = int(len(k))
    return counts


def isd_paths_for(raw_dir: str, sid: str) -> list[str]:
    return sorted(glob.glob(os.path.join(raw_dir, f"{sid}_*.csv.gz")))
