#!/usr/bin/env bash
# Reproduce the live project (rain hedging, docs/SPEC_v3.md) from the committed processed data.
#
#   bash scripts/run_all.sh              # tests + market experiment + Phase 2 evaluation + replication (~5 min)
#   bash scripts/run_all.sh --no-contracts   # skip `npm test` (then sim.experiment uses the committed gas report)
#   bash scripts/run_all.sh --rebuild    # also rebuild the Phase 1 rain tables from data/raw (needs the raw cache)
#   bash scripts/run_all.sh --pull       # also re-pull network data first (NOAA/IEM and Kalshi; slow, ~15 min)
#
# Without --pull nothing touches the network. Without --rebuild nothing under data/processed is rewritten
# except data/processed/hedge/ (Phase 2 stand-in tables, built from committed Phase 0 files).
# Every step is deterministic (seed 473); a clean re-run reproduces the committed results byte for byte
# except PNG metadata.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PULL=0; REBUILD=0; CONTRACTS=1
for a in "$@"; do
  case "$a" in
    --pull) PULL=1 ;;
    --rebuild) REBUILD=1 ;;
    --no-contracts) CONTRACTS=0 ;;
    -h|--help) sed -n '2,14p' "$0"; exit 0 ;;
    *) echo "unknown flag: $a (see --help)"; exit 2 ;;
  esac
done

step() { echo; echo "=================================================================="; echo "== $1"; echo "=================================================================="; }
t0=$(date +%s)
since() { echo "   (step took $(( $(date +%s) - $1 )) s)"; }

step "0. Environment check (scripts/check_env.py)"
python scripts/check_env.py --quiet

if [ "$PULL" = 1 ]; then
  step "P. Network pulls (NOAA/IEM climate reports and Kalshi candles; resumable, cached under data/raw)"
  s=$(date +%s)
  python scripts/rain_fetch_cli.py
  python scripts/kalshi_rain_pull.py
  python scripts/kalshi_rain_quotes.py
  python scripts/kalshi_rain_aggregates.py
  since $s
fi

if [ "$REBUILD" = 1 ]; then
  step "R. Rebuild Phase 1 rain tables from data/raw (observed station data; nothing imputed)"
  s=$(date +%s)
  python scripts/rain_build_daily.py
  python scripts/rain_validate.py
  python scripts/rain_summary.py
  since $s
fi

if [ "$CONTRACTS" = 1 ]; then
  step "1. Contract tests: cd contracts && npm test  (162 tests, about 1.5 min; rewrites remix/, vectors, gas report)"
  s=$(date +%s)
  ( cd contracts && npm test 2>&1 | tail -n 8 )
  since $s
else
  echo "(skipping npm test; using the committed contracts/test/vectors and results/market/gas_report.json)"
fi

step "2. Python tests: python -m pytest tests -q  (400 tests, about 10 s)"
s=$(date +%s)
python -m pytest tests -q
since $s

step "3. Market experiment (SIMULATED LMSR prices): python -m sim.experiment -> results/market/"
s=$(date +%s)
python -m sim.experiment > /dev/null
since $s

step "4. Phase 2 stand-in gauges: scripts/hedge_build_standins.py -> data/processed/rain/daily_{PNE,DYL}.parquet"
s=$(date +%s)
python scripts/hedge_build_standins.py > /dev/null
since $s

step "5. Phase 2 evaluation (pre-registered, docs/PHASE2_PREREG.md): scripts/hedge_run.py -> results/phase2/  (about 75 s)"
s=$(date +%s)
python scripts/hedge_run.py > /dev/null
since $s

step "6. Phase 2 figures and summary: scripts/hedge_report.py -> results/phase2/summary.md, fig_*.png"
s=$(date +%s)
python scripts/hedge_report.py > /dev/null
since $s

step "7. Independent replication (no imports from src/): replication/replicate.py -> replication/*.csv  (about 70 s)"
s=$(date +%s)
python replication/replicate.py > /dev/null
since $s

step "Done in $(( $(date +%s) - t0 )) s"
echo "Headline: results/phase2/summary.md (table 'The registered verdict'); figure results/phase2/fig_hedge_effectiveness.png"
echo "Replication check: compare replication/results.csv with results/phase2/metrics_tidy.csv (docs/status/phase2_replication.md)"
