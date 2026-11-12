"""Rain pairs: station day matrices, pair construction, joint seasons, the exact count contract and its HE.

Rules (docs/PHASE3_PREREG.md, Question 1, rain part; reading choices in docs/status/phase3_rain.md):
  exposure at G   loss day = >= 0.25 inch in 10:00-18:00 local (src.rain loss_0p25_10_18), L = 1 per loss day
  contract at S   payout max(C_S - d, 0) on the same loss-day count at S; d in {0..8} chosen on TRAIN;
                  premium = 1.2 x TRAIN mean payout (modelled), charged every season
  joint day       the 10:00-18:00 window is complete at S and at G (Phase 2 reading choice 1)
  joint season    passes the SPEC_v3 90% rule at S and at G; counts use joint days only
  windows         TRAIN = first floor(0.6 N) joint usable seasons in calendar order, REPORT = the rest
  HE              hedge_eval.metrics.hedge_effectiveness on REPORT, reference = TRAIN mean of the unhedged cost
Nothing from a REPORT season reaches the choice of d (fit_contract reads TRAIN rows only).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..hedge_eval.metrics import hedge_effectiveness
from ..hedge_eval.strategies import D_GRID, argmax_first
from ..panel.hedge import haversine_km
from ..rain import calendar as cal

MAX_KM = 200.0
TRAIN_SHARE = 0.60
LOADING = 0.20
MIN_JOINT_SEASONS = 20          # pairs with fewer joint usable seasons are listed, not scored (main rule)
MIN_WINDOW_SEASONS = 2          # the sensitivity rule: at least 2 TRAIN and 2 REPORT seasons
LOSS_COLUMN = "loss_0p25_10_18"
PAIR_COLUMNS = ["s_id", "g_id", "dist_km", "same_station", "elev_s_m", "elev_g_m", "elev_diff_m",
                "coast_s", "coast_g", "coast_km_s", "coast_km_g"]


# ------------------------------------------------------------------ station day matrices
@dataclass
class DayMatrix:
    """Season-day grid for a set of stations. dates: all season days of all years; season: year per date.

    usable[i, j]  window complete at station i on date j
    loss[i, j]    loss day at station i on date j (False where not usable)
    season_ok[i, y]  station i passes the 90% rule in season index y
    """
    ids: list[str]
    dates: pd.DatetimeIndex
    season: np.ndarray
    seasons: np.ndarray
    usable: np.ndarray
    loss: np.ndarray
    season_ok: np.ndarray

    def row(self, sid: str) -> int:
        return self.ids.index(sid)


def season_day_index(first: int, last: int) -> tuple[pd.DatetimeIndex, np.ndarray]:
    dates, season = [], []
    for y in range(first, last + 1):
        d = cal.season_days(y, cal.ALL_DAYS)
        dates += d
        season += [y] * len(d)
    return pd.DatetimeIndex(pd.to_datetime(dates)), np.asarray(season)


def build_day_matrix(daily_by_station: dict[str, pd.DataFrame], first: int, last: int) -> DayMatrix:
    """From per-station daily tables (src.rain.daily.build_daily output) to aligned boolean matrices."""
    ids = sorted(daily_by_station)
    dates, season = season_day_index(first, last)
    seasons = np.arange(first, last + 1)
    pos = pd.Series(np.arange(len(dates)), index=dates)
    usable = np.zeros((len(ids), len(dates)), dtype=bool)
    loss = np.zeros((len(ids), len(dates)), dtype=bool)
    season_ok = np.zeros((len(ids), len(seasons)), dtype=bool)
    for i, sid in enumerate(ids):
        d = daily_by_station[sid]
        j = pos.reindex(pd.to_datetime(d["date"])).to_numpy()
        ok = ~np.isnan(j)
        j = j[ok].astype(int)
        u = d["usable"].to_numpy(dtype=bool)[ok]
        lo = d[LOSS_COLUMN].fillna(False).to_numpy(dtype=bool)[ok] & u
        usable[i, j] = u
        loss[i, j] = lo
        su = d.groupby("season")["season_usable"].first()
        for y, v in su.items():
            k = y - first
            if 0 <= k < len(seasons):
                season_ok[i, k] = bool(v)
    return DayMatrix(ids, dates, season, seasons, usable, loss, season_ok)


# ------------------------------------------------------------------ pairs
def build_pairs(stations: pd.DataFrame, max_km: float = MAX_KM) -> pd.DataFrame:
    """Every ordered (S, G): S a kept station with has_cli, G any kept station, haversine distance <= max_km.

    S = G is included at distance 0 (same_station True). Columns PAIR_COLUMNS. Sorted by s_id, g_id.
    `stations` needs sid, lat, lon, elev_m, has_cli, kept, coastal, coast_km.
    """
    k = stations[stations["kept"].astype(bool)].sort_values("sid").reset_index(drop=True)
    cli = k[k["has_cli"].astype(bool)]
    rows = []
    for s in cli.itertuples():
        d = haversine_km(s.lat, s.lon, k["lat"].to_numpy(), k["lon"].to_numpy())
        for g, dk in zip(k.itertuples(), d):
            same = g.sid == s.sid
            if same:
                dk = 0.0
            if dk <= max_km:
                rows.append((s.sid, g.sid, float(dk), bool(same), float(s.elev_m), float(g.elev_m),
                             abs(float(g.elev_m) - float(s.elev_m)), bool(s.coastal), bool(g.coastal),
                             float(s.coast_km), float(g.coast_km)))
    return pd.DataFrame(rows, columns=PAIR_COLUMNS)


def pair_seasons(m: DayMatrix, s_id: str, g_id: str) -> pd.DataFrame:
    """Per season: joint days, loss counts at S and G on joint days, agreeing days, joint-usable flag.

    Columns: season, n_days, c_s, c_g, n_agree, usable. Seasons with no joint day are absent.
    """
    i, j = m.row(s_id), m.row(g_id)
    both = m.usable[i] & m.usable[j]
    ls, lg = m.loss[i], m.loss[j]
    t = pd.DataFrame({"season": m.season[both], "c_s": ls[both].astype(int), "c_g": lg[both].astype(int),
                      "agree": (ls[both] == lg[both]).astype(int)})
    g = t.groupby("season").agg(n_days=("c_s", "size"), c_s=("c_s", "sum"), c_g=("c_g", "sum"),
                                n_agree=("agree", "sum")).reset_index()
    ok = m.season_ok[i] & m.season_ok[j]
    g["usable"] = ok[g["season"].to_numpy() - int(m.seasons[0])]
    return g.sort_values("season").reset_index(drop=True)


def trigger_agreement(seasons: pd.DataFrame) -> float:
    """Share of joint days in usable seasons where the two loss flags agree. NaN if no days."""
    u = seasons[seasons["usable"]]
    n = int(u["n_days"].sum())
    return float(u["n_agree"].sum()) / n if n > 0 else float("nan")


def count_correlation(seasons: pd.DataFrame) -> float:
    """Pearson r of c_s, c_g over usable seasons. NaN if fewer than 2 seasons or no variance."""
    u = seasons[seasons["usable"]]
    if len(u) < 2 or u["c_s"].std() == 0 or u["c_g"].std() == 0:
        return float("nan")
    return float(np.corrcoef(u["c_s"].to_numpy(dtype=float), u["c_g"].to_numpy(dtype=float))[0, 1])


# ------------------------------------------------------------------ the contract
def split_windows(usable_seasons: np.ndarray, train_share: float = TRAIN_SHARE) -> tuple[np.ndarray, np.ndarray]:
    """TRAIN = first floor(train_share x N) seasons in calendar order, REPORT = the rest."""
    s = np.sort(np.asarray(usable_seasons))
    n_train = int(math.floor(train_share * len(s) + 1e-9))
    return s[:n_train], s[n_train:]


@dataclass
class Contract:
    d: int
    premium: float          # 1.2 x TRAIN mean payout (MODELLED)
    reference: float        # TRAIN mean of the unhedged cost c_g
    train_he: float
    train_seasons: list


def fit_contract(c_s_train, c_g_train, loading: float = LOADING, grid=D_GRID) -> Contract:
    """Choose d on TRAIN only: the d with the highest TRAIN HE of net = c_g - max(c_s - d, 0) + premium(d).
    Ties (and NaN) go to the smallest d (hedge_eval.strategies.argmax_first)."""
    c_s = np.asarray(c_s_train, dtype=float)
    c_g = np.asarray(c_g_train, dtype=float)
    reference = float(c_g.mean())
    he, prem = [], []
    for d in grid:
        pay = np.maximum(c_s - d, 0.0)
        p = (1.0 + loading) * float(pay.mean())
        prem.append(p)
        he.append(hedge_effectiveness(c_g - pay + p, c_g, reference))
    i = argmax_first(he)
    return Contract(d=int(grid[i]), premium=float(prem[i]), reference=reference, train_he=float(he[i]),
                    train_seasons=[])


def report_he(c_s_report, c_g_report, contract: Contract) -> float:
    """HE on REPORT seasons with the contract fixed. NaN when no REPORT season is above the reference."""
    c_s = np.asarray(c_s_report, dtype=float)
    c_g = np.asarray(c_g_report, dtype=float)
    net = c_g - np.maximum(c_s - contract.d, 0.0) + contract.premium
    return hedge_effectiveness(net, c_g, contract.reference)


def evaluate_pair(seasons: pd.DataFrame, min_joint: int = MIN_JOINT_SEASONS,
                  min_window: int = MIN_WINDOW_SEASONS) -> dict:
    """All per-pair numbers from the pair's season table.

    status  'ok' (scored under the main rule), 'few_joint_seasons' (scored only under the sensitivity rule,
            n_joint < min_joint but TRAIN and REPORT both have >= min_window seasons),
            'too_few_for_windows' (no HE at all).
    he      REPORT HE (NaN when undefined; he_defined says why)
    """
    u = seasons[seasons["usable"]].sort_values("season")
    n = int(len(u))
    train, report = split_windows(u["season"].to_numpy())
    out = dict(n_joint_seasons=n, n_train=int(len(train)), n_report=int(len(report)),
               first_joint=int(u["season"].min()) if n else None, last_joint=int(u["season"].max()) if n else None,
               n_joint_days=int(u["n_days"].sum()), mean_c_s=float(u["c_s"].mean()) if n else float("nan"),
               mean_c_g=float(u["c_g"].mean()) if n else float("nan"),
               trigger_agreement=trigger_agreement(seasons), count_corr=count_correlation(seasons),
               d=None, premium=float("nan"), reference=float("nan"), train_he=float("nan"), he=float("nan"),
               he_defined=False, status="")
    if len(train) < min_window or len(report) < min_window:
        out["status"] = "too_few_for_windows"
        return out
    tr = u[u["season"].isin(train)]
    rp = u[u["season"].isin(report)]
    c = fit_contract(tr["c_s"], tr["c_g"])
    he = report_he(rp["c_s"], rp["c_g"], c)
    out.update(d=c.d, premium=c.premium, reference=c.reference, train_he=c.train_he, he=he,
               he_defined=bool(he == he), status="ok" if n >= min_joint else "few_joint_seasons")
    return out


def evaluate_all(pairs: pd.DataFrame, m: DayMatrix) -> pd.DataFrame:
    rows = []
    for p in pairs.itertuples(index=False):
        s = pair_seasons(m, p.s_id, p.g_id)
        r = evaluate_pair(s)
        rows.append({**p._asdict(), **r})
    return pd.DataFrame(rows)
