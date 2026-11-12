"""Pull the IEM MOS archive for KTTN and KPHL into data/raw/mos/ (resumable; skips cached files).

    python scripts/leadtime_mos_pull.py            # everything in src/leadtime/mos_archive.pull_plan()
    python scripts/leadtime_mos_pull.py --status   # what is cached, no network
    python scripts/leadtime_mos_pull.py --models GFS MEX

One request at a time with a 6 s gap. Log: data/raw/mos/pull_log.txt.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.leadtime.mos_archive import RAW_MOS, cache_path, pull_one, pull_plan  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--models", nargs="*", default=None)
    a = ap.parse_args()
    plan = pull_plan(a.models) if a.models else pull_plan()
    if a.status:
        have = [p for p in plan if cache_path(*p).exists()]
        print(f"cached {len(have)} of {len(plan)}")
        for p in plan:
            if not cache_path(*p).exists():
                print("missing", *p)
        return
    RAW_MOS.mkdir(parents=True, exist_ok=True)
    logf = open(RAW_MOS / "pull_log.txt", "a")

    def log(msg: str) -> None:
        print(msg, flush=True)
        logf.write(msg + "\n")
        logf.flush()

    n_new = 0
    for model, station, year in plan:
        try:
            _, fetched = pull_one(model, station, year, log=log)
            n_new += int(fetched)
        except Exception as e:  # keep going; the file stays missing and --status will show it
            log(f"ERROR {model} {station} {year}: {e!r}")
    log(f"done: fetched {n_new} new files; {sum(cache_path(*p).exists() for p in plan)} of {len(plan)} cached")


if __name__ == "__main__":
    main()
