"""Part 2: rank candidate new markets (see docs/notes/part2_preregistration.md, docs/SPEC_v2.md)."""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.panel import hedge as H  # noqa: E402

OUT = ROOT / "results" / "part2"
NYC, PHL, EWR, TTN = "USW00094728", "USW00013739", "USW00014734", "USW00014792"
SETS = {"L_pre": [NYC, PHL], "L_now": [NYC, PHL, EWR, TTN]}
WIN = {"FIT": (2015, 2019), "SELECT": (2020, 2022), "REPORT": (2023, 2025)}


def yearly_wrong(wide, loc, station, k):
    """Per-year (wrong days, valid days) for hedge (station, k) at loc, season days only."""
    d = wide[[loc, station]].dropna() if loc != station else wide[[loc]].dropna()
    h = d[loc] >= 90
    p = d[station] >= k
    g = pd.DataFrame({"wrong": (h != p).astype(int), "n": 1}, index=d.index)
    return g.groupby(g.index.year).sum()


def fit_hedge(wide, loc, listed, stations):
    best = None
    for s in listed:
        dist = H.haversine_km(stations.lat[loc], stations.lon[loc], stations.lat[s], stations.lon[s])
        for k in range(80, 101):
            y = yearly_wrong(wide, loc, s, k)
            y = y[(y.index >= 2015) & (y.index <= 2019)]
            if y.n.sum() == 0:
                continue
            key = (y.wrong.sum() / y.n.sum(), abs(k - 90), dist, k)
            if best is None or key < best[0]:
                best = (key, s, k)
    return best[1], best[2]


def table_for_set(wide, listed, stations, locs):
    """Per location: fitted hedge and per-year wrong/valid counts."""
    out = {}
    for i in locs:
        s, k = fit_hedge(wide, i, listed, stations)
        out[i] = (s, k, yearly_wrong(wide, i, s, k))
    return out


def rate(y, years):
    y = y.reindex(years).fillna(0)
    return y.wrong.sum() / y.n.sum() if y.n.sum() else np.nan


def main():
    st = pd.read_csv(ROOT / "data/processed/panel/stations.csv").set_index("id")
    wide = H.to_wide(pd.read_parquet(ROOT / "data/processed/panel/tmax_panel.parquet"))
    wide = wide[H.season_mask(wide.index)]
    locs = st.index[st.is_exposure].tolist()
    w = pd.Series(1.0, index=locs)
    wfile = ROOT / "data/processed/weights.csv"
    label = "unweighted"
    if wfile.exists():
        ww = pd.read_csv(wfile).set_index("id").weight
        w = ww.reindex(locs).fillna(0.0)
        label = "census_weighted"
    rng = np.random.default_rng(473)
    rows, greedy = [], []
    for name, L0 in SETS.items():
        cands = [i for i in locs if st.has_cli[i] and i not in L0]
        base = table_for_set(wide, L0, st, locs)
        cache = {}
        def gain_table(listed_plus, base_tab):
            # only the new station can change a location's hedge, so refit against base + s
            tab = {}
            s_new = listed_plus[-1]
            for i in locs:
                bs, bk, by = base_tab[i]
                fy = by[(by.index >= 2015) & (by.index <= 2019)]
                bfit = fy.wrong.sum() / fy.n.sum()
                best = (bfit, abs(bk - 90), 0, bs, bk, by)
                for k in range(80, 101):
                    y = yearly_wrong(wide, i, s_new, k)
                    f = y[(y.index >= 2015) & (y.index <= 2019)]
                    if f.n.sum() == 0:
                        continue
                    key = (f.wrong.sum() / f.n.sum(), abs(k - 90))
                    if key < best[:2]:
                        best = (key[0], key[1], 0, s_new, k, y)
                tab[i] = (best[3], best[4], best[5])
            return tab
        for s in cands:
            plus = gain_table(L0 + [s], base)
            cache[s] = plus
            for win, (a, b) in WIN.items():
                yrs = list(range(a, b + 1))
                g = pd.Series({i: rate(base[i][2], yrs) - rate(plus[i][2], yrs) for i in locs})
                draws = []
                if win != "FIT":
                    for _ in range(1000):
                        ys = rng.choice(yrs, size=len(yrs), replace=True)
                        gi = pd.Series({i: rate_draw(base[i][2], ys) - rate_draw(plus[i][2], ys) for i in locs})
                        draws.append((gi * w).sum())
                lo, hi = (np.percentile(draws, [2.5, 97.5]) if draws else (np.nan, np.nan))
                rows.append(dict(listed_set=name, weights=label, candidate=s, name=st.name[s], state=st.state[s],
                                 window=win, score=(g * w).sum(), score_lo=lo, score_hi=hi,
                                 score_excl_self=(g.drop(s) * w.drop(s)).sum(),
                                 n_locations_switching=sum(plus[i][0] == s for i in locs if i != s)))
        # greedy three picks on SELECT
        L, tab = list(L0), base
        yrs_s, yrs_r = list(range(2020, 2023)), list(range(2023, 2026))
        for step in range(1, 4):
            best = None
            for s in [c for c in cands if c not in L]:
                plus = gain_table(L + [s], tab)
                sc = sum(w[i] * (rate(tab[i][2], yrs_s) - rate(plus[i][2], yrs_s)) for i in locs)
                if best is None or sc > best[0]:
                    best = (sc, s, plus)
            sc, s, plus = best
            rep = sum(w[i] * (rate(tab[i][2], yrs_r) - rate(plus[i][2], yrs_r)) for i in locs)
            greedy.append(dict(listed_set=name, weights=label, step=step, pick=s, name=st.name[s], state=st.state[s],
                               select_score=sc, report_gain=rep))
            L, tab = L + [s], plus
    OUT.mkdir(parents=True, exist_ok=True)
    r = pd.DataFrame(rows)
    r.to_csv(OUT / f"ranking_{label}.csv", index=False)
    pd.DataFrame(greedy).to_csv(OUT / f"greedy_{label}.csv", index=False)
    for name in SETS:
        s = r[(r.listed_set == name) & (r.window == "SELECT")].sort_values("score", ascending=False).reset_index(drop=True)
        s["rank"] = s.index + 1
        rep = r[(r.listed_set == name) & (r.window == "REPORT")].set_index("candidate")
        s["report_gain"] = s.candidate.map(rep.score)
        s["report_lo"] = s.candidate.map(rep.score_lo)
        s["report_hi"] = s.candidate.map(rep.score_hi)
        print(f"\n== {name} ({label}), {len(s)} candidates, ranked on SELECT ==")
        print(s.head(10)[["rank", "name", "state", "score", "score_lo", "score_hi", "score_excl_self",
                          "n_locations_switching", "report_gain", "report_lo", "report_hi"]].round(3).to_string(index=False))
        if name == "L_pre":
            print(s[s.candidate.isin([EWR, TTN])][["rank", "name", "score", "score_excl_self", "report_gain"]].round(3).to_string(index=False))
    print("\n== greedy picks ==")
    print(pd.DataFrame(greedy).round(3).to_string(index=False))


def rate_draw(y, ys):
    y = y.reindex(ys).fillna(0)
    return y.wrong.sum() / y.n.sum() if y.n.sum() else np.nan


if __name__ == "__main__":
    main()
