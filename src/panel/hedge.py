"""Station-hedge mismatch library for the regional panel (SPEC_v2, Part 1 Study A; reused by Part 2).

Everything here follows docs/SPEC_v2.md. Short version:

- Heat event at location i on day t:  H = 1 if TMAX_i >= 90 (``threshold``).
- Contract on station s with strike k: P = 1 if TMAX_s >= k. k is an integer in 80..100.
- Days count only if BOTH temperatures are present. No imputation anywhere.
- R  = mean 1{H != P};  FN = share of days with H=1,P=0;  FP = share with H=0,P=1;
  miss rate = FN days / hot days;  false-payout rate = FP days / payout days.
- Windows: FIT 2015-2019, SELECT 2020-2022, REPORT 2023-2025. Season: May 1 to Sep 30.
- Baseline hedge under listed set L: nearest station in L (haversine), k = 90.
- Adjusted hedge: the (station in L, k) pair with the lowest FIT mismatch. Ties go to the k closest
  to 90, then to the nearest station. SPEC does not say what to do if k = 90-d and k = 90+d still tie
  on the same station; this module then takes the lower k (documented choice, deterministic).
- Bootstrap: whole summers (years) resampled jointly across all stations, 1,000 draws, seed 473.

There are no hidden globals and no file reads. Every function takes its data as arguments:

``panel``    long DataFrame with columns date, id, tmax_f (as in data/processed/panel/tmax_panel.parquet),
             or the wide form returned by :func:`to_wide` (index = date, columns = station id).
``stations`` DataFrame with at least columns id, lat, lon (as in data/processed/panel/stations.csv).

Typical use (Part 2 ranking)::

    wide = to_wide(panel)
    base = mismatch_under_listed_set(L, wide, stations, location_ids=exposure_ids)
    plus = mismatch_under_listed_set(L + [s], wide, stations, location_ids=exposure_ids)
    # compare rows with hedge == "adjusted" and window == "SELECT"
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd

# ----------------------------------------------------------------------------------------------
# Constants from SPEC_v2
# ----------------------------------------------------------------------------------------------
THRESHOLD_F = 90
STRIKES = tuple(range(80, 101))
WINDOWS: Dict[str, Tuple[int, int]] = {"FIT": (2015, 2019), "SELECT": (2020, 2022), "REPORT": (2023, 2025)}
LISTED: Dict[str, str] = {
    "NYC": "USW00094728",           # Central Park
    "Philadelphia": "USW00013739",  # Philadelphia Intl. Kalshi station INFERRED, not confirmed.
    "Newark": "USW00014734",
    "Trenton": "USW00014792",
}
L_PRE: List[str] = [LISTED["NYC"], LISTED["Philadelphia"]]
L_NOW: List[str] = [LISTED["NYC"], LISTED["Philadelphia"], LISTED["Newark"], LISTED["Trenton"]]
BOOT_DRAWS = 1000
BOOT_SEED = 473
COUNT_COLS = ["n", "n_hot", "n_pay", "fn_days", "fp_days"]


@dataclass(frozen=True)
class Hedge:
    """One hedge: buy the contract on ``station`` with integer ``strike``.

    kind     "baseline" or "adjusted".
    dist_km  haversine distance from the location to ``station``.
    fit_R    mismatch on the FIT window (NaN for a baseline hedge unless filled by the caller).
    fit_n    number of FIT days with both values present (0 if not computed).
    """
    station: str
    strike: int
    kind: str
    dist_km: float
    fit_R: float = float("nan")
    fit_n: int = 0


# ----------------------------------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------------------------------
def season_mask(dates) -> np.ndarray:
    """True for dates from May 1 to Sep 30 inclusive."""
    d = pd.DatetimeIndex(pd.to_datetime(dates))
    return np.asarray((d.month >= 5) & (d.month <= 9))


def window_mask(dates, window: Union[str, Tuple[int, int]]) -> np.ndarray:
    """True for dates whose year is inside the window. ``window`` is a name in WINDOWS or (first_year, last_year)."""
    a, b = WINDOWS[window] if isinstance(window, str) else window
    y = pd.DatetimeIndex(pd.to_datetime(dates)).year
    return np.asarray((y >= a) & (y <= b))


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance in km (Earth radius 6371.0088 km). Accepts scalars or arrays."""
    lat1, lon1, lat2, lon2 = (np.radians(np.asarray(x, dtype=float)) for x in (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371.0088 * np.arcsin(np.sqrt(a))


def to_wide(panel: pd.DataFrame) -> pd.DataFrame:
    """Long panel (date, id, tmax_f) -> wide frame (index date, columns id). Missing stays NaN.

    A frame that is already wide (DatetimeIndex, no 'id' column) is returned unchanged.
    Only season days are kept.
    """
    if "id" not in panel.columns:
        wide = panel.copy()
        wide.index = pd.to_datetime(wide.index)
    else:
        p = panel.copy()
        p["date"] = pd.to_datetime(p["date"])
        if p.duplicated(["date", "id"]).any():
            raise ValueError("duplicate (date, id) rows in panel")
        wide = p.pivot(index="date", columns="id", values="tmax_f")
    wide = wide.sort_index()
    return wide[season_mask(wide.index)]


def _dist(stations: pd.DataFrame, a: str, b: str) -> float:
    s = stations.set_index("id")
    return float(haversine_km(s.at[a, "lat"], s.at[a, "lon"], s.at[b, "lat"], s.at[b, "lon"]))


# ----------------------------------------------------------------------------------------------
# Mismatch metrics
# ----------------------------------------------------------------------------------------------
def mismatch_counts(loc_tmax, hedge_tmax, strike: int = THRESHOLD_F, threshold: float = THRESHOLD_F) -> Dict[str, int]:
    """Day counts for one (location, station, strike). Days with either value missing are dropped.

    Returns n (days used), n_hot (H=1), n_pay (P=1), fn_days (H=1,P=0), fp_days (H=0,P=1).
    Both comparisons are >= (a reading equal to the threshold or strike counts).
    """
    x = np.asarray(loc_tmax, dtype=float)
    y = np.asarray(hedge_tmax, dtype=float)
    if x.shape != y.shape:
        raise ValueError("series must have the same length")
    ok = ~np.isnan(x) & ~np.isnan(y)
    h = x[ok] >= threshold
    p = y[ok] >= strike
    return {"n": int(ok.sum()), "n_hot": int(h.sum()), "n_pay": int(p.sum()),
            "fn_days": int((h & ~p).sum()), "fp_days": int((~h & p).sum())}


def metrics_from_counts(c) -> Dict[str, float]:
    """Counts -> R, FN, FP, miss_rate, false_payout_rate. Undefined ratios are NaN (never 0)."""
    n, hot, pay, fn, fp = (float(c[k]) for k in COUNT_COLS)
    nan = float("nan")
    return {
        "R": (fn + fp) / n if n > 0 else nan,
        "FN": fn / n if n > 0 else nan,
        "FP": fp / n if n > 0 else nan,
        "miss_rate": fn / hot if hot > 0 else nan,
        "false_payout_rate": fp / pay if pay > 0 else nan,
    }


def mismatch_metrics(loc_tmax, hedge_tmax, strike: int = THRESHOLD_F, threshold: float = THRESHOLD_F) -> Dict[str, float]:
    """Counts plus the five SPEC metrics for one (location, station, strike)."""
    c = mismatch_counts(loc_tmax, hedge_tmax, strike, threshold)
    out: Dict[str, float] = dict(c)
    out.update(metrics_from_counts(c))
    return out


# ----------------------------------------------------------------------------------------------
# Hedges
# ----------------------------------------------------------------------------------------------
def baseline_hedge(loc_id: str, listed_ids: Sequence[str], stations: pd.DataFrame) -> Hedge:
    """Nearest station in ``listed_ids`` (haversine), strike 90. Uses no temperature data.

    Exact distance ties go to the station that comes first in ``listed_ids``.
    """
    if len(listed_ids) == 0:
        raise ValueError("listed set is empty")
    d = [_dist(stations, loc_id, s) for s in listed_ids]
    j = int(np.argmin(d))
    return Hedge(station=listed_ids[j], strike=THRESHOLD_F, kind="baseline", dist_km=d[j])


def adjusted_hedge(loc_id: str, listed_ids: Sequence[str], panel: pd.DataFrame, stations: pd.DataFrame,
                   fit_window: Union[str, Tuple[int, int]] = "FIT", strikes: Iterable[int] = STRIKES,
                   threshold: float = THRESHOLD_F) -> Hedge:
    """The (station in L, strike) pair with the lowest mismatch on ``fit_window``.

    Only rows of ``panel`` inside ``fit_window`` are read. Ties: strike closest to 90, then nearest
    station, then lower strike. Mismatch values are compared as exact fractions, not floats.
    A station with no overlapping FIT days is skipped. If none overlaps, the baseline pair is returned
    with kind "adjusted" and fit_n = 0.
    """
    wide = to_wide(panel)
    fit = wide[window_mask(wide.index, fit_window)]
    x = fit[loc_id].to_numpy(dtype=float)
    best_key, best = None, None
    for s in listed_ids:
        y = fit[s].to_numpy(dtype=float)
        ok = ~np.isnan(x) & ~np.isnan(y)
        n = int(ok.sum())
        if n == 0:
            continue
        h = x[ok] >= threshold
        d = _dist(stations, loc_id, s)
        for k in strikes:
            mism = int((h != (y[ok] >= k)).sum())
            key = (Fraction(mism, n), abs(k - THRESHOLD_F), d, k)
            if best_key is None or key < best_key:
                best_key = key
                best = Hedge(station=s, strike=int(k), kind="adjusted", dist_km=d, fit_R=mism / n, fit_n=n)
    if best is None:
        b = baseline_hedge(loc_id, listed_ids, stations)
        return Hedge(station=b.station, strike=b.strike, kind="adjusted", dist_km=b.dist_km)
    return best


def yearly_counts(panel: pd.DataFrame, loc_id: str, hedge: Hedge,
                  window: Union[str, Tuple[int, int], None] = None, threshold: float = THRESHOLD_F) -> pd.DataFrame:
    """Per-year day counts (index year; columns n, n_hot, n_pay, fn_days, fp_days) for one hedge.

    ``window`` None means every year in the panel. These yearly counts are what the bootstrap resamples.
    """
    wide = to_wide(panel)
    if window is not None:
        wide = wide[window_mask(wide.index, window)]
    x = wide[loc_id].to_numpy(dtype=float)
    y = wide[hedge.station].to_numpy(dtype=float)
    ok = ~np.isnan(x) & ~np.isnan(y)
    h = (x >= threshold) & ok
    p = (y >= hedge.strike) & ok
    df = pd.DataFrame({"n": ok, "n_hot": h, "n_pay": p, "fn_days": h & ~p, "fp_days": ~h & p & ok},
                      index=wide.index.year).astype(int)
    out = df.groupby(level=0).sum()
    out.index.name = "year"
    return out


def evaluate_hedge(panel: pd.DataFrame, loc_id: str, hedge: Hedge, window: Union[str, Tuple[int, int]],
                   threshold: float = THRESHOLD_F) -> Dict[str, float]:
    """Counts and metrics of ``hedge`` for ``loc_id`` on ``window`` (a name in WINDOWS or a (y0, y1) pair)."""
    c = yearly_counts(panel, loc_id, hedge, window, threshold)[COUNT_COLS].sum().astype(int).to_dict()
    out: Dict[str, float] = dict(c)
    out.update(metrics_from_counts(c))
    return out


# ----------------------------------------------------------------------------------------------
# Per-location results under a listed set (the Part 2 entry point)
# ----------------------------------------------------------------------------------------------
def mismatch_under_listed_set(listed_ids: Sequence[str], panel: pd.DataFrame, stations: pd.DataFrame,
                              location_ids: Optional[Sequence[str]] = None,
                              windows: Sequence[str] = ("SELECT", "REPORT"),
                              fit_window: Union[str, Tuple[int, int]] = "FIT",
                              threshold: float = THRESHOLD_F, return_yearly: bool = False):
    """Baseline and adjusted hedge results for every location under the listed set ``listed_ids``.

    Parameters
    ----------
    listed_ids    GHCN ids of the stations that have a contract. Must be columns of the panel.
    panel         long (date, id, tmax_f) or wide panel. Must contain every location and listed station.
    stations      table with id, lat, lon. If it has a boolean column ``is_exposure`` and
                  ``location_ids`` is None, the exposure locations are used.
    location_ids  locations to evaluate. Default: stations.is_exposure, else every panel column.
    windows       evaluation windows (names in WINDOWS). The adjusted hedge is always fitted on
                  ``fit_window`` only, whatever is listed here.
    return_yearly also return per-year counts (for :func:`year_block_bootstrap`).

    Returns
    -------
    DataFrame, one row per (location, hedge kind, window), columns:
      location_id, hedge ("baseline" | "adjusted"), hedge_station, strike, dist_km, in_listed_set,
      fit_R, fit_n, window, n, n_hot, n_pay, fn_days, fp_days, R, FN, FP, miss_rate, false_payout_rate.
    If return_yearly: (that frame, yearly) where yearly has location_id, hedge, year and the count columns
    for every year inside ``windows``.

    A location that is itself in the listed set gets itself at k = 90 and R = 0. It is kept and flagged
    (in_listed_set) so the caller can decide whether to count it.
    """
    listed_ids = list(listed_ids)
    wide = to_wide(panel)
    if location_ids is None:
        if "is_exposure" in stations.columns:
            location_ids = stations.loc[stations["is_exposure"].astype(bool), "id"].tolist()
        else:
            location_ids = list(wide.columns)
    missing = [s for s in list(location_ids) + listed_ids if s not in wide.columns]
    if missing:
        raise KeyError(f"stations not in panel: {missing}")

    rows, yrows = [], []
    for i in location_ids:
        b = baseline_hedge(i, listed_ids, stations)
        fb = evaluate_hedge(wide, i, b, fit_window, threshold)
        b = Hedge(b.station, b.strike, b.kind, b.dist_km, fit_R=fb["R"], fit_n=fb["n"])
        a = adjusted_hedge(i, listed_ids, wide, stations, fit_window=fit_window, threshold=threshold)
        for hd in (b, a):
            for w in windows:
                yc = yearly_counts(wide, i, hd, w, threshold)
                c = yc[COUNT_COLS].sum().astype(int).to_dict()
                row = {"location_id": i, "hedge": hd.kind, "hedge_station": hd.station, "strike": hd.strike,
                       "dist_km": hd.dist_km, "in_listed_set": i in listed_ids, "fit_R": hd.fit_R,
                       "fit_n": hd.fit_n, "window": w}
                row.update(c)
                row.update(metrics_from_counts(c))
                rows.append(row)
                if return_yearly:
                    y = yc.reset_index()
                    y.insert(0, "hedge", hd.kind)
                    y.insert(0, "location_id", i)
                    yrows.append(y)
    res = pd.DataFrame(rows)
    if return_yearly:
        return res, pd.concat(yrows, ignore_index=True)
    return res


# ----------------------------------------------------------------------------------------------
# Aggregates and the year-block bootstrap
# ----------------------------------------------------------------------------------------------
def aggregate_stats(counts: pd.DataFrame) -> Dict[str, float]:
    """Aggregate statistics over locations. ``counts`` has one row per location with the count columns.

    mean_R             unweighted mean over locations of R_i (locations with n = 0 are skipped)
    miss_rate          pooled: all FN days / all hot days
    false_payout_rate  pooled: all FP days / all payout days
    """
    c = counts[COUNT_COLS].to_numpy(dtype=float)
    return _agg(c)


def _agg(c: np.ndarray) -> Dict[str, float]:
    n, hot, pay, fn, fp = (c[:, j] for j in range(5))
    ok = n > 0
    nan = float("nan")
    return {
        "mean_R": float(np.mean((fn[ok] + fp[ok]) / n[ok])) if ok.any() else nan,
        "miss_rate": float(fn.sum() / hot.sum()) if hot.sum() > 0 else nan,
        "false_payout_rate": float(fp.sum() / pay.sum()) if pay.sum() > 0 else nan,
    }


def bootstrap_year_draws(years: Sequence[int], n_draws: int = BOOT_DRAWS, seed: int = BOOT_SEED) -> np.ndarray:
    """(n_draws, len(years)) array of resampled years (with replacement). Same seed -> same draws."""
    years = np.asarray(sorted(years))
    rng = np.random.default_rng(seed)
    return years[rng.integers(0, len(years), size=(n_draws, len(years)))]


def year_block_bootstrap(arms: Dict[str, pd.DataFrame], years: Optional[Sequence[int]] = None,
                         n_draws: int = BOOT_DRAWS, seed: int = BOOT_SEED) -> pd.DataFrame:
    """Year-block bootstrap of the aggregate statistics.

    Whole summers are resampled with replacement. Every draw uses the same resampled years for all
    stations and all arms, so differences between arms are paired.

    arms   {name: yearly counts}. Each frame has location_id, year and the count columns (as returned by
           mismatch_under_listed_set(..., return_yearly=True), filtered to one hedge kind and one window).
    years  years to resample. Default: the years present in the first arm.

    Returns a DataFrame with n_draws rows and columns "<arm>:<stat>" for stat in
    mean_R, miss_rate, false_payout_rate. Use :func:`percentile_interval` on a column or a difference.
    """
    names = list(arms)
    if years is None:
        years = sorted(arms[names[0]]["year"].unique())
    years = sorted(years)
    draws = bootstrap_year_draws(years, n_draws, seed)
    ypos = {y: j for j, y in enumerate(years)}
    out: Dict[str, np.ndarray] = {}
    # multiplicity of each year in each draw: (n_draws, n_years)
    mult = np.zeros((n_draws, len(years)))
    for j in range(len(years)):
        mult[:, j] = (draws == years[j]).sum(axis=1)
    for name in names:
        df = arms[name]
        locs = sorted(df["location_id"].unique())
        lpos = {l: j for j, l in enumerate(locs)}
        cube = np.zeros((len(locs), len(years), 5))
        d = df[df["year"].isin(years)]
        cube[d["location_id"].map(lpos).to_numpy(), d["year"].map(ypos).to_numpy(), :] = d[COUNT_COLS].to_numpy(float)
        stats = {k: np.empty(n_draws) for k in ("mean_R", "miss_rate", "false_payout_rate")}
        for b in range(n_draws):
            a = _agg(np.tensordot(cube, mult[b], axes=([1], [0])))
            for k in stats:
                stats[k][b] = a[k]
        for k in stats:
            out[f"{name}:{k}"] = stats[k]
    return pd.DataFrame(out)


def percentile_interval(x, level: float = 0.95) -> Tuple[float, float]:
    """Percentile interval of bootstrap draws (NaN draws ignored)."""
    x = np.asarray(x, dtype=float)
    lo = (1 - level) / 2
    return float(np.nanquantile(x, lo)), float(np.nanquantile(x, 1 - lo))
