"""Checks on the built panel files (skipped if the files have not been built yet)."""
from pathlib import Path

import pandas as pd
import pytest

from src.panel import hedge as H

ROOT = Path(__file__).resolve().parents[1]
ST = ROOT / "data/processed/panel/stations.csv"
PANEL = ROOT / "data/processed/panel/tmax_panel.parquet"
pytestmark = pytest.mark.skipif(not (ST.exists() and PANEL.exists()), reason="panel not built")


@pytest.fixture(scope="module")
def st():
    return pd.read_csv(ST)


@pytest.fixture(scope="module")
def panel():
    return pd.read_parquet(PANEL)


def test_listed_stations_present_and_flagged(st, panel):
    s = st.set_index("id")
    for city, sid in H.LISTED.items():
        assert s.at[sid, "is_listed"] == city
        assert sid in set(panel["id"])
        assert bool(s.at[sid, "has_cli"])
    assert s.at["USW00013739", "name"].startswith("PHILA")
    assert bool(s.at["USW00013739", "station_inferred"]) and st["station_inferred"].sum() == 1


def test_exposure_rule(st):
    e = st[st["is_exposure"]]
    assert (e["network"] == "USW").all() and e["id"].str.startswith("USW").all()
    assert (e["cov_all"] >= 0.90).all()
    assert (e[["cov_fit", "cov_select", "cov_report"]] >= 0.80).all().all()
    out = st[(st["network"] == "USW") & ~st["is_exposure"]]
    assert ((out["cov_all"] < 0.90) | (out[["cov_fit", "cov_select", "cov_report"]] < 0.80).any(axis=1)).all()
    assert not st[st["network"] == "USC"]["is_exposure"].any()
    c = st[st["is_candidate"]]
    assert (c["is_exposure"] & c["has_cli"] & c["is_listed"].isna()).all()


def test_panel_is_season_only_observed_only(st, panel):
    d = pd.to_datetime(panel["date"])
    assert H.season_mask(d).all()
    assert d.dt.year.between(2015, 2025).all()
    assert panel["tmax_f"].notna().all()
    assert not panel.duplicated(["date", "id"]).any()
    want = set(st[st["is_exposure"] | st["is_listed"].notna()]["id"])
    assert set(panel["id"]) == want
    assert panel["tmax_f"].between(30, 111).all()


def test_panel_matches_raw_file_for_one_station(panel):
    raw = pd.read_csv(ROOT / "data/raw/region/tmax/USW00014734.csv", parse_dates=["DATE"])
    raw = raw[H.season_mask(raw["DATE"]) & raw["TMAX"].notna()]
    p = panel[panel["id"] == "USW00014734"].sort_values("date")
    assert len(p) == len(raw)
    assert (p["tmax_f"].to_numpy() == raw["TMAX"].to_numpy(dtype=float)).all()
