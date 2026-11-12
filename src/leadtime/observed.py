"""Observed part of Question 2: Kalshi asks at the four Phase 1 decision times, aggregated.

Reads the raw Phase 1 quote table (data/raw/kalshi/rain/quote_table.csv, git-ignored) and returns aggregates
only. Nothing per market leaves this module.
"""
from __future__ import annotations

import math

import pandas as pd

from ..kalshi.rain_quotes import DECISION_HOURS, brier, taker_fee

CLOSE_TO_LEAD_DAYS = {h: h / 24.0 for h in DECISION_HOURS}   # 36 h before close = 1.5 days of lead


def decision_time_aggregates(q: pd.DataFrame, group_name: str) -> list[dict]:
    """One row per decision time for the rows of `q` (already filtered to a group).

    Columns per row (all aggregates):
      market_days          markets in the group
      with_quote           markets with a fresh or stale quote at that time
      usable_ask_share     share of market days with a fresh ask < 1.00 (buyable)
      rain_days            markets that resolved Yes
      rain_no_offer_share  among rain days with any quote: share with ask = 1.00 (no seller) or stale/no quote
      premium              sum of asks on buyable days (1 contract per day)
      fees                 sum of taker fees on buyable days (one-contract orders)
      payout               sum of results on buyable days
      premium_per_payout   premium / payout;  premium_fee_per_payout = (premium + fees) / payout
      brier_mid            Brier score of the mid price on two-sided days (n_two_sided)
      mean_ask_rain, mean_ask_dry   mean ask on buyable rain days and buyable dry days
    """
    out = []
    for h in DECISION_HOURS:
        buy = q[f"buyable_{h}"].fillna(False).astype(bool)
        two = q[f"two_sided_{h}"].fillna(False).astype(bool)
        ask = q[f"ask_{h}"].astype(float)
        res = q["result"].astype(int)
        rain = res == 1
        has = q[f"has_quote_{h}"].fillna(False).astype(bool)
        ask1 = q[f"ask_is_1_{h}"].fillna(False).astype(bool) & ~q[f"stale_{h}"].fillna(False).astype(bool)
        b = q[buy]
        prem = float(ask[buy].sum())
        fees = float(sum(taker_fee(a, 1) for a in ask[buy]))
        pay = float(res[buy].sum())
        mids = q.loc[two, f"mid_{h}"].astype(float).tolist()
        row = {
            "group": group_name, "hours_before_close": h, "lead_days": round(CLOSE_TO_LEAD_DAYS[h], 4),
            "market_days": int(len(q)), "with_quote": int(has.sum()), "bought": int(buy.sum()),
            "usable_ask_share": float(buy.mean()) if len(q) else math.nan,
            "rain_days": int(rain.sum()),
            "rain_days_no_offer": int((rain & ~buy).sum()),
            "rain_no_offer_share": float((rain & ~buy).sum() / rain.sum()) if rain.sum() else math.nan,
            "rain_days_ask_is_1": int((rain & ask1).sum()),
            "premium": round(prem, 2), "fees": round(fees, 2), "payout": pay,
            "premium_per_payout": prem / pay if pay else math.nan,
            "premium_fee_per_payout": (prem + fees) / pay if pay else math.nan,
            "net_per_contract": (pay - prem - fees) / len(b) if len(b) else math.nan,
            "n_two_sided": int(two.sum()),
            "brier_mid": brier(mids, res[two].tolist()) if two.sum() else math.nan,
            "share_yes_two_sided": float(res[two].mean()) if two.sum() else math.nan,
            "mean_mid_two_sided": float(sum(mids) / len(mids)) if mids else math.nan,
            "mean_ask_rain": float(ask[buy & rain].mean()) if (buy & rain).sum() else math.nan,
            "mean_ask_dry": float(ask[buy & ~rain].mean()) if (buy & ~rain).sum() else math.nan,
            "n_ask_rain": int((buy & rain).sum()), "n_ask_dry": int((buy & ~rain).sum()),
            "label": "observed",
        }
        out.append(row)
    return out


def observed_table(q: pd.DataFrame) -> pd.DataFrame:
    """Pooled over the four cities (every series and year), NYC alone, and the 2026 four-city KXRAIN overlap."""
    rows = decision_time_aggregates(q, "four cities, all years")
    rows += decision_time_aggregates(q[q["city"] == "NYC"], "NYC alone, all years")
    rows += decision_time_aggregates(q[(q["series"] == "KXRAIN") & (q["year"] == 2026)], "four cities, KXRAIN 2026")
    rows += decision_time_aggregates(q[(q["year"] >= 2025)], "four cities, 2025-2026")
    return pd.DataFrame(rows)
