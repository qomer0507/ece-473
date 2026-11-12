"""Settlement map and reconciliation of Kalshi settled brackets against station highs.

Outputs (aggregates only, no raw Kalshi rows):
  data/processed/kalshi/settlement_map.csv
  data/processed/kalshi/reconciliation_summary.csv

Usage: python scripts/kalshi_settlement.py
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.kalshi.data import load_events, load_ghcn_tmax, load_iem_cli_high  # noqa: E402
from src.kalshi.study_b import SERIES  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "data" / "processed" / "kalshi"


def classify_rules(primary: str, secondary: str) -> tuple[str, str, str]:
    """(source named, station text, CLI code) from the market rules text."""
    code = ""
    m = re.search(r"\((CLI[A-Z]{3})\)", primary) or re.search(r"\b(CLI[A-Z]{3})\b", secondary)
    if m:
        code = m.group(1)
    if "The Weather Company" in primary:
        source = "The Weather Company"
    elif "Climatological Report (Daily)" in primary:
        source = "NWS Climatological Report (Daily)"
    elif "Daily Climate Report" in primary:
        source = "NWS Daily Climate Report"
    else:
        source = "not named in rules_primary"
    m = (re.search(r"recorded (?:in|at) (.+?)\s*(?:\(CLI[A-Z]{3}\))?\s+(?:on|for) ", primary))
    station = m.group(1).strip() if m else ""
    station = re.sub(r"\(CLI[A-Z]{3}\)$", "", station).strip()
    return source, station, code


def settlement_map() -> pd.DataFrame:
    rows = []
    for city, series in SERIES.items():
        cur = None
        for e in load_events(city):
            src, station, code = classify_rules(e.rules_primary, e.rules_secondary)
            where = ("rules_primary" if f"({code})" in e.rules_primary else "rules_secondary") if code else ""
            key = (src, station, code, where)
            if cur is None or cur["_key"] != key:
                cur = {"_key": key, "city": city, "series": series, "source_named": src,
                       "station_text": station, "cli_code": code,
                       "code_where": where,
                       "first_event": e.event_ticker, "first_date": e.date.isoformat(),
                       "last_event": e.event_ticker, "last_date": e.date.isoformat(), "n_events": 0}
                rows.append(cur)
            cur["last_event"], cur["last_date"] = e.event_ticker, e.date.isoformat()
            cur["n_events"] += 1
    df = pd.DataFrame(rows).drop(columns="_key")
    return df


def reconcile(city: str, ref: pd.Series, ref_name: str, start=None, end=None) -> dict:
    """Compare every market result of each event with the reference high on that date."""
    n = match = flips = flips_unknown = 0
    sizes: Counter = Counter()
    by_year: Counter = Counter()
    mism_year: Counter = Counter()
    first = last = None
    for e in load_events(city):
        if (start and e.date < start) or (end and e.date > end) or e.date not in ref.index:
            continue
        t = int(ref[e.date])
        n += 1
        by_year[e.date.year] += 1
        first = first or e.date
        last = e.date
        ok = all((e.results[b.ticker] == "yes") == b.pays(t) for b in e.brackets)
        if ok:
            match += 1
            continue
        mism_year[e.date.year] += 1
        # size: reference high minus Kalshi settled value; if no value, distance to the settled range
        if e.settle_value is not None:
            d = t - e.settle_value
            kal90 = e.settle_value >= 90
        else:
            r = e.settled_range()
            lo, hi = r if r else (None, None)
            d = (t - hi) if (hi is not None and t > hi) else (t - lo) if (lo is not None and t < lo) else 0
            kal90 = True if (lo is not None and lo >= 90) else False if (hi is not None and hi <= 89) else None
        sizes[d] += 1
        if kal90 is None:
            flips_unknown += 1
        elif kal90 != (t >= 90):
            flips += 1
    return {
        "city": city, "reference": ref_name,
        "first_date": first.isoformat() if first else "", "last_date": last.isoformat() if last else "",
        "days_compared": n, "matches": match, "mismatches": n - match,
        "match_share": round(match / n, 5) if n else float("nan"),
        "mismatch_sizes_degF_ref_minus_kalshi": "; ".join(f"{k:+d}: {v}" for k, v in sorted(sizes.items())),
        "mismatches_by_year": "; ".join(f"{k}: {v}" for k, v in sorted(mism_year.items())),
        "days_by_year": "; ".join(f"{k}: {v}" for k, v in sorted(by_year.items())),
        "flips_90F_trigger": flips, "flips_90F_undetermined": flips_unknown,
    }


def main():
    from datetime import date
    OUT.mkdir(parents=True, exist_ok=True)
    sm = settlement_map()
    sm.to_csv(OUT / "settlement_map.csv", index=False)
    print(sm.to_string())

    rows = []
    for city in SERIES:
        ghcn = load_ghcn_tmax(city)
        cli = load_iem_cli_high(city)
        rows.append(reconcile(city, ghcn, "GHCN-D TMAX (data/raw/region/tmax)"))
        if city == "NYC":
            rows.append(reconcile(city, ghcn, "GHCN-D TMAX, 2023-2025 only", date(2023, 1, 1), date(2025, 12, 31)))
        rows.append(reconcile(city, cli, "NWS CLI high via IEM json/cli.py, all dates"))
        rows.append(reconcile(city, cli, "NWS CLI via IEM, NWS-settled era (to 2026-08-13)", None, date(2026, 8, 13)))
        rows.append(reconcile(city, cli, "NWS CLI via IEM, Weather Company era (from 2026-08-14)", date(2026, 8, 14), None))
    df = pd.DataFrame([r for r in rows if r["days_compared"] > 0])
    df.to_csv(OUT / "reconciliation_summary.csv", index=False)
    pd.set_option("display.width", 250, "display.max_colwidth", 60)
    print(df.drop(columns=["days_by_year"]).to_string())


if __name__ == "__main__":
    main()
