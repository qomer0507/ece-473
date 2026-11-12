"""Loaders for the cached Kalshi pull and for station highs. Read-only helpers."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd

from .client import RAW, REPO, event_date_from_ticker, parse_ts
from .study_b import GHCN, ICAO, SERIES, Bracket, bracket_from_market


@dataclass
class Event:
    city: str
    series: str
    event_ticker: str
    date: date
    close_ts: int
    brackets: list[Bracket]
    results: dict[str, str]            # ticker -> 'yes' / 'no'
    settle_value: int | None           # expiration_value if the API gives one
    rules_primary: str = ""
    rules_secondary: str = ""
    markets: list[dict] = field(default_factory=list, repr=False)

    @property
    def yes_brackets(self) -> list[Bracket]:
        return [b for b in self.brackets if self.results.get(b.ticker) == "yes"]

    def settled_range(self) -> tuple[int | None, int | None] | None:
        """Tightest whole-degree range implied by all market results. None if results conflict."""
        lo, hi = None, None
        for b in self.brackets:
            if self.results.get(b.ticker) == "yes":
                if b.lo is not None:
                    lo = b.lo if lo is None else max(lo, b.lo)
                if b.hi is not None:
                    hi = b.hi if hi is None else min(hi, b.hi)
            elif self.results.get(b.ticker) == "no":
                if b.lo is None and b.hi is not None:      # "<= hi" failed
                    lo = b.hi + 1 if lo is None else max(lo, b.hi + 1)
                elif b.hi is None and b.lo is not None:    # ">= lo" failed
                    hi = b.lo - 1 if hi is None else min(hi, b.lo - 1)
        if lo is not None and hi is not None and lo > hi:
            return None
        return lo, hi


def load_markets(series: str, raw: Path = RAW) -> list[dict]:
    return json.loads((raw / "markets" / f"{series}.json").read_text())


def load_events(city: str, raw: Path = RAW) -> list[Event]:
    series = SERIES[city]
    by_ev: dict[str, list[dict]] = {}
    for m in load_markets(series, raw):
        by_ev.setdefault(m["event_ticker"], []).append(m)
    out = []
    for et, ms in by_ev.items():
        vals = set()
        for m in ms:
            v = m.get("expiration_value")
            if v not in (None, ""):
                try:
                    f = float(v)
                    if f == int(f):
                        vals.add(int(f))
                except ValueError:
                    pass
        out.append(Event(
            city=city, series=series, event_ticker=et, date=event_date_from_ticker(et),
            close_ts=max(parse_ts(m["close_time"]) for m in ms),
            brackets=[bracket_from_market(m) for m in ms],
            results={m["ticker"]: m.get("result") for m in ms},
            settle_value=vals.pop() if len(vals) == 1 else None,
            rules_primary=ms[0].get("rules_primary") or "",
            rules_secondary=ms[0].get("rules_secondary") or "",
            markets=ms,
        ))
    out.sort(key=lambda e: e.date)
    return out


def load_candles(series: str, ticker: str, raw: Path = RAW) -> list[dict] | None:
    """Cached hourly candles, or None if this market was not pulled."""
    p = raw / "candles" / series / f"{ticker}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text())["candlesticks"]


def load_ghcn_tmax(city: str) -> pd.Series:
    """Daily TMAX (deg F) for the city's settlement station from the regional GHCN pull. Index = date."""
    df = pd.read_csv(REPO / "data" / "raw" / "region" / "tmax" / f"{GHCN[city]}.csv")
    s = pd.Series(df["TMAX"].values, index=pd.to_datetime(df["DATE"]).dt.date).dropna()
    return s


def load_iem_cli_high(city: str, raw: Path = RAW) -> pd.Series:
    """NWS CLI daily high from the IEM archive files in data/raw/kalshi/iem_cli/. Index = date."""
    rows = {}
    for p in sorted((raw / "iem_cli").glob(f"{ICAO[city]}_*.json")):
        for r in json.loads(p.read_text())["results"]:
            h = r.get("high")
            if isinstance(h, (int, float)):
                rows[date.fromisoformat(r["valid"])] = int(h)
    return pd.Series(rows, dtype="float64").sort_index()
