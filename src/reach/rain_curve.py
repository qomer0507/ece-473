"""HE against distance: bins, bootstrap bands, reach and the regression.

Bins: same-station pairs form their own bin at 0 km (bin_lo = bin_hi = 0); then (0,10], (10,20], ..., (190,200].
Bin mean = mean HE of the pairs with a defined HE in the bin (also the mean count correlation).
Bootstrap A ("pair"): resample pairs with replacement.
Bootstrap B ("gauge"): resample exposure gauges G with replacement and keep every pair of each drawn gauge,
multiplicity kept, because pairs that share a gauge are not independent.
2,000 draws, numpy default_rng(473). A bin empty in a draw is left out of that bin's interval and counted.
Reach (registered definition) = the largest bin whose 2.5th-percentile band edge is above 0, reported as the
bin's upper edge in km. Contiguous reach (labelled, not the registered definition) = the upper edge of the
last bin before the first bin whose lower band edge is not above 0.
Regression: OLS of HE on distance (per 100 km), |elevation difference| (per 100 m) and the coast indicator of
the exposure gauge; classical SEs plus a gauge-bootstrap interval of each coefficient.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

BIN_KM = 10.0
MAX_KM = 200.0
N_DRAWS = 2000
SEED = 473


def bin_edges(max_km: float = MAX_KM, width: float = BIN_KM) -> np.ndarray:
    return np.arange(0.0, max_km + width / 2, width)


def assign_bins(dist_km, same_station) -> np.ndarray:
    """Bin index: 0 for same-station pairs, k for (10(k-1), 10k] km. -1 when out of range."""
    d = np.asarray(dist_km, dtype=float)
    same = np.asarray(same_station, dtype=bool)
    k = np.ceil(d / BIN_KM - 1e-9).astype(int)
    k = np.where(same | (d <= 0), 0, k)
    k = np.where(d > MAX_KM, -1, k)
    return k


def bin_labels(n_bins: int) -> pd.DataFrame:
    lo = np.concatenate([[0.0], np.arange(0.0, (n_bins - 1) * BIN_KM, BIN_KM)])
    hi = np.concatenate([[0.0], np.arange(BIN_KM, n_bins * BIN_KM, BIN_KM)])
    return pd.DataFrame({"bin": np.arange(n_bins), "bin_lo_km": lo, "bin_hi_km": hi})


def bin_means(values: np.ndarray, bins: np.ndarray, n_bins: int) -> np.ndarray:
    """Mean of `values` per bin (NaN values ignored; NaN where a bin has no defined value)."""
    out = np.full(n_bins, np.nan)
    ok = ~np.isnan(values) & (bins >= 0)
    if not ok.any():
        return out
    s = np.bincount(bins[ok], weights=values[ok], minlength=n_bins)
    n = np.bincount(bins[ok], minlength=n_bins)
    with np.errstate(invalid="ignore", divide="ignore"):
        out = np.where(n > 0, s / np.maximum(n, 1), np.nan)
    return out


def bootstrap_bins(values: np.ndarray, bins: np.ndarray, groups: np.ndarray | None, n_bins: int,
                   n_draws: int = N_DRAWS, seed: int = SEED) -> np.ndarray:
    """Matrix (n_draws, n_bins) of bin means under resampling.

    groups None: resample rows (pairs). groups given: resample distinct group labels (exposure gauges) with
    replacement and take every row of each drawn group, multiplicity kept.
    """
    rng = np.random.default_rng(seed)
    values = np.asarray(values, dtype=float)
    bins = np.asarray(bins)
    n = len(values)
    out = np.full((n_draws, n_bins), np.nan)
    if groups is None:
        for t in range(n_draws):
            idx = rng.integers(0, n, n)
            out[t] = bin_means(values[idx], bins[idx], n_bins)
    else:
        groups = np.asarray(groups)
        labels = np.unique(groups)
        members = {g: np.flatnonzero(groups == g) for g in labels}
        for t in range(n_draws):
            drawn = rng.integers(0, len(labels), len(labels))
            idx = np.concatenate([members[labels[k]] for k in drawn])
            out[t] = bin_means(values[idx], bins[idx], n_bins)
    return out


def band(draws: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """2.5th and 97.5th percentiles per column over the draws where the column is defined, and how many draws
    had the column empty."""
    lo = np.full(draws.shape[1], np.nan)
    hi = np.full(draws.shape[1], np.nan)
    empty = np.zeros(draws.shape[1], dtype=int)
    for j in range(draws.shape[1]):
        c = draws[:, j]
        c = c[~np.isnan(c)]
        empty[j] = draws.shape[0] - len(c)
        if len(c):
            lo[j], hi[j] = np.percentile(c, [2.5, 97.5])
    return lo, hi, empty


def curve_table(pairs: pd.DataFrame, n_draws: int = N_DRAWS, seed: int = SEED) -> pd.DataFrame:
    """One row per bin: n pairs, n with defined HE, mean HE, mean correlation, bands under both schemes."""
    n_bins = int(MAX_KM / BIN_KM) + 1
    bins = assign_bins(pairs["dist_km"], pairs["same_station"])
    he = pairs["he"].to_numpy(dtype=float)
    corr = pairs["count_corr"].to_numpy(dtype=float)
    t = bin_labels(n_bins)
    t["n_pairs"] = np.bincount(bins[bins >= 0], minlength=n_bins)
    t["n_he_defined"] = np.bincount(bins[(bins >= 0) & ~np.isnan(he)], minlength=n_bins)
    t["n_gauges"] = [pairs.loc[bins == b, "g_id"].nunique() for b in range(n_bins)]
    t["mean_he"] = bin_means(he, bins, n_bins)
    t["median_he"] = [float(np.nanmedian(he[bins == b])) if (bins == b).any() and (~np.isnan(he[bins == b])).any()
                      else np.nan for b in range(n_bins)]
    t["mean_corr"] = bin_means(corr, bins, n_bins)
    t["mean_agreement"] = bin_means(pairs["trigger_agreement"].to_numpy(dtype=float), bins, n_bins)
    a = bootstrap_bins(he, bins, None, n_bins, n_draws, seed)
    lo, hi, empty = band(a)
    t["he_lo_pair"], t["he_hi_pair"], t["empty_draws_pair"] = lo, hi, empty
    b = bootstrap_bins(he, bins, pairs["g_id"].to_numpy(), n_bins, n_draws, seed)
    lo, hi, empty = band(b)
    t["he_lo_gauge"], t["he_hi_gauge"], t["empty_draws_gauge"] = lo, hi, empty
    ac = bootstrap_bins(corr, bins, None, n_bins, n_draws, seed)
    lo, hi, _ = band(ac)
    t["corr_lo_pair"], t["corr_hi_pair"] = lo, hi
    return t


def reach_km(curve: pd.DataFrame, lo_col: str) -> dict:
    """Registered reach (largest bin with lower band edge > 0) and the contiguous reach, in km (bin upper edge).
    Same-station bin (0 km) is not a distance bin; it is reported separately."""
    c = curve[curve["bin"] > 0]
    above = c[lo_col].to_numpy() > 0
    reg = float(c["bin_hi_km"].to_numpy()[above].max()) if above.any() else 0.0
    contiguous = 0.0
    for ok, hi in zip(above, c["bin_hi_km"]):
        if not ok:
            break
        contiguous = float(hi)
    return {"reach_km": reg, "contiguous_reach_km": contiguous,
            "same_station_lo_above_0": bool(curve.loc[curve["bin"] == 0, lo_col].to_numpy()[0] > 0)
            if (curve["bin"] == 0).any() else None}


# ------------------------------------------------------------------ regression
REG_COLUMNS = ["dist_100km", "elev_diff_100m", "coast_g"]


def design(pairs: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    p = pairs[~pairs["he"].isna()]
    x = np.column_stack([np.ones(len(p)), p["dist_km"].to_numpy(dtype=float) / 100.0,
                         p["elev_diff_m"].to_numpy(dtype=float) / 100.0, p["coast_g"].to_numpy(dtype=float)])
    return x, p["he"].to_numpy(dtype=float), p["g_id"].to_numpy()


def ols(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    """Coefficients, classical standard errors, R^2."""
    beta, *_ = np.linalg.lstsq(x, y, rcond=None)
    resid = y - x @ beta
    n, k = x.shape
    sigma2 = float(resid @ resid) / max(n - k, 1)
    cov = sigma2 * np.linalg.pinv(x.T @ x)
    se = np.sqrt(np.diag(cov))
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - float(resid @ resid) / ss_tot if ss_tot > 0 else float("nan")
    return beta, se, r2


def regression(pairs: pd.DataFrame, n_draws: int = N_DRAWS, seed: int = SEED, label: str = "all_pairs") -> pd.DataFrame:
    """OLS table with classical SEs and a gauge-bootstrap 95% interval per coefficient."""
    x, y, g = design(pairs)
    beta, se, r2 = ols(x, y)
    rng = np.random.default_rng(seed)
    labels = np.unique(g)
    members = {lab: np.flatnonzero(g == lab) for lab in labels}
    draws = np.full((n_draws, x.shape[1]), np.nan)
    for t in range(n_draws):
        idx = np.concatenate([members[labels[k]] for k in rng.integers(0, len(labels), len(labels))])
        draws[t], *_ = np.linalg.lstsq(x[idx], y[idx], rcond=None)
    lo, hi = np.nanpercentile(draws, [2.5, 97.5], axis=0)
    return pd.DataFrame({"model": label, "term": ["intercept"] + REG_COLUMNS, "coef": beta, "se_classical": se,
                         "lo_gauge_boot": lo, "hi_gauge_boot": hi, "n_pairs": len(y), "n_gauges": len(labels),
                         "r2": r2})
