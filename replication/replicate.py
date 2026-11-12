"""Independent replication of the Phase 2 headline numbers (docs/PHASE2_PREREG.md).

Written from the pre-registration, SPEC_v3 and the Phase 1 status files only.
Does not import anything from src/. Plain pandas / numpy.

Run:  python replication/replicate.py
Writes replication/results.csv, params.csv, per_season_B1.csv, season_compare_phase1.csv,
ambiguity_sensitivity.csv.
"""
from __future__ import annotations

import datetime as dt
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "replication"
PROBE = ROOT / "data/processed/rain_probe"

THR = 0.25
HOURS = list(range(10, 18))  # hours labelled 10..17 local = 10:00-18:00
LOADING = 0.20

# ---------------------------------------------------------------- defaults for ambiguous points
DEFAULT = dict(
    source_rule="best_per_season",   # or "merge_hours"
    ghcn_missing="no",               # "no": missing official total = Kalshi No ; "drop": drop the day
    joint_season_rule="each",        # "each": both stations pass 90% on their own ; "joint_days": >=90% of season days usable at both
    p_days="case_days",              # monthly p from TRAIN usable (case) season days
    fee="per_contract_ceil",         # n * ceil_cent(0.07*ask*(1-ask)) ; "order_ceil": ceil_cent(0.07*n*ask*(1-ask)) ; "no_round": 0.07*n*ask*(1-ask)
    unfilled="scale_both",           # rain-day order scaled by 1-u (cost and payout) ; "off": u = 0
    edges="invcdf",                  # "invcdf" | "linear_floor" | "linear_round" | "linear_ceil" | "invcdf_excl"
    tie="first",                     # argmax tie: first (smallest n / d) or "last"
    d4="own",                        # strategy 4 deductible: chosen for itself ("own") or copied from strategy 3 ("same")
    s5_price="daily_p",              # strategy 5: per-day price (1+load)*p_month ; "season_mean": (1+load)*n*TRAIN mean K_S per season
    a=None,                          # override markup (sensitivity 0.068)
    loading=LOADING,
)


# ---------------------------------------------------------------- calendar
def memorial_day(y: int) -> dt.date:
    d = dt.date(y, 5, 31)
    while d.weekday() != 0:
        d -= dt.timedelta(days=1)
    return d


def labor_day(y: int) -> dt.date:
    d = dt.date(y, 9, 1)
    while d.weekday() != 0:
        d += dt.timedelta(days=1)
    return d


def season_days(y: int) -> list[dt.date]:
    start = memorial_day(y) - dt.timedelta(days=3)  # the Friday before
    end = labor_day(y)
    return [start + dt.timedelta(days=i) for i in range((end - start).days + 1)]


# ---------------------------------------------------------------- hourly -> daily
_hourly_cache: dict = {}


def load_hourly(station: str) -> pd.DataFrame:
    if station in _hourly_cache:
        return _hourly_cache[station]
    frames = []
    for f in sorted(PROBE.glob(f"hourly_maysep_{station}_*.csv.gz")):
        d = pd.read_csv(f, usecols=["source", "ldate", "lhour", "present", "precip_in", "trace", "pno"])
        frames.append(d)
    h = pd.concat(frames, ignore_index=True)
    h = h[h.lhour.isin(HOURS)].copy()
    h["present"] = h["present"].astype(bool)
    # an hour is present only if a row exists AND present is True (absent row = missing; present & 0.0 = dry)
    h = h[h.present]
    h["season"] = h.ldate.str[:4].astype(int)
    # guard: one row per source/date/hour
    h = h.groupby(["source", "ldate", "lhour"], as_index=False).agg(
        precip_in=("precip_in", "max"), season=("season", "first"))
    _hourly_cache[station] = h
    return h


def station_daily(station: str, source_rule: str) -> pd.DataFrame:
    """One row per season day: hours_present (0..8), open_rain, usable, loss; plus chosen source."""
    h = load_hourly(station)
    rows = []
    years = sorted(h.season.unique())
    for y in years:
        days = [d.isoformat() for d in season_days(y)]
        hy = h[(h.season == y) & h.ldate.isin(days)]
        if source_rule == "best_per_season":
            cnt = hy.groupby("source").size()
            if len(cnt) == 0:
                src = None
                sel = hy
            else:
                best = cnt.max()
                cands = sorted(cnt[cnt == best].index)
                if len(cands) > 1:
                    src = "IEM_METAR" if y >= 1997 else "NCEI_ISD"
                else:
                    src = cands[0]
                sel = hy[hy.source == src]
        elif source_rule == "merge_hours":
            # hour by hour: IEM_METAR from 1997, NCEI_ISD before; fill from the other source when absent
            pref = "IEM_METAR" if y >= 1997 else "NCEI_ISD"
            hy2 = hy.assign(rank=(hy.source != pref).astype(int)).sort_values("rank")
            sel = hy2.drop_duplicates(["ldate", "lhour"], keep="first")
            src = "merged"
        else:
            raise ValueError(source_rule)
        g = sel.groupby("ldate").agg(hours_present=("lhour", "nunique"), open_rain=("precip_in", "sum"))
        for d in days:
            if d in g.index:
                hp, r = int(g.at[d, "hours_present"]), float(g.at[d, "open_rain"])
            else:
                hp, r = 0, 0.0
            rows.append((y, d, src, hp, r))
    df = pd.DataFrame(rows, columns=["season", "date", "source", "hours_present", "open_rain"])
    df["usable"] = df.hours_present == len(HOURS)
    df["open_rain"] = df.open_rain.round(4)
    df["loss"] = (df.open_rain >= THR - 1e-9) & df.usable
    share = df.groupby("season").hours_present.sum() / (df.groupby("season").size() * len(HOURS))
    df["share_hours"] = df.season.map(share)
    df["season_usable"] = df.share_hours >= 0.90
    return df


def ghcn(station: str) -> pd.Series:
    g = pd.read_parquet(ROOT / f"data/processed/rain/daily_{station}.parquet", columns=["date", "ghcn_prcp_in"])
    g["date"] = pd.to_datetime(g.date).dt.strftime("%Y-%m-%d")
    return g.set_index("date").ghcn_prcp_in


# ---------------------------------------------------------------- case day tables
def build_case(settle: str, park: str, opt: dict) -> pd.DataFrame:
    """Day table restricted to the common usable days of usable seasons.
    Columns: season, date, month, c (loss at S), dpark (loss at park), k (Kalshi pays at S)."""
    s = station_daily(settle, opt["source_rule"])
    g = ghcn(settle)
    s = s.assign(ghcn=s.date.map(g))
    if park == settle:
        j = s.assign(usable_p=s.usable, loss_p=s.loss, season_usable_p=s.season_usable)
    else:
        p = station_daily(park, opt["source_rule"])[["date", "usable", "loss", "season_usable"]]
        p.columns = ["date", "usable_p", "loss_p", "season_usable_p"]
        j = s.merge(p, on="date", how="inner")
    j["both"] = j.usable & j.usable_p
    if opt["joint_season_rule"] == "each":
        ok = j.season_usable & j.season_usable_p
    else:
        ok = j.season.map(j.groupby("season").both.mean() >= 0.90)
    j = j[ok & j.both].copy()
    if opt["ghcn_missing"] == "drop":
        j = j[j.ghcn.notna()].copy()
    j["k"] = (j.ghcn.fillna(0.0) >= 0.01 - 1e-9).astype(int)
    j["c"] = j.loss.astype(int)
    j["dpark"] = j.loss_p.astype(int)
    j["month"] = j.date.str[5:7].astype(int)
    return j[["season", "date", "month", "c", "dpark", "k", "ghcn"]].reset_index(drop=True)


# ---------------------------------------------------------------- pricing
PM = json.loads((ROOT / "data/processed/kalshi_rain/price_model.json").read_text())["models"]["skill"]


def ceil_cent(x: float) -> float:
    return math.ceil(round(x * 100, 9)) / 100.0


def clamp_cent(x):
    return np.clip(np.round(np.asarray(x) * 100 + 1e-9) / 100.0, 0.01, 0.99)


def kalshi_season(days: pd.DataFrame, p_month: dict, n: float, opt: dict) -> pd.DataFrame:
    """Per-season premium (ask + fee) and payout for n contracts every day. MODELLED prices."""
    a = PM["a"] if opt["a"] is None else opt["a"]
    s_, u = PM["s"], (PM["u"] if opt["unfilled"] == "scale_both" else 0.0)
    p = days.month.map(p_month).to_numpy(float)
    rain = days.k.to_numpy(float)
    ask = clamp_cent(p + s_ * (rain - p) + a)
    qty = n * np.where(rain == 1, 1 - u, 1.0)
    raw = 0.07 * ask * (1 - ask)
    if opt["fee"] == "per_contract_ceil":
        fee = qty * np.array([ceil_cent(v) for v in raw])
    elif opt["fee"] == "order_ceil":
        fee = np.array([ceil_cent(q * v) for q, v in zip(qty, raw)])
    else:
        fee = qty * raw
    out = pd.DataFrame({"season": days.season.to_numpy(), "prem": qty * ask + fee, "pay": qty * rain})
    return out.groupby("season").sum()


# ---------------------------------------------------------------- metric
def he(net, unhedged, ref):
    sv_h = np.mean(np.maximum(np.asarray(net, float) - ref, 0.0) ** 2)
    sv_u = np.mean(np.maximum(np.asarray(unhedged, float) - ref, 0.0) ** 2)
    return np.nan if sv_u == 0 else 1.0 - sv_h / sv_u


def argbest(vals, tie):
    v = np.asarray(vals, float)
    m = np.nanmax(v)
    idx = np.where(np.isclose(v, m, rtol=0, atol=1e-12))[0]
    return int(idx[0] if tie == "first" else idx[-1])


# ---------------------------------------------------------------- bucket edges
def edges_from_train(c_train: np.ndarray, rule: str):
    c = np.sort(np.asarray(c_train, int))
    N = len(c)
    raw = []
    for k in range(1, 6):
        q = k / 6
        if rule in ("invcdf", "invcdf_excl"):
            # smallest observed value v with share(C <= v) >= k/6
            v = int(c[int(math.ceil(q * N - 1e-9)) - 1])
            if rule == "invcdf_excl":
                v -= 1  # tied seasons go to the bucket above
        else:
            x = float(np.quantile(c, q))  # linear interpolation
            v = {"linear_floor": math.floor(x + 1e-9), "linear_round": int(math.floor(x + 0.5 + 1e-9)),
                 "linear_ceil": math.ceil(x - 1e-9)}[rule]
        raw.append(v)
    e, note = [], ""
    for v in raw:
        v = max(v, 0)
        if e and v <= e[-1]:
            v = e[-1] + 1  # tie: move the edge up so six distinct buckets remain
            note = "raw quantile edges %s had ties; moved up to stay strictly increasing" % raw
        e.append(v)
    return e, raw, note


def bucket_of(c, e):
    return int(np.searchsorted(np.asarray(e), c, side="left"))  # bucket j covers (e[j-1], e[j]] ; 5 = above e5


# ---------------------------------------------------------------- one case
def run_case(name: str, settle: str, park: str, train: tuple, report: tuple, opt: dict, drop_seasons=()):
    days = build_case(settle, park, opt)
    days = days[~days.season.isin(drop_seasons)]
    days = days[(days.season >= train[0]) & (days.season <= report[1])]
    seas = days.groupby("season").agg(days_used=("c", "size"), D=("dpark", "sum"), C=("c", "sum"), K=("k", "sum"))
    is_tr = (seas.index >= train[0]) & (seas.index <= train[1])
    is_rp = (seas.index >= report[0]) & (seas.index <= report[1])
    tr, rp = seas[is_tr], seas[is_rp]
    ref = tr.D.mean()
    load = opt["loading"]
    dtr = days[days.season.isin(tr.index)]
    p_month = dtr.groupby("month").k.mean().to_dict()
    for m in days.month.unique():
        p_month.setdefault(m, dtr.k.mean())

    net = {"0": seas.D.astype(float)}
    prem = {"0": seas.D * 0.0}
    pay = {"0": seas.D * 0.0}
    params = {"case": name, "settle": settle, "park": park, "train": f"{train[0]}-{train[1]}",
              "report": f"{report[0]}-{report[1]}", "n_train": len(tr), "n_report": len(rp),
              "ref_level_train_mean_D": ref,
              "p_month": json.dumps({int(k): round(v, 4) for k, v in sorted(p_month.items())})}

    def he_tr(x):
        return he(x[is_tr], seas.D[is_tr], ref)

    # ---- strategies 1, 2
    grid = [round(0.05 * i, 2) for i in range(1, 21)]
    ks1 = kalshi_season(days, p_month, 1.0, opt).reindex(seas.index)
    net["1"] = seas.D - ks1.pay + ks1.prem; prem["1"] = ks1.prem; pay["1"] = ks1.pay
    cand = [kalshi_season(days, p_month, n, opt).reindex(seas.index) for n in grid]
    hes = [he_tr(seas.D - k.pay + k.prem) for k in cand]
    i = argbest(hes, opt["tie"])
    params["n2"] = grid[i]; params["HE2_train_by_n"] = json.dumps([round(v, 4) for v in hes])
    net["2"] = seas.D - cand[i].pay + cand[i].prem; prem["2"] = cand[i].prem; pay["2"] = cand[i].pay

    # ---- strategy 3
    e, raw, note = edges_from_train(tr.C.to_numpy(), opt["edges"])
    bt = np.array([bucket_of(c, e) for c in tr.C])
    N = len(tr)
    nj = np.array([(bt == j).sum() for j in range(6)])
    q = (nj + 0.5) / (N + 3)
    m = []
    for j in range(6):
        if nj[j] > 0:
            m.append(float(tr.C.to_numpy()[bt == j].mean()))
        elif j == 5:
            m.append(e[4] + 2.0)
        else:
            lo = 0 if j == 0 else e[j - 1] + 1
            m.append((lo + e[j]) / 2.0)
    m = np.array(m)
    ball = np.array([bucket_of(c, e) for c in seas.C])
    res3 = []
    for d in range(0, 9):
        h = np.maximum(m - d, 0.0)
        pr = (1 + load) * float((h * q).sum())
        res3.append((h, pr, he_tr(seas.D - h[ball] + pr)))
    d3 = argbest([r[2] for r in res3], opt["tie"])
    h, pr3, _ = res3[d3]
    net["3"] = seas.D - h[ball] + pr3; prem["3"] = seas.D * 0.0 + pr3; pay["3"] = pd.Series(h[ball], index=seas.index)
    params.update(edges=json.dumps(e), raw_quantile_edges=json.dumps(raw), edge_note=note,
                  n_j=json.dumps(nj.tolist()), m_j=json.dumps([round(x, 4) for x in m]),
                  h_j=json.dumps([round(x, 4) for x in h]), d3=d3,
                  q_j=json.dumps([round(x, 4) for x in q]), premium3=pr3,
                  HE3_train_by_d=json.dumps([round(r[2], 4) for r in res3]))

    # ---- strategy 4
    res4 = []
    for d in range(0, 9):
        po = np.maximum(seas.C - d, 0.0)
        pr = (1 + load) * float(po[is_tr].mean())
        res4.append((po, pr, he_tr(seas.D - po + pr)))
    d4 = d3 if opt["d4"] == "same" else argbest([r[2] for r in res4], opt["tie"])
    po4, pr4, _ = res4[d4]
    net["4"] = seas.D - po4 + pr4; prem["4"] = seas.D * 0.0 + pr4; pay["4"] = po4
    params.update(d4=d4, premium4=pr4, HE4_train_by_d=json.dumps([round(r[2], 4) for r in res4]))

    # ---- strategy 5 (Kalshi daily at (1+loading) * expected payout, no fee, no spread, every order filled)
    if opt["s5_price"] == "daily_p":
        unit_prem = (1 + load) * days.assign(p=days.month.map(p_month)).groupby("season").p.sum().reindex(seas.index)
    else:
        unit_prem = seas.D * 0.0 + (1 + load) * tr.K.mean()
    hes5 = [he_tr(seas.D - n * seas.K + n * unit_prem) for n in grid]
    i5 = argbest(hes5, opt["tie"])
    n5 = grid[i5]
    net["5"] = seas.D - n5 * seas.K + n5 * unit_prem; prem["5"] = n5 * unit_prem; pay["5"] = n5 * seas.K
    net["5n1"] = seas.D - seas.K + unit_prem; prem["5n1"] = unit_prem; pay["5n1"] = seas.K * 1.0
    params.update(n5=n5, HE5_train_by_n=json.dumps([round(v, 4) for v in hes5]),
                  premium2_mean_train=float(prem["2"][is_tr].mean()), premium5_mean_train=float(prem["5"][is_tr].mean()))

    return dict(name=name, seas=seas, is_tr=is_tr, is_rp=is_rp, ref=ref, net=net, prem=prem, pay=pay, params=params)


def metrics_rows(r):
    rows = []
    for win, mask in (("TRAIN", r["is_tr"]), ("REPORT", r["is_rp"])):
        D = r["seas"].D[mask]
        for s in r["net"]:
            x = r["net"][s][mask]
            rows += [
                (r["name"], s, win, "HE", he(x, D, r["ref"])),
                (r["name"], s, win, "mean_net_cost", float(x.mean())),
                (r["name"], s, win, "total_premium", float(r["prem"][s][mask].sum())),
                (r["name"], s, win, "mean_payout", float(r["pay"][s][mask].mean())),
                (r["name"], s, win, "sd_net_cost", float(x.std(ddof=1))),
                (r["name"], s, win, "n_seasons", int(mask.sum())),
            ]
    return rows


def bootstrap(r, draws=2000, seed=473):
    """Resample whole REPORT seasons with replacement. Reference level stays the TRAIN mean."""
    rng = np.random.default_rng(seed)
    m = r["is_rp"]
    D = r["seas"].D[m].to_numpy(float)
    X = {s: r["net"][s][m].to_numpy(float) for s in r["net"]}
    n = len(D)
    out = {s: [] for s in X}
    out["3-2"] = []
    for _ in range(draws):
        idx = rng.integers(0, n, n)
        hv = {s: he(X[s][idx], D[idx], r["ref"]) for s in X}
        for s in X:
            out[s].append(hv[s])
        out["3-2"].append(hv["3"] - hv["2"])
    rows = []
    for s, v in out.items():
        v = np.array(v, float)
        lab = "HE" if s != "3-2" else "HE3_minus_HE2"
        st = s if s != "3-2" else "3-2"
        rows += [(r["name"], st, "REPORT", lab + "_boot_lo95", float(np.nanpercentile(v, 2.5))),
                 (r["name"], st, "REPORT", lab + "_boot_hi95", float(np.nanpercentile(v, 97.5))),
                 (r["name"], st, "REPORT", lab + "_boot_undefined_draws", int(np.isnan(v).sum()))]
    pt = he(X["3"], D, r["ref"]) - he(X["2"], D, r["ref"])
    rows.append((r["name"], "3-2", "REPORT", "HE3_minus_HE2", pt))
    return rows


CASES = {
    "A": dict(settle="TTN", park="TTN", train=(1999, 2014), report=(2015, 2026)),
    "B1": dict(settle="TTN", park="PNE", train=(1999, 2014), report=(2015, 2026)),
    "D": dict(settle="PHL", park="PHL", train=(1941, 1990), report=(1991, 2026)),
    "D_ex1941_47": dict(settle="PHL", park="PHL", train=(1948, 1990), report=(1991, 2026)),
    "D_PNE": dict(settle="PHL", park="PNE", train=(1941, 1990), report=(1991, 2026)),
}


def compare_phase1(opt):
    rows = []
    for st in ("TTN", "PHL"):
        d = build_case(st, st, opt)
        mine = d.groupby("season").agg(my_usable_days=("c", "size"), my_C=("c", "sum"), my_K=("k", "sum"))
        allst = station_daily(st, opt["source_rule"])
        info = allst.groupby("season").agg(my_days=("date", "size"), my_share=("share_hours", "first"),
                                           my_season_usable=("season_usable", "first"), my_source=("source", "first"))
        # counts for unusable seasons too (Phase 1 lists them)
        g = ghcn(st)
        au = allst[allst.usable].assign(k=lambda x: (x.date.map(g).fillna(0) >= 0.01 - 1e-9).astype(int))
        allc = au.groupby("season").agg(my_usable_days=("loss", "size"), my_C=("loss", "sum"), my_K=("k", "sum"))
        p1 = pd.read_csv(ROOT / f"data/processed/rain/season_counts_{st}.csv")
        p1 = p1[p1.calendar == "all_days"].set_index("season")
        j = info.join(allc).join(p1[["days", "usable_days", "loss_days", "ref_ghcn_pay_days",
                                     "share_open_hours_present", "season_usable"]], how="outer")
        j.insert(0, "station", st)
        j["diff_C"] = j.my_C - j.loss_days
        j["diff_K"] = j.my_K - j.ref_ghcn_pay_days
        j["diff_usable_days"] = j.my_usable_days - j.usable_days
        j["diff_season_usable"] = j.my_season_usable.astype("boolean") != j.season_usable.astype("boolean")
        rows.append(j.reset_index())
    return pd.concat(rows, ignore_index=True)


def main():
    opt = dict(DEFAULT)
    res, rows, prm = {}, [], []
    for name, c in CASES.items():
        r = run_case(name, opt=opt, **c)
        res[name] = r
        rows += metrics_rows(r) + bootstrap(r)
        prm.append(r["params"])
    pd.DataFrame(rows, columns=["case", "strategy", "window", "metric", "value"]).to_csv(OUT / "results.csv", index=False)
    pd.DataFrame(prm).to_csv(OUT / "params.csv", index=False)

    b = res["B1"]
    ps = b["seas"].copy()
    ps.insert(0, "window", np.where(b["is_tr"], "TRAIN", "REPORT"))
    for s in ("2", "3", "4", "5"):
        ps[f"payout_{s}"] = b["pay"][s]; ps[f"premium_{s}"] = b["prem"][s]; ps[f"net_{s}"] = b["net"][s]
    ps.rename(columns={"D": "D_park_PNE", "C": "C_S_TTN", "K": "K_S_TTN"}).to_csv(OUT / "per_season_B1.csv")

    cmp_ = compare_phase1(opt)
    cmp_.to_csv(OUT / "season_compare_phase1.csv", index=False)

    # ---- ambiguity sensitivity: change one reading at a time
    alts = [("source_rule", "merge_hours"), ("ghcn_missing", "drop"), ("joint_season_rule", "joint_days"),
            ("fee", "order_ceil"), ("fee", "no_round"), ("unfilled", "off"),
            ("edges", "linear_floor"), ("edges", "linear_round"), ("edges", "linear_ceil"), ("edges", "invcdf_excl"),
            ("tie", "last"), ("d4", "same"), ("s5_price", "season_mean"), ("a", 0.0684),
            ("loading", 0.10), ("loading", 0.30)]
    srows = []

    def summarise(label, key, val, o):
        for name in ("A", "B1", "D"):
            r = run_case(name, opt=o, **CASES[name])
            D = r["seas"].D[r["is_rp"]]
            row = dict(variant=label, key=key, value=val, case=name, n2=r["params"]["n2"], d3=r["params"]["d3"],
                       d4=r["params"]["d4"], n5=r["params"]["n5"], edges=r["params"]["edges"],
                       n_train=r["params"]["n_train"], n_report=r["params"]["n_report"])
            for s in ("2", "3", "4", "5"):
                row[f"HE{s}_REPORT"] = he(r["net"][s][r["is_rp"]], D, r["ref"])
            row["HE3_minus_HE2_REPORT"] = row["HE3_REPORT"] - row["HE2_REPORT"]
            rng = np.random.default_rng(473)
            Dv = D.to_numpy(float); x2 = r["net"]["2"][r["is_rp"]].to_numpy(float); x3 = r["net"]["3"][r["is_rp"]].to_numpy(float)
            dd = []
            for _ in range(2000):
                ix = rng.integers(0, len(Dv), len(Dv))
                dd.append(he(x3[ix], Dv[ix], r["ref"]) - he(x2[ix], Dv[ix], r["ref"]))
            row["diff_lo95"], row["diff_hi95"] = np.nanpercentile(dd, 2.5), np.nanpercentile(dd, 97.5)
            srows.append(row)

    summarise("main", "", "", opt)
    for k, v in alts:
        o = dict(opt); o[k] = v
        summarise(f"{k}={v}", k, v, o)
    pd.DataFrame(srows).to_csv(OUT / "ambiguity_sensitivity.csv", index=False)
    return res, cmp_


if __name__ == "__main__":
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40); pd.set_option("display.max_rows", 400)
    res, cmp_ = main()
    for n, r in res.items():
        print("=====", n, {k: v for k, v in r["params"].items() if not k.startswith("HE")})
        print(r["seas"].T.to_string())
    out = pd.read_csv(OUT / "results.csv")
    print(out[out.metric.isin(["HE", "HE3_minus_HE2", "HE3_minus_HE2_boot_lo95", "HE3_minus_HE2_boot_hi95"])]
          .pivot_table(index=["case", "window", "metric"], columns="strategy", values="value").round(4).to_string())
    bad = cmp_[(cmp_.diff_C != 0) | (cmp_.diff_K != 0) | cmp_.diff_season_usable | (cmp_.diff_usable_days != 0)]
    print("Phase 1 comparison: seasons checked", cmp_.loss_days.notna().sum(), "rows differing", len(bad))
    print(bad.to_string())
