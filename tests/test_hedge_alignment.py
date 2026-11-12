"""Joint usable-day alignment across two locations, and the leak test (REPORT seasons cannot move TRAIN choices)."""
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.hedge_eval import cases as hc  # noqa: E402
from src.hedge_eval import data as hd  # noqa: E402
from src.hedge_eval import strategies as hs  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRICE = {"a": 0.0851, "s": 0.5037, "u": 0.0833}
WINDOWS = ("10_16", "10_18", "10_20")
THRESHOLDS = ("0p10", "0p25", "0p50")


def daily(rows, season_usable=True):
    """rows: (date, usable_10_18, rain_10_18, ghcn) -> a daily table in the Phase 1 format (all windows equal)."""
    out = []
    for date, usable, rain, ghcn in rows:
        r = {"date": pd.Timestamp(date), "season": pd.Timestamp(date).year, "season_usable": season_usable,
             "weekend_or_holiday": pd.Timestamp(date).weekday() >= 5, "ghcn_prcp_in": ghcn}
        for w in WINDOWS:
            r[f"usable_{w}"] = usable
            for t in THRESHOLDS:
                r[f"loss_{t}_{w}"] = (rain >= float(t.replace("p", "."))) if usable else pd.NA
        out.append(r)
    d = pd.DataFrame(out)
    for c in d.columns:
        if c.startswith("loss_"):
            d[c] = d[c].astype("boolean")
    return d


def test_only_days_usable_at_both_locations_count():
    # 2001-06-01 Fri, 02 Sat, 03 Sun, 04 Mon, 05 Tue
    s = daily([("2001-06-01", True, 0.30, 0.40), ("2001-06-02", True, 0.30, 0.35), ("2001-06-03", False, 0.0, 0.50),
               ("2001-06-04", True, 0.00, 0.01), ("2001-06-05", True, 0.25, np.nan)])
    p = daily([("2001-06-01", True, 0.00, 0.0), ("2001-06-02", False, 0.0, 0.0), ("2001-06-03", True, 0.60, 0.0),
               ("2001-06-04", True, 0.26, 0.0), ("2001-06-05", True, 0.30, 0.0)])
    j = hd.joint_daily(s, p)
    # day 2 is unusable at the park, day 3 at S: both dropped at BOTH locations
    assert list(j["date"].dt.day) == [1, 4, 5]
    assert list(j["c_s"]) == [1, 0, 1]          # 0.25 counts (equality)
    assert list(j["k_s"]) == [1, 1, 0]          # 0.01 pays; a missing daily total is No
    assert list(j["d_park"]) == [0, 1, 1]
    a = hd.season_aggregates(j)
    assert a.loc[0, ["n_days", "D_park", "C_S", "K_S"]].tolist() == [3, 2, 2, 2]


def test_same_station_keeps_every_usable_day_and_d_equals_c():
    s = daily([("2001-06-01", True, 0.30, 0.40), ("2001-06-02", False, 0.0, 0.2), ("2001-06-03", True, 0.0, 0.0)])
    j = hd.joint_daily(s, s)
    assert len(j) == 2 and (j["d_park"] == j["c_s"]).all()


def test_season_must_be_usable_at_both_locations():
    s = daily([("2001-06-01", True, 0.3, 0.4), ("2002-06-01", True, 0.3, 0.4)])
    p = pd.concat([daily([("2001-06-01", True, 0.3, 0.0)], season_usable=False),
                   daily([("2002-06-01", True, 0.3, 0.0)])], ignore_index=True)
    assert list(hd.joint_daily(s, p)["season"]) == [2002]


def test_park_definitions_change_d_park_only():
    s = daily([("2001-06-01", True, 0.30, 0.4), ("2001-06-02", True, 0.30, 0.4)])     # Fri, Sat
    p = daily([("2001-06-01", True, 0.12, 0.0), ("2001-06-02", True, 0.55, 0.0)])
    assert list(hd.joint_daily(s, p, hd.ParkLoss("0p10", "10_18"))["d_park"]) == [1, 1]
    assert list(hd.joint_daily(s, p, hd.ParkLoss("0p50", "10_18"))["d_park"]) == [0, 1]
    wk = hd.joint_daily(s, p, hd.ParkLoss("0p10", "10_18", True))
    assert list(wk["d_park"]) == [0, 1]                      # Friday cannot be a loss day
    assert list(wk["c_s"]) == [1, 1]                         # the contract still counts all days


def test_park_window_must_be_complete_at_the_park():
    s = daily([("2001-06-01", True, 0.30, 0.4), ("2001-06-02", True, 0.30, 0.4)])
    p = daily([("2001-06-01", True, 0.30, 0.0), ("2001-06-02", True, 0.30, 0.0)])
    p.loc[1, "usable_10_20"] = False
    p.loc[1, "loss_0p25_10_20"] = pd.NA
    assert len(hd.joint_daily(s, p, hd.ParkLoss("0p25", "10_20"))) == 1
    assert len(hd.joint_daily(s, p, hd.ParkLoss("0p25", "10_18"))) == 2


def test_split_windows_inclusive():
    s = daily([(f"{y}-06-01", True, 0.3, 0.4) for y in range(1998, 2018)])
    tr, rp = hd.split_windows(hd.joint_daily(s, s), (1999, 2014), (2015, 2026))
    assert sorted(tr["season"]) == list(range(1999, 2015)) and sorted(rp["season"]) == [2015, 2016, 2017]


# ------------------------------------------------------------------ leak test
def synthetic_station(seed, seasons, n_days=80):
    rng = np.random.default_rng(seed)
    rows = []
    for y in seasons:
        wet = rng.uniform(0.2, 0.5)
        for i in range(n_days):
            date = pd.Timestamp(y, 6, 1) + pd.Timedelta(days=i)
            rain = float(np.round(rng.exponential(0.3), 2)) if rng.random() < wet else 0.0
            open_rain = rain * rng.uniform(0, 1)
            rows.append((date, rng.random() < 0.97, round(open_rain, 2), rain))
    return daily(rows)


def scramble_report(d, first_report, seed):
    """Replace every weather value in seasons >= first_report with different random values."""
    rng = np.random.default_rng(seed)
    out = d.copy()
    m = (out["season"] >= first_report).to_numpy()
    n = int(m.sum())
    out.loc[m, "ghcn_prcp_in"] = rng.choice([0.0, 0.5, 2.0], n)
    for c in out.columns:
        if c.startswith("loss_"):
            out.loc[m, c] = pd.array(rng.random(n) < 0.5, dtype="boolean")
    return out


def params_tuple(p):
    d = p.to_dict()
    return {k: d[k] for k in d}


def test_leak_report_seasons_cannot_change_train_choices_synthetic():
    seasons = range(1999, 2027)
    tables = {"S": synthetic_station(1, seasons), "P": synthetic_station(2, seasons)}
    case = hc.Case("leak", "S", "P")
    base = hc.run_case(case, tables, PRICE, n_draws=20)
    changed_tables = {k: scramble_report(v, 2015, 99 + i) for i, (k, v) in enumerate(tables.items())}
    changed = hc.run_case(case, changed_tables, PRICE, n_draws=20)
    assert params_tuple(base["params"]) == params_tuple(changed["params"])          # every TRAIN-chosen number
    tr_a = base["seasons"][base["seasons"].window == "TRAIN"].reset_index(drop=True)
    tr_b = changed["seasons"][changed["seasons"].window == "TRAIN"].reset_index(drop=True)
    pd.testing.assert_frame_equal(tr_a, tr_b)
    rp_a = base["seasons"][base["seasons"].window == "REPORT"]
    rp_b = changed["seasons"][changed["seasons"].window == "REPORT"]
    assert not np.allclose(rp_a["net_cost"].to_numpy(), rp_b["net_cost"].to_numpy())  # the scramble did bite


def test_leak_changing_train_does_change_choices():
    seasons = range(1999, 2027)
    s = synthetic_station(1, seasons)
    a = hc.run_case(hc.Case("x", "S", "S"), {"S": s}, PRICE, n_draws=5)["params"]
    s2 = s.copy()
    m = (s2["season"] <= 2014).to_numpy()
    s2.loc[m, "ghcn_prcp_in"] = 0.0
    b = hc.run_case(hc.Case("x", "S", "S"), {"S": s2}, PRICE, n_draws=5)["params"]
    assert a.p_month != b.p_month       # the test above is not passing only because nothing can move


@pytest.mark.skipif(not os.path.exists(os.path.join(ROOT, "data", "processed", "rain", "daily_PNE.parquet")),
                    reason="stand-in gauge table not built")
@pytest.mark.parametrize("case_id", ["A", "B1", "D-PNE"])
def test_leak_on_real_tables(case_id):
    rain = os.path.join(ROOT, "data", "processed", "rain")
    case = [c for c in hc.registered_cases() if c.case_id == case_id][0]
    tables = {s: hd.load_daily(rain, s) for s in {case.settlement, case.park}}
    j = hd.joint_daily(tables[case.settlement], tables[case.park], case.park_loss)
    train, _ = hd.split_windows(j, case.train, case.report)
    base = hs.fit_params(train, PRICE)
    changed_tables = {k: scramble_report(v, case.report[0], 5) for k, v in tables.items()}
    j2 = hd.joint_daily(changed_tables[case.settlement], changed_tables[case.park], case.park_loss)
    train2, report2 = hd.split_windows(j2, case.train, case.report)
    assert params_tuple(base) == params_tuple(hs.fit_params(train2, PRICE))
    assert params_tuple(base) == params_tuple(hc.run_case(case, changed_tables, PRICE, n_draws=5)["params"])
    assert max(base.train_seasons) <= case.train[1]


def test_registered_cases_match_the_preregistration():
    cs = {c.case_id: c for c in hc.registered_cases()}
    assert cs["A"].train == (1999, 2014) and cs["A"].report == (2015, 2026) and cs["A"].settlement == cs["A"].park
    assert (cs["B1"].settlement, cs["B1"].park) == ("TTN", "PNE") and (cs["B2"].settlement, cs["B2"].park) == ("TTN", "DYL")
    assert cs["D-same"].train == (1941, 1990) and cs["D-same"].report == (1991, 2026)
    assert (cs["D-PNE"].settlement, cs["D-PNE"].park) == ("PHL", "PNE")
    assert cs["E"].strategies == ("0", "3", "4")
    assert cs["C-c1-B1"].park_loss.threshold_tag == "0p10" and cs["C-c2-TTN"].park_loss.threshold_tag == "0p50"
    assert cs["C-c3-B1"].park_loss.window_tag == "10_20" and cs["C-c4-TTN"].park_loss.window_tag == "10_16"
    assert cs["C-c5-B1"].park_loss.weekend_holiday_only
    assert len([c for c in cs if c.startswith("C-")]) == 10
