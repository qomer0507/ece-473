"""Local residual payout model (Viktor workstream).

Formulas (SPEC.md, CONTEXT.md section 4):

    target_t   = N * 1{local_tmax_t >= k}                 local target payout
    station_t  = q * N * 1{station_tmax_t >= k}           Strategy A (q = station fraction, default 1)
    residual_t = max(target_t - station_t, 0)             shortfall-only residual layer
    two_part_t = station_t + residual_t                   Strategy B

Conventions:
- Threshold equality triggers (>=), matching SPEC "TMAX >= 90".
- All functions are vectorized over numpy arrays / pandas Series.
- NaN temperatures propagate to NaN payouts. Nothing is imputed.
  Use `missing_mask` / `require_complete` to flag or reject rows.
- Payouts are gross cash flows. Premiums are handled in metrics.py and
  are never netted into these functions.

Strategy A payout comes from Ehfaz's src/station_hedge.py when it exists.
Until then a private fallback with the same binary rule is used, and
STATION_PAYOUT_SOURCE says which one is active.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "local_target_payout",
    "station_payout",
    "residual_shortfall_payout",
    "two_part_payout",
    "overhedge_amount",
    "missing_mask",
    "require_complete",
    "STATION_PAYOUT_SOURCE",
]


def _as_float_array(x) -> np.ndarray:
    return np.asarray(x, dtype=float)


def _check_terms(threshold, notional) -> None:
    if not np.isfinite(threshold):
        raise ValueError(f"threshold must be finite, got {threshold!r}")
    if not np.isfinite(notional) or notional < 0:
        raise ValueError(f"notional must be finite and >= 0, got {notional!r}")


def _binary_payout(temp, threshold: float, notional: float) -> np.ndarray:
    """N * 1{temp >= threshold}; NaN where temp is NaN."""
    _check_terms(threshold, notional)
    t = _as_float_array(temp)
    out = np.where(t >= threshold, float(notional), 0.0)
    return np.where(np.isnan(t), np.nan, out)


def local_target_payout(local_tmax, threshold: float, notional: float = 800.0) -> np.ndarray:
    """Stylized local target payout N * 1{local_tmax >= threshold}.

    This is the payout the business would want at its own location.
    It is a modeling target, not observed revenue loss.
    """
    return _binary_payout(local_tmax, threshold, notional)


def _station_payout(station_tmax, threshold: float, notional: float = 800.0) -> np.ndarray:
    """Fallback Strategy A payout N * 1{station_tmax >= threshold}.

    Used only when src/station_hedge.py is missing. Same rule as SPEC.
    """
    return _binary_payout(station_tmax, threshold, notional)


try:  # prefer the teammate implementation (Ehfaz owns src/station_hedge.py)
    from src.station_hedge import station_payout as _ext_station_payout  # type: ignore

    STATION_PAYOUT_SOURCE = "src.station_hedge.station_payout"
except Exception:  # pragma: no cover - depends on teammate progress
    _ext_station_payout = None
    STATION_PAYOUT_SOURCE = "src.local_residual._station_payout (fallback)"


def station_payout(station_tmax, threshold: float, notional: float = 800.0) -> np.ndarray:
    """Strategy A payout. Delegates to station_hedge.station_payout if present.

    NaN station temperatures always give NaN here, whatever the external
    function does, so missing data is never treated as "no trigger".
    """
    t = _as_float_array(station_tmax)
    if _ext_station_payout is None:
        return _station_payout(t, threshold, notional)
    out = _as_float_array(_ext_station_payout(t, threshold, notional))
    return np.where(np.isnan(t), np.nan, out)


def residual_shortfall_payout(target, station) -> np.ndarray:
    """Residual R = max(target - station, 0). NaN in either input gives NaN.

    This removes underpayment only. Overpayment (station pays more than
    target) is not offset; measure it with `overhedge_amount`.
    """
    return np.maximum(_as_float_array(target) - _as_float_array(station), 0.0)


def overhedge_amount(target, station) -> np.ndarray:
    """max(station - target, 0): station pays but local target does not."""
    return np.maximum(_as_float_array(station) - _as_float_array(target), 0.0)


def two_part_payout(target, station) -> np.ndarray:
    """Strategy B gross payout: station + max(target - station, 0).

    Equals max(target, station). Never below target, so B has zero
    shortfall by construction.
    """
    s = _as_float_array(station)
    return s + residual_shortfall_payout(target, s)


def missing_mask(*arrays) -> np.ndarray:
    """True where any input is NaN (row must be dropped or flagged)."""
    masks = [np.isnan(_as_float_array(a)) for a in arrays]
    return np.logical_or.reduce(masks)


def require_complete(*arrays) -> None:
    """Raise ValueError if any input contains NaN. Use before computing metrics."""
    m = missing_mask(*arrays)
    if np.any(m):
        raise ValueError(f"{int(m.sum())} row(s) have missing temperature/payout values; "
                         "drop or flag them before evaluation (no imputation).")
