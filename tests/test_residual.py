"""Deterministic edge-case tests for the local residual model and metrics."""
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import backtest as bt  # noqa: E402
from src import local_residual as lr  # noqa: E402
from src import metrics as mt  # noqa: E402

N, K = 800.0, 90.0


def _case(local, station, n_station=N):
    t = lr.local_target_payout([local], K, N)
    s = lr.station_payout([station], K, n_station)
    r = lr.residual_shortfall_payout(t, s)
    b = lr.two_part_payout(t, s)
    o = lr.overhedge_amount(t, s)
    return t[0], s[0], r[0], b[0], o[0]


def test_both_trigger_no_residual():
    t, s, r, b, o = _case(95, 93)
    assert (t, s, r, b, o) == (N, N, 0.0, N, 0.0)


def test_local_only_residual_covers_gap():
    t, s, r, b, o = _case(92, 88)
    assert t == N and s == 0.0 and r == N and b == N and o == 0.0


def test_station_only_overhedge_recorded():
    t, s, r, b, o = _case(87, 91)
    assert t == 0.0 and s == N and r == 0.0
    assert b == N  # B keeps the station overpayment
    assert o == N  # overhedge is recorded, not zero
    pm = mt.payout_metrics([t], [b])
    assert pm["mean_overhedge"] == N and pm["mean_shortfall"] == 0.0


def test_neither_triggers():
    assert _case(80, 85) == (0.0, 0.0, 0.0, 0.0, 0.0)


def test_threshold_equality_triggers():
    t, s, r, b, o = _case(90.0, 90.0)
    assert t == N and s == N and r == 0.0
    t, s, r, *_ = _case(90.0, 89.9)
    assert t == N and s == 0.0 and r == N


def test_nan_propagates_and_is_flagged():
    t = lr.local_target_payout([np.nan, 95], K, N)
    s = lr.station_payout([95, np.nan], K, N)
    assert np.isnan(t[0]) and np.isnan(s[1])
    r = lr.residual_shortfall_payout(t, s)
    assert np.isnan(r).all()  # never silently 0
    assert lr.missing_mask([np.nan, 95], [95, np.nan]).tolist() == [True, True]
    with pytest.raises(ValueError):
        lr.require_complete(t, s)
    with pytest.raises(ValueError):
        mt.payout_metrics(t, s)


def test_backtest_drops_and_counts_missing_rows():
    df = pd.DataFrame({
        "date": ["2016-07-01", "2016-07-02", "2016-07-03", "2023-07-01", "2016-01-15"],
        "city": "X", "local_station_id": "L", "ref_station_id": "R",
        "local_tmax_f": [95, np.nan, 80, 92, 95], "ref_tmax_f": [95, 90, 91, 88, 95],
        "data_quality": "ok"})
    clean, acct = bt.prepare(df)
    assert len(clean) == 3  # Jan row out of season, one NaN row dropped
    assert int(acct["missing_rows"].sum()) == 1


def test_partial_station_notional_scales_residual():
    for q in (0.0, 0.25, 0.5, 1.0):
        t, s, r, b, _ = _case(95, 95, n_station=q * N)
        assert s == pytest.approx(q * N)
        assert r == pytest.approx((1 - q) * N)
        assert b == pytest.approx(N)


def test_invalid_terms_rejected():
    with pytest.raises(ValueError):
        lr.local_target_payout([95], K, -1.0)
    with pytest.raises(ValueError):
        lr.local_target_payout([95], float("nan"), N)


def test_premiums_separate_from_payouts():
    target = np.array([N, 0, N, 0])
    station = np.array([N, N, 0, 0])
    resid = lr.residual_shortfall_payout(target, station)
    b = lr.two_part_payout(target, station)
    # gross payouts do not depend on any premium
    assert b.tolist() == [N, N, N, 0]
    er = resid.mean()
    assert mt.premium(er, 0.0) == pytest.approx(er)
    assert mt.premium(er, 0.5) == pytest.approx(1.5 * er)
    # net cost subtracts payout and adds premium as separate terms
    c = mt.net_cost(target, b, 10.0)
    assert c.tolist() == [10.0, 10.0 - N, 10.0, 10.0]


def test_mismatch_rates():
    m = mt.trigger_mismatch_rates([1, 1, 0, 0], [1, 0, 1, 0])
    assert m["local_only_rate"] == 0.25 and m["station_only_rate"] == 0.25
    assert m["mismatch_rate"] == 0.5


def test_break_even_zero_under_risk_neutral_positive_under_risk_aversion():
    rng = np.random.default_rng(1)
    loc = rng.normal(88, 5, 2000)
    st = loc + rng.normal(0, 3, 2000)
    t = lr.local_target_payout(loc, K, N)
    s = lr.station_payout(st, K, N)
    r = lr.residual_shortfall_payout(t, s)
    er = r.mean()
    assert er > 0
    be_rn = mt.break_even_loading(t, s, r, er, mt.make_objective("risk_neutral"))
    assert be_rn == pytest.approx(0.0, abs=1e-9)
    be_mv = mt.break_even_loading(t, s, r, er, mt.make_objective("mean_variance", notional=N, a=1.0))
    be_cv = mt.break_even_loading(t, s, r, er, mt.make_objective("mean_cvar", gamma=0.25))
    assert be_mv > 0 and be_cv > 0
    # B has zero shortfall by construction
    assert mt.payout_metrics(t, lr.two_part_payout(t, s))["mean_shortfall"] == 0.0


def test_break_even_nan_when_no_residual():
    t = np.array([0.0, N]); s = np.array([0.0, N])
    r = lr.residual_shortfall_payout(t, s)
    assert math.isnan(mt.break_even_loading(t, s, r, 0.0, mt.risk_neutral))


def test_cvar_simple():
    c = np.arange(100, dtype=float)
    # worst 5% of 100 values = 95..99, mean 97
    assert mt.mean_cvar(c, gamma=1.0, alpha=0.95) == pytest.approx(c.mean() + 97.0)
