"""Extract daily TMAX for our stations from the prior Ceraunic repo cache.

This is the data path that worked in the Milestone I sandbox (NCEI is blocked from the shell).

Provenance: derived cache from prior Ceraunic repo (https://github.com/ehfuzzz/ceraunic),
file data/cache/eval04/ghcnd_tmax.parquet. Original source: NOAA NCEI GHCN-Daily by_station
files, https://www.ncei.noaa.gov/pub/data/ghcn/daily/by_station/{ID}.csv.gz, pulled 2026-09-30 UTC
(see that repo's data/manifests/eval04-sources.csv). Built by src/wi/pool/scenarios.py:load_tmax:
TMAX rows with a non-blank GHCN quality flag are dropped, tenths degC -> whole degF via
floor(C*9/5 + 32 + 0.5).

Usage:
    git clone --depth 1 https://github.com/ehfuzzz/ceraunic /tmp/ceraunic
    pip install pyarrow pandas
    python scripts/pull_ceraunic_cache.py /tmp/ceraunic
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "ghcnd_tmax_from_ceraunic_cache.csv"
PROV = ROOT / "data" / "manifests" / "raw_provenance.csv"

# Prior-repo column code -> GHCN-D id. Only the stations we use.
CODES = {
    "NYC": "USW00094728", "LGA": "USW00014732", "JFK": "USW00094789", "EWR": "USW00014734",
    "TEB": "USW00094741", "TTN": "USW00014792", "PNE": "USW00094732", "DYL": "USW00054786",
    "SMQ": "USW00054785",
}
START, END = "2010-01-01", "2025-12-31"


def md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def main(repo: str) -> None:
    repo_p = Path(repo)
    src = repo_p / "data" / "cache" / "eval04" / "ghcnd_tmax.parquet"
    df = pd.read_parquet(src)
    df.index = pd.to_datetime(df.index)
    df = df.loc[START:END, list(CODES)]
    long = (df.rename(columns=CODES).rename_axis("date").reset_index()
              .melt(id_vars="date", var_name="station_id", value_name="tmax_f")
              .dropna(subset=["tmax_f"]))
    long["date"] = long["date"].dt.strftime("%Y-%m-%d")
    long["tmax_f"] = long["tmax_f"].astype(int)
    long = long.sort_values(["station_id", "date"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    long.to_csv(OUT, index=False)
    try:
        commit = subprocess.check_output(["git", "-C", str(repo_p), "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        commit = "unknown"
    row = pd.DataFrame([{
        "file": str(OUT.relative_to(ROOT)), "rows": len(long), "md5": md5(OUT),
        "source": "derived cache from prior Ceraunic repo; original source NOAA NCEI GHCN-Daily by_station",
        "source_url": "https://github.com/ehfuzzz/ceraunic/blob/main/data/cache/eval04/ghcnd_tmax.parquet",
        "source_commit": commit, "source_md5": md5(src),
        "original_url_pattern": "https://www.ncei.noaa.gov/pub/data/ghcn/daily/by_station/{ID}.csv.gz",
        "original_pulled_utc": "2026-09-30",
        "extracted_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }])
    row.to_csv(PROV, index=False)
    print(f"wrote {OUT} rows={len(long)}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/ceraunic")
