"""Tests for src/load_weather.py and src/basis_risk.py.

Hand-checked toy data plus checks of the real files when they exist.
"""
from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.basis_risk import pair_table, temp_diff_stats, trigger_mismatch  # noqa: E402
from src.load_weather import (ALIGNED, ALIGNED_COLS, RAW_CACHE, STATIONS, align_pair,  # noqa: E402
                              haversine_km, load_raw, season_dates)


@pytest.fixture
def toy_raw():
    # local L, reference R; 2020-07-01..05. L missing on 07-03, R missing on 07-05.
    rows = [("2020-07-01", "L", 91), ("2020-07-01", "R", 88),
            ("2020-07-02", "L", 89), ("2020-07-02", "R", 90),
            ("2020-07-03", "R", 95),
            ("2020-07-04", "L", 95), ("2020-07-04", "R", 96),
            ("2020-07-05", "L", 80)]
    return pd.DataFrame(rows, columns=["date", "station_id", "tmax_f"]).astype({"tmax_f": float})


def test_align_flags_missing_without_imputation(toy_raw):
    dates = pd.date_range("2020-07-01", "2020-07-06")
    a = align_pair(toy_raw, "X", "L", "R", dates)
    assert list(a.columns) == ALIGNED_COLS
    assert len(a) == 6  # full date grid, including a day with no data at all
    q = dict(zip(a["date"], a["data_quality"]))
    assert q == {"2020-07-01": "ok", "2020-07-02": "ok", "2020-07-03": "missing_local",
                 "2020-07-04": "ok", "2020-07-05": "missing_ref", "2020-07-06": "missing_both"}
    row3 = a[a["date"] == "2020-07-03"].iloc[0]
    assert math.isnan(row3["local_tmax_f"]) and row3["ref_tmax_f"] == 95
    assert a["local_tmax_f"].isna().sum() == 2 and a["ref_tmax_f"].isna().sum() == 2


def test_qflag_values_become_missing(tmp_path):
    p = tmp_path / "raw.csv"
    p.write_text("date,station_id,tmax_f,qflag\n2020-07-01,L,91,\n2020-07-02,L,120,X\n")
    r = load_raw(p)
    assert r["tmax_f"].iloc[0] == 91 and math.isnan(r["tmax_f"].iloc[1])


def test_duplicate_rows_rejected(tmp_path):
    p = tmp_path / "raw.csv"
    p.write_text("date,station_id,tmax_f\n2020-07-01,L,91\n2020-07-01,L,92\n")
    with pytest.raises(ValueError):
        load_raw(p)


def test_trigger_mismatch_hand_counts():
    # ok days only, from the toy: (L,R) = (91,88), (89,90), (95,96); k=90
    m = trigger_mismatch(np.array([91, 89, 95]), np.array([88, 90, 96]), 90)
    assert m["n_days"] == 3 and m["heat_days_local"] == 2 and m["heat_days_ref"] == 2
    assert m["both_heat"] == 1 and m["local_heat_ref_not"] == 1 and m["ref_heat_local_not"] == 1
    assert m["p_local_heat_ref_not"] == pytest.approx(1 / 3)
    assert m["mismatch_rate"] == pytest.approx(2 / 3)
    # threshold is inclusive: 90 counts as heat at k=90
    assert trigger_mismatch(np.array([90]), np.array([90]), 90)["both_heat"] == 1


def test_trigger_mismatch_rejects_nan():
    with pytest.raises(ValueError):
        trigger_mismatch(np.array([90, np.nan]), np.array([90, 91]), 90)


def test_pair_table_uses_only_ok_rows(toy_raw):
    a = align_pair(toy_raw, "X", "L", "R", pd.date_range("2020-07-01", "2020-07-06"))
    t = pair_table(a, thresholds=(90,))
    r = t.iloc[0]
    assert r["days_in_window"] == 6 and r["days_ok"] == 3
    assert r["coverage_pct"] == pytest.approx(50.0)
    assert r["mean_diff_f"] == pytest.approx(((91 - 88) + (89 - 90) + (95 - 96)) / 3)


def test_temp_diff_stats_identical_series():
    s = temp_diff_stats(np.array([80.0, 85, 90]), np.array([80.0, 85, 90]))
    assert s["mean_diff_f"] == 0 and s["mae_f"] == 0 and s["corr"] == pytest.approx(1.0)


def test_haversine_known_distance():
    # Central Park to LaGuardia, coordinates from NCEI; about 7.5 km
    assert haversine_km(40.77898, -73.96925, 40.77945, -73.88027) == pytest.approx(7.49, abs=0.02)


def test_season_dates_window():
    d = season_dates("2015-05-01", "2025-09-30")
    assert d.min() == pd.Timestamp("2015-05-01") and d.max() == pd.Timestamp("2025-09-30")
    assert set(d.month) == {5, 6, 7, 8, 9} and len(d) == 11 * 153


# ---- checks on the real data files (skipped if not built) ----

@pytest.mark.skipif(not RAW_CACHE.exists(), reason="raw data not extracted")
def test_raw_matches_ncei_spotcheck():
    """Every TMAX value fetched straight from NCEI agrees with the raw file used for analysis."""
    raw = load_raw(RAW_CACHE).set_index(["date", "station_id"])["tmax_f"]
    spot = ROOT / "data" / "raw" / "ncei_spotcheck"
    n = 0
    for f in sorted(spot.glob("*.csv")):
        with f.open() as fh:
            for r in csv.DictReader(fh):
                v = float(r["TMAX"])
                f_val = v if "standard" in f.name else math.floor(v / 10 * 9 / 5 + 32 + 0.5)
                assert raw.loc[(r["DATE"], r["STATION"])] == f_val, (f.name, r)
                n += 1
    assert n >= 40


@pytest.mark.skipif(not ALIGNED.exists(), reason="aligned table not built")
def test_aligned_file_shape():
    a = pd.read_csv(ALIGNED, dtype={"date": str})
    st = pd.read_csv(STATIONS)
    assert list(a.columns) == ALIGNED_COLS
    assert not a.duplicated(["date", "local_station_id", "ref_station_id"]).any()
    n_local = (st["role"] == "local").sum()
    assert len(a) == n_local * 11 * 153
    ok = a["data_quality"] == "ok"
    assert a.loc[ok, ["local_tmax_f", "ref_tmax_f"]].notna().all().all()
    assert a.loc[~ok, ["local_tmax_f", "ref_tmax_f"]].isna().any(axis=1).all()
