"""Distance bins, bootstrap bands (by pair and by exposure gauge) and reach (reading choices 8-9).

Bins: same-station pairs form bin 0 (label "0"); then (0,10], (10,20], ..., (190,200]. A bin's value is the mean
HE of its pairs with a defined HE. Pairs with NaN HE carry no weight anywhere here.

Bootstrap A ("pair"): pairs resampled with replacement.
Bootstrap B ("gauge"): exposure gauges G resampled with replacement; every pair of a drawn gauge is kept, with
multiplicity. 2,000 draws each, numpy default_rng(473). A bin that is empty in a draw is NaN for that draw and
left out of the percentile; the number of such draws is reported.

Reach (registered): the largest bin whose 2.5th-percentile band edge is above 0, reported as the bin's upper
edge in km. Contiguous reach (labelled extra): the upper edge of the last bin before the first bin whose lower
band edge is not above 0.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

BIN_WIDTH_KM = 10.0
MAX_KM = 200.0
N_DRAWS = 2000
SEED = 473
INTERVAL = (2.5, 97.5)


def bin_edges(max_km: float = MAX_KM, width: float = BIN_WIDTH_KM) -> np.ndarray:
    """Upper edges: 0 (same station), 10, 20, ..., max_km."""
    return np.concatenate([[0.0], np.arange(width, max_km + 1e-9, width)])


def bin_index(dist_km, same_station) -> np.ndarray:
    """0 for same-station pairs; otherwise ceil(dist / width) (so 0 < d <= 10 -> 1, 10 < d <= 20 -> 2, ...)."""
    d = np.asarray(dist_km, dtype=float)
    same = np.asarray(same_station, dtype=bool)
    idx = np.ceil(d / BIN_WIDTH_KM - 1e-9).astype(int)
    idx[same] = 0
    idx[(~same) & (idx < 1)] = 1
    return idx


def bin_table(edges: np.ndarray) -> pd.DataFrame:
    lo = np.concatenate([[0.0], edges[:-1]])
    labels = ["same station"] + [f"({int(a)},{int(b)}]" for a, b in zip(lo[1:], edges[1:])]
    return pd.DataFrame({"bin": np.arange(len(edges)), "lo_km": lo, "hi_km": edges, "label": labels})


def _weighted_bin_means(w: np.ndarray, he: np.ndarray, bins: np.ndarray, n_bins: int) -> np.ndarray:
    """w: (draws, units) multiplicities; he, bins: per unit. Returns (draws, n_bins) means, NaN where empty."""
    onehot = np.zeros((len(he), n_bins))
    onehot[np.arange(len(he)), bins] = 1.0
    cnt = w @ onehot
    tot = w @ (onehot * he[:, None])
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(cnt > 0, tot / cnt, np.nan)


def bootstrap_bins(pairs: pd.DataFrame, scheme: str, n_draws: int = N_DRAWS, seed: int = SEED,
                   edges: np.ndarray | None = None) -> np.ndarray:
    """(n_draws, n_bins) bin means per bootstrap draw. scheme 'pair' or 'gauge'. Pairs with NaN HE are dropped."""
    edges = bin_edges() if edges is None else edges
    p = pairs[pairs["he"].notna()].reset_index(drop=True)
    he = p["he"].to_numpy(dtype=float)
    bins = bin_index(p["dist_km"], p["same_station"])
    rng = np.random.default_rng(seed)
    if scheme == "pair":
        n = len(p)
        idx = rng.integers(0, n, size=(n_draws, n))
        w = np.stack([np.bincount(row, minlength=n) for row in idx]).astype(float)
    elif scheme == "gauge":
        gauges = np.array(sorted(pairs["g_id"].unique()))  # every exposure gauge, even if all its pairs are NaN
        gi = np.searchsorted(gauges, p["g_id"].to_numpy())
        idx = rng.integers(0, len(gauges), size=(n_draws, len(gauges)))
        wg = np.stack([np.bincount(row, minlength=len(gauges)) for row in idx]).astype(float)
        w = wg[:, gi]
    else:
        raise ValueError(f"unknown scheme {scheme!r}")
    return _weighted_bin_means(w, he, bins, len(edges))


def curve_table(pairs: pd.DataFrame, n_draws: int = N_DRAWS, seed: int = SEED) -> pd.DataFrame:
    """Per bin: n pairs, n with HE, mean HE, and the 95% band under both schemes (plus empty-draw counts)."""
    edges = bin_edges()
    t = bin_table(edges)
    allb = bin_index(pairs["dist_km"], pairs["same_station"])
    ok = pairs["he"].notna().to_numpy()
    t["n_pairs"] = np.bincount(allb, minlength=len(edges))
    t["n_he"] = np.bincount(allb[ok], minlength=len(edges))
    t["n_gauges"] = [pairs.loc[(allb == b) & ok, "g_id"].nunique() for b in t["bin"]]
    sums = np.bincount(allb[ok], weights=pairs["he"].to_numpy()[ok], minlength=len(edges))
    with np.errstate(invalid="ignore", divide="ignore"):
        t["mean_he"] = np.where(t["n_he"] > 0, sums / t["n_he"], np.nan)
    # labelled extra, not the registered statistic: median HE of the bin's pairs
    t["median_he"] = [pairs.loc[(allb == b) & ok, "he"].median() if (t.loc[b, "n_he"] > 0) else np.nan
                      for b in t["bin"]]
    for scheme in ("pair", "gauge"):
        draws = bootstrap_bins(pairs, scheme, n_draws, seed, edges)
        with np.errstate(invalid="ignore"):
            lo = np.nanpercentile(draws, INTERVAL[0], axis=0) if len(draws) else np.nan
            hi = np.nanpercentile(draws, INTERVAL[1], axis=0) if len(draws) else np.nan
        t[f"lo_{scheme}"] = lo
        t[f"hi_{scheme}"] = hi
        t[f"empty_draws_{scheme}"] = np.isnan(draws).sum(axis=0)
    return t


def reach_km(curve: pd.DataFrame, lo_col: str) -> dict:
    """Registered reach and the contiguous variant from a curve table (bins in distance order).

    reach_km: upper edge of the LARGEST bin whose lower band edge > 0 (NaN if none).
    contiguous_reach_km: upper edge of the last bin before the first bin whose lower band edge is not > 0
    (0 if the same-station bin itself fails; NaN if no bin has a band).
    """
    c = curve.sort_values("bin")
    above = (c[lo_col] > 0).to_numpy()
    hi = c["hi_km"].to_numpy(dtype=float)
    reach = float(hi[above].max()) if above.any() else float("nan")
    if not c[lo_col].notna().any():
        contig = float("nan")
    else:
        contig = 0.0
        for a, h in zip(above, hi):
            if not a:
                break
            contig = float(h)
    return {"reach_km": reach, "contiguous_reach_km": contig,
            "n_bins_above": int(above.sum()), "n_bins_with_band": int(c[lo_col].notna().sum())}
