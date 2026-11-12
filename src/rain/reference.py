"""Comparison data for validation: GHCN-Daily PRCP and the NWS daily climate report (CLI) as served by IEM.

Neither is used to build the daily table's flags. They are joined as reference columns and used in checks.
"""
from __future__ import annotations

import glob
import json
import os

import pandas as pd

GHCN_ID = {"TTN": "USW00014792", "PHL": "USW00013739", "ABE": "USW00014737"}
CLI_ID = {"TTN": "KTTN", "PHL": "KPHL", "ABE": "KABE"}


def load_ghcn_prcp(ncei_daily_dir: str, station: str) -> pd.Series:
    """GHCN-Daily PRCP in inches indexed by datetime.date. A trace is recorded as 0.00. Missing days are absent."""
    files = sorted(glob.glob(os.path.join(ncei_daily_dir, f"{GHCN_ID[station]}_*.csv")))
    parts = [pd.read_csv(f, dtype=str) for f in files if os.path.getsize(f) > 0]
    parts = [p for p in parts if "PRCP" in p.columns]
    if not parts:
        return pd.Series(dtype=float, name="ghcn_prcp_in")
    d = pd.concat(parts, ignore_index=True)
    d["prcp"] = pd.to_numeric(d["PRCP"], errors="coerce")
    d = d.dropna(subset=["prcp"]).drop_duplicates("DATE")
    s = pd.Series(d["prcp"].to_numpy(), index=pd.to_datetime(d["DATE"]).dt.date, name="ghcn_prcp_in")
    return s.sort_index()


def parse_cli_precip(value) -> tuple[float | None, str]:
    """IEM CLI 'precip' field -> (inches or None, kind) with kind in 'measured', 'trace', 'missing'.

    IEM gives a number, 'T' for trace (some versions give 0.0001), or 'M' / null for missing.
    """
    if value is None:
        return None, "missing"
    if isinstance(value, str):
        v = value.strip().upper()
        if v == "T":
            return 0.0, "trace"
        try:
            value = float(v)
        except ValueError:
            return None, "missing"
    value = float(value)
    if value != value:
        return None, "missing"
    if 0 < value < 0.005:
        return 0.0, "trace"
    return round(value, 2), "measured"


def load_cli(cli_dirs: list[str], station: str) -> pd.DataFrame:
    """NWS climate report daily precipitation from cached IEM json files <dir>/<KXXX>_<year>.json.

    Returns columns date, cli_precip_in, cli_kind, cli_pays (>= 0.01 inch; trace and missing = No).
    If a file for the same year is in several directories the first directory wins.
    """
    rows, seen = [], set()
    for folder in cli_dirs:
        for path in sorted(glob.glob(os.path.join(folder, f"{CLI_ID[station]}_*.json"))):
            year = os.path.basename(path).split("_")[1].split(".")[0]
            if year in seen:
                continue
            seen.add(year)
            with open(path) as fh:
                payload = json.load(fh)
            for r in payload.get("results", []):
                precip, kind = parse_cli_precip(r.get("precip"))
                rows.append((pd.Timestamp(r["valid"]).date(), precip, kind))
    out = pd.DataFrame(rows, columns=["date", "cli_precip_in", "cli_kind"]).drop_duplicates("date")
    out["cli_pays"] = (out["cli_precip_in"].fillna(0) >= 0.01) & (out["cli_kind"] == "measured")
    return out.sort_values("date").reset_index(drop=True)
