"""Check that this machine can run the live project (rain hedging, SPEC_v3) end to end.

    python scripts/check_env.py            # report only; exit 1 if anything required is missing
    python scripts/check_env.py --quiet    # one line per problem, nothing when all is well

Checks, in order:
  1. Python version and packages.
  2. Node, npm and contracts/node_modules (needed for `npm test` in contracts/).
  3. The processed data files each phase reads, and which script writes a missing one.
  4. The raw-data directory (git-ignored; only needed to rebuild processed data or to re-pull).
Nothing is downloaded, built or changed. Read-only.
"""
from __future__ import annotations

import importlib
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PY_MIN = (3, 10)
PACKAGES = [  # (import name, pip name, why)
    ("numpy", "numpy", "everything"),
    ("pandas", "pandas", "everything"),
    ("pyarrow", "pyarrow", "reading data/processed/**/*.parquet"),
    ("matplotlib", "matplotlib", "figures (hedge_report.py, sim.experiment, rain_summary.py)"),
    ("pytest", "pytest", "python -m pytest tests -q"),
    ("requests", "requests", "network pulls only (kalshi_rain_pull.py, rain_fetch_cli.py)"),
]
OPTIONAL_PACKAGES = [
    ("scipy", "scipy", "optional; some Phase 3 regressions"),
]

# (path relative to repo, needed by, produced by). Order = pipeline order.
PROCESSED = [
    # Phase 0/1 rain inputs (hourly reductions; built from data/raw by the Phase 0 scripts)
    ("data/processed/rain_probe/hourly_maysep_TTN_IEM_METAR.csv.gz", "Phase 1 rain build, replication",
     "scripts/p0_rain_analyze.py (needs data/raw/rain, network pulls first)"),
    ("data/processed/rain_probe/hourly_maysep_PHL_IEM_METAR.csv.gz", "Phase 1 rain build, replication",
     "scripts/p0_rain_analyze.py"),
    ("data/processed/rain_probe/hourly_maysep_PNE_IEM_METAR.csv.gz", "Phase 2 stand-ins, replication",
     "scripts/p0_rain_analyze.py"),
    ("data/processed/rain_probe/park_station_distances.csv", "Phase 2 (stand-in distances)", "scripts/p0_rain_parks.py"),
    # Phase 1 rain outputs
    ("data/processed/rain/daily_TTN.parquet", "Phase 2 evaluation, replication, market experiment",
     "scripts/rain_build_daily.py (needs data/raw/rain/ncei_daily)"),
    ("data/processed/rain/daily_PHL.parquet", "Phase 2 evaluation, replication", "scripts/rain_build_daily.py"),
    ("data/processed/rain/daily_ABE.parquet", "Phase 2 case E", "scripts/rain_build_daily.py"),
    ("data/processed/rain/season_counts_TTN.csv", "market experiment (sim.experiment), contract tests, deploy guide",
     "scripts/rain_build_daily.py"),
    ("data/processed/rain/parks.csv", "Phase 2 (park coordinates)", "scripts/rain_parks.py"),
    # Phase 1 Kalshi output (aggregates only; the fitted price model)
    ("data/processed/kalshi_rain/price_model.json", "Phase 2 evaluation, replication (modelled Kalshi prices)",
     "scripts/kalshi_rain_aggregates.py (needs data/raw/kalshi, network pull first)"),
    # Phase 2 stand-ins
    ("data/processed/rain/daily_PNE.parquet", "Phase 2 cases B1, D-PNE", "scripts/hedge_build_standins.py"),
    ("data/processed/rain/daily_DYL.parquet", "Phase 2 case B2", "scripts/hedge_build_standins.py"),
    # Phase 3 temperature panel (earlier study's panel, reused)
    ("data/processed/panel/stations.csv", "Phase 3 temperature reach", "scripts/panel_build_stations.py (needs data/raw/region)"),
    ("data/processed/panel/tmax_panel.parquet", "Phase 3 temperature reach", "scripts/panel_build_panel.py"),
]

# Result files the README links; absent means the step has not been run on this checkout.
RESULTS = [
    ("results/phase2/summary.md", "scripts/hedge_run.py then scripts/hedge_report.py"),
    ("results/phase2/fig_hedge_effectiveness.png", "scripts/hedge_report.py"),
    ("replication/results.csv", "python replication/replicate.py"),
    ("results/market/summary.md", "python -m sim.experiment (after npm test)"),
    ("contracts/test/vectors/rain_contract_quotes.json", "cd contracts && npm test"),
]

RAW = [
    ("data/raw/rain", "re-pull / rebuild of the rain tables (Phase 0-1 fetch scripts)"),
    ("data/raw/kalshi", "re-pull of Kalshi candles (scripts/kalshi_rain_pull.py); never committed"),
    ("data/raw/region/tmax", "rebuild of the temperature panel; also tests/test_panel_data.py::test_panel_matches_raw_file_for_one_station"),
]


def cmd_version(cmd: str) -> str | None:
    exe = shutil.which(cmd)
    if not exe:
        return None
    try:
        out = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=20)
        return (out.stdout or out.stderr).strip().splitlines()[0]
    except Exception:  # noqa: BLE001
        return "present (version unknown)"


def main(argv=None) -> int:
    quiet = "--quiet" in (argv or sys.argv[1:])
    problems: list[str] = []
    notes: list[str] = []

    def ok(msg):
        if not quiet:
            print("  ok   " + msg)

    def bad(msg):
        problems.append(msg)
        print("  MISSING  " + msg)

    def warn(msg):
        notes.append(msg)
        if not quiet:
            print("  note " + msg)

    if not quiet:
        print(f"Repo: {ROOT}")
        print("\n1. Python")
    v = sys.version_info[:3]
    if v >= PY_MIN:
        ok(f"python {'.'.join(map(str, v))}")
    else:
        bad(f"python {'.'.join(map(str, v))} is below {'.'.join(map(str, PY_MIN))}")
    for mod, pip, why in PACKAGES:
        try:
            m = importlib.import_module(mod)
            ok(f"{mod} {getattr(m, '__version__', '')}".rstrip())
        except ImportError:
            bad(f"python package {mod} (pip install {pip}); needed for {why}")
    for mod, pip, why in OPTIONAL_PACKAGES:
        try:
            m = importlib.import_module(mod)
            ok(f"{mod} {getattr(m, '__version__', '')} ({why})")
        except ImportError:
            warn(f"optional package {mod} absent (pip install {pip}); {why}")

    if not quiet:
        print("\n2. Node and the contracts")
    for c in ("node", "npm"):
        ver = cmd_version(c)
        if ver:
            ok(f"{c} {ver}")
        else:
            bad(f"{c} not on PATH; needed for `cd contracts && npm test` (Node 18+ works)")
    nm = os.path.join(ROOT, "contracts", "node_modules")
    if os.path.isdir(os.path.join(nm, "hardhat")) and os.path.isdir(os.path.join(nm, "solc")):
        ok("contracts/node_modules (hardhat, solc present)")
    else:
        bad("contracts/node_modules incomplete; run `cd contracts && npm ci` (network; pins solc 0.8.26, hardhat 2.22.17)")

    if not quiet:
        print("\n3. Processed data (committed; each phase reads these)")
    for rel, needed_by, produced_by in PROCESSED:
        if os.path.exists(os.path.join(ROOT, rel)):
            ok(rel)
        else:
            bad(f"{rel}  needed by: {needed_by};  produced by: {produced_by}")

    if not quiet:
        print("\n4. Results the README links (regenerated by scripts/run_all.sh)")
    for rel, produced_by in RESULTS:
        if os.path.exists(os.path.join(ROOT, rel)):
            ok(rel)
        else:
            warn(f"{rel} absent; produced by: {produced_by}")

    if not quiet:
        print("\n5. Raw data (git-ignored, optional)")
    raw_root = os.path.join(ROOT, "data", "raw")
    if os.path.islink(raw_root):
        warn(f"data/raw is a symlink to {os.readlink(raw_root)}")
    for rel, why in RAW:
        if os.path.isdir(os.path.join(ROOT, rel)):
            ok(rel)
        else:
            warn(f"{rel} absent: fine for reproducing results from processed data; needed only for {why}")

    if not quiet:
        print()
    if problems:
        print(f"{len(problems)} required item(s) missing (see MISSING lines above).")
        return 1
    print("All required items present." + (f" {len(notes)} note(s)." if notes else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
