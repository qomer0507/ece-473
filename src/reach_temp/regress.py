"""OLS of HE on distance, elevation difference and a coast indicator (reading choice 10).

he ~ 1 + dist_100km + abs_elev_diff_100m + coast
  dist_100km         distance / 100
  abs_elev_diff_100m |elev_G - elev_S| / 100
  coast              1 if the exposure gauge G is within COAST_KM of the shoreline (Phase 1 coast_km)
Classical (homoskedastic) standard errors and a 95% percentile interval from the gauge bootstrap of the
coefficients (exposure gauges resampled with replacement, every pair of a drawn gauge kept). Pairs with NaN HE
are left out. Pairs that share a gauge are not independent, so the classical SE is too small; the gauge interval
is the one to read.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

COAST_KM = 25.0
TERMS = ("intercept", "dist_100km", "abs_elev_diff_100m", "coast")
N_DRAWS = 2000
SEED = 473


def design(pairs: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    """(X, y, rows used). Needs columns he, dist_km, elev_diff_m, coast_g."""
    p = pairs[pairs["he"].notna()].reset_index(drop=True)
    X = np.column_stack([np.ones(len(p)), p["dist_km"].to_numpy(dtype=float) / 100.0,
                         p["elev_diff_m"].to_numpy(dtype=float) / 100.0, p["coast_g"].to_numpy(dtype=float)])
    return X, p["he"].to_numpy(dtype=float), p


def _wls(X: np.ndarray, y: np.ndarray, w: np.ndarray) -> np.ndarray:
    sw = np.sqrt(w)
    beta, *_ = np.linalg.lstsq(X * sw[:, None], y * sw, rcond=None)
    return beta


def ols_table(pairs: pd.DataFrame, n_draws: int = N_DRAWS, seed: int = SEED) -> tuple[pd.DataFrame, dict]:
    """Coefficient table (coef, classical se, t, p, gauge-bootstrap 2.5/97.5) and a fit summary dict."""
    X, y, p = design(pairs)
    n, k = X.shape
    beta = _wls(X, y, np.ones(n))
    resid = y - X @ beta
    dof = n - k
    s2 = float(resid @ resid) / dof
    cov = s2 * np.linalg.inv(X.T @ X)
    se = np.sqrt(np.diag(cov))
    t = beta / se
    pv = 2 * stats.t.sf(np.abs(t), dof)
    r2 = 1 - float(resid @ resid) / float(((y - y.mean()) ** 2).sum())

    gauges = np.array(sorted(pairs["g_id"].unique()))
    gi = np.searchsorted(gauges, p["g_id"].to_numpy())
    rng = np.random.default_rng(seed)
    draws = np.full((n_draws, k), np.nan)
    for r in range(n_draws):
        wg = np.bincount(rng.integers(0, len(gauges), size=len(gauges)), minlength=len(gauges)).astype(float)
        w = wg[gi]
        if (w > 0).sum() <= k or np.ptp(X[w > 0, 1]) == 0:
            continue
        draws[r] = _wls(X, y, w)
    lo = np.nanpercentile(draws, 2.5, axis=0)
    hi = np.nanpercentile(draws, 97.5, axis=0)
    table = pd.DataFrame({"term": TERMS, "coef": beta, "se_classical": se, "t": t, "p_classical": pv,
                          "lo_gauge": lo, "hi_gauge": hi})
    info = {"n_pairs": int(n), "n_gauges": int(p["g_id"].nunique()), "r2": float(r2),
            "n_draws_valid": int((~np.isnan(draws[:, 0])).sum()), "resid_sd": float(np.sqrt(s2))}
    return table, info
