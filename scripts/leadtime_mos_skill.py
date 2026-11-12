"""Task 2: MOS probability of measurable precipitation by lead, paired with the Kalshi-rule outcome.

Writes data/processed/leadtime/mos_pop_{TTN,PHL}.parquet (one row per station, model line, target lead, day) and
results/phase3/leadtime_skill_by_lead.csv (Brier and calibration per lead; climatology's Brier). No network.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.leadtime.mos_archive import MODEL_YEARS  # noqa: E402
from src.leadtime.mos_pop import brier_score, calibration, load_model, pop_table  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
RAIN = REPO / "data" / "processed" / "rain"
OUT_DIR = REPO / "data" / "processed" / "leadtime"
RES = REPO / "results" / "phase3"
STATION = {"TTN": "KTTN", "PHL": "KPHL"}
MAIN_LEADS = (1.5, 2, 3, 4, 5, 6, 7)
P06_LEADS = (1, 1.5, 2, 3)
# (line name, model, pop column, leads)
LINES = [
    ("GFS", "GFS", "pop", MAIN_LEADS),          # p12x2 at 1.5-3 d (MAV reaches 72 h; leads 4-7 come out empty)
    ("GFS-p06x4", "GFS", "pop_p06", P06_LEADS),
    ("AVN", "AVN", "pop", MAIN_LEADS),
    ("AVN-p06x4", "AVN", "pop_p06", P06_LEADS),
    ("MEX", "MEX", "pop", MAIN_LEADS),          # p24 at every lead
    ("MEX-p12x2", "MEX", "pop_p12", MAIN_LEADS),
    ("NBS", "NBS", "pop", MAIN_LEADS),
    ("NBS-p06x4", "NBS", "pop_p06", P06_LEADS),
    ("NBE", "NBE", "pop", MAIN_LEADS),
]


def outcomes(station: str) -> pd.DataFrame:
    d = pd.read_parquet(RAIN / f"daily_{station}.parquet")
    d["date"] = pd.to_datetime(d["date"])
    d = d[d["ghcn_prcp_in"].notna()]
    return pd.DataFrame({"date": d["date"].to_numpy(), "season": d["season"].to_numpy(dtype=int),
                         "month": d["date"].dt.month.to_numpy(), "rain": (d["ghcn_prcp_in"] >= 0.01).astype(int).to_numpy()})


def climatology_brier(obs: pd.DataFrame, seasons: np.ndarray, p_source: pd.DataFrame) -> float:
    """Brier of the monthly rain share of `p_source` days (all seasons of the station outside `seasons` is not
    used; p is the share over ALL station seasons except the one being scored: leave-one-season-out)."""
    o = obs[obs["season"].isin(seasons)]
    vals = []
    for s, g in o.groupby("season"):
        rest = p_source[p_source["season"] != s]
        pm = rest.groupby("month")["rain"].mean()
        p = g["month"].map(pm).fillna(rest["rain"].mean())
        vals.append((p.to_numpy() - g["rain"].to_numpy()) ** 2)
    return float(np.concatenate(vals).mean()) if vals else float("nan")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RES.mkdir(parents=True, exist_ok=True)
    skill_rows, cal_rows = [], []
    for st, icao in STATION.items():
        obs = outcomes(st)
        tables = []
        for line, model, col, leads in LINES:
            mos = load_model(model, icao, list(MODEL_YEARS[model]))
            if mos.empty:
                continue
            t = pop_table(mos, obs["date"], leads, column=col)
            t = t.merge(obs, on="date", how="inner")
            t.insert(0, "line", line)
            t.insert(0, "station", st)
            t["pop_used"] = t[col]
            tables.append(t)
            for L, g in t.groupby("target_lead"):
                if len(g) == 0:
                    continue
                seasons = np.sort(g["season"].unique())
                cb = climatology_brier(obs, seasons, obs)
                skill_rows.append({
                    "station": st, "line": line, "model": model, "pop_field": col if col != "pop" else
                    ("p24" if (g["field"] == "p24").all() else "p12x2"), "target_lead_days": L,
                    "mean_lead_days": float(g["lead_days"].mean()), "n_days": int(len(g)),
                    "n_seasons": int(len(seasons)), "first_season": int(seasons[0]), "last_season": int(seasons[-1]),
                    "mean_pop": float(g["pop_used"].mean()), "rain_share": float(g["rain"].mean()),
                    "brier": brier_score(g["pop_used"], g["rain"]), "brier_climatology_same_days": cb,
                    "skill_vs_climatology": 1.0 - brier_score(g["pop_used"], g["rain"]) / cb if cb else np.nan,
                    "mean_pop_rain_days": float(g.loc[g["rain"] == 1, "pop_used"].mean()),
                    "mean_pop_dry_days": float(g.loc[g["rain"] == 0, "pop_used"].mean()),
                    "label": "observed forecast skill (MOS archive vs station outcome)",
                })
                c = calibration(g["pop_used"], g["rain"])
                c.insert(0, "target_lead_days", L)
                c.insert(0, "line", line)
                c.insert(0, "station", st)
                cal_rows.append(c)
        allt = pd.concat(tables, ignore_index=True)
        allt.to_parquet(OUT_DIR / f"mos_pop_{st}.parquet", index=False)
        # coverage per season for the main lines (for the 90% availability rule)
        cov = (allt.groupby(["line", "target_lead", "season"]).size().rename("n_mos").reset_index()
               .merge(obs.groupby("season").size().rename("n_days").reset_index(), on="season"))
        cov["share"] = cov["n_mos"] / cov["n_days"]
        cov.insert(0, "station", st)
        cov.to_csv(OUT_DIR / f"mos_coverage_{st}.csv", index=False, float_format="%.3f")
    skill = pd.DataFrame(skill_rows)
    skill.to_csv(RES / "leadtime_skill_by_lead.csv", index=False, float_format="%.4f")
    pd.concat(cal_rows, ignore_index=True).to_csv(RES / "leadtime_calibration_by_lead.csv", index=False,
                                                  float_format="%.4f")
    cols = ["station", "line", "pop_field", "target_lead_days", "mean_lead_days", "n_days", "n_seasons", "first_season",
            "last_season", "mean_pop", "rain_share", "brier", "brier_climatology_same_days", "skill_vs_climatology"]
    print(skill[cols].to_string(index=False))


if __name__ == "__main__":
    main()
